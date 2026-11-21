"""Electricity-bill scam in Malayalam, Kannada and Tamil script is rated high (rule R16)."""
import pytest

from app.security.message_rules import analyze_message

CASES = {
    "ml": "പ്രിയ ഉപഭോക്താവേ, നിങ്ങളുടെ KSEB വൈദ്യുതി ബിൽ കുടിശ്ശികയായതിനാൽ ഇന്ന് രാത്രി 9.30-ന് വൈദ്യുതി വിച്ഛേദിക്കും. "
          "ഒഴിവാക്കാൻ ഉടൻ ഈ നമ്പറിൽ വിളിക്കുക: 9847012345.",
    "kn": "ಆತ್ಮೀಯ ಗ್ರಾಹಕರೇ, ನಿಮ್ಮ ವಿದ್ಯುತ್ ಬಿಲ್ ಬಾಕಿ ಇರುವುದರಿಂದ ಇಂದು ರಾತ್ರಿ ವಿದ್ಯುತ್ ಕಡಿತಗೊಳಿಸಲಾಗುವುದು. "
          "ತಕ್ಷಣ ಈ ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ: 9845012345.",
    "ta": "அன்புள்ள வாடிக்கையாளரே, உங்கள் மின்சாரம் பில் நிலுவையில் உள்ளதால் இன்று இரவு மின் இணைப்பு துண்டிக்கப்படும். "
          "உடனே இந்த எண்ணை அழைக்கவும்: 9840012345.",
}


@pytest.mark.parametrize("lang", sorted(CASES))
def test_electricity_scam_is_high(lang):
    analysis = analyze_message(CASES[lang])
    codes = {s.code for s in analysis.signals}
    assert {"electricity_disconnection", "asks_to_call_number"} <= codes, codes
