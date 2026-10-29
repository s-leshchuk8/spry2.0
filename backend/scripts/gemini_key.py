"""User-run hidden key prompt. No key argument, environment variable, local file or debug logs.

Default mode makes NO network request until the user types TEST GEMINI ONCE after key entry.
--list-models lists metadata only after its own confirmation; it never runs inference.
--store-secret is a separately approved future AWS write, never performed by test mode.
"""

import argparse
import getpass
import json
import logging
import os
import sys
import warnings
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.agenda import (  # noqa: E402
    MODEL,
    PROMPT_VERSION,
    TEST_MODELS,
    AgendaParseError,
    GeminiAPIError,
    GeminiClient,
    parse_agenda,
    validate_key,
)
from app.config import settings  # noqa: E402

SECRET_NAME = "meetings/gemini-api-key"


def store_secret(key):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    if any(k.startswith("AWS_ENDPOINT_URL") and value for k, value in os.environ.items()) or any(
        os.environ.get(k)
        for k in [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_SECURITY_TOKEN",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_ROLE_ARN",
            "AWS_CONFIG_FILE",
            "AWS_SHARED_CREDENTIALS_FILE",
            "AWS_ENDPOINT_URL",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        ]
    ):
        raise ValueError("Credential overrides are not permitted")
    session = boto3.Session(profile_name="spry-friend", region_name="us-east-1")
    config = Config(connect_timeout=3, read_timeout=5, retries={"total_max_attempts": 1})
    if session.client("sts", config=config).get_caller_identity()["Account"] != "891447916595":
        raise ValueError("Wrong AWS account")
    client = session.client("secretsmanager", config=config)
    payload = json.dumps({"api_key": key})
    try:
        existing = client.describe_secret(SecretId=SECRET_NAME)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise ValueError("Secret inspection failed") from None
        result = client.create_secret(
            Name=SECRET_NAME,
            SecretString=payload,
            Tags=[{"Key": "PROJECT_NAME", "Value": "meetings"}],
        )
    else:
        if (
            not existing["ARN"].startswith(
                "arn:aws:secretsmanager:us-east-1:891447916595:secret:meetings/gemini-api-key-"
            )
            or {t["Key"]: t["Value"] for t in existing.get("Tags", [])}.get("PROJECT_NAME") != "meetings"
        ):
            raise ValueError("Unexpected secret ownership")
        if existing.get("KmsKeyId") not in (None, "alias/aws/secretsmanager"):
            raise ValueError("Explicit KMS configuration requires review before updating the secret")
        result = client.put_secret_value(SecretId=existing["ARN"], SecretString=payload)
    print("Stored in Secrets Manager. ARN:", result["ARN"])  # ARN only, never value.


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Unsupported arguments. Never pass an API key as an argument.\n")


def main():
    parser = SafeParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--store-secret", action="store_true", help="Requires separate AWS-write approval")
    mode.add_argument(
        "--list-models", action="store_true", help="Read model IDs/methods only; no inference or AWS"
    )
    parser.add_argument("--model", choices=TEST_MODELS, help="Override only this single generation probe")
    args = parser.parse_args()
    if args.model and (args.store_secret or args.list_models):
        parser.error("--model applies only to the single generation probe")
    selected_model = args.model or MODEL
    logging.disable(logging.CRITICAL)
    # Fail closed instead of getpass falling back to echoed stdin (pipes, notebooks, tool consoles).
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print("Run directly in your private local terminal; key input requires a TTY.")
        return 1
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Gemini API key (hidden; memory only): ")
        validate_key(key)
        if args.store_secret:
            phrase = "STORE SECRET IN 891447916595"
            print("AWS WRITE: create/update only meetings/gemini-api-key in spry-friend/us-east-1.")
        elif args.list_models:
            phrase = "LIST GEMINI MODELS"
            print("Read-only model metadata only; no generation, no AWS, no automatic retries.")
        else:
            phrase = "TEST GEMINI ONCE"
            print("Test model:", selected_model)
            print("No request has been sent. This mode never contacts AWS or stores your key.")
            print("One synthetic-agenda request; no retries. Type the phrase only when you approve the test.")
        if input(f"Type {phrase} to approve, or Enter to discard: ") != phrase:
            print("Cancelled. No request made; key not saved.")
            return 0
        if args.store_secret:
            store_secret(key)
        elif args.list_models:
            print(json.dumps(GeminiClient(key).list_models()))
        else:
            settings.PARSER_MODEL = MODEL
            settings.parser_prompt_version = PROMPT_VERSION
            agenda, usage = parse_agenda(
                "Team planning, 30 minutes. Agenda: review milestones, owner Alex, 10 minutes.",
                date.today(),
                "UTC",
                client=GeminiClient(key, model=selected_model),
                max_attempts=1,
                max_output_tokens=512,
            )
            print(
                json.dumps(
                    {"status": "validated", "model": selected_model, "items": len(agenda.items), **usage}
                )
            )
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Cancelled; key not saved locally.")
        return 1
    except GeminiAPIError as exc:
        print(
            json.dumps(
                {
                    "status": "api_error",
                    "http_status": exc.status_code,
                    **exc.google_error,
                    "automatic_retry": False,
                }
            )
        )
        return 1
    except AgendaParseError:
        print(json.dumps({"status": "invalid_response", "automatic_retry": False}))
        return 1
    except Exception:
        # Never print exception messages, request objects, headers, secret payloads or tracebacks.
        print("Operation failed. No secret details displayed; no automatic retry.")
        return 1
    finally:
        key = None  # Release the reference; Python does not guarantee zeroing process memory.


if __name__ == "__main__":
    raise SystemExit(main())
