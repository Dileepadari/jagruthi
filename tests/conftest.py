import sys
from pathlib import Path

# The modules import as `modules.x`, `core.x` and so on, so the repository root
# has to be importable however pytest was invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture
def config():
    """A config shaped like config.yaml, with a real counsellor contact."""
    return {
        "app": {"name": "Jagruthi", "session_timeout": 30},
        "campus": {"name": "Test Campus", "city": "Testville"},
        "emotional": {
            "enabled": True,
            "sensitivity": 0.65,
            "crisis_escalation": True,
            "counsellor_name": "Student Counsellor",
            "counsellor_room": "Admin Block, Room 12",
            "counsellor_contact": "+91-9876543210",
        },
        "roles": {"default": "student", "options": ["student", "faculty", "staff"]},
    }


class FakeLLM:
    """Stands in for LLMRouter. Records calls, and can be told to fail."""

    def __init__(self, reply="I hear you.", raises=None):
        self.reply = reply
        self.raises = raises
        self.calls = []

    def chat(self, messages, system="", emotional=False):
        self.calls.append({"messages": messages, "system": system, "emotional": emotional})
        if self.raises:
            raise self.raises
        return self.reply


@pytest.fixture
def fake_llm():
    return FakeLLM


class FakeSession:
    def __init__(self, mood="neutral", language="en", history=None):
        self.mood = mood
        self.language = language
        self.history = history if history is not None else []
        self.mode = "normal"
        self.role = "student"


@pytest.fixture
def session():
    return FakeSession
