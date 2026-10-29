import json
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException

from app.ai import agenda_lambda as module
from app.ai.agenda import AgendaParseError, ParsedAgenda
from app.config import settings


@pytest.fixture(autouse=True)
def mocks(monkeypatch):
    monkeypatch.setattr(settings, "PARSER_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setattr(settings, "parser_prompt_version", "agenda-v2-gemini")
    monkeypatch.setattr(settings, "parser_mock", False)
    monkeypatch.setattr(settings, "parser_billing_tier", "paid")
    monkeypatch.setattr(settings, "cognito_user_pool_id", "test")
    monkeypatch.setattr(module, "verify_id_token", lambda token: NS(sub="user"))
    monkeypatch.setattr(
        module,
        "parse_agenda",
        lambda *args: (ParsedAgenda(language="uk", items=[]), {"input_tokens": 100, "output_tokens": 50}),
    )


def event(**body):
    return {
        "requestContext": {"http": {"method": "POST"}},
        "headers": {"authorization": "Bearer private-token"},
        "body": json.dumps({"text": "private agenda", "today": "2026-10-12", "tz": "Europe/Kyiv", **body}),
    }


def test_success_log_is_private(caplog):
    assert module.handler(event(), None)["statusCode"] == 200
    records = [json.loads(r.message) for r in caplog.records if r.name == module.__name__]
    assert len(records) == 1
    assert records[0]["input_tokens"] == 100 and records[0]["cost_usd"] > 0
    assert "private agenda" not in caplog.text and "private-token" not in caplog.text


def test_unauthenticated_never_calls_model(monkeypatch):
    monkeypatch.setattr(module, "verify_id_token", lambda _: (_ for _ in ()).throw(HTTPException(401)))
    monkeypatch.setattr(module, "parse_agenda", lambda *_: pytest.fail("model called"))
    assert module.handler(event(), None)["statusCode"] == 401
    request = event()
    request["headers"] = {}
    assert module.handler(request, None)["statusCode"] == 401


@pytest.mark.parametrize(
    "body,status",
    [
        ({"text": "x" * 10001}, 413),
        ({"text": " "}, 400),
        ({"today": "not-a-date"}, 400),
        ({"tz": "bad/zone"}, 400),
        ({"text": 123}, 400),
    ],
)
def test_invalid_input(body, status, monkeypatch):
    monkeypatch.setattr(module, "parse_agenda", lambda *_: pytest.fail("model called"))
    assert module.handler(event(**body), None)["statusCode"] == status


@pytest.mark.parametrize("raw", ["[]", "null", "bad json"])
def test_invalid_json(raw):
    request = event()
    request["body"] = raw
    assert module.handler(request, None)["statusCode"] == 400


@pytest.mark.parametrize("status,expected", [(429, 429), (503, 503), (403, 502)])
def test_model_errors(status, expected, monkeypatch):
    def fail(*args):
        error = RuntimeError("sensitive provider response")
        error.status_code = status
        raise error

    monkeypatch.setattr(module, "parse_agenda", fail)
    result = module.handler(event(), None)
    assert result["statusCode"] == expected and "sensitive" not in result["body"]


def test_invalid_agenda_usage(monkeypatch, caplog):
    def fail(*args):
        raise AgendaParseError("invalid", {"input_tokens": 200, "output_tokens": 100})

    monkeypatch.setattr(module, "parse_agenda", fail)
    assert module.handler(event(), None)["statusCode"] == 422
    assert '"input_tokens": 200' in caplog.text


def test_method_and_base64():
    import base64

    request = event()
    request["requestContext"]["http"]["method"] = "GET"
    assert module.handler(request, None)["statusCode"] == 405
    request = event()
    request["body"] = base64.b64encode(request["body"].encode()).decode()
    request["isBase64Encoded"] = True
    assert module.handler(request, None)["statusCode"] == 200


@pytest.mark.parametrize(
    "provider_code,http_status,expected,outcome",
    [
        ("ThrottlingException", 429, 429, "busy"),
        ("AccessDeniedException", 403, 502, "model_access_denied"),
        ("ServiceUnavailableException", 503, 503, "unavailable"),
        ("ModelTimeoutException", 408, 503, "unavailable"),
    ],
)
def test_botocore_errors(provider_code, http_status, expected, outcome, monkeypatch, caplog):
    from botocore.exceptions import ClientError

    def fail(*args):
        error = ClientError(
            {
                "Error": {"Code": provider_code, "Message": "private provider payload"},
                "ResponseMetadata": {"HTTPStatusCode": http_status},
            },
            "Converse",
        )
        error.agenda_usage = {"input_tokens": 200, "output_tokens": 100}
        raise error

    monkeypatch.setattr(module, "parse_agenda", fail)
    result = module.handler(event(), None)
    assert result["statusCode"] == expected
    assert json.loads(result["body"])["error"] == outcome
    record = next(json.loads(r.message) for r in caplog.records if r.name == module.__name__)
    assert record["input_tokens"] == 200 and record["cost_usd"] > 0
    assert "private provider payload" not in caplog.text and "private provider payload" not in result["body"]


def test_local_mock_is_labelled_and_never_calls_bedrock(monkeypatch, caplog):
    monkeypatch.setattr(settings, "parser_mock", True)
    monkeypatch.setattr(module, "parse_agenda", lambda *_: pytest.fail("model called"))
    response = module.handler(event(), None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200 and body["mock"] is True and body["model"] == "mock"
    assert "MOCK" in body["agenda"]["title"]
    record = next(json.loads(r.message) for r in caplog.records if r.name == module.__name__)
    assert record["model"] == "mock" and record["cost_usd"] == 0
    assert record["input_tokens"] == record["output_tokens"] == 0
    request = event()
    request["headers"] = {}
    assert module.handler(request, None)["statusCode"] == 401


def test_gemini_throttle_before_generation_is_429_without_retry(monkeypatch, caplog):
    from unittest.mock import Mock

    from app.ai import agenda

    client = Mock()
    client.generate.side_effect = agenda.GeminiAPIError(429)
    monkeypatch.setattr(agenda, "_secret_key", lambda _: "test-key")
    monkeypatch.setattr(agenda, "GeminiClient", lambda _: client)
    monkeypatch.setattr(module, "parse_agenda", agenda.parse_agenda)
    result = module.handler(event(), None)
    assert result["statusCode"] == 429
    assert json.loads(result["body"])["error"] == "busy"
    client.generate.assert_called_once()
    record = next(json.loads(r.message) for r in caplog.records if r.name == module.__name__)
    assert record["outcome"] == "busy" and record["input_tokens"] == record["output_tokens"] == 0
    assert "test-key" not in caplog.text + result["body"]
