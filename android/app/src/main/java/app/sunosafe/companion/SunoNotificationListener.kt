package app.sunosafe.companion

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Watches new notifications from the messaging apps the user has left switched on,
 * after the user has granted "Notification access" to SunoSafe in Android settings.
 *
 *   new notification ─► watched + enabled app? ─► read title + text Android exposes
 *        ─► text hidden by the app? ─► count it, tell the user, send nothing
 *        ─► Prefilter (link or scam wording?) ─► no: forget it, nothing leaves the phone
 *                                              └► yes: SunoSafe backend ─► mini-SIEM ─► warn if dangerous
 *
 * Limits that cannot be engineered around: SunoSafe sees only what the notification
 * contains, and only while access is on.
 */
class SunoNotificationListener : NotificationListenerService() {

    private val worker: ExecutorService = Executors.newSingleThreadExecutor()

    // Recently handled texts, so edits/updates of the same message are not re-sent.
    private val recent = object : LinkedHashMap<Int, Long>(64, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Long>?) = size > 200
    }

    override fun onListenerConnected() {
        Prefs.setLastResult(this, "Notification access is on. SunoSafe is ready.")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        try {
            handle(sbn)
        } catch (e: Exception) {
            // Never let one odd notification stop the listener.
        }
    }

    private fun handle(sbn: StatusBarNotification) {
        if (!Prefs.monitoringOn(this) || !Prefs.isPaired(this)) return
        // Test builds only: notifications posted with `adb shell cmd notification post` count as a
        // watched app, so the whole flow can be verified on a real phone without a second phone.
        val adbTest = sbn.packageName == "com.android.shell" &&
            (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0
        val appName = if (adbTest) "ADB test" else Prefs.WATCHED_APPS[sbn.packageName] ?: return   // only messaging apps
        if (!adbTest && !Prefs.appEnabled(this, sbn.packageName)) return   // user switched this app off
        val notification = sbn.notification ?: return
        if (sbn.isOngoing) return                                           // calls in progress, uploads ...
        if (notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return   // "3 new messages" bundles

        val extras = notification.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString().orEmpty().trim()
        if (text.isEmpty()) return

        Prefs.bump(this, "seen")
        if (PhoneNumbers.looksHidden(text)) {
            Prefs.bump(this, "hidden")
            Prefs.setLastResult(this, "A message in $appName had its text hidden by the app, so it could not be checked. " +
                "If it worries you, copy it into SunoSafe.")
            return
        }
        Prefilter.reason(text) ?: return    // ordinary message: stays on the phone

        val key = (sbn.packageName + "\n" + text).hashCode()
        val now = System.currentTimeMillis()
        synchronized(recent) {
            val last = recent[key]
            if (last != null && now - last < 10 * 60 * 1000) return
            recent[key] = now
        }

        Prefs.bump(this, "sent")
        val context = applicationContext
        worker.execute {
            val verdict = Backend.report(context, sbn.packageName, title, text)
            when {
                verdict == null ->
                    Prefs.setLastResult(context, "A message in $appName could not be checked (no connection to SunoSafe). " +
                        "This does not mean it is safe.")
                verdict.alert -> {
                    Prefs.bump(context, "alerts")
                    Prefs.addWatchNumbers(context, verdict.watchNumbers, verdict.incidentId)
                    Prefs.setLastResult(context, "Warned you about a message in $appName.")
                    val heading = if (verdict.label == "danger") "Danger: scam message in $appName" else "Be careful: message in $appName"
                    Alerts.warn(context, heading, verdict)
                }
                else ->
                    Prefs.setLastResult(context, "Checked a message in $appName: no strong warning signs found.")
            }
        }
    }

    override fun onDestroy() {
        worker.shutdown()
        super.onDestroy()
    }
}
