import logging
import os
from typing import Optional
 
log = logging.getLogger(__name__)
 
 
class GroqClient:
    def __init__(self, config: dict):
        self.model          = config["llm"]["groq"]["model"]
        self.emotional_model = config["llm"]["groq"].get("emotional_model", self.model)
        self.max_tokens     = config["llm"]["groq"]["max_tokens"]
        self.temperature    = config["llm"]["groq"]["temperature"]
        self._client        = None
 
    def load(self):
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key or api_key == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY not set in .env")
        self._client = Groq(api_key=api_key)
        log.info("Groq client ready (model=%s)", self.model)
 
    def is_ready(self) -> bool:
        return self._client is not None
 
    def chat(
        self,
        messages: list[dict],
        system: str = "",
        emotional: bool = False,
    ) -> str:
        assert self._client, "Call load() first"
        model = self.emotional_model if emotional else self.model
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)
 
        try:
            resp = self._client.chat.completions.create(
                model=model,
                messages=full,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error("Groq API error: %s", e)
            raise