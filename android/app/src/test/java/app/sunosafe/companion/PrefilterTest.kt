package app.sunosafe.companion

import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

/** The on-phone filter decides what may leave the device, so it is tested on its own. */
class PrefilterTest {

    @Test
    fun ordinaryMessagesStayOnThePhone() {
        listOf(
            "Amma: dinner is ready, come home soon",
            "Meeting moved to 4 pm tomorrow",
            "Happy birthday! See you on Sunday",
            "",
        ).forEach { assertNull(it, Prefilter.reason(it)) }
    }

    @Test
    fun messagesWithLinksAreSentForChecking() {
        listOf(
            "Track your parcel at https://india-post-track.example/abc",
            "update here hxxps://sbi-kyc[.]co/upd",
            "Pay now: upi://pay?pa=refund@ybl&am=10",
            "see sbi-kyc-update.in/verify today",
        ).forEach { assertNotNull(it, Prefilter.reason(it)) }
    }

    @Test
    fun scamWordingWithoutALinkIsSentForChecking() {
        listOf(
            "Share the OTP sent to your phone",
            "Your account will be blocked today, call 9876543210",
            "You won a lottery prize of 25 lakh",
            "This is CBI, you are under digital arrest",
            "पुलिस आपके घर आएगी, तुरंत कॉल करें",
        ).forEach { assertNotNull(it, Prefilter.reason(it)) }
    }
}
