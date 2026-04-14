import re
 
ROLE_KEYWORDS = {
    "faculty":  ["professor", "faculty", "teacher", "lecturer", "dr.", "sir", "ma'am",
                  "i teach", "my students", "hod"],
    "staff":    ["staff", "admin", "office", "hr", "accounts", "maintenance", "warden"],
    "student":  ["student", "i study", "my course", "my class", "semester", "btech",
                  "mtech", "year student"],
}
 
 
def detect_role(text: str) -> str | None:
    """
    Returns detected role string or None if unclear.
    Called on the first utterance of a session.
    """
    t = text.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(k in t for k in keywords):
            return role
    return None
 
 
def role_greeting(role: str, campus: str) -> str:
    greetings = {
        "student": f"Hello! I'm Jagruthi, your campus assistant at {campus}. How can I help you today?",
        "faculty": f"Good day! I'm Jagruthi, the campus information assistant at {campus}. How may I assist you?",
        "staff":   f"Hello! I'm Jagruthi. What information do you need today?",
    }
    return greetings.get(role, greetings["student"])