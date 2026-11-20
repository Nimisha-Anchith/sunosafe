package app.sunosafe.companion

import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService

/**
 * Checks incoming callers, after the user makes SunoSafe the phone's
 * "Caller ID & spam" app (the call-screening role).
 *
 * What it can and cannot do (Android rules, not choices):
 *  - It receives the caller's number for calls from numbers NOT in the contacts.
 *    It never hears the call audio.
 *  - It must answer Android within seconds, so it always lets the call ring
 *    normally first (it never blocks or silences), then checks.
 *
 * The check:
 *  1. Instant, on the phone: is this number one that appeared in a scam message
 *     SunoSafe warned about? (No network needed.) If yes, warn aloud while it rings.
 *  2. In the background: ask the SunoSafe backend, which correlates the call with
 *     the earlier incident in the mini-SIEM. Ordinary callers are not recorded.
 */
class SunoCallScreener : CallScreeningService() {

    override fun onScreenCall(details: Call.Details) {
        // 1. Answer Android immediately: let the call through untouched.
        respondToCall(details, CallResponse.Builder().build())

        if (Build.VERSION.SDK_INT >= 29 && details.callDirection != Call.Details.DIRECTION_INCOMING) return
        if (!Prefs.monitoringOn(this)) return
        val number = details.handle?.schemeSpecificPart
        val context = applicationContext
        Prefs.bump(context, "calls")

        // 2. Instant local check.
        val localIncident = Prefs.watchedIncident(context, number)
        if (localIncident != null) {
            Prefs.bump(context, "call_alerts")
            Prefs.setLastResult(context, "Warned you about a call from a number seen in a scam message.")
            Alerts.warn(context, "Careful: this caller is linked to a scam",
                Verdict(true, "high", "danger", callWarning(context), localIncident.takeIf { it > 0 },
                    sayEn = EN_CALL_WARNING, audioId = "call-watch-" + Prefs.lang(context)))
        }

        // 3. Backend correlation (records the call only if it is linked to scam evidence).
        if (!Prefs.isPaired(context)) return
        Thread {
            val verdict = Backend.reportCall(context, number)
            if (verdict != null && verdict.alert && localIncident == null) {
                Prefs.bump(context, "call_alerts")
                Prefs.setLastResult(context, "Warned you about a call linked to an earlier scam.")
                Alerts.warn(context, "Careful: this caller is linked to a scam",
                    verdict.copy(say = verdict.say.ifBlank { callWarning(context) },
                        sayEn = verdict.sayEn.ifBlank { EN_CALL_WARNING }))
            }
        }.start()
    }

    private fun callWarning(c: android.content.Context): String =
        if (Prefs.lang(c) == "hi") "सावधान। यह नंबर पहले आए एक धोखाधड़ी संदेश में था। कोई OTP, PIN या बैंक जानकारी न बताएं।"
        else EN_CALL_WARNING

    private companion object {
        const val EN_CALL_WARNING = "Careful. This caller's number appeared in a scam message you received. " +
            "Do not share any OTP, PIN or bank details."
    }
}
