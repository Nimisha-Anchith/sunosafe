package app.sunosafe.companion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PhoneNumbersTest {
    @Test
    fun numbersAreNormalisedTheSameWayAsTheBackend() {
        assertEquals("9876543210", PhoneNumbers.normalize("+91 98765 43210"))
        assertEquals("9876543210", PhoneNumbers.normalize("98765-43210"))
        assertEquals("9876543210", PhoneNumbers.normalize("09876543210"))
        assertEquals("9876543210", PhoneNumbers.normalize("919876543210"))
        assertNull(PhoneNumbers.normalize(""))
        assertNull(PhoneNumbers.normalize(null))
        assertNull(PhoneNumbers.normalize("12"))
    }

    @Test
    fun hiddenNotificationTextIsRecognised() {
        assertTrue(PhoneNumbers.looksHidden("Contents hidden"))
        assertTrue(PhoneNumbers.looksHidden("3 new messages"))
        assertTrue(PhoneNumbers.looksHidden("New message"))
        assertFalse(PhoneNumbers.looksHidden("Your account will be blocked today"))
    }
}
