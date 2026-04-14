import logging
import os
 
log = logging.getLogger(__name__)
 
 
class Transcriber:
    def __init__(self, config: dict):
        self.cfg   = config["stt"]
        self._model = None
 
    def load(self):
        from faster_whisper import WhisperModel
        log.info("Loading Whisper model '%s'...", self.cfg["model"])
        self._model = WhisperModel(
            self.cfg["model"],
            device=self.cfg.get("device", "cpu"),
            compute_type=self.cfg.get("compute_type", "int8"),
        )
        log.info("Whisper loaded.")
 
    def transcribe(self, audio_path: str) -> tuple[str, str]:
        """Returns (text, language_code)."""
        assert self._model, "Call load() first"
        lang_hint = None if self.cfg.get("language") == "auto" else self.cfg["language"]
 
        segments, info = self._model.transcribe(
            audio_path,
            beam_size=self.cfg.get("beam_size", 5),
            language=lang_hint,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(s.text.strip() for s in segments)
        lang = info.language or "en"
        log.debug("Transcribed [%s]: %s", lang, text)
 
        # Cleanup temp file
        try:
            os.unlink(audio_path)
        except OSError:
            pass
 
        return text.strip(), lang