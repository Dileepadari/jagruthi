import logging
 
log = logging.getLogger(__name__)
 
 
class OllamaClient:
    def __init__(self, config: dict):
        self.model      = config["llm"]["ollama"]["model"]
        self.host       = config["llm"]["ollama"]["host"]
        self.max_tokens = config["llm"]["ollama"]["max_tokens"]
        self._client    = None
 
    def load(self):
        try:
            import ollama
            self._client = ollama.Client(host=self.host)
            # quick ping
            self._client.list()
            log.info("Ollama ready (model=%s)", self.model)
        except Exception as e:
            log.warning("Ollama not available: %s", e)
            self._client = None
 
    def is_ready(self) -> bool:
        return self._client is not None
 
    def chat(self, messages: list[dict], system: str = "", **_) -> str:
        assert self._client, "Ollama not available"
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)
 
        try:
            resp = self._client.chat(
                model=self.model,
                messages=full,
                options={"num_predict": self.max_tokens},
            )
            return resp["message"]["content"].strip()
        except Exception as e:
            log.error("Ollama error: %s", e)
            raise