package app.sunosafe.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
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

        if (Prefs.speakOn(c)) Speaker.say(c, verdict.say, Prefs.lang(c), verdict.sayEn, verdict.audioId)
    }
}

/**
 * Speaks a warning with the phone's built-in text-to-speech voice, instantly and
 * offline. (The conversational explanation afterwards uses Murf Falcon through
 * the Agora voice agent.) Stays silent when the phone is on silent or vibrate.
 *
 * Hindi: many phones (Samsung's own engine included) report Hindi as "supported"
 * but have no Hindi voice downloaded, or speak Devanagari text with an English
 * voice, which produces silence. So SunoSafe prefers Google's speech engine when
 * it is installed, checks that a usable Hindi voice is really on the phone, and
 * otherwise speaks the English copy of the warning. A warning is never dropped.
 */
object Speaker {
    private const val GOOGLE_TTS = "com.google.android.tts"
    private var tts: TextToSpeech? = null
    private var ready = false
    private var pending: Triple<String, String, String>? = null

    /** What happened the last time a warning was spoken; shown on the main screen. */
    @Volatile var lastNote: String = ""
        private set

    /**
     * Speak a warning. First choice: the Murf Falcon audio from the SunoSafe backend (natural voice in all five
     * languages, same voice as the voice agent). If that cannot be fetched or played, the phone's own voice.
     */
    fun say(c: Context, text: String, lang: String, english: String = "", audioId: String? = null) {
        if (text.isBlank()) return
        val app = c.applicationContext
        val audio = app.getSystemService(AudioManager::class.java)
        if (audio.ringerMode != AudioManager.RINGER_MODE_NORMAL) {
            lastNote = "Phone is on silent or vibrate, so the warning was not spoken."
            return
        }
        if (audioId.isNullOrBlank() || !Prefs.isPaired(app)) {
            phoneVoice(app, text, lang, english)
            return
        }
        Thread {
            val file = Backend.fetchSpeech(app, audioId)
            if (file == null) {
                lastNote = "Could not get the SunoSafe voice, so the phone's own voice was used."
                phoneVoice(app, text, lang, english)
            } else {
                Handler(Looper.getMainLooper()).post {
                    play(app, file) { phoneVoice(app, text, lang, english) }
                }
            }
        }.start()
    }

    private var player: MediaPlayer? = null

    private fun play(c: Context, file: java.io.File, onFail: () -> Unit) {
        try {
            player?.release()
            val attrs = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
            val manager = c.getSystemService(AudioManager::class.java)
            val focus = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(attrs).build()
            manager.requestAudioFocus(focus)
            val mp = MediaPlayer()
            player = mp
            mp.setAudioAttributes(attrs)
            mp.setDataSource(file.path)
            mp.setOnPreparedListener {
                lastNote = "Spoke the warning with the SunoSafe voice."
                it.start()
            }
            mp.setOnCompletionListener {
                manager.abandonAudioFocusRequest(focus)
                it.release()
                if (player === it) player = null
            }
            mp.setOnErrorListener { m, _, _ ->
                manager.abandonAudioFocusRequest(focus)
                m.release()
                if (player === m) player = null
                file.delete()
                onFail()
                true
            }
            mp.prepareAsync()
        } catch (e: Exception) {
            file.delete()
            onFail()
        }
    }

    @Synchronized
    private fun phoneVoice(c: Context, text: String, lang: String, english: String) {
        val item = Triple(text, lang, english)
        if (tts == null) {
            pending = item
            val app = c.applicationContext
            val engine = if (hasEngine(app, GOOGLE_TTS)) GOOGLE_TTS else null
            val listener = TextToSpeech.OnInitListener { status ->
                synchronized(this) {
                    ready = status == TextToSpeech.SUCCESS
                    if (ready) {
                        tts?.setSpeechRate(0.9f)
                        pending?.let { speakNow(it.first, it.second, it.third) }
                    } else {
                        lastNote = "The phone's speech engine did not start."
                    }
                    pending = null
                }
            }
            tts = if (engine != null) TextToSpeech(app, listener, engine) else TextToSpeech(app, listener)
        } else if (ready) {
            speakNow(text, lang, english)
        } else {
            pending = item
        }
    }

    private fun hasEngine(c: Context, pkg: String): Boolean = try {
        c.packageManager.getPackageInfo(pkg, 0)
        true
    } catch (e: Exception) {
        false
    }

    /** True only if the engine has a Hindi (or other) voice that is actually installed. */
    private fun usableVoice(engine: TextToSpeech, locale: Locale): Boolean {
        val availability = engine.isLanguageAvailable(locale)
        if (availability < TextToSpeech.LANG_AVAILABLE) return false
        val voices = try { engine.voices } catch (e: Exception) { null } ?: return true
        return voices.any { v ->
            v.locale.language == locale.language &&
                !v.features.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)
        }
    }

    private fun speakNow(text: String, lang: String, english: String) {
        val engine = tts ?: return
        val wanted = if (lang == "hi") Locale("hi", "IN") else Locale("en", "IN")
        val spoken: String
        if (lang == "en" || usableVoice(engine, wanted)) {
            engine.setLanguage(wanted)
            spoken = text
            lastNote = if (lang == "hi") "Spoke the warning in Hindi." else "Spoke the warning."
        } else {
            // No real Hindi voice: speak English rather than stay silent.
            if (engine.setLanguage(Locale("en", "IN")) < TextToSpeech.LANG_AVAILABLE) engine.setLanguage(Locale.ENGLISH)
            spoken = english.ifBlank { "Warning from SunoSafe. Please look at your phone." }
            lastNote = "No Hindi voice is installed on this phone, so the warning was spoken in English. " +
                "To add one: Settings, General management, Text-to-speech, choose Google, then install Hindi voice data."
        }
        engine.speak(spoken, TextToSpeech.QUEUE_FLUSH, null, "sunosafe-warning")
    }
}
