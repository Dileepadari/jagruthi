"""
Pre-loads all heavy models into RAM.
Called from main.py before the pipeline starts.
"""
import logging
log = logging.getLogger(__name__)
 
 
def warmup(config: dict):
    log.info("[warmup] Loading Whisper...")
    from stt.transcriber import Transcriber
    t = Transcriber(config)
    t.load()
 
    log.info("[warmup] Loading Piper TTS...")
    from tts.synthesizer import Synthesizer
    s = Synthesizer(config)
    s.load()
 
    log.info("[warmup] Loading embedding model + ChromaDB...")
    from rag.rag_chain import RAGChain
    r = RAGChain(config)
    r.load()
 
    log.info("[warmup] All models loaded.")