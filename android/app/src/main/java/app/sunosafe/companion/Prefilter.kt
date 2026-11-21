package app.sunosafe.companion

/**
 * On-phone first look at a notification, before anything leaves the device.
 *
 * Most notifications are ordinary personal messages. Sending all of them to a
 * server would be a privacy problem, so only a notification that contains a
 * link or typical scam wording is forwarded for a full investigation. Everything
 * else is dropped here and never transmitted.
 *
 * This is deliberately a wide net, not a verdict: the backend's rules, link
 * investigation and correlation decide whether something is dangerous.
 */
object Prefilter {

    private val LINK = Regex(
        """(?i)\b(?:h(?:tt|xx)ps?://|www\.|upi://)\S+|\b[a-z0-9-]{2,}(?:\.|\[\.\])(?:com|in|co|net|org|info|xyz|top|online|site|link|app|shop|live|cc|ly|me|io)\b(?:/\S*)?"""
    )

    private val SCAM_WORDS = Regex(
        """(?i)\b(otp|one[\s-]?time password|upi\s?pin|m-?pin|cvv|kyc|password|net\s?banking|""" +
            """blocked|suspend(ed)?|deactivat\w*|disconnect\w*|expire[sd]?|""" +
            """lottery|prize|winner|lucky draw|kbc|refund|cashback|reward|""" +
            """anydesk|teamviewer|quick\s?support|\.apk|install (this|the|our) app|""" +
            """arrest\w*|police|cbi|customs|court|warrant|fir|narcotics|""" +
            """electricity|bijli|aadhaa?r|pan card|verify your|update your|click (here|the link)|""" +
            """turant|abhi|band ho)\b|तुरंत|पुलिस|गिरफ्तार|ओटीपी|बंद|ब्लॉक|बिजली|केवाईसी|लॉटरी|इनाम|आधार""" +
            // Malayalam, Kannada, Tamil: OTP, police, arrest, blocked, electricity, cut off, KYC, urgent, lottery, prize, Aadhaar
            """|ഒടിപി|ഓടിപി|ഒ\.ടി\.പി|പോലീസ്|പൊലീസ്|അറസ്റ്റ്|ബ്ലോക്ക്|വൈദ്യുതി|കറന്റ്|വിച്ഛേദി|കെവൈസി|ഉടൻ|ലോട്ടറി|സമ്മാനം|ആധാർ""" +
            """|ಒಟಿಪಿ|ಓಟಿಪಿ|ಪೊಲೀಸ್|ಬಂಧನ|ಬ್ಲಾಕ್|ವಿದ್ಯುತ್|ಕರೆಂಟ್|ಕಡಿತ|ಕೆವೈಸಿ|ತಕ್ಷಣ|ಲಾಟರಿ|ಬಹುಮಾನ|ಆಧಾರ್""" +
            """|ஓடிபி|ஓ\.டி\.பி|காவல்|போலீஸ்|கைது|முடக்க|மின்சாரம்|மின்\s*இணைப்பு|துண்டி|கேஒய்சி|உடனே|லாட்டரி|பரிசு|ஆதார்"""
    )

    /** Why this notification deserves a full check, or null if it should stay on the phone. */
    fun reason(text: String): String? {
        if (text.isBlank()) return null
        if (LINK.containsMatchIn(text)) return "contains a link"
        if (SCAM_WORDS.containsMatchIn(text)) return "contains wording often used in scams"
        return null
    }
}
