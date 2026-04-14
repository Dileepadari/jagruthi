# Language utilities used across modules.
 
SUPPORTED = {"en", "hi", "te"}
 
LANG_NAME = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "te": "Telugu (తెలుగు)",
}
 
 
def detect_language_code(lang: str) -> str:
    """Normalise Whisper language codes."""
    if not lang:
        return "en"
    lang = lang.lower().split("-")[0]  # e.g. 'en-US' → 'en'
    return lang if lang in SUPPORTED else "en"
 
 
def greeting_in_lang(lang: str) -> str:
    return {
        "en": "Hello! I'm Jagruthi. How can I help you?",
        "hi": "Namaste! Main Jagruthi hoon. Main aapki kaise madad kar sakta hoon?",
        "te": "Namaskaram! Nenu Jagruthi. Meeru em cheppali?",
    }.get(lang, "Hello! I'm Jagruthi. How can I help you?")