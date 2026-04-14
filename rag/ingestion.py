import hashlib
import logging
from pathlib import Path
from typing import Iterator
 
log = logging.getLogger(__name__)
 
CHUNK_SIZE    = 512
CHUNK_OVERLAP = 50
 
 
def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words  = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        chunks.append(chunk)
        i += size - overlap
    return [c for c in chunks if len(c.strip()) > 30]
 
 
def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".docx", ".doc"):
        return _extract_docx(path)
    elif suffix == ".txt":
        return path.read_text(errors="ignore")
    elif suffix == ".csv":
        return _extract_csv(path)
    else:
        log.warning("Unsupported file type: %s", suffix)
        return ""
 
 
def _extract_pdf(path: Path) -> str:
    import fitz  # PyMuPDF
    text = []
    with fitz.open(path) as doc:
        for page in doc:
            text.append(page.get_text())
    return "\\n".join(text)
 
 
def _extract_docx(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    return "\\n".join(p.text for p in doc.paragraphs)
 
 
def _extract_csv(path: Path) -> str:
    import pandas as pd
    df = pd.read_csv(path)
    return df.to_string(index=False)
 
 
def ingest_directory(
    directory: Path,
    role_visibility: list[str] | None = None,
) -> Iterator[tuple[str, dict, str]]:
    """
    Yields (chunk_text, metadata, doc_id) tuples for all documents
    in `directory` recursively.
    """
    if role_visibility is None:
        role_visibility = ["student", "faculty", "staff"]
 
    for fpath in sorted(directory.rglob("*")):
        if fpath.is_dir() or fpath.suffix.lower() not in \
                (".pdf", ".docx", ".doc", ".txt", ".csv"):
            continue
 
        log.info("Ingesting: %s", fpath)
        raw = _extract_text(fpath)
        if not raw.strip():
            log.warning("Empty extract: %s", fpath)
            continue
 
        chunks = _chunk_text(raw)
        log.debug("  → %d chunks", len(chunks))
 
        doc_type = fpath.parent.name   # folder name = doc_type (timetables, etc.)
        for i, chunk in enumerate(chunks):
            uid = hashlib.md5(f"{fpath}_{i}".encode()).hexdigest()
            meta = {
                "source":           str(fpath.name),
                "doc_type":         doc_type,
                "role_visibility":  ",".join(role_visibility),
                "chunk_index":      i,
            }
            yield chunk, meta, uid