import csv
import logging
from datetime import datetime
from pathlib import Path
 
log = logging.getLogger(__name__)
 
LOG_FILE = Path("admin/logs/interactions.csv")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
 
_HEADERS = ["timestamp", "session_id", "role", "user_input", "response_preview", "language"]
 
def _ensure_header():
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(_HEADERS)
 
 
def log_interaction(session_id: str, role: str, user_input: str,
                    response: str, language: str):
    _ensure_header()
    try:
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