import logging
import re
from pathlib import Path
 
log = logging.getLogger(__name__)
 
CRISIS_PHRASES = [
    "kill myself", "end my life", "want to die", "no point living",
    "can't go on", "give up on life", "hate myself",
]
STRESS_PHRASES = [
    "so stressed", "can't handle", "breaking down", "overwhelmed",
    "anxiety", "panic", "failing", "no one cares", "all alone",
    "depressed", "hopeless", "terrible", "want to give up",
    "i failed", "tired of everything", "crying",
]
 
_EMOTIONAL_PROMPT = Path("llm/prompts/system_emotional.txt")
_FRIEND_PROMPT    = Path("llm/prompts/system_friend.txt")
 
 
class EmotionalSupport:
    def __init__(self, config: dict, llm):
        self.config = config
        self.llm    = llm
        self._ec    = config["emotional"]
        self._campus = config["campus"]["name"]
 
    def assess(self, text: str) -> str:
        """
        Returns mood string: neutral | stressed | sad | anxious | crisis
        Uses keyword heuristics first (fast), then LLM confirmation.
        """
        t = text.lower()
 
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
            if mood in ("neutral", "stressed", "sad", "anxious", "crisis"):
                return mood
        except Exception as e:
            log.warning("LLM mood assessment failed: %s", e)
        return "stressed"
 
    def respond(self, session, text: str) -> str:
        lang   = session.language
        mood   = session.mood
        system = _EMOTIONAL_PROMPT.read_text().format(
            campus_name     = self._campus,
            mood            = mood,
            counsellor_name = self._ec["counsellor_name"],
            counsellor_room = self._ec["counsellor_room"],
            counsellor_contact = self._ec["counsellor_contact"],
            language        = lang,
        )
 
        messages = list(session.history)
        response = self.llm.chat(messages, system=system, emotional=True)
 
        if mood == "crisis" and self._ec["crisis_escalation"]:
            response += (
                f" Please consider reaching out to our counsellor: "
                f"{self._ec['counsellor_name']} at {self._ec['counsellor_room']}, "
                f"{self._ec['counsellor_contact']}."
            )
 
        return response