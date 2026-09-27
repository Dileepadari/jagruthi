# High-level convenience wrappers used by the admin CLI
# The main RAG answering logic lives in rag/rag_chain.py
 
from pathlib import Path

# Repo-relative, not cwd-relative: the systemd unit sets WorkingDirectory
# so production was fine, but running this from anywhere else looked in
# the wrong place and failed mid-run.
_REPO_ROOT = Path(__file__).resolve().parent.parent
 
 
def list_knowledge_sources() -> list[str]:
    raw = _REPO_ROOT / "knowledge_base" / "raw"
    sources = []
    for f in sorted(raw.rglob("*")):
        if f.is_file():
            sources.append(str(f.relative_to(raw)))
    return sources
 
 
def document_count(vectorstore) -> int:
    return vectorstore.count()