"""Scam rules on native-script text: what a Hindi / Malayalam / Kannada / Tamil phone call or message looks like."""
import pytest

from app.security.indic import gloss
from app.security.message_rules import analyze_message
from app.soc.severity import assess


def level(text: str, live: bool = True) -> str:
    codes = analyze_message(text).codes() | ({"live_caller"} if live else set())
    return assess(codes).level


SCAM_CALLS = {
    "hi-1": "नमस्ते, मैं एसबीआई बैंक से बोल रहा हूँ। आपका खाता आज बंद हो जाएगा। अभी ओटीपी बताइए।",
    "hi-2": "मैं स्टेट बैंक ऑफ इंडिया के केवाईसी विभाग से बात कर रहा हूं, आपके फोन पर जो ओटीपी आया है वो बता दीजिए",
    "hi-3": "मैं SBI से बोल रहा हूँ, आपका OTP बताइए नहीं तो अकाउंट ब्लॉक हो जाएगा",
    "hi-4": "आप एनीडेस्क ऐप डाउनलोड कीजिए और अपना यूपीआई पिन डालिए",
    "hi-5": "मैं पुलिस से बोल रहा हूँ, आपके नाम पर पार्सल में ड्रग्स मिला है, आपको डिजिटल अरेस्ट किया जा रहा है, "
            "तुरंत पैसे ट्रांसफर कीजिए",
    "ml-1": "ഞാൻ എസ്ബിഐ ബാങ്കിൽ നിന്നാണ് വിളിക്കുന്നത്, നിങ്ങളുടെ ഒടിപി പറയൂ",
    "ml-2": "നിങ്ങളുടെ അക്കൗണ്ട് ഇന്ന് ബ്ലോക്ക് ആകും, ഫോണിൽ വന്ന ഒടിപി ഉടൻ പറഞ്ഞു തരൂ",
    "kn-1": "ನಾನು ಎಸ್‌ಬಿಐ ಬ್ಯಾಂಕ್‌ನಿಂದ ಕರೆ ಮಾಡುತ್ತಿದ್ದೇನೆ, ನಿಮ್ಮ ಒಟಿಪಿ ಹೇಳಿ",
    "kn-2": "ನಿಮ್ಮ ಖಾತೆ ಇಂದು ಬ್ಲಾಕ್ ಆಗುತ್ತದೆ, ತಕ್ಷಣ ಒಟಿಪಿ ತಿಳಿಸಿ",
    "ta-1": "நான் எஸ்பிஐ வங்கியிலிருந்து பேசுகிறேன், உங்கள் ஓடிபி சொல்லுங்கள்",
    "ta-2": "உங்கள் கணக்கு இன்று முடக்கப்படும், உடனே ஓடிபி சொல்லுங்க",
}


SCAM_CALLS.update({
    "hi-card": "हेलो मैं बैंक से बोल रहा हूं आपका एटीएम कार्ड ब्लॉक हो गया है कार्ड का नंबर और पीछे का सीवीवी बताइए",
    "hi-code": "सर आपके नंबर पर एक कोड आया होगा वो कोड बता दीजिए",
    "hi-lottery": "आपको लॉटरी में पच्चीस लाख रुपये का इनाम मिला है, प्रोसेसिंग फीस के लिए पांच हजार रुपये भेजिए",
    "hi-customs": "मैं कूरियर कंपनी से बोल रहा हूँ, आपका पार्सल कस्टम में फंसा है, छुड़ाने के लिए पैसे जमा कीजिए",
    "en-card": "tell me your card number and CVV sir",
    "en-details": "please give me your debit card details",
    "ml-card": "നിങ്ങളുടെ എടിഎം കാർഡ് ബ്ലോക്ക് ആയി, കാർഡ് നമ്പർ പറയൂ",
    "kn-card": "ನಿಮ್ಮ ಎಟಿಎಂ ಕಾರ್ಡ್ ಬ್ಲಾಕ್ ಆಗಿದೆ, ಕಾರ್ಡ್ ನಂಬರ್ ಹೇಳಿ",
    "ta-card": "உங்கள் ஏடிஎம் கார்டு பிளாக் ஆகிவிட்டது, கார்டு நம்பர் சொல்லுங்கள்",
})


def test_caller_asking_for_money_is_a_caution_not_an_alarm():
    assert level("हां जी मैं आपका बेटा बोल रहा हूं, मेरा फोन खराब हो गया, इस नंबर पर दस हजार रुपये भेज दो") == "medium"
    assert level("मम्मी मैं बोल रही हूं, शाम को पैसे भेज दूंगी") == "info"          # "I will send you money" is not a demand
    assert level("नमस्ते जी, मैं गैस एजेंसी से बोल रहा हूं, आपका सिलेंडर कल आएगा") == "info"


def test_ordinary_promo_messages_stay_low():
    assert level("Use code SAVE10 and share with friends to get 10% off.", live=False) in ("info", "low")
    assert level("Get Rs 50 cashback when you pay with your wallet today.", live=False) in ("info", "low", "medium")
    assert "requests_otp" not in analyze_message("Your OTP is 482913. Never tell it to anyone.").codes()


@pytest.mark.parametrize("name", SCAM_CALLS)
def test_native_script_scam_call_is_high(name):
    assert level(SCAM_CALLS[name]) in ("high", "critical"), gloss(SCAM_CALLS[name])


@pytest.mark.parametrize("text", [
    "नमस्ते, मैं रमेश बोल रहा हूँ बिजली विभाग से, मीटर रीडिंग के लिए कल आऊँगा",
    "हेलो, मैं आपका पड़ोसी बोल रहा हूँ, शाम को घर आ रहा हूँ",
    "നമസ്കാരം, ഞാൻ രമേശ് ആണ്, നാളെ വീട്ടിൽ വരാം",
    "ನಮಸ್ಕಾರ, ನಾನು ರಮೇಶ್, ನಾಳೆ ಮನೆಗೆ ಬರುತ್ತೇನೆ",
    "வணக்கம், நான் ரமேஷ் பேசுகிறேன், நாளை வீட்டுக்கு வருகிறேன், பின் பேசலாம்",
])
def test_ordinary_native_script_call_is_not_flagged(text):
    assert level(text) == "info", gloss(text)


@pytest.mark.parametrize("text", [
    "आपका ओटीपी 482913 है। इसे किसी के साथ साझा न करें।",
    "SBI: आपका OTP 482913 है। OTP किसी को मत बताइए।",
    "बैंक कभी ओटीपी नहीं मांगता। ओटीपी किसी को बताना नहीं है।",
    "നിങ്ങളുടെ ഒടിപി 482913 ആണ്. ഇത് ആരോടും പറയരുത്.",
    "ನಿಮ್ಮ ಒಟಿಪಿ 482913. ಇದನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ.",
    "உங்கள் ஓடிபி 482913. இதை யாரிடமும் சொல்லாதீர்கள்.",
])
def test_genuine_do_not_share_warnings_are_not_requests(text):
    codes = analyze_message(text).codes()
    assert "requests_otp" not in codes, gloss(text)


def test_brand_is_recognised_in_native_script():
    assert analyze_message("मैं एसबीआई से बोल रहा हूँ").brands == ["sbi"]
    assert "sbi" in analyze_message("ഞാൻ എസ്ബിഐ ബാങ്കിൽ നിന്നാണ്").brands
    assert "sbi" in analyze_message("ನಾನು ಎಸ್‌ಬಿಐ ಬ್ಯಾಂಕ್‌ನಿಂದ").brands          # written with a zero-width joiner
    assert "sbi" in analyze_message("நான் எஸ்பிஐ வங்கியிலிருந்து").brands


def test_digital_arrest_rule_needs_both_threat_and_money():
    assert level("This is the police. You are under digital arrest. Transfer the money now.", live=False) == "high"
    assert level("Please pay the electricity bill amount of Rs 500 by Friday.", live=False) in ("info", "low")
    assert level("The police station is near the court.", live=False) in ("info", "low")


def test_english_and_links_are_untouched_by_the_gloss():
    text = "Dear customer, update KYC at https://sbi-kyc-update.in/verify and share the OTP"
    assert gloss(text) == text
    mixed = "केवाईसी अपडेट करें https://sbi-kyc-update.in/verify"
    assert analyze_message(mixed).web_urls == ["https://sbi-kyc-update.in/verify"]


def test_electricity_bill_scam_is_high_but_a_maintenance_notice_is_not():
    scam = ("Dear Consumer, your electricity power will be disconnected tonight at 9.30 PM because your previous month "
            "bill was not updated. Please immediately contact our electricity officer on 9123456780")
    assert level(scam, live=False) == "high"
    hindi = "प्रिय उपभोक्ता, आज रात आपकी बिजली काट दी जाएगी। तुरंत हमारे अधिकारी को 9123456780 पर कॉल करें"
    assert level(hindi, live=False) == "high"
    notice = "BESCOM: power cut tonight 10 PM to 12 AM in your area for maintenance work. Sorry for the inconvenience."
    assert level(notice, live=False) in ("info", "low")
