import csv
import logging
from datetime import datetime
from pathlib import Path
 
log = logging.getLogger(__name__)
 
# Resolved against the repository, not the current working directory, and not
# created at import time. Importing this module used to make an admin/logs
# directory wherever the process happened to be started from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = _REPO_ROOT / "admin" / "logs" / "interactions.csv"

_HEADERS = ["timestamp", "session_id", "role", "user_input", "response_preview", "language"]


def _ensure_header():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(_HEADERS)


 
def log_interaction(session_id: str, role: str, user_input: str,
                    response: str, language: str):
    # _ensure_header is inside the try as well: it creates a directory and
    # writes a file, and a read-only or full disk there should not take down a
    # conversation turn.
    try:
        _ensure_header()
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(),
                session_id,
                role,
                user_input[:200],
                response[:200],
                language,
            ])
    except Exception as e:
        log.warning("Failed to log interaction: %s", e)