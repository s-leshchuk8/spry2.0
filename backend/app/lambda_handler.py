"""AWS Lambda entry point: HTTP requests from the function URL, plus a `migrate` action.

`make aws-backend-migrate` invokes the function directly with {"action": "migrate"} to apply
Alembic migrations and seed data; function URL events never carry a top-level "action".
"""

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from mangum import Mangum

from app import seed
from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

http_handler = Mangum(app, lifespan="off")


def migrate() -> dict[str, str]:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    command.upgrade(config, "head")
    seed.main()
    return {"status": "migrated"}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("action") == "migrate":
        return migrate()
    return http_handler(event, context)
