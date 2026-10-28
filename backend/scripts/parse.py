import sys
from datetime import date

from app.ai.agenda import parse_agenda

agenda, usage = parse_agenda(sys.argv[1], date.today(), "Europe/Kyiv")
print(agenda.model_dump_json(indent=2))
print(usage)