"""Short spoken warnings in the user's preferred language.

These are fixed, reviewed sentences (not machine translation at alert time),
so a warning can be spoken instantly and offline on the phone. Detailed
explanations come from the voice agent, which answers in the chosen language.

Languages: English (en) and Hindi (hi) are written here. Other languages fall
back to English for the instant phone warning; the voice agent itself can
still reply in Malayalam, Kannada or Tamil.
"""
from __future__ import annotations

SUPPORTED = ("en", "hi", "ml", "kn", "ta")
NAMES = {"en": "English", "hi": "Hindi", "ml": "Malayalam", "kn": "Kannada", "ta": "Tamil"}


def lang_or_default(lang: str | None) -> str:
    return lang if lang in SUPPORTED else "en"


def message_alert(lang: str, level: str, english_summary: str) -> str:
    """Spoken when a notification looks dangerous."""
    if lang == "hi":
        if level in ("high", "critical"):
            return ("सावधान। यह संदेश धोखाधड़ी जैसा लगता है। इसका लिंक न खोलें, "
                    "और कोई OTP, PIN या पासवर्ड किसी को न बताएं।")
        return "ध्यान दें। इस संदेश में कुछ खतरे के संकेत हैं। कोई भी जानकारी देने से पहले रुकें।"
    return english_summary


def call_alert(lang: str) -> str:
    """Spoken while the phone rings, when the caller's number appeared in a scam message."""
    if lang == "hi":
        return ("सावधान। यह नंबर पहले आए एक धोखाधड़ी संदेश में था। "
                "कोई OTP, PIN या बैंक जानकारी न बताएं। ज़रूरत हो तो बैंक के आधिकारिक नंबर पर खुद कॉल करें।")
    return ("Careful. This caller's number appeared in a scam message you received. "
            "Do not share any OTP, PIN or bank details. If needed, call your bank yourself on its official number.")


def voice_greeting(lang: str, severity: str, brand: str | None, by_message_and_call: bool) -> str:
    """First thing the voice agent says when opened from a SunoSafe warning."""
    if lang == "hi":
        who = f"{brand} के नाम से " if brand else ""
        if by_message_and_call:
            story = f"आपको {who}एक संदेश और एक कॉल आया है, और दोनों एक ही धोखाधड़ी का हिस्सा लगते हैं।"
        else:
            story = f"आपको {who}एक संदिग्ध संदेश आया है।"
        return (f"नमस्ते, मैं सुनोसेफ़ हूँ। {story} कृपया कोई OTP या PIN न बताएं। "
                "आप मुझसे पूछ सकते हैं क्यों, या कहें 'ब्लॉक कर दो'।")
    who = f" pretending to be {brand}" if brand else ""
    if by_message_and_call:
        story = f"A message and a phone call{who} reached you, and they look like the same scam."
    else:
        story = f"A suspicious message{who} reached you."
    calm = "Please stay calm and do not share any OTP or PIN."
    return f"Namaste, SunoSafe here with a safety warning. {story} {calm} You can ask me why, or say block it."


def drill_greeting(lang: str) -> str:
    """Opening line of the scam-practice drill."""
    if lang == "hi":
        return ("यह सुनोसेफ़ का अभ्यास है, असली कॉल नहीं। अब मैं एक धोखेबाज़ की तरह बात करूँगी, "
                "ताकि आप 'ना' कहना सीख सकें। कोई असली जानकारी न बताएं। "
                "नमस्ते जी, मैं आपके बैंक के KYC विभाग से बोल रही हूँ, आपका खाता आज बंद हो जाएगा।")
    return ("This is a SunoSafe practice drill, not a real call. I will now pretend to be a scam caller "
            "so you can practise saying no. Never say any real details. "
            "Hello, I am calling from your bank's KYC department. Your account will be blocked today.")
