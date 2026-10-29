import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ai.agenda import parse_agenda

tz = os.environ.get("PARSER_TIMEZONE", "Europe/Kyiv")
agenda, usage = parse_agenda(sys.argv[1], datetime.now(ZoneInfo(tz)).date(), tz)
print(agenda.model_dump_json(indent=2))
print(usage)
