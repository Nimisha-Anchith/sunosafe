package app.sunosafe.companion

import org.junit.Assert.assertTrue
import org.junit.Test

/** Every on-screen text has all five languages, none left empty. */
class TrTest {
    @Test
    fun everyKeyHasFiveLanguages() {
        assertTrue(Tr.complete())
    }
}
