import logging
import os
import subprocess
import tempfile
import json
from pathlib import Path
 
import numpy as np
import soundfile as sf
 
from stt.language_detect import get_voice_for_lang
 
log = logging.getLogger(__name__)
 
VOICES_DIR = Path("tts/voices")
 
 
class Synthesizer:
    def __init__(self, config: dict):
        self.cfg     = config["tts"]
        self.voices  = config["tts"]["voices"]
        self._piper  = None
 
    def load(self):
        """Check piper binary is available."""
        result = subprocess.run(["piper", "--version"], capture_output=True)
        if result.returncode == 0:
            log.info("Piper TTS ready: %s", result.stdout.decode().strip())
            self._piper = "piper"
        else:
            # Try local venv piper
            local = Path("venv/bin/piper")
            if local.exists():
                self._piper = str(local)
                log.info("Using local piper: %s", self._piper)
            else:
                log.warning("Piper binary not found — TTS will use espeak fallback")
                self._piper = None
 
    def _voice_path(self, lang: str) -> Path | None:
        voice_name = get_voice_for_lang(lang)
        # exact match
        exact = VOICES_DIR / f"{voice_name}.onnx"
        if exact.exists():
            return exact
        # glob match (handles wildcards like te_IN-*)
        prefix = voice_name.replace("-*", "").replace("*", "")
        matches = list(VOICES_DIR.glob(f"{prefix}*.onnx"))
        if matches:
            return matches[0]
        # fallback to any English voice
        fallback = list(VOICES_DIR.glob("en_US*.onnx"))
        return fallback[0] if fallback else None

    def sample_rate_for_lang(self, lang: str) -> int:
        voice_path = self._voice_path(lang)
        if voice_path:
            config_json = voice_path.with_suffix(".onnx.json")
            if config_json.exists():
                try:
                    data = json.loads(config_json.read_text())
                    return int(data.get("audio", {}).get("sample_rate", 22050))
                except Exception as e:
                    log.warning("Failed to read voice sample rate for %s: %s", voice_path.name, e)
        return 22050
 
    def synthesize(self, text: str, lang: str = "en") -> np.ndarray:
        """Returns float32 audio array at the voice's native sample rate."""
        voice_path = self._voice_path(lang)
 
        if self._piper and voice_path:
            return self._piper_synth(text, voice_path)
        else:
            return self._espeak_fallback(text)
 
    def _piper_synth(self, text: str, voice_path: Path) -> np.ndarray:
        config_json = voice_path.with_suffix(".onnx.json")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
 
        cmd = [
            self._piper,
            "--model", str(voice_path),
            "--output_file", tmp.name,
        ]
        if config_json.exists():
            cmd += ["--config", str(config_json)]
 
        proc = subprocess.run(
            cmd,
            input=text.encode(),
            capture_output=True,
        )
        if proc.returncode != 0:
            log.error("Piper error: %s", proc.stderr.decode())
            return self._espeak_fallback(text)
 
        audio, _ = sf.read(tmp.name, dtype="float32")
        os.unlink(tmp.name)
        return audio
 
    def _espeak_fallback(self, text: str) -> np.ndarray:
        """Last-resort espeak-ng fallback (robotic but always works)."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        subprocess.run(
            ["espeak-ng", "-w", tmp.name, text],
            capture_output=True,
        )
        audio, _ = sf.read(tmp.name, dtype="float32")
        os.unlink(tmp.name)
        return audio