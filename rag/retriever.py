import logging
 
log = logging.getLogger(__name__)
 
 
class Retriever:
    def __init__(self, vectorstore, config: dict):
        self.vs  = vectorstore
        self.k   = config["rag"]["retrieval_k"]
 
    def retrieve(self, query: str, role: str = "student") -> list[str]:
        """
        Returns top-k relevant chunks.
        Filters by role_visibility so staff-only docs don't surface for students.
        """
        # ChromaDB where filter uses $contains on a comma-separated string
        # We query without filter first, then post-filter (simpler + more compatible)
        results = self.vs.query(query, n_results=self.k * 2)
 
        filtered = []
        for r in results:
            vis = r["metadata"].get("role_visibility", "student,faculty,staff")
            if role in vis:
                filtered.append(r["document"])
            if len(filtered) >= self.k:
                break
 
        log.debug("Retrieved %d chunks for role=%s", len(filtered), role)
        return filtered