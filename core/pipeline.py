import asyncio
import logging
from pathlib import Path
 
from core.event_bus import bus
from core.session import SessionManager
from modules.role_manager import detect_role
from modules.emotional_support import EmotionalSupport
from modules.feedback import log_interaction
 
log = logging.getLogger(__name__)

# Resolved against the repository, not the current working directory. The
# systemd unit sets WorkingDirectory so production was fine, but running
# `python3 main.py` from anywhere else raised FileNotFoundError mid-turn.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_FRIEND_PROMPT_PATH = _REPO_ROOT / "llm" / "prompts" / "system_friend.txt"
_ROLE_PROMPT_PATH = _REPO_ROOT / "llm" / "prompts" / "system_rolebase.txt"

_RAG_INTENT_KEYWORDS = {
    "college", "campus", "university", "institute", "iiit", "history",
    "department", "faculty", "professor", "hod", "office", "admin",
    "exam", "exams", "timetable", "schedule", "calendar", "deadline",
    "syllabus", "admission", "fees", "scholarship", "hostel", "rules",
    "mess", "library", "club", "event", "placement", "internship",
    "contact", "directory", "policy", "procedure",
}
 
 
class Pipeline:
    """
    Orchestrates the full STT → intent → LLM → TTS loop.
    Runs on a single asyncio event loop so blocking calls are
    pushed to executor threads.
    """
 
    def __init__(self, config: dict):
        self.config = config
        self.sessions = SessionManager(config["app"]["session_timeout"])
        self._initialized = False
 
    # ── Initialization ─────────────────────────────────────────────────
    async def initialize(self):
        log.info("Initialising pipeline components...")
        loop = asyncio.get_event_loop()
 
        # Lazy imports - modules load their heavy models on first import
        from wake.detector import WakeWordDetector
        from stt.transcriber import Transcriber
        from tts.synthesizer import Synthesizer
        from tts.player import AudioPlayer
        from llm.router import LLMRouter
        from rag.rag_chain import RAGChain
 
        self.wake = WakeWordDetector(self.config)
        self.transcriber = Transcriber(self.config)
        self.tts = Synthesizer(self.config)
        self.player = AudioPlayer()
        self.llm = LLMRouter(self.config)
        self.rag = RAGChain(self.config)
        self.emotional = EmotionalSupport(self.config, self.llm)
 
        await loop.run_in_executor(None, self._load_models)
        self._initialized = True
        log.info("Pipeline ready.")
 
    def _load_models(self):
        self.llm.load()
        self.transcriber.load()
        self.tts.load()
        self.rag.load()
 
    # ── Main loop ──────────────────────────────────────────────────────
    async def run_forever(self):
        assert self._initialized, "Call initialize() first"
        from stt.audio_capture import AudioCapture
        capture = AudioCapture(self.config)
 
        log.info("Listening for wake word...")
        async for audio_chunk in capture.stream():
            if self.wake.detected(audio_chunk):
                log.info("Wake word detected!")
                await bus.publish("wake_detected")
                # A turn must never take the kiosk down. There was no handler
                # here at all, so one LLM timeout or one bad audio frame killed
                # the process; systemd restarted it, which on a Pi means
                # reloading Whisper, the embeddings model and Chroma before it
                # can listen again. A student who had just been talking to it
                # got silence for a minute or more.
                try:
                    await self._handle_turn(capture)
                except Exception:
                    log.exception("Turn failed; continuing to listen")
                    try:
                        from hardware.led import LED
                        LED().ready()
                    except Exception:
                        pass
 
    async def _handle_turn(self, capture):
        """One full conversation turn: record → transcribe → respond → speak."""
        from hardware.led import LED
        led = LED()
 
        session = self.sessions.get_or_create()
 
        # 1. Record utterance
        led.listening()
        log.info("Recording utterance...")
        audio_path = await asyncio.get_event_loop().run_in_executor(
            None, capture.record_utterance
        )
        led.thinking()
 
        # 2. Transcribe
        text, lang = await asyncio.get_event_loop().run_in_executor(
            None, self.transcriber.transcribe, audio_path
        )
        if not text.strip():
            log.info("Empty transcription, skipping")
            led.ready()
            return
 
        log.info("User (%s) [%s]: %s", session.role, lang, text)
        session.language = lang
        session.add_turn("user", text)
 
        # 3. Role detection (first turn or explicit mention)
        if len(session.history) == 1:
            detected_role = detect_role(text)
            if detected_role:
                session.role = detected_role
 
        # 4. Emotional check
        mood = await asyncio.get_event_loop().run_in_executor(
            None, self.emotional.assess, text
        )
        if mood in ("stressed", "sad", "anxious", "crisis"):
            session.set_emotional(mood)
 
        # 5. Generate response
        if session.mode == "emotional_support":
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.emotional.respond, session, text
            )
        else:
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._institutional_respond, session, text
            )
 
        log.info("Jagruthi: %s", response[:120])
        session.add_turn("assistant", response)
 
        # 6. Synthesize and play
        led.speaking()
        await asyncio.get_event_loop().run_in_executor(
            None, self._speak_response, response, session.language
        )
        led.ready()
 
        # 7. Log (skip emotional sessions)
        if session.log_enabled:
            log_interaction(session.session_id, session.role, text, response, lang)
 
    def _institutional_respond(self, session, text: str) -> str:
        """Route to RAG only for college/institutional queries, else normal LLM chat."""
        if self._should_use_rag(text):
            return self.rag.answer(
                query=text,
                role=session.role,
                history=session.history[:-1],   # exclude current turn
                language=session.language,
            )
        return self._general_respond(session)

    def _should_use_rag(self, text: str) -> bool:
        t = text.lower()
        return any(k in t for k in _RAG_INTENT_KEYWORDS)

    def _general_respond(self, session) -> str:
        """Friendly non-RAG conversation flow using LLM only."""
        role_system = _ROLE_PROMPT_PATH.read_text().format(
            campus_name=self.config["campus"]["name"],
            role=session.role,
            language=session.language,
        )
        friend_system = _FRIEND_PROMPT_PATH.read_text().format(
            language=session.language,
        )
        system = f"{role_system}\n\n{friend_system}"
        return self.llm.chat(session.history, system=system)

    def _speak_response(self, response: str, language: str):
        log.info("Synthesizing speech for language=%s", language)
        audio_out = self.tts.synthesize(response, language)
        sample_rate = self.tts.sample_rate_for_lang(language)
        self.player.play(audio_out, sample_rate)
 
    # ── Called by CheckInScheduler ──────────────────────────────────────
    async def speak_checkin(self, message: str):
        from tts.player import AudioPlayer
        player = AudioPlayer()
        await asyncio.get_event_loop().run_in_executor(
            None, self._speak_checkin, player, message
        )

    def _speak_checkin(self, player, message: str):
        audio = self.tts.synthesize(message, "en")
        player.play(audio, self.tts.sample_rate_for_lang("en"))