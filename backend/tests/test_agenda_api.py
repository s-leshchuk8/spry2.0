import pytest

from tests.test_api import meeting_payload
from tests.test_auth import bearer, cognito, token  # noqa: F401

FINAL = {
    "title": "Corrected",
    "language": "uk",
    "items": [
        {"topic": "Pricing", "owner": "Олена", "minutes": 15},
        {"topic": "Customer feedback", "owner": "Taras", "minutes": None},
        {"topic": "Annual discount", "owner": None, "minutes": None},
    ],
    "action_items": [{"task": "Compare prices", "owner": "Taras", "due": "2026-10-16"}],
}


@pytest.mark.parametrize(
    "model,prompt_version",
    [
        ("anthropic.claude-opus-5-5", "agenda-v1"),
        ("us.amazon.nova-micro-v1:0", "agenda-v1"),
        ("gemini-2.5-flash-lite", "agenda-v2-gemini"),
        ("gemini-3.5-flash-lite", "agenda-v2-gemini"),
    ],
)
def test_agenda_save_preserves_suggestion_and_owner(client, model, prompt_version):
    anna, other = bearer(token()), bearer(token(sub="other", email="other@example.com"))
    meeting = client.post("/api/meetings", json=meeting_payload(), headers=anna).json()
    path = f"/api/meetings/{meeting['id']}/agenda"
    assert client.get(path, headers=anna).json() is None
    original = {**FINAL, "title": "Original"}
    payload = {
        "final_agenda": FINAL,
        "ai_suggestion": {
            "agenda": original,
            "model": model,
            "prompt_version": prompt_version,
        },
    }
    saved = client.post(path, json=payload, headers=anna)
    assert saved.status_code == 200
    assert saved.json()["final_agenda"]["title"] == "Corrected"
    assert saved.json()["ai_suggestion"]["agenda"]["title"] == "Original"
    assert client.get(path, headers=anna).json() == saved.json()
    # The normal meeting editor must not replace or erase the independently saved agenda.
    updated = {**meeting_payload(), "title": "Meeting details edited"}
    assert client.put(f"/api/meetings/{meeting['id']}", json=updated, headers=anna).status_code == 200
    reopened = client.get(path, headers=anna).json()
    assert reopened["final_agenda"]["items"] == FINAL["items"]
    assert reopened["final_agenda"]["action_items"] == FINAL["action_items"]
    assert reopened["ai_suggestion"] == saved.json()["ai_suggestion"]
    assert client.get(path, headers=other).status_code == 404
    assert client.post(path, json=payload, headers=other).status_code == 404
    assert client.get(path).status_code == 401
    assert client.post(path, json={"final_agenda": {"items": [{}]}}, headers=anna).status_code == 422
    assert client.get(f"/api/meetings/{meeting['id']}", headers=anna).json()["title"] == updated["title"]


def test_manual_agenda_and_delete_cascade(client):
    headers = bearer(token())
    meeting = client.post("/api/meetings", json=meeting_payload(), headers=headers).json()
    path = f"/api/meetings/{meeting['id']}"
    result = client.post(path + "/agenda", json={"final_agenda": FINAL}, headers=headers)
    assert result.status_code == 200 and result.json()["ai_suggestion"] is None
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path + "/agenda", headers=headers).status_code == 404
