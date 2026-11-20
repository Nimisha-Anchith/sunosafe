package app.sunosafe.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

/**
 * Keeps SunoSafe protecting the phone while the app is closed.
 *
 * A small, permanent "SunoSafe protection is on" notification (Android's rule for apps that
 * work in the background). While it runs, Samsung's battery saver does not put SunoSafe to
 * sleep, and it fetches warnings from the backend every 10 s (e.g. "SunoSafe answered a scam
 * call for you"). Started when the app opens and again after the phone restarts.
 */
class ProtectionService : Service() {
    private var poller: ScheduledExecutorService? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        running = true
        val note = statusNotification(this)
        if (Build.VERSION.SDK_INT >= 34) startForeground(ID, note, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        else startForeground(ID, note)
        poller = Executors.newSingleThreadScheduledExecutor().also {
            it.scheduleWithFixedDelay({ poll() }, 3, POLL_SECONDS, TimeUnit.SECONDS)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        running = false
        poller?.shutdownNow()
        super.onDestroy()
    }

    private fun poll() {
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

    companion object {
        private const val ID = 7001
        private const val CHANNEL = "sunosafe_status"
        private const val POLL_SECONDS = 10L
        @Volatile var running = false

        fun start(c: Context) {
            if (!Prefs.isPaired(c)) return
            try {
                c.startForegroundService(Intent(c, ProtectionService::class.java))
            } catch (e: Exception) {
                // Android may refuse a start from the background; the next app open or boot retries.
            }
        }

        private fun statusNotification(c: Context): Notification {
            val manager = c.getSystemService(NotificationManager::class.java)
            if (manager.getNotificationChannel(CHANNEL) == null) {
                manager.createNotificationChannel(NotificationChannel(CHANNEL, "SunoSafe protection status",
                    NotificationManager.IMPORTANCE_MIN).apply { setShowBadge(false) })
            }
            val open = PendingIntent.getActivity(c, 0, Intent(c, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            return Notification.Builder(c, CHANNEL)
                .setSmallIcon(R.drawable.ic_shield)
                .setContentTitle("SunoSafe protection is on")
                .setContentText("Checking messages, WhatsApp and calls for scams")
                .setOngoing(true)
                .setContentIntent(open)
                .build()
        }
    }
}

/** Starts protection again after the phone restarts or the app is updated. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            ProtectionService.start(context)
        }
    }
}
