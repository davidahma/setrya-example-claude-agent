"""Serve a shared handoff through the Claude Agent SDK's session reader."""
import asyncio
from contextlib import contextmanager
import json

from claude_agent_sdk import get_session_messages_from_store
import yaml

STACK = "claude-agent"
SESSION = "43815787-7631-4e38-a59c-b7c73f6aaa21"
TARGET = "f0912ce4-adfc-4b47-b2d2-f11be6db146e"
CONTROL = "afa2cabc-603f-4759-a9e1-b15186b7ba0d"


def record(uuid, parent, text):
    return {"type": "user", "uuid": uuid, "parentUuid": parent, "sessionId": SESSION,
            "message": {"role": "user", "content": text}}


class Handoff:
    def __init__(self, path):
        self.path = path

    def save(self, entries):
        temp = self.path.with_suffix(".tmp")
        temp.write_text("".join(json.dumps(row) + "\n" for row in entries), encoding="utf-8")
        temp.replace(self.path)

    async def load(self, key):
        if key["session_id"] != SESSION:
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def answer(self, question):
        messages = asyncio.run(get_session_messages_from_store(self, SESSION))
        expected = "Thursday" if question == "When is dispatch?" else "Harbor-17"
        return next((m.message["content"] for m in messages if m.message.get("content") == expected),
                    "No matching note.")

    def erase(self):
        rows = asyncio.run(self.load({"session_id": SESSION}))
        kept = [row for row in rows if row["uuid"] != TARGET]
        for row in kept:
            if row.get("parentUuid") == TARGET:
                row["parentUuid"] = None
        self.save(kept)

    def configure_case(self, path):
        case = yaml.safe_load(path.read_text())
        case["facts"]["target"]["stored"]["absent"] = [[record(CONTROL, None, "Thursday")]]
        path.write_text(yaml.safe_dump(case, sort_keys=False))


@contextmanager
def open_fixture(root, env):
    env["SETRYA_TEST_TRANSCRIPTS"] = str(root)
    handoff = Handoff(root / (SESSION + ".jsonl"))
    handoff.save([record(TARGET, None, "Harbor-17"), record(CONTROL, TARGET, "Thursday")])
    yield handoff
