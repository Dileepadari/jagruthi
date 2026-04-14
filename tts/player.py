import logging
import numpy as np
import sounddevice as sd
 
log = logging.getLogger(__name__)
 
SAMPLE_RATE = 22050
 
 
class AudioPlayer:
    def play(self, audio: np.ndarray, sample_rate: int = SAMPLE_RATE):
        """Blocking plsayback.s"""
        if audio is None or len(audio) == 0:
            log.warning("Empty audio — nothing to play")
            return
        try:
            log.info("Playing audio: %d samples at %d Hz", len(audio), sample_rate)
            sd.play(audio.astype(np.float32), sample_rate)
            sd.wait()
        except Exception as e:
            log.exception("Audio playback failed: %s", e)
            raise