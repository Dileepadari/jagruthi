import time
import logging
from dataclasses import dataclass, field
from typing import Optional
 
log = logging.getLogger(__name__)
 
 
@dataclass
class Session:
    """Holds all per-conversation state."""
    session_id: str
    role: str = "student"
    language: str = "en"
    user_name: Optional[str] = None
    mode: str = "normal"            # normal | emotional_support | companion
    mood: str = "neutral"           # neutral | stressed | sad | anxious | crisis
    history: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    log_enabled: bool = True
 
    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self.last_active = time.time()
        if len(self.history) > 20:          # keep last 10 exchanges
            self.history = self.history[-20:]
 
    def is_expired(self, timeout_seconds: int) -> bool:
        return (time.time() - self.last_active) > timeout_seconds
 
    def set_emotional(self, mood: str):
        self.mode = "emotional_support"
        self.mood = mood
        self.log_enabled = False            # privacy: no logs for emotional sessions
        log.info("Session switched to emotional_support mode (mood=%s)", mood)
 
    def reset(self):
        self.history = []
        self.mode = "normal"
        self.mood = "neutral"
        self.log_enabled = True
        self.last_active = time.time()
        log.debug("Session reset")
 
 
class SessionManager:
    def __init__(self, timeout_seconds: int = 30):
        self._current: Optional[Session] = None
        self._timeout = timeout_seconds
        self._session_counter = 0
 
    def get_or_create(self) -> Session:
        if self._current is None or self._current.is_expired(self._timeout):
            self._session_counter += 1
            self._current = Session(session_id=f"s{self._session_counter:04d}")
            log.info("New session: %s", self._current.session_id)
        return self._current
 
    def current(self) -> Optional[Session]:
        return self._current
 
    def force_new(self):
        self._current = None