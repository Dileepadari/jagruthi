#!/usr/bin/env python3
"""
Asserts config.yaml parses and carries every key the code actually reads.

A missing key here is a KeyError partway through a conversation turn, on a
kiosk, with nobody watching the journal.
"""
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# path -> the module that would blow up without it
REQUIRED = {
    ("app", "name"): "main.py",
    ("app", "wake_word"): "wake/detector.py",
    ("app", "session_timeout"): "core/pipeline.py",
    ("stt", "model"): "stt/transcriber.py",
    ("stt", "language"): "stt/transcriber.py",
    ("tts", "engine"): "tts/synthesizer.py",
    ("tts", "voices"): "tts/synthesizer.py",
    ("llm", "primary"): "llm/router.py",
    ("llm", "fallback"): "llm/router.py",
    ("llm", "groq", "model"): "llm/groq_client.py",
    ("llm", "ollama", "model"): "llm/ollama_client.py",
    ("llm", "ollama", "host"): "llm/ollama_client.py",
    ("rag", "chunk_size"): "rag/ingestion.py",
    ("rag", "retrieval_k"): "rag/retriever.py",
    ("rag", "embeddings_model"): "rag/embeddings.py",
    ("rag", "db_path"): "rag/vectorstore.py",
    ("rag", "collection_name"): "rag/vectorstore.py",
    ("audio", "sample_rate"): "stt/audio_capture.py",
    ("audio", "chunk_duration_ms"): "wake/detector.py",
    ("roles", "default"): "modules/role_manager.py",
    ("emotional", "enabled"): "modules/emotional_support.py",
    ("emotional", "crisis_escalation"): "modules/emotional_support.py",
    ("emotional", "counsellor_name"): "modules/emotional_support.py",
    ("emotional", "counsellor_room"): "modules/emotional_support.py",
    ("emotional", "counsellor_contact"): "modules/emotional_support.py",
    ("scheduler", "enabled"): "modules/scheduler.py",
    ("campus", "name"): "core/pipeline.py",
    ("logging", "level"): "main.py",
}


def get(cfg, path):
    node = cfg
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def main() -> int:
    cfg = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    failures = 0

    for path, used_by in REQUIRED.items():
        if get(cfg, path) is None:
            print(f"FAIL missing config key {'.'.join(path)}  (read by {used_by})")
            failures += 1

    # Every prompt the code formats must exist and must not leave a stray
    # placeholder unfilled at runtime.
    for name in ("system_emotional", "system_friend", "system_institutional", "system_rolebase"):
        p = REPO_ROOT / "llm" / "prompts" / f"{name}.txt"
        if not p.exists():
            print(f"FAIL missing prompt file {p.relative_to(REPO_ROOT)}")
            failures += 1

    # The counsellor contact is what a student in crisis is told to ring. A
    # placeholder is allowed to ship (this is a template repo) but must be
    # visible, not silent.
    sys.path.insert(0, str(REPO_ROOT))
    from modules.emotional_support import looks_like_placeholder

    contact = get(cfg, ("emotional", "counsellor_contact"))
    if looks_like_placeholder(str(contact or "")):
        print(
            f"WARN emotional.counsellor_contact is still a placeholder ({contact!r}). "
            "Crisis escalation will name the counsellor but give no number."
        )

    if failures:
        print(f"\nconfig check: {failures} problem(s)")
        return 1
    print("config check: every key the code reads is present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
