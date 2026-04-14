import logging
import numpy as np
import sounddevice as sd
 
log = logging.getLogger(__name__)
 
 
def play_wav(path: str, sample_rate: int = 22050):
    import soundfile as sf
    data, sr = sf.read(path, dtype="float32")
    sd.play(data, sr)
    sd.wait()
 
 
def play_array(audio: np.ndarray, sample_rate: int = 22050):
    sd.play(audio.astype(np.float32), sample_rate)
    sd.wait()