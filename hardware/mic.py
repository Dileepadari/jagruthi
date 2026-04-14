import logging
import numpy as np
import sounddevice as sd
 
log = logging.getLogger(__name__)
 
 
def list_devices():
    print(sd.query_devices())
 
 
def get_input_device_index(prefer_keyword: str = "USB") -> int | None:
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if prefer_keyword.lower() in d["name"].lower() and d["max_input_channels"] > 0:
            log.info("Found preferred mic: [%d] %s", i, d["name"])
            return i
    return None   # use system default
 
 
def record_seconds(
    duration: float,
    sample_rate: int = 16000,
    device: int | None = None,
) -> np.ndarray:
    """Blocking: records exactly `duration` seconds and returns int16 array."""
    samples = int(duration * sample_rate)
    audio = sd.rec(samples, samplerate=sample_rate, channels=1,
                   dtype="int16", device=device)
    sd.wait()
    return audio.flatten()