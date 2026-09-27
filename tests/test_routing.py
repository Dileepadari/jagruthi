"""
Role detection, language normalisation, session state and LLM fallback.

All of it is pure logic that runs without Whisper, Piper, Chroma or a network,
which is the only reason it can be tested at all on a machine that is not the
Pi.
"""

import pytest

from core.session import Session, SessionManager
from modules.multilingual import SUPPORTED, detect_language_code, greeting_in_lang
from modules.role_manager import detect_role, role_greeting


# -- role detection --------------------------------------------------------

@pytest.mark.parametrize(
    "utterance,expected",
    [
        ("I am a student here", "student"),
        ("I study computer science", "student"),
        ("this is my third semester", "student"),
        ("I am a professor in the CSE department", "faculty"),
        ("I teach data structures", "faculty"),
        ("I work in the accounts office", "staff"),
        ("I am the hostel warden", "staff"),
    ],
)
def test_roles_are_detected(utterance, expected):
    assert detect_role(utterance) == expected


@pytest.mark.parametrize(
    "utterance",
    [
        # Every one of these used to match a keyword *inside* another word and
        # route an ordinary question to the wrong role and the wrong prompt.
        "I desire to know the exam date",   # "sir" in "desire"
        "three days left",                  # "hr" in "three"
        "I came through the main gate",     # "hr" in "through"
        "what is the method for applying",  # "hod" in "method"
        "Chris told me about this",         # "hr" in "Chris"
        "where is the hostel",
        "when does the library close",
        "",
    ],
)
def test_ordinary_speech_does_not_claim_a_role(utterance):
    assert detect_role(utterance) is None


def test_detection_is_case_insensitive():
    assert detect_role("I am a STUDENT") == "student"
    assert detect_role("I am a Professor") == "faculty"


def test_dr_prefix_still_matches():
    # "dr." ends in a literal dot, which must not demand a word character after it.
    assert detect_role("I am Dr. Rao from ECE") == "faculty"


def test_every_greeting_names_the_campus():
    for role in ("student", "faculty"):
        assert "Test Campus" in role_greeting(role, "Test Campus")
    # An unknown role falls back rather than raising.
    assert role_greeting("visitor", "Test Campus")


# -- language --------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("en", "en"), ("hi", "hi"), ("te", "te"),
        ("en-US", "en"), ("EN", "en"), ("hi-IN", "hi"),
        ("fr", "en"), ("", "en"), (None, "en"),
    ],
)
def test_language_codes_are_normalised(raw, expected):
    assert detect_language_code(raw) == expected


def test_every_supported_language_has_a_greeting():
    for lang in SUPPORTED:
        assert greeting_in_lang(lang).strip()
    assert greeting_in_lang("fr") == greeting_in_lang("en")


# -- session ---------------------------------------------------------------

def test_history_is_capped():
    s = Session(session_id="s1")
    for i in range(40):
        s.add_turn("user", f"message {i}")
    assert len(s.history) == 20
    assert s.history[-1]["content"] == "message 39"


def test_emotional_mode_disables_logging():
    # Privacy: an emotional session must not be written to the CSV.
    s = Session(session_id="s1")
    assert s.log_enabled is True
    s.set_emotional("crisis")
    assert s.mode == "emotional_support"
    assert s.mood == "crisis"
    assert s.log_enabled is False


def test_reset_restores_logging_and_mode():
    s = Session(session_id="s1")
    s.set_emotional("crisis")
    s.add_turn("user", "hello")
    s.reset()
    assert s.mode == "normal"
    assert s.mood == "neutral"
    assert s.log_enabled is True
    assert s.history == []


def test_expiry():
    s = Session(session_id="s1")
    assert not s.is_expired(30)
    s.last_active -= 60
    assert s.is_expired(30)


def test_manager_reuses_a_live_session_and_replaces_an_expired_one():
    m = SessionManager(timeout_seconds=30)
    first = m.get_or_create()
    assert m.get_or_create() is first

    first.last_active -= 60
    second = m.get_or_create()
    assert second is not first
    assert second.session_id != first.session_id


def test_force_new_starts_a_fresh_session():
    m = SessionManager(timeout_seconds=30)
    first = m.get_or_create()
    m.force_new()
    assert m.get_or_create() is not first


# -- LLM routing -----------------------------------------------------------

class _Backend:
    def __init__(self, ready=True, reply="ok", raises=None):
        self._ready, self.reply, self.raises = ready, reply, raises
        self.calls = 0

    def is_ready(self):
        return self._ready

    def load(self):
        pass

    def chat(self, messages, system="", emotional=False):
        self.calls += 1
        if self.raises:
            raise self.raises
        return self.reply


@pytest.fixture
def router(monkeypatch):
    """An LLMRouter with both backends faked and the internet check stubbed."""
    import llm.router as mod

    def build(groq, ollama, online=True):
        monkeypatch.setattr(mod, "_has_internet", lambda *a, **k: online)
        r = mod.LLMRouter.__new__(mod.LLMRouter)
        r.groq, r.ollama, r._config, r._groq_disabled = groq, ollama, {}, False
        return r

    return build


def test_groq_is_preferred_when_online(router):
    groq, ollama = _Backend(reply="from groq"), _Backend(reply="from ollama")
    assert router(groq, ollama).chat([]) == "from groq"
    assert ollama.calls == 0


def test_falls_back_to_ollama_when_offline(router):
    groq, ollama = _Backend(reply="from groq"), _Backend(reply="from ollama")
    assert router(groq, ollama, online=False).chat([]) == "from ollama"
    assert groq.calls == 0


def test_falls_back_to_ollama_when_groq_raises(router):
    groq = _Backend(raises=RuntimeError("429 rate limited"))
    ollama = _Backend(reply="from ollama")
    assert router(groq, ollama).chat([]) == "from ollama"


def test_a_decommissioned_model_disables_groq_for_the_run(router):
    groq = _Backend(raises=RuntimeError("model_decommissioned: llama-3.1"))
    ollama = _Backend(reply="from ollama")
    r = router(groq, ollama)
    assert r.chat([]) == "from ollama"
    assert r._groq_disabled is True
    r.chat([])
    assert groq.calls == 1  # not tried a second time


def test_no_backend_returns_an_apology_rather_than_raising(router):
    # The pipeline speaks whatever comes back, so this must be a sentence, not
    # an exception.
    groq, ollama = _Backend(ready=False), _Backend(ready=False)
    out = router(groq, ollama).chat([])
    assert isinstance(out, str) and out.strip()
    assert "trouble" in out.lower()
