import asyncio
import logging
import tempfile
from typing import AsyncGenerator
 
import numpy as np
import sounddevice as sd
import soundfile as sf
 
log = logging.getLogger(__name__)
 
SAMPLE_RATE = 16000
CHUNK_MS    = 80
CHUNK_SAMP  = int(SAMPLE_RATE * CHUNK_MS / 1000)   # 1280 samples
 
 
class AudioCapture:
    def __init__(self, config: dict):
        self.cfg     = config["audio"]
        self.sr      = SAMPLE_RATE
        self.thresh  = self.cfg.get("silence_threshold", 300)
        self.sil_dur = self.cfg.get("silence_duration", 1.5)
        self.max_sec = self.cfg.get("record_seconds", 8)
 
    async def stream(self) -> AsyncGenerator[np.ndarray, None]:
        """Yields 80ms audio chunks indefinitely (for wake word scanning)."""
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()
 
        def _cb(indata, frames, t, status):
            loop.call_soon_threadsafe(q.put_nowait, indata[:, 0].copy())
 
        with sd.InputStream(samplerate=self.sr, channels=1, dtype="int16",
                             blocksize=CHUNK_SAMP, callback=_cb):
            while True:
                chunk = await q.get()
                yield chunk
 
    def record_utterance(self) -> str:
        """
        Blocking: records until silence detected (or max_sec reached).
        Returns path to a 16kHz mono WAV file.
        """
        log.debug("Recording utterance...")
        frames = []
        silent_chunks = 0
        required_silent = int(self.sil_dur * 1000 / CHUNK_MS)
        max_chunks = int(self.max_sec * 1000 / CHUNK_MS)
 
        with sd.InputStream(samplerate=self.sr, channels=1, dtype="int16",
                             blocksize=CHUNK_SAMP) as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(CHUNK_SAMP)
                chunk = chunk[:, 0]
                frames.append(chunk)
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
                if rms < self.thresh:
                    silent_chunks += 1
                    if silent_chunks >= required_silent and len(frames) > required_silent + 5:
                        break
                else:
                    silent_chunks = 0
 
        audio = np.concatenate(frames)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio, self.sr, subtype="PCM_16")
        log.debug("Recorded %d samples → %s", len(audio), tmp.name)
        return tmp.name