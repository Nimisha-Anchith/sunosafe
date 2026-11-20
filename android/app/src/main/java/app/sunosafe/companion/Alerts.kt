package app.sunosafe.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.speech.tts.TextToSpeech
import java.util.Locale

/** Shows SunoSafe's own warning and, if allowed, speaks it at once. */
object Alerts {
    private const val CHANNEL = "sunosafe_alerts"

    fun ensureChannel(c: Context) {
        val manager = c.getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL) != null) return
        val channel = NotificationChannel(CHANNEL, c.getString(R.string.channel_alerts), NotificationManager.IMPORTANCE_HIGH)
        channel.description = c.getString(R.string.channel_alerts_desc)
        channel.enableVibration(true)
        channel.vibrationPattern = longArrayOf(0, 300, 120, 300, 120, 300)
        manager.createNotificationChannel(channel)
    }

    /** Opens the SunoSafe voice agent (Agora + Murf) already briefed on this incident. */
    fun voiceIntent(c: Context, incidentId: Int?): Intent {
        val app = Prefs.appUrl(c)
        val intent = if (app.startsWith("https://")) {
            val q = buildString {
                append("$app/talk?lang=${Prefs.lang(c)}")
                if (incidentId != null && incidentId > 0) append("&incident=$incidentId")
            }
            Intent(Intent.ACTION_VIEW, Uri.parse(q))
        } else Intent(c, MainActivity::class.java)
        return intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    private fun evidenceIntent(c: Context, incidentId: Int?): Intent {
        val app = Prefs.appUrl(c)
        val intent = if (app.startsWith("https://") && incidentId != null) Intent(Intent.ACTION_VIEW, Uri.parse("$app/?incident=$incidentId"))
        else Intent(c, MainActivity::class.java)
        return intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    fun warn(c: Context, title: String, verdict: Verdict) {
        ensureChannel(c)
        Prefs.setLastIncident(c, verdict.incidentId)
        val danger = verdict.label == "danger" || verdict.level == "high" || verdict.level == "critical"
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val id = verdict.incidentId ?: (System.currentTimeMillis() % 100000).toInt()
        val hear = PendingIntent.getActivity(c, id * 2, voiceIntent(c, verdict.incidentId), flags)
        val evidence = PendingIntent.getActivity(c, id * 2 + 1, evidenceIntent(c, verdict.incidentId), flags)

        val notification = Notification.Builder(c, CHANNEL)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(title)
            .setContentText(verdict.say)
            .setStyle(Notification.BigTextStyle().bigText(verdict.say))
            .setCategory(Notification.CATEGORY_ALARM)
            .setColor(if (danger) 0xFFB42318.toInt() else 0xFFB45309.toInt())
            .setAutoCancel(true)
            .setContentIntent(hear)
            .addAction(Notification.Action.Builder(null, "Talk to SunoSafe", hear).build())
            .addAction(Notification.Action.Builder(null, "See evidence", evidence).build())
            .build()
        // One notification per incident: repeated warnings about the same scam update it.
        c.getSystemService(NotificationManager::class.java).notify(id, notification)

        if (Prefs.speakOn(c)) Speaker.say(c, verdict.say, Prefs.lang(c))
    }
}

/**
 * Speaks a warning with the phone's built-in text-to-speech voice, instantly and
 * offline. (The conversational explanation afterwards uses Murf Falcon through
 * the Agora voice agent.) Stays silent when the phone is on silent or vibrate.
 */
object Speaker {
    private var tts: TextToSpeech? = null
    private var ready = false
    private var pending: Pair<String, String>? = null

    @Synchronized
    fun say(c: Context, text: String, lang: String) {
        if (text.isBlank()) return
        val audio = c.getSystemService(AudioManager::class.java)
        if (audio.ringerMode != AudioManager.RINGER_MODE_NORMAL) return
        if (tts == null) {
            pending = text to lang
            tts = TextToSpeech(c.applicationContext) { status ->
                synchronized(this) {
                    ready = status == TextToSpeech.SUCCESS
                    if (ready) {
                        tts?.setSpeechRate(0.9f)
                        pending?.let { speakNow(it.first, it.second) }
                    }
                    pending = null
                }
            }
        } else if (ready) {
            speakNow(text, lang)
        } else {
            pending = text to lang
        }
    }

    private fun speakNow(text: String, lang: String) {
        val engine = tts ?: return
        val wanted = if (lang == "hi") Locale("hi", "IN") else Locale("en", "IN")
        val result = engine.setLanguage(wanted)
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            engine.language = Locale.ENGLISH   // fall back rather than stay silent
        }
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "sunosafe-warning")
    }
}
