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
            """turant|abhi|band ho)\b|तुरंत|पुलिस|गिरफ्तार|ओटीपी|बंद|ब्लॉक"""
    )

    /** Why this notification deserves a full check, or null if it should stay on the phone. */
    fun reason(text: String): String? {
        if (text.isBlank()) return null
        if (LINK.containsMatchIn(text)) return "contains a link"
        if (SCAM_WORDS.containsMatchIn(text)) return "contains wording often used in scams"
        return null
    }
}
