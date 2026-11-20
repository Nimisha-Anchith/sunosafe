"""Short spoken warnings in the user's preferred language.

These are fixed, reviewed sentences (not machine translation at alert time),
so a warning is predictable and safe to speak. Detailed explanations come from
the voice agent, which answers in the chosen language.

Languages: English (en), Hindi (hi), Malayalam (ml), Kannada (kn), Tamil (ta).
The sentences are spoken by Murf Falcon (see speech.py), so every language has a
natural voice that does not depend on what is installed on the phone.
"""
from __future__ import annotations

SUPPORTED = ("en", "hi", "ml", "kn", "ta")
NAMES = {"en": "English", "hi": "Hindi", "ml": "Malayalam", "kn": "Kannada", "ta": "Tamil"}


def lang_or_default(lang: str | None) -> str:
    return lang if lang in SUPPORTED else "en"


# Everything a language needs. {brand}, {want} are filled in by the functions below.
_T: dict[str, dict[str, str]] = {
    "hi": {
        "shield_refuse": "माफ़ कीजिए, मैं इसमें मदद नहीं कर सकता। जिन्हें आपने कॉल किया है वे फ़ोन पर कोई कोड या बैंक जानकारी नहीं देते, और असली बैंक कभी ये नहीं माँगते। सुनोसेफ़ ने इस कॉल को दर्ज कर लिया है। नमस्ते।",
        "msg_high": "सावधान। यह संदेश धोखाधड़ी जैसा लगता है। इसका लिंक न खोलें, और कोई OTP, PIN या पासवर्ड किसी को न बताएं।",
        "msg_medium": "ध्यान दें। इस संदेश में कुछ खतरे के संकेत हैं। कोई भी जानकारी देने से पहले रुकें।",
        "call": "सावधान। यह नंबर पहले आए एक धोखाधड़ी संदेश में था। कोई OTP, PIN या बैंक जानकारी न बताएं। "
                "ज़रूरत हो तो बैंक के आधिकारिक नंबर पर खुद कॉल करें।",
        "who": "{brand} के नाम से ",
        "story_both": "आपको {who}एक संदेश और एक कॉल आया है, और दोनों एक ही धोखाधड़ी का हिस्सा लगते हैं।",
        "story_one": "आपको {who}एक संदिग्ध संदेश आया है।",
        "greeting": "नमस्ते, मैं सुनोसेफ़ हूँ। {story} कृपया कोई OTP या PIN न बताएं। "
                    "आप मुझसे पूछ सकते हैं क्यों, या कहें 'ब्लॉक कर दो'।",
        "plain": "नमस्ते, मैं सुनोसेफ़ हूँ। आप मुझसे किसी संदेश, लिंक या कॉल के बारे में पूछ सकते हैं।",
        "drill": "यह सुनोसेफ़ का अभ्यास है, असली कॉल नहीं। अब मैं एक धोखेबाज़ की तरह बात करूँगी, "
                 "ताकि आप 'ना' कहना सीख सकें। कोई असली जानकारी न बताएं। "
                 "नमस्ते जी, मैं आपके बैंक के KYC विभाग से बोल रही हूँ, आपका खाता आज बंद हो जाएगा।",
        "shield": "नमस्ते, यह सुनोसेफ़ कॉल असिस्टेंट है। जिन्हें आपने कॉल किया है, वे अभी बात नहीं कर सकते। "
                  "कृपया बताइए आप कौन हैं और किस काम से कॉल कर रहे हैं।",
        "shield_alert": "सुनोसेफ़ ने आपके लिए एक कॉल उठाया। कॉल करने वाला {who}बात कर रहा था। {want_line}"
                        "यह धोखाधड़ी लगती है। उस नंबर पर वापस कॉल न करें, और कोई OTP या PIN किसी को न बताएं।",
        "want_line": "उसने {want} माँगा। ",
        "otp": "OTP", "pin": "PIN", "password": "पासवर्ड", "remote_app": "एक ऐप डाउनलोड करवाना",
        "money": "पैसे", "card": "कार्ड की जानकारी", "kyc": "KYC अपडेट",
    },
    "ml": {
        "shield_refuse": "ക്ഷമിക്കണം, എനിക്ക് ഇതിൽ സഹായിക്കാൻ കഴിയില്ല. നിങ്ങൾ വിളിച്ച വ്യക്തി ഫോണിൽ കോഡുകളോ ബാങ്ക് വിവരങ്ങളോ നൽകാറില്ല, യഥാർത്ഥ ബാങ്കുകൾ അവ ചോദിക്കാറുമില്ല. ഈ കോൾ സുനോസേഫ് രേഖപ്പെടുത്തി. നമസ്കാരം.",
        "msg_high": "ശ്രദ്ധിക്കൂ. ഈ സന്ദേശം തട്ടിപ്പാണെന്ന് തോന്നുന്നു. ലിങ്ക് തുറക്കരുത്, OTP, PIN, പാസ്‌വേഡ് എന്നിവ ആരോടും പറയരുത്.",
        "msg_medium": "ശ്രദ്ധിക്കൂ. ഈ സന്ദേശത്തിൽ ചില അപകട സൂചനകളുണ്ട്. ഏതെങ്കിലും വിവരം നൽകുന്നതിന് മുമ്പ് നിൽക്കുക.",
        "call": "ശ്രദ്ധിക്കൂ. ഈ നമ്പർ നേരത്തെ വന്ന ഒരു തട്ടിപ്പ് സന്ദേശത്തിൽ ഉണ്ടായിരുന്നു. OTP, PIN, ബാങ്ക് വിവരങ്ങൾ ഒന്നും "
                "പറയരുത്. ആവശ്യമെങ്കിൽ ബാങ്കിന്റെ ഔദ്യോഗിക നമ്പറിൽ നിങ്ങൾ തന്നെ വിളിക്കുക.",
        "who": "{brand} എന്ന പേരിൽ ",
        "story_both": "നിങ്ങൾക്ക് {who}ഒരു സന്ദേശവും ഒരു ഫോൺ കോളും വന്നു, രണ്ടും ഒരേ തട്ടിപ്പിന്റെ ഭാഗമാണെന്ന് തോന്നുന്നു.",
        "story_one": "നിങ്ങൾക്ക് {who}സംശയാസ്പദമായ ഒരു സന്ദേശം വന്നു.",
        "greeting": "നമസ്കാരം, ഞാൻ സുനോസേഫ്. {story} ദയവായി OTP അല്ലെങ്കിൽ PIN പറയരുത്. "
                    "എന്തുകൊണ്ടെന്ന് എന്നോട് ചോദിക്കാം, അല്ലെങ്കിൽ 'ബ്ലോക്ക് ചെയ്യൂ' എന്ന് പറയാം.",
        "plain": "നമസ്കാരം, ഞാൻ സുനോസേഫ്. ഏതെങ്കിലും സന്ദേശത്തെയോ ലിങ്കിനെയോ കോളിനെയോ കുറിച്ച് എന്നോട് ചോദിക്കാം.",
        "drill": "ഇത് സുനോസേഫിന്റെ പരിശീലനമാണ്, യഥാർത്ഥ കോൾ അല്ല. 'ഇല്ല' എന്ന് പറയാൻ പഠിക്കാൻ ഞാൻ ഇപ്പോൾ ഒരു തട്ടിപ്പുകാരനെപ്പോലെ "
                 "സംസാരിക്കും. യഥാർത്ഥ വിവരങ്ങൾ ഒന്നും പറയരുത്. ഹലോ, ഞാൻ നിങ്ങളുടെ ബാങ്കിന്റെ KYC വിഭാഗത്തിൽ നിന്നാണ് "
                 "വിളിക്കുന്നത്. നിങ്ങളുടെ അക്കൗണ്ട് ഇന്ന് ബ്ലോക്ക് ആകും.",
        "shield": "നമസ്കാരം, ഇത് സുനോസേഫ് കോൾ അസിസ്റ്റന്റാണ്. നിങ്ങൾ വിളിച്ച വ്യക്തിക്ക് ഇപ്പോൾ സംസാരിക്കാൻ കഴിയില്ല. "
                  "നിങ്ങൾ ആരാണെന്നും എന്തിനാണ് വിളിക്കുന്നതെന്നും പറയാമോ?",
        "shield_alert": "സുനോസേഫ് നിങ്ങൾക്കായി ഒരു കോൾ എടുത്തു. വിളിച്ചയാൾ {who}സംസാരിച്ചു. {want_line}"
                        "ഇത് തട്ടിപ്പാണെന്ന് തോന്നുന്നു. ആ നമ്പറിലേക്ക് തിരിച്ചു വിളിക്കരുത്, OTP, PIN എന്നിവ ആരോടും പറയരുത്.",
        "want_line": "അയാൾ {want} ചോദിച്ചു. ",
        "otp": "OTP", "pin": "PIN", "password": "പാസ്‌വേഡ്", "remote_app": "ഒരു ആപ്പ് ഇൻസ്റ്റാൾ ചെയ്യാൻ",
        "money": "പണം", "card": "കാർഡ് വിവരങ്ങൾ", "kyc": "KYC അപ്ഡേറ്റ്",
    },
    "kn": {
        "shield_refuse": "ಕ್ಷಮಿಸಿ, ಇದರಲ್ಲಿ ನಾನು ಸಹಾಯ ಮಾಡಲಾಗುವುದಿಲ್ಲ. ನೀವು ಕರೆ ಮಾಡಿದ ವ್ಯಕ್ತಿ ಫೋನಿನಲ್ಲಿ ಕೋಡ್ ಅಥವಾ ಬ್ಯಾಂಕ್ ವಿವರಗಳನ್ನು ನೀಡುವುದಿಲ್ಲ, ನಿಜವಾದ ಬ್ಯಾಂಕುಗಳು ಅವನ್ನು ಕೇಳುವುದೂ ಇಲ್ಲ. ಈ ಕರೆಯನ್ನು ಸುನೋಸೇಫ್ ದಾಖಲಿಸಿದೆ. ನಮಸ್ಕಾರ.",
        "msg_high": "ಎಚ್ಚರಿಕೆ. ಈ ಸಂದೇಶ ವಂಚನೆಯಂತೆ ಕಾಣುತ್ತಿದೆ. ಲಿಂಕ್ ತೆರೆಯಬೇಡಿ, OTP, PIN ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
        "msg_medium": "ಗಮನಿಸಿ. ಈ ಸಂದೇಶದಲ್ಲಿ ಕೆಲವು ಅಪಾಯದ ಸೂಚನೆಗಳಿವೆ. ಯಾವುದೇ ಮಾಹಿತಿ ನೀಡುವ ಮೊದಲು ನಿಲ್ಲಿ.",
        "call": "ಎಚ್ಚರಿಕೆ. ಈ ಸಂಖ್ಯೆ ಮೊದಲು ಬಂದ ಒಂದು ವಂಚನೆಯ ಸಂದೇಶದಲ್ಲಿ ಇತ್ತು. OTP, PIN ಅಥವಾ ಬ್ಯಾಂಕ್ ವಿವರಗಳನ್ನು ಹೇಳಬೇಡಿ. "
                "ಬೇಕಾದರೆ ಬ್ಯಾಂಕಿನ ಅಧಿಕೃತ ಸಂಖ್ಯೆಗೆ ನೀವೇ ಕರೆ ಮಾಡಿ.",
        "who": "{brand} ಹೆಸರಿನಲ್ಲಿ ",
        "story_both": "ನಿಮಗೆ {who}ಒಂದು ಸಂದೇಶ ಮತ್ತು ಒಂದು ಫೋನ್ ಕರೆ ಬಂದಿದೆ, ಎರಡೂ ಒಂದೇ ವಂಚನೆಯ ಭಾಗದಂತೆ ಕಾಣುತ್ತವೆ.",
        "story_one": "ನಿಮಗೆ {who}ಒಂದು ಅನುಮಾನಾಸ್ಪದ ಸಂದೇಶ ಬಂದಿದೆ.",
        "greeting": "ನಮಸ್ಕಾರ, ನಾನು ಸುನೋಸೇಫ್. {story} ದಯವಿಟ್ಟು OTP ಅಥವಾ PIN ಹೇಳಬೇಡಿ. "
                    "ಯಾಕೆ ಎಂದು ನನ್ನನ್ನು ಕೇಳಬಹುದು, ಅಥವಾ 'ಬ್ಲಾಕ್ ಮಾಡಿ' ಎಂದು ಹೇಳಬಹುದು.",
        "plain": "ನಮಸ್ಕಾರ, ನಾನು ಸುನೋಸೇಫ್. ಯಾವುದೇ ಸಂದೇಶ, ಲಿಂಕ್ ಅಥವಾ ಕರೆಯ ಬಗ್ಗೆ ನನ್ನನ್ನು ಕೇಳಬಹುದು.",
        "drill": "ಇದು ಸುನೋಸೇಫ್‌ನ ಅಭ್ಯಾಸ, ನಿಜವಾದ ಕರೆ ಅಲ್ಲ. ನೀವು 'ಇಲ್ಲ' ಎಂದು ಹೇಳಲು ಕಲಿಯಲು ನಾನು ಈಗ ವಂಚಕನಂತೆ ಮಾತನಾಡುತ್ತೇನೆ. "
                 "ನಿಜವಾದ ಮಾಹಿತಿ ಯಾವುದನ್ನೂ ಹೇಳಬೇಡಿ. ಹಲೋ, ನಾನು ನಿಮ್ಮ ಬ್ಯಾಂಕಿನ KYC ವಿಭಾಗದಿಂದ ಕರೆ ಮಾಡುತ್ತಿದ್ದೇನೆ. "
                 "ನಿಮ್ಮ ಖಾತೆ ಇಂದು ಬಂದ್ ಆಗುತ್ತದೆ.",
        "shield": "ನಮಸ್ಕಾರ, ಇದು ಸುನೋಸೇಫ್ ಕರೆ ಸಹಾಯಕ. ನೀವು ಕರೆ ಮಾಡಿದ ವ್ಯಕ್ತಿ ಈಗ ಮಾತನಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ. "
                  "ನೀವು ಯಾರು ಮತ್ತು ಯಾಕೆ ಕರೆ ಮಾಡುತ್ತಿದ್ದೀರಿ ಎಂದು ಹೇಳುತ್ತೀರಾ?",
        "shield_alert": "ಸುನೋಸೇಫ್ ನಿಮಗಾಗಿ ಒಂದು ಕರೆ ತೆಗೆದುಕೊಂಡಿತು. ಕರೆ ಮಾಡಿದವರು {who}ಮಾತನಾಡಿದರು. {want_line}"
                        "ಇದು ವಂಚನೆಯಂತೆ ಕಾಣುತ್ತಿದೆ. ಆ ಸಂಖ್ಯೆಗೆ ಮರಳಿ ಕರೆ ಮಾಡಬೇಡಿ, OTP ಅಥವಾ PIN ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
        "want_line": "ಅವರು {want} ಕೇಳಿದರು. ",
        "otp": "OTP", "pin": "PIN", "password": "ಪಾಸ್‌ವರ್ಡ್", "remote_app": "ಒಂದು ಆ್ಯಪ್ ಇನ್‌ಸ್ಟಾಲ್ ಮಾಡಲು",
        "money": "ಹಣ", "card": "ಕಾರ್ಡ್ ವಿವರಗಳು", "kyc": "KYC ಅಪ್‌ಡೇಟ್",
    },
    "ta": {
        "shield_refuse": "மன்னிக்கவும், இதில் என்னால் உதவ முடியாது. நீங்கள் அழைத்தவர் தொலைபேசியில் குறியீடுகள் அல்லது வங்கி விவரங்களைத் தருவதில்லை, உண்மையான வங்கிகளும் அவற்றைக் கேட்பதில்லை. இந்த அழைப்பை சுனோசேஃப் பதிவு செய்துள்ளது. வணக்கம்.",
        "msg_high": "எச்சரிக்கை. இந்த செய்தி மோசடி போல் தெரிகிறது. இணைப்பைத் திறக்காதீர்கள், OTP, PIN, கடவுச்சொல்லை யாரிடமும் சொல்லாதீர்கள்.",
        "msg_medium": "கவனியுங்கள். இந்த செய்தியில் சில ஆபத்து அறிகுறிகள் உள்ளன. எந்தத் தகவலையும் கொடுக்கும் முன் நிறுத்துங்கள்.",
        "call": "எச்சரிக்கை. இந்த எண் முன்பு வந்த ஒரு மோசடி செய்தியில் இருந்தது. OTP, PIN அல்லது வங்கி விவரங்களைச் சொல்லாதீர்கள். "
                "தேவைப்பட்டால் வங்கியின் அதிகாரப்பூர்வ எண்ணை நீங்களே அழையுங்கள்.",
        "who": "{brand} என்ற பெயரில் ",
        "story_both": "உங்களுக்கு {who}ஒரு செய்தியும் ஒரு தொலைபேசி அழைப்பும் வந்துள்ளன, இரண்டும் ஒரே மோசடியின் பகுதியாகத் தெரிகிறது.",
        "story_one": "உங்களுக்கு {who}சந்தேகத்திற்குரிய ஒரு செய்தி வந்துள்ளது.",
        "greeting": "வணக்கம், நான் சுனோசேஃப். {story} தயவுசெய்து OTP அல்லது PIN சொல்லாதீர்கள். "
                    "ஏன் என்று என்னிடம் கேட்கலாம், அல்லது 'பிளாக் செய்' என்று சொல்லலாம்.",
        "plain": "வணக்கம், நான் சுனோசேஃப். எந்தச் செய்தி, இணைப்பு அல்லது அழைப்பு பற்றியும் என்னிடம் கேட்கலாம்.",
        "drill": "இது சுனோசேஃபின் பயிற்சி, உண்மையான அழைப்பு அல்ல. நீங்கள் 'இல்லை' என்று சொல்லக் கற்றுக்கொள்ள நான் இப்போது ஒரு "
                 "மோசடிக்காரர் போல் பேசுவேன். உண்மையான தகவல் எதையும் சொல்லாதீர்கள். வணக்கம், நான் உங்கள் வங்கியின் KYC "
                 "பிரிவிலிருந்து அழைக்கிறேன். உங்கள் கணக்கு இன்று முடக்கப்படும்.",
        "shield": "வணக்கம், இது சுனோசேஃப் அழைப்பு உதவியாளர். நீங்கள் அழைத்தவர் இப்போது பேச முடியாது. "
                  "நீங்கள் யார், ஏன் அழைக்கிறீர்கள் என்று சொல்லுங்களா?",
        "shield_alert": "சுனோசேஃப் உங்களுக்காக ஒரு அழைப்பை எடுத்தது. அழைத்தவர் {who}பேசினார். {want_line}"
                        "இது மோசடி போல் தெரிகிறது. அந்த எண்ணுக்கு திரும்ப அழைக்காதீர்கள், OTP அல்லது PIN யாரிடமும் சொல்லாதீர்கள்.",
        "want_line": "அவர் {want} கேட்டார். ",
        "otp": "OTP", "pin": "PIN", "password": "கடவுச்சொல்", "remote_app": "ஒரு செயலியை நிறுவ",
        "money": "பணம்", "card": "அட்டை விவரங்கள்", "kyc": "KYC புதுப்பிப்பு",
    },
}


def message_alert(lang: str, level: str, english_summary: str) -> str:
    """Spoken when a notification looks dangerous."""
    t = _T.get(lang)
    if t is None:
        return english_summary
    return t["msg_high"] if level in ("high", "critical") else t["msg_medium"]


def call_alert(lang: str) -> str:
    """Spoken while the phone rings, when the caller's number appeared in a scam message."""
    t = _T.get(lang)
    if t:
        return t["call"]
    return ("Careful. This caller's number appeared in a scam message you received. "
            "Do not share any OTP, PIN or bank details. If needed, call your bank yourself on its official number.")


def plain_greeting(lang: str) -> str:
    """Opening line of the voice agent when it is not opened from a warning."""
    t = _T.get(lang)
    return t["plain"] if t else "Namaste, I am SunoSafe. You can ask me about a message, a link or a call."


# What a scam was about, when no company name was claimed (used in the voice agent's first sentence).
TOPICS = {
    "police": {"en": "about a fake police or customs case", "hi": "नकली पुलिस या कस्टम केस के बारे में ",
               "ml": "വ്യാജ പോലീസ് അല്ലെങ്കിൽ കസ്റ്റംസ് കേസിനെക്കുറിച്ച് ", "kn": "ನಕಲಿ ಪೊಲೀಸ್ ಅಥವಾ ಕಸ್ಟಮ್ಸ್ ಪ್ರಕರಣದ ಬಗ್ಗೆ ",
               "ta": "போலி காவல்துறை அல்லது சுங்க வழக்கு பற்றி "},
    "electricity": {"en": "about cutting your electricity", "hi": "बिजली काटने के बारे में ",
                    "ml": "വൈദ്യുതി വിച്ഛേദിക്കുന്നതിനെക്കുറിച്ച് ", "kn": "ವಿದ್ಯುತ್ ಕಡಿತದ ಬಗ್ಗೆ ",
                    "ta": "மின்சாரம் துண்டிப்பு பற்றி "},
    "prize": {"en": "about a prize or refund", "hi": "इनाम या रिफंड के बारे में ", "ml": "സമ്മാനം അല്ലെങ്കിൽ റീഫണ്ടിനെക്കുറിച്ച് ",
              "kn": "ಬಹುಮಾನ ಅಥವಾ ರಿಫಂಡ್ ಬಗ್ಗೆ ", "ta": "பரிசு அல்லது பணம் திரும்பப் பெறுவது பற்றி "},
}


def voice_greeting(lang: str, severity: str, brand: str | None, by_message_and_call: bool,
                   topic: str | None = None) -> str:
    """First thing the voice agent says when opened from a SunoSafe warning.
    `brand` = the company the latest scam claimed to be; otherwise `topic` = what it was about."""
    t = _T.get(lang)
    about = TOPICS.get(topic or "", {}).get(lang) if not brand else None
    if t:
        who = t["who"].format(brand=brand) if brand else (about or "")
        story = (t["story_both"] if by_message_and_call else t["story_one"]).format(who=who)
        return t["greeting"].format(story=story)
    who = f" pretending to be {brand}" if brand else (f" {about}" if about else "")
    if by_message_and_call:
        story = f"A message and a phone call{who} reached you, and they look like the same scam."
    else:
        story = f"A suspicious message{who} reached you."
    calm = "Please stay calm and do not share any OTP or PIN."
    return f"Namaste, SunoSafe here with a safety warning. {story} {calm} You can ask me why, or say block it."


def drill_greeting(lang: str) -> str:
    """Opening line of the scam-practice drill."""
    t = _T.get(lang)
    if t:
        return t["drill"]
    return ("This is a SunoSafe practice drill, not a real call. I will now pretend to be a scam caller "
            "so you can practise saying no. Never say any real details. "
            "Hello, I am calling from your bank's KYC department. Your account will be blocked today.")


# ---------------------------------------------------------------- call shield
def shield_greeting(lang: str) -> str:
    """What SunoSafe says when it answers a forwarded call for the user (the CALLER hears this)."""
    t = _T.get(lang)
    if t:
        return t["shield"]
    return ("Hello, this is the SunoSafe call assistant. The person you called cannot take this call right now. "
            "Please tell me who you are and why you are calling.")


def shield_alert(lang: str, brand: str | None, asked: list[str]) -> str:
    """Spoken to the USER on their phone after SunoSafe screened a scam call for them."""
    t = _T.get(lang)
    if t:
        who = t["who"].format(brand=brand) if brand else ""
        want = ", ".join(t[a] for a in asked if a in t and a in _ASKS)
        want_line = t["want_line"].format(want=want) if want else ""
        return t["shield_alert"].format(who=who, want_line=want_line)
    asks_en = {"otp": "an OTP", "pin": "a PIN", "password": "a password", "remote_app": "to install an app",
               "money": "money", "card": "card details", "kyc": "a KYC update"}
    who = f" The caller claimed to be {brand}." if brand else ""
    want = ", ".join(asks_en[a] for a in asked if a in asks_en)
    want_line = f" They asked for {want}." if want else ""
    return (f"SunoSafe answered a call for you.{who}{want_line} "
            "This looks like a scam. Do not call that number back, and never share an OTP or PIN.")


_ASKS = ("otp", "pin", "password", "remote_app", "money", "card", "kyc")


def shield_refuse(lang: str) -> str:
    """Fixed reply when a caller to the call assistant asks for a secret. Spoken to the CALLER."""
    t = _T.get(lang)
    if t:
        return t["shield_refuse"]
    return ("I am sorry, I cannot help with that. The person you called never shares codes or bank details on the phone, "
            "and genuine banks never ask for them. This call has been noted by SunoSafe. Goodbye.")
