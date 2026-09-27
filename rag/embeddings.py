import logging
 
log = logging.getLogger(__name__)
 
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
 
 
class EmbeddingModel:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
 
    def load(self):
        from sentence_transformers import SentenceTransformer
        log.info("Loading embedding model: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        log.info("Embedding model loaded.")
 
    def embed(self, texts: list[str]) -> list[list[float]]:
        assert self._model, "Call load() first"
        return self._model.encode(texts, normalize_embeddings=True).tolist()
 
    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
 
 
# Module-level singleton
_instance: EmbeddingModel | None = None
 
def get_embedder(model_name: str = DEFAULT_MODEL) -> EmbeddingModel:
    global _instance
    if _instance is None:
        _instance = EmbeddingModel(model_name)
        _instance.load()
    return _instance