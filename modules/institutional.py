# High-level convenience wrappers used by the admin CLI
# The main RAG answering logic lives in rag/rag_chain.py
 
from pathlib import Path
 
 
def list_knowledge_sources() -> list[str]:
    raw = Path("knowledge_base/raw")
    sources = []
    for f in sorted(raw.rglob("*")):
        if f.is_file():
            sources.append(str(f.relative_to(raw)))
    return sources
 
 
def document_count(vectorstore) -> int:
    return vectorstore.count()