import logging
import socket
 
from llm.groq_client import GroqClient
from llm.ollama_client import OllamaClient
 
log = logging.getLogger(__name__)
 
 
def _has_internet(host="8.8.8.8", port=53, timeout=2) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False
 
 
class LLMRouter:
    """Routes to Groq (online) or Ollama (offline) automatically."""
 
    def __init__(self, config: dict):
        self.groq   = GroqClient(config)
        self.ollama = OllamaClient(config)
        self._config = config
        self._groq_disabled = False

    def _should_disable_groq(self, error: Exception) -> bool:
        msg = str(error).lower()
        return "model_decommissioned" in msg or "decommissioned" in msg
 
    def load(self):
        try:
            self.groq.load()
        except Exception as e:
            log.warning("Groq unavailable at load time: %s", e)
        self.ollama.load()
 
    def chat(self, messages: list[dict], system: str = "", emotional: bool = False) -> str:
        if (not self._groq_disabled) and self.groq.is_ready() and _has_internet():
            try:
                return self.groq.chat(messages, system=system, emotional=emotional)
            except Exception as e:
                if self._should_disable_groq(e):
                    self._groq_disabled = True
                    log.warning("Groq disabled for this run due to model deprecation error: %s", e)
                log.warning("Groq failed (%s), falling back to Ollama", e)
 
        if self.ollama.is_ready():
            return self.ollama.chat(messages, system=system)
 
        log.error("No LLM backend available!")
        return "Sorry, I am having trouble connecting right now. Please try again in a moment."