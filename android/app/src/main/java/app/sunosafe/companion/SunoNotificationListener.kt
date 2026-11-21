package app.sunosafe.companion

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

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

    private companion object {
        const val POLL_SECONDS = 10L
    }

    private val worker: ExecutorService = Executors.newSingleThreadExecutor()

    // Recently handled texts, so edits/updates of the same message are not re-sent.
    private val recent = object : LinkedHashMap<Int, Long>(64, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Long>?) = size > 200
    }

    // Call shield: when a forwarded call is answered by SunoSafe's call assistant (Vobiz number ->
    // Agora agent), the backend queues a warning. This service is kept alive by Android while
    // notification access is on, so it asks for new warnings every few seconds.
    private var poller: ScheduledExecutorService? = null

    override fun onListenerConnected() {
        Prefs.setLastResult(this, "Notification access is on. SunoSafe is ready.")
        ProtectionService.start(this)
        if (poller == null) {
            poller = Executors.newSingleThreadScheduledExecutor().also {
                it.scheduleWithFixedDelay({ pollShieldAlerts() }, 5, POLL_SECONDS, TimeUnit.SECONDS)
            }
        }
    }

    override fun onListenerDisconnected() {
        poller?.shutdownNow()
        poller = null
    }

    private fun pollShieldAlerts() {
        if (ProtectionService.running) return   // the protection service polls instead
        try {
            val c = applicationContext
            if (!Prefs.monitoringOn(c) || !Prefs.isPaired(c)) return
            val alerts = Backend.fetchAlerts(c, Prefs.lastAlertId(c)) ?: return
            for (a in alerts) {
                Prefs.setLastAlertId(c, a.id)
                Prefs.bump(c, "call_alerts")
                Prefs.setLastResult(c, "SunoSafe answered a scam call for you and warned you.")
                Alerts.warn(c, "SunoSafe answered a scam call for you", a.verdict)
            }
        } catch (e: Exception) {
            // keep polling
        }
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
        if (!Checker.firstTime(text)) return  // already warned via the SMS reader or the screen

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
            var verdict = Backend.report(context, sbn.packageName, title, text)
            if (verdict == null) {               // network blip or the server waking up: try once more
                Thread.sleep(4000)
                verdict = Backend.report(context, sbn.packageName, title, text)
            }
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
        poller?.shutdownNow()
        worker.shutdown()
        super.onDestroy()
    }
}
