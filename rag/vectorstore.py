import logging
from pathlib import Path
 
import chromadb
from chromadb.config import Settings
 
log = logging.getLogger(__name__)
 
 
class VectorStore:
    def __init__(self, config: dict):
        db_path   = config["rag"]["db_path"]
        self.collection_name = config["rag"]["collection_name"]
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("ChromaDB ready - collection '%s' has %d docs",
                 self.collection_name, self._col.count())
 
    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Add pre-embedded documents."""
        self._col.add(documents=documents, metadatas=metadatas, ids=ids)
        log.debug("Added %d docs to vectorstore", len(documents))
 
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Returns list of {document, metadata, distance}."""
        kw = {}
        if where:
            kw["where"] = where
 
        results = self._col.query(
            query_texts=[query_text],
            n_results=min(n_results, max(self._col.count(), 1)),
            **kw,
        )
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"document": doc, "metadata": meta, "distance": dist})
        return output
 
    def count(self) -> int:
        return self._col.count()
 
    def delete_collection(self):
        self._client.delete_collection(self.collection_name)
        log.warning("Collection '%s' deleted", self.collection_name)