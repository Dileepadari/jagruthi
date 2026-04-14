#!/usr/bin/env python3
"""
CLI tool to (re-)ingest documents into the Jagruthi knowledge base.
 
Usage:
    python3 admin/ingest_cli.py                    # ingest everything in knowledge_base/raw
    python3 admin/ingest_cli.py --reset            # wipe DB and re-ingest
    python3 admin/ingest_cli.py --file path.pdf    # ingest single file
    python3 admin/ingest_cli.py --status           # show DB stats
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
 
import argparse
import logging
from pathlib import Path
 
import yaml
from dotenv import load_dotenv
 
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("ingest_cli")
 
 
def main():
    parser = argparse.ArgumentParser(description="Jagruthi Knowledge Base Ingestion CLI")
    parser.add_argument("--reset",  action="store_true", help="Wipe vectorstore and re-ingest all")
    parser.add_argument("--file",   type=str, help="Ingest a single file")
    parser.add_argument("--status", action="store_true", help="Show vectorstore stats")
    args = parser.parse_args()
 
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
 
    from rag.vectorstore import VectorStore
    from rag.ingestion import ingest_directory, _extract_text, _chunk_text
 
    vs = VectorStore(config)
 
    if args.status:
        print(f"\\nVectorstore: {config['rag']['db_path']}")
        print(f"Collection:  {config['rag']['collection_name']}")
        print(f"Documents:   {vs.count()} chunks")
        return
 
    if args.reset:
        log.warning("Resetting vectorstore...")
        vs.delete_collection()
        vs = VectorStore(config)
 
    if args.file:
        path = Path(args.file)
        if not path.exists():
            log.error("File not found: %s", path)
            return
        log.info("Ingesting single file: %s", path)
        raw  = _extract_text(path)
        chunks = _chunk_text(raw)
        import hashlib
        docs, metas, ids = [], [], []
        for i, chunk in enumerate(chunks):
            uid = hashlib.md5(f"{path}_{i}".encode()).hexdigest()
            docs.append(chunk)
            metas.append({"source": path.name, "doc_type": path.parent.name,
                          "role_visibility": "student,faculty,staff", "chunk_index": i})
            ids.append(uid)
        vs.add(docs, metas, ids)
        log.info("Added %d chunks from %s", len(docs), path.name)
        return
 
    # Default: ingest all
    raw_dir = Path("knowledge_base/raw")
    log.info("Ingesting all documents from %s ...", raw_dir)
    from rag.ingestion import ingest_directory
    docs, metas, ids = [], [], []
    count = 0
 
    for chunk, meta, uid in ingest_directory(raw_dir):
        docs.append(chunk)
        metas.append(meta)
        ids.append(uid)
        if len(docs) >= 500:
            vs.add(docs, metas, ids)
            count += len(docs)
            log.info("  Committed %d chunks so far...", count)
            docs, metas, ids = [], [], []
 
    if docs:
        vs.add(docs, metas, ids)
        count += len(docs)
 
    log.info("Done. Total chunks in DB: %d", vs.count())
 
 
if __name__ == "__main__":
    main()