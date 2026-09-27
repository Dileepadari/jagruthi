"""
The crisis path, which is the highest-stakes code in this repository.

Everything here is about one question: does a student who says something
alarming reliably get told how to reach a human? The original answer was "only
if the LLM call succeeds, only if they said it in English, and the phone number
was a placeholder".
"""

import copy

import pytest

from modules.emotional_support import (
    CRISIS_PHRASES,
    EmotionalSupport,
    looks_like_placeholder,
)


# -- keyword triage --------------------------------------------------------

@pytest.mark.parametrize(
    "utterance",
    [
        "I want to die",
        "honestly I just want to kill myself",
        "there is no point living any more",
        "I keep thinking about suicide",
    ],
)
def test_english_crisis_is_detected(config, fake_llm, utterance):
    es = EmotionalSupport(config, fake_llm())
    assert es.assess(utterance) == "crisis"


@pytest.mark.parametrize(
    "utterance",
    [
        "मुझे मरना चाहता हूं",
        "main ab jeena nahi chahta",
        "मैं आत्महत्या करना चाहता हूँ",
    ],
)
def test_hindi_crisis_is_detected(config, fake_llm, utterance):
    # The kiosk advertises Hindi. A crisis said in Hindi used to score
    # "neutral" and never reach triage at all.
    es = EmotionalSupport(config, fake_llm())
    assert es.assess(utterance) == "crisis"


@pytest.mark.parametrize(
    "utterance",
    [
        "నాకు చచ్చిపోవాలని ఉంది",
        "naaku batakalani ledu",
        "atmahatya cheskovalani undi",
    ],
)
def test_telugu_crisis_is_detected(config, fake_llm, utterance):
    es = EmotionalSupport(config, fake_llm())
    assert es.assess(utterance) == "crisis"


def test_crisis_keyword_is_not_sent_to_the_llm_to_be_downgraded(config, fake_llm):
    # A crisis keyword short-circuits. If it went to the LLM, a model answering
    # "neutral" would silently disarm the escalation.
    llm = fake_llm(reply="neutral")
    es = EmotionalSupport(config, llm)
    assert es.assess("I want to die") == "crisis"
    assert llm.calls == []


def test_ordinary_speech_is_neutral(config, fake_llm):
    llm = fake_llm(reply="crisis")
    es = EmotionalSupport(config, llm)
    assert es.assess("when is the next exam") == "neutral"
    assert es.assess("") == "neutral"
    assert llm.calls == []


def test_stress_phrases_go_to_the_llm(config, fake_llm):
    llm = fake_llm(reply="anxious")
    es = EmotionalSupport(config, llm)
    assert es.assess("I am so stressed about this") == "anxious"
    assert len(llm.calls) == 1


def test_stress_falls_back_to_stressed_when_the_llm_is_down(config, fake_llm):
    # Not "neutral": a stress phrase matched, so the safe direction with no LLM
    # is to treat it as real.
    es = EmotionalSupport(config, fake_llm(raises=RuntimeError("no backend")))
    assert es.assess("I feel completely overwhelmed") == "stressed"


def test_llm_can_still_escalate_a_stress_phrase_to_crisis(config, fake_llm):
    es = EmotionalSupport(config, fake_llm(reply="crisis"))
    assert es.assess("I want to give up") == "crisis"


def test_an_unparseable_llm_answer_does_not_become_a_mood(config, fake_llm):
    es = EmotionalSupport(config, fake_llm(reply="I think they seem a bit sad?"))
    assert es.assess("I am so stressed") == "stressed"


# -- the counsellor details ------------------------------------------------

def test_placeholder_detection():
    assert looks_like_placeholder("+91-XXXXXXXXXX")
    assert looks_like_placeholder("xxx")
    assert looks_like_placeholder("")
    assert looks_like_placeholder("   ")
    assert looks_like_placeholder("TBD")
    assert not looks_like_placeholder("+91-9876543210")
    assert not looks_like_placeholder("Admin Block, Room 12")


def test_details_include_a_real_contact(config, fake_llm):
    es = EmotionalSupport(config, fake_llm())
    details = es.counsellor_details()
    assert "Student Counsellor" in details
    assert "+91-9876543210" in details
    assert "Admin Block, Room 12" in details


def test_a_placeholder_contact_is_never_read_out(config, fake_llm):
    # config.yaml ships "+91-XXXXXXXXXX". Speaking that to someone in crisis is
    # worse than not offering a number at all.
    cfg = copy.deepcopy(config)
    cfg["emotional"]["counsellor_contact"] = "+91-XXXXXXXXXX"
    es = EmotionalSupport(cfg, fake_llm())
    details = es.counsellor_details()
    assert "X" not in details
    assert "Student Counsellor" in details
    assert "Admin Block, Room 12" in details


def test_details_still_name_someone_when_nothing_is_configured(config, fake_llm):
    cfg = copy.deepcopy(config)
    cfg["emotional"]["counsellor_contact"] = "+91-XXXXXXXXXX"
    cfg["emotional"]["counsellor_room"] = ""
    cfg["emotional"]["counsellor_name"] = ""
    es = EmotionalSupport(cfg, fake_llm())
    details = es.counsellor_details()
    assert "counsellor" in details.lower()
    assert "X" not in details


# -- responding ------------------------------------------------------------

def test_crisis_response_appends_the_details(config, fake_llm, session):
    es = EmotionalSupport(config, fake_llm(reply="That sounds really heavy."))
    out = es.respond(session(mood="crisis"), "I want to die")
    assert "That sounds really heavy." in out
    assert "+91-9876543210" in out


def test_crisis_details_survive_the_llm_failing(config, fake_llm, session):
    # The whole point. The escalation used to be appended only after a
    # successful llm.chat(), so an exception there meant the student heard
    # nothing at all - and with no handler in the pipeline, the kiosk died.
    es = EmotionalSupport(config, fake_llm(raises=RuntimeError("groq timeout")))
    out = es.respond(session(mood="crisis"), "I want to die")
    assert "+91-9876543210" in out
    assert "Student Counsellor" in out
    assert out.strip()


def test_crisis_details_survive_a_missing_prompt_file(config, fake_llm, session, monkeypatch):
    import modules.emotional_support as mod
    from pathlib import Path

    monkeypatch.setattr(mod, "_EMOTIONAL_PROMPT", Path("/nonexistent/prompt.txt"))
    es = EmotionalSupport(config, fake_llm())
    out = es.respond(session(mood="crisis"), "I want to die")
    assert "+91-9876543210" in out


def test_non_crisis_failure_still_says_something_kind(config, fake_llm, session):
    es = EmotionalSupport(config, fake_llm(raises=RuntimeError("down")))
    out = es.respond(session(mood="stressed"), "I am overwhelmed")
    assert out.strip()
    assert "Student Counsellor" in out


def test_escalation_can_be_turned_off(config, fake_llm, session):
    cfg = copy.deepcopy(config)
    cfg["emotional"]["crisis_escalation"] = False
    es = EmotionalSupport(cfg, fake_llm(reply="I hear you."))
    out = es.respond(session(mood="crisis"), "I want to die")
    assert out == "I hear you."


def test_the_prompt_is_filled_in_and_marked_emotional(config, fake_llm, session):
    llm = fake_llm()
    es = EmotionalSupport(config, llm)
    es.respond(session(mood="sad", language="hi"), "I feel low")
    call = llm.calls[-1]
    assert call["emotional"] is True
    assert "Test Campus" in call["system"]
    assert "sad" in call["system"]
    assert "hi" in call["system"]
    assert "{" not in call["system"]  # every placeholder was substituted


def test_prompt_path_does_not_depend_on_the_working_directory(tmp_path, monkeypatch, config, fake_llm, session):
    # It used to be a relative Path, so this raised FileNotFoundError from
    # inside the crisis path.
    monkeypatch.chdir(tmp_path)
    es = EmotionalSupport(config, fake_llm(reply="ok"))
    out = es.respond(session(mood="crisis"), "I want to die")
    assert "+91-9876543210" in out


def test_no_crisis_phrase_is_empty_or_duplicated():
    assert all(p.strip() for p in CRISIS_PHRASES)
    assert all(p == p.lower() for p in CRISIS_PHRASES if p.isascii())
