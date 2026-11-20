package app.sunosafe.companion

import android.content.Context
import java.util.concurrent.Executors

/**
 * One path for every automatic check (new SMS, SMS inbox, notifications, messages on screen):
 *
 *   text ─► Prefilter (link or scam wording?) ─► no: nothing leaves the phone
 *        ─► seen in the last 30 min (any source)? ─► yes: skip, so one message = one warning
 *        ─► SunoSafe backend ─► mini-SIEM ─► spoken warning if dangerous
 */
object Checker {
    private const val WINDOW_MS = 30 * 60 * 1000L
    private val worker = Executors.newSingleThreadExecutor()
    private val recent = object : LinkedHashMap<Int, Long>(256, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Long>?) = size > 2000
    }

    /** Same message text from different places (SMS app, notification, screen) counts once. */
    fun key(text: String): Int = text.lowercase().replace(Regex("\\s+"), " ").trim().take(300).hashCode()

    /** True the first time this text is seen within the window; records it. */
    fun firstTime(text: String, now: Long = System.currentTimeMillis()): Boolean = synchronized(recent) {
        val k = key(text)
        val last = recent[k]
        if (last != null && now - last < WINDOW_MS) false else { recent[k] = now; true }
    }

    fun forget(text: String) = synchronized(recent) { recent.remove(key(text)) }

    /**
     * Check one message in the background. [warn] = speak and notify when dangerous
     * (false for bulk inbox scans, which summarise instead). Returns immediately.
     */
    fun check(c: Context, appPackage: String, appName: String, title: String, text: String, source: String,
              warn: Boolean = true, onResult: ((Verdict?) -> Unit)? = null) {
        val context = c.applicationContext
        if (!Prefs.monitoringOn(context) || !Prefs.isPaired(context)) return
        if (Prefilter.reason(text) == null) return
        if (!firstTime(text)) return
        Prefs.bump(context, "sent")
        worker.execute {
            val verdict = Backend.report(context, appPackage, title, text.take(4000), source = source)
            when {
                verdict == null -> Prefs.setLastResult(context,
                    "A message in $appName could not be checked (no connection to SunoSafe). This does not mean it is safe.")
                verdict.alert -> {
                    Prefs.bump(context, "alerts")
                    Prefs.addWatchNumbers(context, verdict.watchNumbers, verdict.incidentId)
                    Prefs.setLastResult(context, "Warned you about a message in $appName.")
                    if (warn) {
                        val heading = if (verdict.label == "danger") "Danger: scam message in $appName"
                                      else "Be careful: message in $appName"
                        Alerts.warn(context, heading, verdict)
                    }
                }
                else -> Prefs.setLastResult(context, "Checked a message in $appName: no strong warning signs found.")
            }
            onResult?.invoke(verdict)
        }
    }
}
