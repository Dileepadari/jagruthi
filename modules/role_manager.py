import re

ROLE_KEYWORDS = {
    "faculty": ["professor", "faculty", "teacher", "lecturer", "dr.", "sir", "ma'am",
                "i teach", "my students", "hod"],
    "staff": ["staff", "admin", "office", "hr", "accounts", "maintenance", "warden"],
    "student": ["student", "i study", "my course", "my class", "semester", "btech",
                "mtech", "year student"],
}


def _compile(keyword: str) -> re.Pattern:
    """
    Word-boundary matcher for one keyword.

    These used to be plain substring tests, which is why an ordinary question
    was routed to the wrong role and the wrong system prompt:

        "I desire to know the exam date"    -> faculty   ("sir" inside "desire")
        "three days left"                   -> staff     ("hr" inside "three")
        "what is the method for applying"   -> faculty   ("hod" inside "method")

    A trailing "." as in "dr." is a literal, not a wildcard, and must not
    require a word character after it.
    """
    escaped = re.escape(keyword)
    prefix = r"\b" if keyword[0].isalnum() else ""
    suffix = r"\b" if keyword[-1].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


_ROLE_PATTERNS = {
    role: [_compile(k) for k in keywords] for role, keywords in ROLE_KEYWORDS.items()
}


def detect_role(text: str) -> str | None:
    """
    Returns a detected role, or None if unclear.
    Called on the first utterance of a session.
    """
    if not text:
        return None
    for role, patterns in _ROLE_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            return role
    return None


def role_greeting(role: str, campus: str) -> str:
    greetings = {
        "student": f"Hello! I'm Jagruthi, your campus assistant at {campus}. How can I help you today?",
        "faculty": f"Good day! I'm Jagruthi, the campus information assistant at {campus}. How may I assist you?",
        "staff": "Hello! I'm Jagruthi. What information do you need today?",
    }
    return greetings.get(role, greetings["student"])
