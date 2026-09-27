import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

# Prompts are resolved against the repository, not the current working
# directory. The systemd unit sets WorkingDirectory so production was fine, but
# `python3 main.py` from anywhere else raised FileNotFoundError from inside the
# crisis path, which is the worst possible place for it.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_EMOTIONAL_PROMPT = _REPO_ROOT / "llm" / "prompts" / "system_emotional.txt"

# Crisis and stress phrases in all three languages this kiosk advertises, in
# script and in the romanised spelling Whisper often produces for transliterated
# speech. The list used to be English only, so a student saying the same thing
# in Hindi or Telugu was classified "neutral" and never reached even the LLM
# triage, let alone the counsellor. Matching is substring and lowercase, so
# these catch the phrase inside a longer sentence.
CRISIS_PHRASES = [
    # English
    "kill myself", "end my life", "want to die", "no point living",
    "can't go on", "cant go on", "give up on life", "hate myself",
    "better off dead", "end it all", "not worth living", "harm myself",
    "hurt myself", "suicide", "suicidal",
    # Hindi
    "मरना चाहता", "मरना चाहती", "जान दे", "आत्महत्या", "जीना नहीं चाहता",
    "जीने का मन नहीं",
    "marna chahta", "marna chahti", "jaan de dun", "jaan dena",
    "atmahatya", "jeena nahi chahta", "jeene ka mann nahi",
    # Telugu
    "చచ్చిపోవాలని", "ఆత్మహత్య", "బతకాలని లేదు", "చనిపోవాలని",
    "chachipovalani", "atmahatya", "batakalani ledu", "chanipovalani",
]

STRESS_PHRASES = [
    # English
    "so stressed", "can't handle", "cant handle", "breaking down",
    "overwhelmed", "anxiety", "panic", "failing", "no one cares",
    "all alone", "depressed", "hopeless", "terrible", "want to give up",
    "i failed", "tired of everything", "crying", "burnt out", "burned out",
    "worthless", "can't sleep", "cant sleep",
    # Hindi
    "बहुत तनाव", "परेशान", "अकेला", "डर लग", "रो रहा", "रो रही",
    "bahut tanav", "pareshan", "akela hoon", "dar lag raha",
    "ro raha", "ro rahi", "himmat nahi",
    # Telugu
    "చాలా ఒత్తిడి", "ఒంటరిగా", "భయంగా", "ఏడుస్తున్నా",
    "chala ottidi", "ontariga", "bhayanga", "edustunna",
]

_MOODS = ("neutral", "stressed", "sad", "anxious", "crisis")

# A contact that is still the shipped placeholder, e.g. "+91-XXXXXXXXXX".
# Reading that out to someone in crisis is worse than saying nothing.
_PLACEHOLDER_RE = re.compile(r"^[^0-9]*$|x{3,}", re.IGNORECASE)


def looks_like_placeholder(value: str) -> bool:
    """True when a configured contact has not actually been filled in."""
    if not value or not value.strip():
        return True
    return bool(_PLACEHOLDER_RE.search(value.strip()))


class EmotionalSupport:
    def __init__(self, config: dict, llm):
        self.config = config
        self.llm = llm
        self._ec = config["emotional"]
        self._campus = config["campus"]["name"]

        if looks_like_placeholder(self._ec.get("counsellor_contact", "")):
            # Loud, once, at startup: this is the number a student in crisis is
            # told to ring.
            log.error(
                "emotional.counsellor_contact is not configured (%r). Crisis "
                "escalation will name the counsellor and room but cannot give "
                "a phone number. Set it in config.yaml.",
                self._ec.get("counsellor_contact"),
            )

    # -- assessment ---------------------------------------------------------

    def assess(self, text: str) -> str:
        """
        Returns one of: neutral | stressed | sad | anxious | crisis

        Keyword heuristics first (fast, offline, and the only thing that works
        when the LLM is down), then LLM confirmation for the softer signals. A
        crisis keyword short-circuits: the LLM is never given the chance to
        downgrade it.
        """
        t = (text or "").lower()

        if any(p in t for p in CRISIS_PHRASES):
            return "crisis"

        if any(p in t for p in STRESS_PHRASES):
            return self._llm_assess(text)

        return "neutral"

    def _llm_assess(self, text: str) -> str:
        system = (
            "You are a mental health triage assistant. "
            "Classify the following message into exactly one word: "
            "neutral, stressed, sad, anxious, or crisis. "
            "Reply with only the single word."
        )
        try:
            result = self.llm.chat(
                [{"role": "user", "content": text}],
                system=system,
            )
            mood = result.strip().lower().split()[0]
            if mood in _MOODS:
                return mood
        except Exception as e:
            log.warning("LLM mood assessment failed: %s", e)
        # Deliberately not "neutral": we got here because a stress phrase
        # matched, so the safe direction when the LLM cannot be reached is to
        # treat it as real.
        return "stressed"

    # -- escalation ---------------------------------------------------------

    def counsellor_details(self) -> str:
        """
        The sentence naming the counsellor. Built without the LLM, because this
        is the one piece of information that has to survive the LLM being down.
        """
        name = self._ec.get("counsellor_name") or "our student counsellor"
        room = self._ec.get("counsellor_room")
        contact = self._ec.get("counsellor_contact")

        where = []
        if room and not looks_like_placeholder(room):
            where.append(room)
        if contact and not looks_like_placeholder(contact):
            where.append(contact)

        if where:
            return (
                f" Please consider reaching out to our counsellor: "
                f"{name} at {', '.join(where)}."
            )
        return (
            f" Please consider reaching out to {name} on campus. "
            f"Someone at the admin office can point you to them."
        )

    def _crisis_fallback(self) -> str:
        """What is said when the LLM cannot be reached during a crisis turn."""
        return (
            "I am really glad you told me, and I do not want you to be alone "
            "with this right now." + self.counsellor_details()
        )

    # -- response -----------------------------------------------------------

    def respond(self, session, text: str) -> str:
        mood = session.mood
        is_crisis = mood == "crisis" and self._ec.get("crisis_escalation", True)

        try:
            system = _EMOTIONAL_PROMPT.read_text().format(
                campus_name=self._campus,
                mood=mood,
                counsellor_name=self._ec.get("counsellor_name", ""),
                counsellor_room=self._ec.get("counsellor_room", ""),
                counsellor_contact=self._ec.get("counsellor_contact", ""),
                language=session.language,
            )
            response = self.llm.chat(list(session.history), system=system, emotional=True)
        except Exception as e:
            # A missing prompt file, a network error, an Ollama timeout. None of
            # them are a reason for a student in crisis to hear nothing: the
            # escalation used to be appended only after a successful LLM call.
            log.error("Emotional response generation failed: %s", e)
            if is_crisis:
                return self._crisis_fallback()
            return (
                "I am here, and I am listening. I am having trouble finding my "
                "words just now, but I do not want you to feel alone."
                + self.counsellor_details()
            )

        if is_crisis:
            response += self.counsellor_details()

        return response
