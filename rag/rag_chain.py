import logging
from pathlib import Path

# Repo-relative, not cwd-relative: the systemd unit sets WorkingDirectory
# so production was fine, but running this from anywhere else looked in
# the wrong place and failed mid-run.
_REPO_ROOT = Path(__file__).resolve().parent.parent
 
log = logging.getLogger(__name__)
 
_SYSTEM_PROMPT_PATH = _REPO_ROOT / "llm" / "prompts" / "system_institutional.txt"
 
 
class RAGChain:
    """
    Full RAG loop: embed query → retrieve chunks → LLM answer.
    Uses LLMRouter directly (not LangChain) to keep latency low on RPi.
    """
 
    def __init__(self, config: dict):
        self.config = config
        self._vs    = None
        self._ret   = None
        self._llm   = None
 
    def load(self):
        from rag.vectorstore import VectorStore
        from rag.retriever import Retriever
        from llm.router import LLMRouter
 
        self._vs  = VectorStore(self.config)
        self._ret = Retriever(self._vs, self.config)
        self._llm = LLMRouter(self.config)
        self._llm.load()
 
        # Auto-ingest knowledge_base/raw if vectorstore is empty
        if self._vs.count() == 0:
            log.info("Vector store empty - ingesting knowledge_base/raw ...")
            self._ingest_all()
            log.info("Ingestion complete. Store has %d chunks.", self._vs.count())
 
    def _ingest_all(self):
        from rag.ingestion import ingest_directory
        raw_dir = _REPO_ROOT / "knowledge_base" / "raw"
        docs, metas, ids = [], [], []
 
        for chunk, meta, uid in ingest_directory(raw_dir):
            docs.append(chunk)
            metas.append(meta)
            ids.append(uid)
            if len(docs) >= 500:          # batch insert
                self._vs.add(docs, metas, ids)
                docs, metas, ids = [], [], []
 
        if docs:
            self._vs.add(docs, metas, ids)
 
    def answer(
        self,
        query: str,
        role: str = "student",
        history: list[dict] | None = None,
        language: str = "en",
    ) -> str:
        chunks = self._ret.retrieve(query, role=role)
 
        if not chunks:
            return (
                "I don't have specific information on that right now. "
                "Please check with the relevant office or faculty directly."
            )
 
        context = "\\n\\n---\\n\\n".join(chunks)
        system_template = _SYSTEM_PROMPT_PATH.read_text()
        system = system_template.format(
            campus_name=self.config["campus"]["name"],
            role=role,
            language=language,
        )
 
        messages = list(history or [])
        messages.append({
            "role": "user",
            "content": (
                f"Context from campus documents:\\n{context}\\n\\n"
                f"Question: {query}"
            ),
        })
 
        return self._llm.chat(messages, system=system)