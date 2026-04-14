# Whisper already returns language code during transcription.
# This module provides a lookup for Piper voice selection.
 
LANG_TO_VOICE = {
    "en": "en_US-lessac-medium",
    "hi": "hi_IN-hfc_female-medium",
    "te": "te_IN-*",
    "ta": "en_US-lessac-medium",   # fallback Tamil -> English TTS for now
}
 
LANG_DISPLAY = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}
 
 
def get_voice_for_lang(lang_code: str) -> str:
    return LANG_TO_VOICE.get(lang_code, "en_US-lessac-medium")
 
 
def display_name(lang_code: str) -> str:
    return LANG_DISPLAY.get(lang_code, lang_code)