"""Exercise hidden-input confirmation gates without a key, network or AWS calls."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "gemini_key_helper", Path(__file__).parents[1] / "scripts/gemini_key.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.fixture
def terminal(monkeypatch, capsys):
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py"])
    monkeypatch.setattr(helper.logging, "disable", lambda *_: None)
    import resource

    monkeypatch.setattr(resource, "setrlimit", lambda *_: None)
    monkeypatch.setattr(helper.getpass, "getpass", lambda _: "secret-test-sentinel")
    monkeypatch.setattr(helper, "store_secret", lambda *_: pytest.fail("AWS write"))
    monkeypatch.setattr(helper.settings, "PARSER_MODEL", helper.MODEL)
    monkeypatch.setattr(helper.settings, "parser_prompt_version", helper.PROMPT_VERSION)

    def enter():
        # pytest replaces capture streams between fixture setup and test execution.
        monkeypatch.setattr(helper.sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(helper.sys.stderr, "isatty", lambda: True)

    return enter


def test_no_tty_fails_before_reading_key(monkeypatch, capsys):
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py"])
    monkeypatch.setattr(helper.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(helper.logging, "disable", lambda *_: None)
    monkeypatch.setattr(helper.getpass, "getpass", lambda _: pytest.fail("key read"))
    assert helper.main() == 1
    assert "requires a TTY" in capsys.readouterr().out


def test_cancel_discards_key_without_any_request(terminal, monkeypatch, capsys):
    terminal()
    monkeypatch.setattr("builtins.input", lambda _: "")
    monkeypatch.setattr(helper, "parse_agenda", lambda *a, **kw: pytest.fail("model request"))
    assert helper.main() == 0
    assert "secret-test-sentinel" not in capsys.readouterr().out


def test_explicit_confirmation_requests_one_attempt_only(terminal, monkeypatch, capsys):
    terminal()
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    parse = Mock(return_value=(SimpleNamespace(items=[]), {"input_tokens": 7, "output_tokens": 5}))
    monkeypatch.setattr(helper, "parse_agenda", parse)
    assert helper.main() == 0
    parse.assert_called_once()
    assert parse.call_args.kwargs["max_attempts"] == 1
    assert parse.call_args.kwargs["max_output_tokens"] == 512
    assert "secret-test-sentinel" not in capsys.readouterr().out


def test_failure_never_prints_upstream_message(terminal, monkeypatch, capsys):
    terminal()
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    monkeypatch.setattr(helper, "parse_agenda", Mock(side_effect=RuntimeError("secret-test-sentinel")))
    assert helper.main() == 1
    assert "secret-test-sentinel" not in capsys.readouterr().out


def test_store_requires_different_explicit_approval(terminal, monkeypatch):
    terminal()
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", "--store-secret"])
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    assert helper.main() == 0  # Test approval never authorizes a secret write.


def test_key_argument_is_never_echoed(monkeypatch, capsys):
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", "private-accidental-key"])
    with pytest.raises(SystemExit):
        helper.main()
    output = capsys.readouterr()
    assert "private-accidental-key" not in output.err + output.out


def test_store_checks_account_before_accessing_secret(monkeypatch):
    import boto3

    sts = Mock()
    sts.get_caller_identity.return_value = {"Account": "968053399627"}
    session = Mock()
    session.client.return_value = sts
    monkeypatch.setattr(boto3, "Session", Mock(return_value=session))
    with pytest.raises(ValueError, match="Wrong AWS account"):
        helper.store_secret("private-test-key")
    assert [c.args[0] for c in session.client.call_args_list] == ["sts"]


def test_store_uses_in_memory_sdk_value_not_files_or_cli(monkeypatch, capsys):
    import boto3
    from botocore.exceptions import ClientError

    sts, secret = Mock(), Mock()
    sts.get_caller_identity.return_value = {"Account": "891447916595"}
    secret.describe_secret.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException"}}, "DescribeSecret"
    )
    arn = "arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-ABC123"
    secret.create_secret.return_value = {"ARN": arn}
    session = Mock()
    session.client.side_effect = lambda name, **kw: sts if name == "sts" else secret
    factory = Mock(return_value=session)
    monkeypatch.setattr(boto3, "Session", factory)
    helper.store_secret("private-test-key")
    factory.assert_called_once_with(profile_name="spry-friend", region_name="us-east-1")
    assert "private-test-key" in secret.create_secret.call_args.kwargs["SecretString"]
    assert "private-test-key" not in capsys.readouterr().out


def test_list_models_requires_own_confirmation_and_never_generates(terminal, monkeypatch, capsys):
    terminal()
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", "--list-models"])
    monkeypatch.setattr("builtins.input", lambda _: "LIST GEMINI MODELS")
    client = Mock()
    client.list_models.return_value = [
        {"name": "models/example", "supportedGenerationMethods": ["generateContent"]}
    ]
    monkeypatch.setattr(helper, "GeminiClient", lambda _: client)
    monkeypatch.setattr(helper, "parse_agenda", lambda *a, **kw: pytest.fail("generation called"))
    assert helper.main() == 0
    client.list_models.assert_called_once()
    output = capsys.readouterr().out
    assert "models/example" in output and "secret-test-sentinel" not in output


def test_generation_confirmation_does_not_authorize_model_listing(terminal, monkeypatch):
    terminal()
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", "--list-models"])
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    monkeypatch.setattr(helper, "GeminiClient", lambda _: pytest.fail("network client created"))
    assert helper.main() == 0


def test_helper_reports_google_error_details_without_sensitive_values(terminal, monkeypatch, capsys):
    import json

    from app.ai.agenda import sanitized_google_error

    terminal()
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    diagnostics = sanitized_google_error(
        json.dumps(
            {
                "error": {
                    "code": 404,
                    "status": "NOT_FOUND",
                    "message": "Model is not found for API version v1beta; "
                    "secret-test-sentinel Confidential agenda",
                }
            }
        ).encode()
    )
    monkeypatch.setattr(helper, "parse_agenda", Mock(side_effect=helper.GeminiAPIError(404, diagnostics)))
    assert helper.main() == 1
    output = capsys.readouterr().out
    record = json.loads(output.strip().splitlines()[-1])
    assert record["http_status"] == record["error_code"] == 404
    assert record["error_status"] == "NOT_FOUND" and record["message_redacted"]
    assert record["automatic_retry"] is False
    assert "secret-test-sentinel" not in output and "Confidential agenda" not in output


@pytest.mark.parametrize("model", ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"])
def test_model_override_is_only_for_explicit_single_probe(terminal, monkeypatch, capsys, model):
    terminal()
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", "--model", model])
    monkeypatch.setattr("builtins.input", lambda _: "TEST GEMINI ONCE")
    factory = Mock()
    monkeypatch.setattr(helper, "GeminiClient", factory)
    parse = Mock(return_value=(SimpleNamespace(items=[]), {"input_tokens": 7, "output_tokens": 5}))
    monkeypatch.setattr(helper, "parse_agenda", parse)
    assert helper.main() == 0
    factory.assert_called_once_with("secret-test-sentinel", model=model)
    assert parse.call_args.kwargs["max_attempts"] == 1
    assert parse.call_args.kwargs["max_output_tokens"] == 512
    output = capsys.readouterr().out
    assert model in output and "secret-test-sentinel" not in output
    assert helper.MODEL == helper.settings.PARSER_MODEL == "gemini-3.5-flash-lite"


@pytest.mark.parametrize(
    "extra",
    [
        ["--model", "unknown"],
        ["--list-models", "--model", "gemini-3.1-flash-lite"],
        ["--store-secret", "--model", "gemini-3.5-flash-lite"],
    ],
)
def test_probe_override_invalid_modes_fail_before_key_entry(monkeypatch, extra):
    monkeypatch.setattr(helper.sys, "argv", ["gemini_key.py", *extra])
    monkeypatch.setattr(helper.getpass, "getpass", lambda _: pytest.fail("Key read"))
    with pytest.raises(SystemExit):
        helper.main()


def test_store_stops_before_write_on_unreviewed_kms_key(monkeypatch):
    import boto3

    sts, secret = Mock(), Mock()
    sts.get_caller_identity.return_value = {"Account": "891447916595"}
    secret.describe_secret.return_value = {
        "ARN": "arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-ABC123",
        "Tags": [{"Key": "PROJECT_NAME", "Value": "meetings"}],
        "KmsKeyId": "unreviewed-explicit-key",
    }
    session = Mock()
    session.client.side_effect = lambda name, **kw: sts if name == "sts" else secret
    monkeypatch.setattr(boto3, "Session", Mock(return_value=session))
    with pytest.raises(ValueError, match="KMS configuration requires review"):
        helper.store_secret("private-test-key")
    secret.put_secret_value.assert_not_called()
    secret.create_secret.assert_not_called()
