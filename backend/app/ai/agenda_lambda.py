"""agenda-parser Lambda (outside the VPC): pasted text in, SUGGESTED agenda out.

It never touches the database and never writes anything. Saving goes through the normal API.
Image command: app.ai.agenda_lambda.handler

PARSER_MOCK=1 returns a fixed sample agenda WITHOUT calling any model. It exists only to test
the Lambda, auth, CORS and the screen while model access is pending; the response and the log
line say model="mock", so it can never be mistaken for a real parse.
"""
import base64
import json
import logging
import os
import time
from datetime import date

from fastapi import HTTPException

from app.ai.agenda import (PROMPT_VERSION, ActionItem, AgendaItem, AgendaParseError,
                           ParsedAgenda, model_id, parse_agenda, provider)
from app.auth import verify_id_token
from app.config import settings

log = logging.getLogger()
log.setLevel(logging.INFO)

MAX_CHARS = 10_000

# USD per 1M tokens (input, output). Check the Bedrock pricing page: the bill is what counts.
PRICES = {
    "opus-5-5": (4.00, 20.00),
    "sonnet-5-5": (2.00, 10.00),
    "haiku-5-5": (0.10, 0.50),
    "nova-micro": (0.035, 0.14),
    "nova-lite": (0.06, 0.24),
    "nova-pro": (0.80, 3.20),
}


def cost_usd(model: str, usage: dict) -> float | None:
    for key, (price_in, price_out) in PRICES.items():
        if key in model:
            return round((usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1_000_000, 6)
    return None


def _resp(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def _mock_agenda() -> ParsedAgenda:
    return ParsedAgenda(
        title="Pricing sync (MOCK)", language="uk", duration_minutes=45,
        items=[AgendaItem(topic="Нові тарифи Pro", owner="Олена", minutes=15),
               AgendaItem(topic="Фідбек від клієнтів", owner="Taras"),
               AgendaItem(topic="Що робимо з річною знижкою")],
        action_items=[ActionItem(task="Зібрати порівняння з конкурентами", owner="Taras")],
    )


def handler(event, context):
    # 1. Authentication: every call costs money.
    if not settings.auth_enabled:
        return _resp(500, {"error": "auth_not_configured"})
    token = (event.get("headers") or {}).get("authorization", "")
    token = token[7:] if token.lower().startswith("bearer ") else token
    try:
        user = verify_id_token(token.strip())
    except HTTPException:
        return _resp(401, {"error": "unauthorized"})
    except Exception:  # e.g. the signing keys could not be loaded
        log.exception("token verification failed")
        return _resp(500, {"error": "auth_error"})

    # 2. Input and limits.
    try:
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        body = json.loads(raw)
        text, today, tz = body["text"], date.fromisoformat(body["today"]), str(body["tz"])
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty text")
    except (KeyError, ValueError, TypeError):
        return _resp(400, {"error": "bad_request",
                           "detail": 'expected JSON {"text": "...", "today": "YYYY-MM-DD", "tz": "Europe/Kyiv"}'})
    if len(text) > MAX_CHARS:
        return _resp(413, {"error": "text_too_long", "max_chars": MAX_CHARS})

    # 3. Parse (or the clearly labelled mock).
    mock = os.environ.get("PARSER_MOCK") == "1"
    model = "mock" if mock else model_id()
    started = time.monotonic()
    try:
        if mock:
            agenda, usage = _mock_agenda(), {"input_tokens": 0, "output_tokens": 0}
        else:
            agenda, usage = parse_agenda(text, today, tz)
    except AgendaParseError as e:
        return _resp(422, {"error": str(e)})
    except Exception as e:  # throttling, access denied, network ...
        busy = "Throttl" in type(e).__name__ or "RateLimit" in type(e).__name__ \
            or getattr(e, "status_code", None) == 429
        log.exception("model call failed")
        return _resp(429 if busy else 502, {"error": "busy" if busy else "model_error"})

    # 4. One JSON log line per parse (item 4 of the submission).
    log.info(json.dumps({
        "event": "agenda_parsed", "user": user.sub, "provider": "mock" if mock else provider(),
        "model": model, "prompt_version": PROMPT_VERSION, **usage,
        "latency_ms": int((time.monotonic() - started) * 1000), "cost_usd": cost_usd(model, usage),
    }, ensure_ascii=False))
    out = {"agenda": agenda.model_dump(mode="json"), "model": model, "prompt_version": PROMPT_VERSION}
    if mock:
        out["mock"] = True
    return _resp(200, out)
