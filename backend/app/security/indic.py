"""Make Hindi, Malayalam, Kannada and Tamil text readable by the scam rules.

The rules in message_rules.py are written for English and romanised Hindi. A real
phone call transcribed by speech-to-text, or a WhatsApp message in an Indian
language, arrives in native script: "आपका ओटीपी बताइए", "നിങ്ങളുടെ ഒടിപി പറയൂ".
Before the rules run, `gloss()` replaces the scam-relevant words of each script
with the canonical English words the rules already understand, in place, so word
order and distance are kept:

    "मैं एसबीआई से बोल रहा हूँ, ओटीपी बताइए"  ->  "मैं  SBI  से बोल रहा हूँ,  OTP   tell "
    "ओटीपी किसी के साथ साझा न करें"            ->  " OTP  किसी के साथ  do not share "   (a genuine warning)

This is a reviewed word list, not machine translation: deterministic, explainable,
and it cannot be talked into anything. It is deliberately limited to the vocabulary
of common Indian phone and message scams. "Do not ..." forms come first, because
real banks write "never share your OTP" and that must not look like a request.

Limits: spelling variants not in the list are missed; the Malayalam, Kannada and
Tamil lists were written without a native-speaker review.
"""
from __future__ import annotations

import re

_ZERO_WIDTH = re.compile("[​-‍﻿]")


def _compile(script_range: str, pairs: list[tuple[str, str]]) -> list[tuple[re.Pattern, str]]:
    """`{W}` in a pattern means "not next to another letter of this script" (a whole word)."""
    not_before, not_after = f"(?<![{script_range}])", f"(?![{script_range}])"
    out = []
    for pattern, english in pairs:
        pattern = pattern.replace("{W<}", not_before).replace("{W>}", not_after)
        out.append((re.compile(pattern), f" {english} "))
    return out


# ------------------------------------------------------------------ Hindi (Devanagari)
_HI = _compile("ऀ-ॿ", [
    # "do not share / tell" first
    (r"(साझा|सांझा|शेयर)\s+(न|ना|मत|नहीं)\s+(करें|करे|कीजिए|कीजिये|करना|करो|करिए)", "do not share"),
    (r"{W<}(कभी\s+)?(न|ना|मत|नहीं)\s+(बताएं|बताएँ|बताइए|बताइये|बताना|बताओ|बताए|बताये|दें|दीजिए|देना|भेजें|भेजिए|भेजना|"
     r"डालें|डालिए|डालना)", "do not tell"),
    (r"(बताना|देना|भेजना|डालना)\s+(नहीं|मत)", "do not tell"),
    # risky apps (before the plain "share" verb)
    (r"स्क्रीन\s?शेयर", "screen share"),
    (r"एनी\s?डेस्क", "anydesk"), (r"टीम\s?व्यूअर", "teamviewer"), (r"क्विक\s?सपोर्ट", "quicksupport"),
    (r"(ऐप्प|ऐप|एप्लीकेशन|एप्लिकेशन|एप)\s+(को\s+)?(डाउनलोड|इंस्टॉल|इनस्टॉल|इंस्टाल)", "download this app"),
    # verbs
    (r"बता\s*(दीजिए|दीजिये|दो|दें|देना)", "tell"), (r"भेज\s*(दीजिए|दीजिये|दो|दें|देना)", "send"),
    (r"बताइएगा|बताइए|बताइये|बताएं|बताएँ|बताओ|बताना|बताए|बताये", "tell"),
    (r"भेजिए|भेजिये|भेजें|भेजो", "send"),
    (r"(शेयर|साझा)(\s+(करें|कीजिए|कीजिये|करो|करिए))?", "share"),
    (r"दे\s+दीजिए|दीजिएगा|दीजिए|दीजिये", "give"),
    (r"डालिए|डालिये|डालें|डालो|डालना|दर्ज\s+(करें|कीजिए|करो)", "enter"),
    # secrets
    (r"वन\s?टाइम\s?पासवर्ड", "one time password"), (r"(वेरिफिकेशन|सत्यापन)\s+कोड", "verification code"),
    (r"ओ\.?\s?टी\.?\s?पी\.?", "OTP"), (r"पासवर्ड", "password"),
    (r"कोड\s+(आया|आएगा|भेजा|मिला)", "verification code"), (r"{W<}कोड{W>}", "verification code"),
    (r"यू\.?\s?पी\.?\s?आई\.?", "UPI"), (r"एटीएम", "ATM"), (r"एम\s?पिन", "mpin"), (r"{W<}पिन{W>}", "PIN"),
    (r"सीवीवी", "CVV"), (r"कार्ड\s+(का\s+)?(नंबर|नम्बर)", "card number"), (r"डेबिट\s+कार्ड", "debit card"),
    (r"क्रेडिट\s+कार्ड", "credit card"), (r"आधार", "aadhaar"), (r"पैन\s+कार्ड", "pan card"),
    (r"नेट\s?बैंकिंग", "net banking"),
    (r"बैंक\s+(डिटेल्स|डिटेल|विवरण|की\s+जानकारी)|खाते\s+की\s+जानकारी", "bank details"),
    # account threats
    (r"के\.?\s?वाई\.?\s?सी\.?", "KYC"), (r"अपडेट", "update"), (r"वेरीफाई|वेरिफाई|सत्यापित", "verify"),
    (r"खाता|खाते|अकाउंट|एकाउंट|अकाउन्ट", "account"), (r"{W<}कार्ड{W>}", "card"), (r"{W<}सिम{W>}", "sim"),
    (r"ब्लॉक|सस्पेंड|फ्रीज|निलंबित|{W<}बंद{W>}", "blocked"),
    # pressure
    (r"तुरंत|फौरन|फ़ौरन|जल्दी", "urgent"), (r"आज\s+ही|{W<}आज{W>}", "today"), (r"{W<}अभी{W>}", "right now"),
    # authority
    (r"डिजिटल\s+अरेस्ट", "digital arrest"), (r"पुलिस", "police"), (r"सी\.?बी\.?आई\.?", "CBI"),
    (r"गिरफ्तार|गिरफ़्तार|अरेस्ट", "arrest"), (r"कोर्ट|अदालत", "court"), (r"कस्टम्स|कस्टम|सीमा\s+शुल्क", "customs"),
    (r"वारंट", "warrant"), (r"नारकोटिक्स", "narcotics"), (r"एफ\.?\s?आई\.?\s?आर\.?", "FIR"), (r"साइबर\s+सेल", "cyber cell"),
    # money
    (r"ट्रांसफर|ट्रान्सफर", "transfer"), (r"पैसे|पैसा|रुपये|रुपए|रूपये|रकम|राशि", "money"), (r"जुर्माना", "fine"),
    (r"{W<}जमा{W>}", "deposit"),
    # lures
    (r"लॉटरी", "lottery"), (r"इनाम|पुरस्कार", "prize"), (r"कैशबैक", "cashback"), (r"रिफंड", "refund"),
    # brands
    (r"एस\.?\s?बी\.?\s?आई\.?", "SBI"), (r"स्टेट\s+बैंक", "state bank"), (r"एचडीएफसी", "HDFC"), (r"आईसीआईसीआई", "ICICI"),
    (r"एक्सिस\s+बैंक", "axis bank"), (r"पीएनबी", "PNB"), (r"पंजाब\s+नेशनल\s+बैंक", "punjab national bank"),
    (r"कोटक", "kotak"), (r"पेटीएम", "paytm"), (r"फोन\s?पे", "phonepe"), (r"गूगल\s+पे|जीपे", "google pay"),
    (r"अमेज़न|अमेजन|अमेज़ॅन|ऐमज़ॉन", "amazon"), (r"फ्लिपकार्ट", "flipkart"), (r"इनकम\s+टैक्स|आयकर", "income tax"),
    (r"आर\.?बी\.?आई\.?|रिज़र्व\s+बैंक|रिजर्व\s+बैंक", "RBI"), (r"{W<}ट्राई{W>}", "TRAI"),
    (r"इंडिया\s+पोस्ट|डाक\s+विभाग", "india post"),
    (r"बैंक", "bank"), (r"बिजली", "bijli"), (r"{W<}(कट|काट){W>}", "cut"), (r"कॉल", "call"),
])

# ------------------------------------------------------------------ Malayalam
_ML = _compile("ഀ-ൿ", [
    (r"(പറയ|പങ്കിട|പങ്കുവയ്ക്ക|പങ്കുവെക്ക|കൊടുക്ക|നൽക|അയക്ക|അയയ്ക്ക|ഷെയർ\s*ചെയ്യ)രുത്", "do not share"),
    (r"സ്ക്രീൻ\s?ഷെയർ", "screen share"), (r"എനി\s?ഡെസ്ക്", "anydesk"), (r"ടീം\s?വ്യൂവർ", "teamviewer"),
    (r"(ആപ്ലിക്കേഷൻ|ആപ്പ്|ആപ്)\s*(ഡൗൺലോഡ്|ഇൻസ്റ്റാൾ)", "download this app"),
    (r"പറഞ്ഞു\s?തരൂ|പറഞ്ഞു\s?തരണം|പറയാമോ|പറയണം|പറയുക|പറയൂ", "tell"),
    (r"അയയ്ക്കൂ|അയക്കൂ|അയക്കുക|അയക്കണം", "send"),
    (r"ഷെയർ\s*ചെയ്യൂ|ഷെയർ\s*ചെയ്യുക|ഷെയർ\s*ചെയ്യണം|പങ്കിടൂ|പങ്കിടുക", "share"),
    (r"തരൂ|തരണം|നൽകൂ|നൽകുക|നൽകണം|കൊടുക്കൂ", "give"),
    (r"ടൈപ്പ്\s*ചെയ്യൂ|എന്റർ\s*ചെയ്യൂ|അടിക്കൂ", "enter"),
    (r"ഒ\.?\s?ടി\.?\s?പി\.?|ഓടിപി|ഒറ്റത്തവണ\s+പാസ്‌?വേഡ്", "OTP"), (r"{W<}കോഡ്{W>}", "verification code"),
    (r"പാസ്സ്?വേർഡ്|പാസ്വേഡ്|പാസ്വേർഡ്", "password"), (r"യു\.?പി\.?ഐ\.?", "UPI"),
    (r"പിൻ\s+നമ്പർ|{W<}പിൻ{W>}", "PIN"), (r"സിവിവി", "CVV"), (r"കാർഡ്\s+നമ്പർ", "card number"),
    (r"ആധാർ", "aadhaar"), (r"(ബാങ്ക്|അക്കൗണ്ട്)\s+വിവരങ്ങൾ", "bank details"),
    (r"കെ\.?വൈ\.?സി\.?", "KYC"), (r"അപ്ഡേറ്റ്", "update"),
    (r"അക്കൗണ്ട്|അക്കൌണ്ട്", "account"), (r"കാർഡ്", "card"), (r"{W<}സിം{W>}", "sim"),
    (r"ബ്ലോക്ക്|മരവിപ്പി|റദ്ദാക്ക|സസ്പെൻഡ്", "blocked"),
    (r"ഉടനെ|ഉടൻ|അടിയന്തിര", "urgent"), (r"ഇപ്പോൾ\s?തന്നെ", "right now"), (r"ഇന്ന്\s?തന്നെ|{W<}ഇന്ന്{W>}", "today"),
    (r"പോലീസ്|പൊലീസ്", "police"), (r"സിബിഐ", "CBI"), (r"അറസ്റ്റ്", "arrest"), (r"കോടതി", "court"),
    (r"കസ്റ്റംസ്", "customs"), (r"വാറന്റ്|വാറണ്ട്", "warrant"),
    (r"ട്രാൻസ്ഫർ", "transfer"), (r"പണം|രൂപ|{W<}തുക{W>}", "money"), (r"{W<}പിഴ{W>}", "fine"),
    (r"ലോട്ടറി", "lottery"), (r"സമ്മാനം", "prize"), (r"റീഫണ്ട്", "refund"), (r"ക്യാഷ്ബാക്ക്", "cashback"),
    (r"എസ്\.?\s?ബി\.?\s?ഐ\.?", "SBI"), (r"സ്റ്റേറ്റ്\s+ബാങ്ക്", "state bank"), (r"എച്ച്ഡിഎഫ്സി", "HDFC"),
    (r"ഐസിഐസിഐ", "ICICI"), (r"പേടിഎം", "paytm"), (r"ഫോൺപേ", "phonepe"), (r"ഗൂഗിൾ\s+പേ", "google pay"),
    (r"ആമസോൺ", "amazon"), (r"ഫ്ലിപ്കാർട്ട്", "flipkart"), (r"ആർബിഐ", "RBI"), (r"ബാങ്ക്", "bank"), (r"കോൾ", "call"),
])

# ------------------------------------------------------------------ Kannada
_KN = _compile("ಀ-೿", [
    (r"(ಹೇಳ|ತಿಳಿಸ|ಕೊಡ|ನೀಡ|ಕಳುಹಿಸ|ಹಂಚಿಕೊಳ್ಳ|ಶೇರ್\s*ಮಾಡ)(ಬೇಡಿ|ಬೇಡ|ಬಾರದು)", "do not share"),
    (r"ಸ್ಕ್ರೀನ್\s?ಶೇರ್", "screen share"), (r"ಎನಿ\s?ಡೆಸ್ಕ್", "anydesk"), (r"ಟೀಮ್\s?ವ್ಯೂವರ್", "teamviewer"),
    (r"(ಅಪ್ಲಿಕೇಶನ್|ಆ್ಯಪ್|ಆಪ್)\s*(ಡೌನ್ಲೋಡ್|ಇನ್ಸ್ಟಾಲ್)", "download this app"),
    (r"ಹೇಳಿ|ತಿಳಿಸಿ", "tell"), (r"ಕಳುಹಿಸಿ|ಕಳಿಸಿ", "send"), (r"ಶೇರ್\s*ಮಾಡಿ|ಹಂಚಿಕೊಳ್ಳಿ", "share"),
    (r"{W<}(ಕೊಡಿ|ನೀಡಿ){W>}", "give"), (r"ನಮೂದಿಸಿ|ಟೈಪ್\s*ಮಾಡಿ", "enter"),
    (r"ಒ\.?\s?ಟಿ\.?\s?ಪಿ\.?|ಓಟಿಪಿ", "OTP"), (r"{W<}ಕೋಡ್{W>}", "verification code"), (r"ಪಾಸ್ವರ್ಡ್", "password"), (r"ಯು\.?ಪಿ\.?ಐ\.?", "UPI"),
    (r"{W<}ಪಿನ್{W>}", "PIN"), (r"ಸಿವಿವಿ", "CVV"), (r"ಕಾರ್ಡ್\s+(ನಂಬರ್|ಸಂಖ್ಯೆ)", "card number"),
    (r"ಆಧಾರ್", "aadhaar"), (r"ಬ್ಯಾಂಕ್\s+ವಿವರ", "bank details"),
    (r"ಕೆ\.?ವೈ\.?ಸಿ\.?", "KYC"), (r"ಅಪ್ಡೇಟ್", "update"),
    (r"ಖಾತೆ|ಅಕೌಂಟ್", "account"), (r"ಕಾರ್ಡ್", "card"), (r"{W<}ಸಿಮ್{W>}", "sim"),
    (r"ಬ್ಲಾಕ್|ಬಂದ್|ಸ್ಥಗಿತ|ನಿರ್ಬಂಧ", "blocked"),
    (r"ತಕ್ಷಣ|ಕೂಡಲೇ|ತುರ್ತು", "urgent"), (r"ಈಗಲೇ", "right now"), (r"ಇಂದೇ|{W<}ಇಂದು{W>}", "today"),
    (r"ಪೊಲೀಸ್|ಪೋಲೀಸ್", "police"), (r"ಸಿಬಿಐ", "CBI"), (r"ಬಂಧನ|ಬಂಧಿಸ|ಅರೆಸ್ಟ್", "arrest"), (r"ನ್ಯಾಯಾಲಯ|ಕೋರ್ಟ್", "court"),
    (r"ಕಸ್ಟಮ್ಸ್", "customs"), (r"ವಾರಂಟ್", "warrant"),
    (r"ವರ್ಗಾಯಿಸ|ಟ್ರಾನ್ಸ್ಫರ್", "transfer"), (r"{W<}ಹಣ|ರೂಪಾಯಿ|ಮೊತ್ತ", "money"), (r"{W<}ದಂಡ{W>}", "fine"),
    (r"ಲಾಟರಿ", "lottery"), (r"ಬಹುಮಾನ", "prize"), (r"ರಿಫಂಡ್", "refund"), (r"ಕ್ಯಾಶ್ಬ್ಯಾಕ್", "cashback"),
    (r"ಎಸ್\.?\s?ಬಿ\.?\s?ಐ\.?", "SBI"), (r"ಸ್ಟೇಟ್\s+ಬ್ಯಾಂಕ್", "state bank"), (r"ಎಚ್ಡಿಎಫ್ಸಿ", "HDFC"), (r"ಐಸಿಐಸಿಐ", "ICICI"),
    (r"ಪೇಟಿಎಂ", "paytm"), (r"ಫೋನ್ಪೇ", "phonepe"), (r"ಗೂಗಲ್\s+ಪೇ", "google pay"), (r"ಅಮೆಜಾನ್", "amazon"),
    (r"ಫ್ಲಿಪ್ಕಾರ್ಟ್", "flipkart"), (r"ಆರ್ಬಿಐ", "RBI"), (r"ಬ್ಯಾಂಕ್", "bank"), (r"ಕರೆ\s+ಮಾಡಿ", "call"),
])

# ------------------------------------------------------------------ Tamil
_TA = _compile("஀-௿", [
    (r"(சொல்ல|கூற|கொடுக்க|பகிர|அனுப்ப|தெரிவிக்க)(ாதீர்கள்|ாதீர்|ாதீங்க|ாதே|\s*வேண்டாம்|க்?\s*கூடாது)", "do not share"),
    (r"ஸ்கிரீன்\s?ஷேர்", "screen share"), (r"எனிடெஸ்க்|ஏனிடெஸ்க்", "anydesk"), (r"டீம்\s?வியூவர்", "teamviewer"),
    (r"(அப்ளிகேஷன்|செயலியை|செயலி|ஆப்)\s*(ஐ\s+)?(டவுன்லோட்|பதிவிறக்க|இன்ஸ்டால்|நிறுவ)", "download this app"),
    (r"சொல்லுங்கள்|சொல்லுங்க|சொல்லவும்|கூறுங்கள்|தெரிவிக்கவும்|தெரிவியுங்கள்", "tell"),
    (r"அனுப்புங்கள்|அனுப்புங்க|அனுப்பவும்", "send"),
    (r"பகிருங்கள்|பகிரவும்|ஷேர்\s*(செய்யுங்கள்|பண்ணுங்க)", "share"),
    (r"கொடுங்கள்|கொடுங்க|தாருங்கள்|தரவும்", "give"),
    (r"உள்ளிடவும்|உள்ளிடுங்கள்|டைப்\s*(செய்யுங்கள்|பண்ணுங்க)", "enter"),
    (r"ஓ\.?\s?டி\.?\s?பி\.?|ஒடிபி|ஒரு\s?முறை\s+கடவுச்சொல்", "OTP"), (r"{W<}கோட்{W>}|குறியீடு", "verification code"),
    (r"கடவுச்சொல்|பாஸ்வேர்டு|பாஸ்வேர்ட்", "password"),
    # "பின்" alone means "after" in Tamil, so only clear PIN phrases count.
    (r"(யுபிஐ|யூபிஐ)\s+பின்", "UPI PIN"), (r"ஏடிஎம்\s+பின்", "ATM PIN"), (r"எம்\s?பின்", "mpin"),
    (r"பின்\s+(எண்ணை|எண்|நம்பரை|நம்பர்)", "PIN"), (r"யுபிஐ|யூபிஐ", "UPI"),
    (r"சிவிவி", "CVV"), (r"கார்டு\s+(எண்|நம்பர்)", "card number"), (r"ஆதார்", "aadhaar"),
    (r"வங்கி\s+(விவரங்கள்|விவரம்|தகவல்)", "bank details"),
    (r"கே\.?ஒய்\.?சி\.?", "KYC"), (r"அப்டேட்|புதுப்பி", "update"),
    (r"கணக்கு|அக்கவுண்ட்|அகவுண்ட்", "account"), (r"கார்டு", "card"), (r"{W<}சிம்{W>}", "sim"),
    (r"முடக்க|பிளாக்|நிறுத்தப்படு", "blocked"),
    (r"உடனடியாக|உடனே|அவசர", "urgent"), (r"இப்போதே", "right now"), (r"இன்றே|{W<}இன்று{W>}", "today"),
    (r"போலீஸ்|காவல்துறை", "police"), (r"சிபிஐ", "CBI"), (r"கைது|அரெஸ்ட்", "arrest"), (r"நீதிமன்ற|கோர்ட்", "court"),
    (r"சுங்க|கஸ்டம்ஸ்", "customs"), (r"வாரண்ட்", "warrant"),
    (r"டிரான்ஸ்ஃபர்|ட்ரான்ஸ்பர்|டிரான்ஸ்பர்", "transfer"), (r"பணத்தை|பணம்|ரூபாய்|தொகை", "money"), (r"அபராதம்", "fine"),
    (r"லாட்டரி", "lottery"), (r"பரிசு", "prize"), (r"ரீஃபண்ட்", "refund"), (r"கேஷ்பேக்", "cashback"),
    (r"எஸ்\.?\s?பி\.?\s?ஐ\.?", "SBI"), (r"ஸ்டேட்\s+(பேங்க்|வங்கி)", "state bank"), (r"எச்டிஎஃப்சி", "HDFC"),
    (r"ஐசிஐசிஐ", "ICICI"), (r"பேடிஎம்", "paytm"), (r"போன்பே", "phonepe"), (r"கூகுள்\s+பே", "google pay"),
    (r"அமேசான்", "amazon"), (r"பிளிப்கார்ட்", "flipkart"), (r"ஆர்பிஐ", "RBI"), (r"வங்கி|பேங்க்", "bank"),
    (r"அழையுங்கள்|கால்\s+பண்ணுங்க", "call"),
])

_SCRIPTS = [(re.compile("[ऀ-ॿ]"), _HI), (re.compile("[ഀ-ൿ]"), _ML),
            (re.compile("[ಀ-೿]"), _KN), (re.compile("[஀-௿]"), _TA)]


def gloss(text: str) -> str:
    """Return `text` with known scam vocabulary in Indian scripts replaced by English rule words.

    Text without those scripts is returned unchanged, so English and romanised
    messages behave exactly as before.
    """
    if not text:
        return text
    for detector, table in _SCRIPTS:
        if detector.search(text):
            text = _ZERO_WIDTH.sub("", text)
            for pattern, english in table:
                text = pattern.sub(english, text)
    return text
