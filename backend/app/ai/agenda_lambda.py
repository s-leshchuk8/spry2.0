"""Public Function URL handler: authenticate, parse, return a suggestion; never save."""

import base64
import json
import logging
import time
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from app.ai.agenda import PROMPT_VERSION, AgendaParseError, cost_usd, parse_agenda
from app.ai.contracts import AgendaItem, ParsedAgenda
from app.auth import verify_id_token
from app.config import settings

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
MAX_CHARS = 10_000


def response(status: int, error: str, detail: str | None = None):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"error": error, "detail": detail or error}),
    }


def handler(event, context):
    # URL-level CORS handles preflight. Application rejects every non-POST request.
    if event.get("requestContext", {}).get("http", {}).get("method") != "POST":
        return response(405, "method_not_allowed")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if not settings.auth_enabled or not auth.lower().startswith("bearer "):
        return response(401, "unauthorized", "Sign in to parse an agenda")
    try:
        user = verify_id_token(auth[7:].strip())
    except HTTPException:
        return response(401, "unauthorized", "Your session has expired; sign in again")
    except Exception:
        return response(503, "auth_unavailable", "Authentication is temporarily unavailable")
    try:
        raw = event.get("body") or ""
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError
        text, day, tz = body["text"], body["today"], body["tz"]
        if not all(isinstance(v, str) for v in (text, day, tz)) or not text.strip():
            raise ValueError
        if len(text) > MAX_CHARS:
            return response(413, "text_too_long", "Paste at most 10,000 characters")
        today = date.fromisoformat(day)
        if today.isoformat() != day:
            raise ValueError
        ZoneInfo(tz)
    except (KeyError, ValueError, TypeError, UnicodeError, ZoneInfoNotFoundError):
        return response(400, "bad_request", "Expected text, YYYY-MM-DD today, and an IANA timezone")

    model = "mock" if settings.parser_mock else settings.PARSER_MODEL
    started = time.monotonic()
    usage = {"input_tokens": 0, "output_tokens": 0}
    outcome = "success"
    try:
        if settings.parser_mock:
            agenda = ParsedAgenda(
                title="LOCAL MOCK — review manually",
                language="en",
                items=[AgendaItem(topic="MOCK sample topic")],
            )
        else:
            agenda, usage = parse_agenda(text, today, tz)
        result = {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps(
                {
                    "agenda": agenda.model_dump(mode="json"),
                    "model": model,
                    "prompt_version": PROMPT_VERSION,
                    **({"mock": True} if settings.parser_mock else {}),
                },
                ensure_ascii=False,
            ),
        }
    except AgendaParseError as exc:
        usage, outcome = exc.usage, "invalid_agenda"
        result = response(422, outcome, "Could not find a valid agenda. Edit the text or enter it manually")
    except Exception as exc:
        usage = getattr(exc, "agenda_usage", usage)
        provider = getattr(exc, "response", {})
        provider_code = provider.get("Error", {}).get("Code", "")
        status = provider.get("ResponseMetadata", {}).get("HTTPStatusCode", getattr(exc, "status_code", None))
        if status == 429 or provider_code in ("ThrottlingException", "TooManyRequestsException"):
            outcome, code = "busy", 429
        elif (
            status in (408, 500, 502, 503, 504)
            or provider_code
            in ("ServiceUnavailableException", "InternalServerException", "ModelTimeoutException")
            or "Timeout" in type(exc).__name__
            or "Connection" in type(exc).__name__
        ):
            outcome, code = "unavailable", 503
        elif provider_code == "AccessDeniedException" or status == 403:
            outcome, code = "model_access_denied", 502
        else:
            outcome, code = "model_error", 502
        result = response(
            code, outcome, "Parsing service is unavailable. Try again or enter the agenda manually"
        )
    finally:
        try:
            cost = 0.0 if settings.parser_mock else cost_usd(model, usage)
        except KeyError:
            cost = None
        log.info(
            json.dumps(
                {
                    "event": "agenda_parsed",
                    "user": user.sub,
                    "model": model,
                    "prompt_version": PROMPT_VERSION,
                    **usage,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "cost_usd": cost,
                    "billing_tier": settings.parser_billing_tier,
                    "outcome": outcome,
                }
            )
        )
    return result
