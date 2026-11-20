package app.sunosafe.companion

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Telephony
import java.util.concurrent.atomic.AtomicInteger

/**
 * Every new SMS, the moment it arrives, even with the SunoSafe app closed and even when the
 * SMS app hides the text in its notification. Needs the "SMS" permission (asked in the app).
 * Android delivers SMS_RECEIVED to apps that hold RECEIVE_SMS; only the system can send it.
 */
class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val parts = try { Telephony.Sms.Intents.getMessagesFromIntent(intent) } catch (e: Exception) { null } ?: return
        if (parts.isEmpty()) return
        val sender = parts[0].displayOriginatingAddress.orEmpty()
        val body = parts.joinToString("") { it.displayMessageBody.orEmpty() }.trim()
        if (body.isEmpty()) return
        Prefs.bump(context, "sms_seen")
        Checker.check(context, "sms", "SMS", sender.take(60), body, source = "sms")
    }
}

/** Scan the SMS already in the inbox (last [days] days), without opening them. */
object SmsInbox {
    fun allowed(c: Context): Boolean =
        c.checkSelfPermission(Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED

    /**
     * Runs in the background. Suspicious messages are recorded in the mini-SIEM; instead of one
     * alarm per old message, one summary warning is shown for the most serious one.
     */
    fun scan(c: Context, days: Int = 30, maxChecks: Int = 15, done: (scanned: Int, sent: Int) -> Unit = { _, _ -> }) {
        val app = c.applicationContext
        if (!allowed(app) || !Prefs.isPaired(app) || !Prefs.monitoringOn(app)) return done(0, 0)
        Thread {
            val since = System.currentTimeMillis() - days * 24L * 3600 * 1000
            val texts = ArrayList<Pair<String, String>>()
            try {
                app.contentResolver.query(Uri.parse("content://sms/inbox"), arrayOf("address", "body", "date"),
                    "date > ?", arrayOf(since.toString()), "date DESC")?.use { cur ->
                    while (cur.moveToNext() && texts.size < 500) {
                        texts.add(cur.getString(0).orEmpty() to cur.getString(1).orEmpty())
                    }
                }
            } catch (e: Exception) {
                Prefs.setLastResult(app, "Could not read the SMS inbox: ${e.javaClass.simpleName}.")
            }
            val suspicious = texts.filter { Prefilter.reason(it.second) != null }.take(maxChecks)
            Prefs.bump(app, "inbox_scans")
            if (suspicious.isEmpty()) {
                Prefs.setLastResult(app, "Scanned ${texts.size} SMS from the last $days days: nothing suspicious.")
                return@Thread done(texts.size, 0)
            }
            val pending = AtomicInteger(suspicious.size)
            val dangerous = ArrayList<Verdict>()
            for ((sender, body) in suspicious) {
                // Already-checked texts are skipped by Checker; count them as finished.
                if (!Checker.firstTime(body)) { if (pending.decrementAndGet() == 0) finish(app, texts.size, dangerous, done); continue }
                Checker.forget(body)
                Checker.check(app, "sms", "SMS inbox", sender.take(60), body, source = "sms", warn = false) { v ->
                    if (v != null && v.alert) synchronized(dangerous) { dangerous.add(v) }
                    if (pending.decrementAndGet() == 0) finish(app, texts.size, dangerous, done)
                }
            }
        }.start()
    }

    private fun finish(app: Context, scanned: Int, dangerous: List<Verdict>, done: (Int, Int) -> Unit) {
        if (dangerous.isNotEmpty()) {
            val worst = dangerous.maxByOrNull { if (it.label == "danger") 2 else 1 }!!
            Prefs.setLastResult(app, "Scanned $scanned SMS: ${dangerous.size} look like scams.")
            Alerts.warn(app, "Found ${dangerous.size} suspicious SMS in your inbox", worst)
        } else {
            Prefs.setLastResult(app, "Scanned $scanned SMS: no strong warning signs.")
        }
        done(scanned, dangerous.size)
    }
}
