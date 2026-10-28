"""Offline checks of the parser's validation + retry logic. No AWS calls.

Run:  cd backend && uv run python scripts/test_agenda_offline.py
"""
import json
from datetime import date
from types import SimpleNamespace as NS

from app.ai.agenda import RECORD_AGENDA, AgendaParseError, ConverseAdapter, parse_agenda
from app.ai.schema import inline_refs

TODAY = date(2026, 10, 12)
GOOD = {"title": "Pricing sync", "language": "uk",
        "items": [{"topic": "Нові тарифи Pro", "owner": "Олена", "minutes": 15}]}
BAD = {"language": "uk", "items": [{"topic": "x", "minutes": 0}]}  # minutes must be >= 1


# ---- fake Anthropic client -------------------------------------------------
def tool(data, id="t1"):
    return NS(type="tool_use", id=id, input=data)


def reply(*blocks, stop="tool_use"):
    return NS(content=list(blocks), stop_reason=stop, usage=NS(input_tokens=100, output_tokens=50))


class Fake:
    """Stands in for the Anthropic client: client.messages.create(...)"""

    def __init__(self, *replies):
        self.replies, self.calls, self.messages = list(replies), 0, self

    def create(self, **kwargs):
        self.calls += 1
        return self.replies.pop(0)


# 1. valid answer: one call
fake = Fake(reply(tool(GOOD)))
agenda, usage = parse_agenda("text", TODAY, "Europe/Kyiv", client=fake)
assert agenda.items[0].owner == "Олена" and fake.calls == 1 and usage["input_tokens"] == 100

# 2. invalid first, valid second: exactly one retry, usage is summed
fake = Fake(reply(tool(BAD)), reply(tool(GOOD)))
agenda, usage = parse_agenda("text", TODAY, "Europe/Kyiv", client=fake)
assert fake.calls == 2 and usage == {"input_tokens": 200, "output_tokens": 100}

# 3. invalid twice: a clear error, never an invalid agenda
try:
    parse_agenda("text", TODAY, "Europe/Kyiv", client=Fake(reply(tool(BAD)), reply(tool(BAD))))
    raise SystemExit("FAIL: should have raised")
except AgendaParseError:
    pass

# 4. no tool call (e.g. a refusal): a clear error
try:
    parse_agenda("text", TODAY, "Europe/Kyiv", client=Fake(reply(NS(type="text", text="no"), stop="refusal")))
    raise SystemExit("FAIL: should have raised")
except AgendaParseError:
    pass


# ---- fake Bedrock Converse client ------------------------------------------
def cresp(data=None):
    content = [{"toolUse": {"toolUseId": "c1", "name": "record_agenda", "input": data}}] if data else [{"text": "no"}]
    return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "tool_use" if data else "end_turn",
            "usage": {"inputTokens": 80, "outputTokens": 40}}


class FakeRuntime:
    def __init__(self, *responses):
        self.responses, self.calls, self.last = list(responses), 0, None

    def converse(self, **kwargs):
        self.calls += 1
        self.last = kwargs
        return self.responses.pop(0)


# 5. Converse: valid answer
rt = FakeRuntime(cresp(GOOD))
agenda, usage = parse_agenda("text", TODAY, "Europe/Kyiv", adapter=ConverseAdapter(rt))
assert agenda.title == "Pricing sync" and rt.calls == 1 and usage == {"input_tokens": 80, "output_tokens": 40}

# 6. Converse: invalid first, then valid; the retry carries a toolResult with status=error
rt = FakeRuntime(cresp(BAD), cresp(GOOD))
parse_agenda("text", TODAY, "Europe/Kyiv", adapter=ConverseAdapter(rt))
assert rt.calls == 2 and rt.last["messages"][-1]["content"][0]["toolResult"]["status"] == "error"

# 7. Converse: plain text instead of a tool call -> clear error
try:
    parse_agenda("text", TODAY, "Europe/Kyiv", adapter=ConverseAdapter(FakeRuntime(cresp())))
    raise SystemExit("FAIL: should have raised")
except AgendaParseError:
    pass

# 8. the schema sent to Converse has no $ref/$defs/anyOf, and keeps the field called "title"
simple = inline_refs(RECORD_AGENDA["input_schema"])
text = json.dumps(simple)
assert "$ref" not in text and "$defs" not in text and "anyOf" not in text
assert "title" in simple["properties"] and "topic" in simple["properties"]["items"]["items"]["properties"]

print("OK: 8 offline checks passed")
