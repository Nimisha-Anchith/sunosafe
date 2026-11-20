package app.sunosafe.companion

/** Phone number and notification-text helpers shared by the listener and call screener. */
object PhoneNumbers {

    /** "+91 98765-43210", "tel:9876543210" -> "9876543210". Null when it is not a usable number. */
    fun normalize(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        var digits = raw.filter { it.isDigit() }
        if (digits.length == 12 && digits.startsWith("91")) digits = digits.substring(2)
        if (digits.length == 11 && digits.startsWith("0")) digits = digits.substring(1)
        return if (digits.length in 7..13) digits else null
    }

    private val HIDDEN = Regex(
        """(?i)^(contents? hidden|message hidden|new message|\d+\s+new messages?|sensitive notification content hidden|""" +
            """you have a new message|\d+\s+messages? from \d+ chats?|checking for new messages)\.?$"""
    )

    /** True when the app hid the real message text (lock-screen privacy, bundles, placeholders). */
    fun looksHidden(text: String): Boolean = HIDDEN.matches(text.trim())
}
