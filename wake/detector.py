import logging
import numpy as np
 
log = logging.getLogger(__name__)
 
CHUNK_SAMPLES = 1280   # 80ms @ 16kHz — required by openWakeWord
 
 
class WakeWordDetector:
    def __init__(self, config: dict):
        self.config = config
        self._model = None
        self._wake_word = config["app"]["wake_word"]
        self._buffer = np.array([], dtype=np.int16)
        self._load()
 
    def _load(self):
        try:
            from openwakeword.model import Model
            self._model = Model(
                wakeword_models=[self._wake_word],
                inference_framework="onnx",
            )
            log.info("Wake word model loaded: %s", self._wake_word)
        except Exception as e:
            log.warning("openWakeWord unavailable (%s) — using manual trigger mode", e)
            self._model = None
 
    def detected(self, audio_chunk: np.ndarray) -> bool:
        """Returns True if wake word detected in this audio chunk."""
        if self._model is None:
            # Fallback: if audio is loud enough treat as activation
            rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
            return rms > 2000
 
        self._buffer = np.append(self._buffer, audio_chunk)
        results = []
        while len(self._buffer) >= CHUNK_SAMPLES:
            chunk = self._buffer[:CHUNK_SAMPLES]
            self._buffer = self._buffer[CHUNK_SAMPLES:]
            pred = self._model.predict(chunk)
            scores = list(pred.values())
            results.append(any(s > 0.5 for s in scores))
 
        return any(results)