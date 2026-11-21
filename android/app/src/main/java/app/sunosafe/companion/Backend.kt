package app.sunosafe.companion

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** What the SunoSafe backend answered. */
data class Verdict(
    val alert: Boolean,
    val level: String,
    val label: String,
    val say: String,
    val incidentId: Int?,
    val watchNumbers: List<String> = emptyList(),
    /** English copy, spoken when the phone has no voice for the chosen language. */
    val sayEn: String = "",
    /** Id of the Murf audio for [say]; null when the backend has none. */
    val audioId: String? = null,
)

/**
 * Talks to the SunoSafe gateway. Only HTTPS is allowed, the device token goes in
 * the Authorization header, and any failure returns null: a network problem must
 * never crash the listener, and it is shown as "could not check", never "safe".
 */
object Backend {
    // The hosted backend (free plan) can take ~30 s to wake up after being idle: wait long enough.
    private const val TIMEOUT_MS = 45_000
    private val AUDIO_ID = Regex("^[A-Za-z0-9-]{3,40}$")

    /**
     * The spoken warning as an MP3 made by Murf Falcon (works for every language, whatever voices the phone has).
     * Audio is kept in the app's cache so a repeated warning plays instantly and offline. Null on any failure.
     */
    fun fetchSpeech(c: Context, audioId: String): java.io.File? {
        if (!audioId.matches(AUDIO_ID)) return null
        val dir = java.io.File(c.cacheDir, "speech").apply { mkdirs() }
        val file = java.io.File(dir, "$audioId.mp3")
        if (file.isFile && file.length() > 1000) return file
        val base = Prefs.gatewayUrl(c)
        if (!base.startsWith("https://")) return null
        var connection: HttpURLConnection? = null
        return try {
            connection = (URL("$base/device/speech/$audioId").openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 6_000
                readTimeout = 10_000
                instanceFollowRedirects = false
                setRequestProperty("Authorization", "Bearer " + Prefs.deviceToken(c))
            }
            if (connection.responseCode != 200) return null
            val bytes = connection.inputStream.use { it.readBytes() }
            if (bytes.size < 1000 || bytes.size > 2_000_000) return null
            val tmp = java.io.File(dir, "$audioId.part")
            tmp.writeBytes(bytes)
            if (!tmp.renameTo(file)) return null
            // keep the cache small
            dir.listFiles()?.sortedByDescending { it.lastModified() }?.drop(40)?.forEach { it.delete() }
            file
        } catch (e: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }

    fun report(c: Context, appPackage: String, title: String, text: String, source: String = "notification"): Verdict? =
        post(c, "/device/notifications", JSONObject()
            .put("app", appPackage)
            .put("title", title.take(200))
            .put("text", text.take(4000))
            .put("device_id", Prefs.deviceId(c))
            .put("lang", Prefs.lang(c))
            .put("source", source))

    fun reportCall(c: Context, number: String?, timeoutMs: Int = 4_000): Verdict? =
        post(c, "/device/calls", JSONObject()
            .put("number", (number ?: "").filter { it.isDigit() || it == '+' }.take(20))
            .put("device_id", Prefs.deviceId(c))
            .put("lang", Prefs.lang(c)), timeoutMs)

    /** One warning queued by the backend, e.g. after SunoSafe's call assistant answered a scam call. */
    data class DeviceAlert(val id: Int, val verdict: Verdict)

    /** Fetch warnings the phone has not shown yet. Null on any failure (never treated as "safe"). */
    fun fetchAlerts(c: Context, afterId: Int): List<DeviceAlert>? {
        val base = Prefs.gatewayUrl(c)
        if (!base.startsWith("https://")) return null
        var connection: HttpURLConnection? = null
        return try {
            connection = (URL("$base/device/alerts?after=$afterId&lang=${Prefs.lang(c)}").openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 8_000
                readTimeout = 8_000
                instanceFollowRedirects = false
                setRequestProperty("Authorization", "Bearer " + Prefs.deviceToken(c))
            }
            if (connection.responseCode != 200) return null
            val list = JSONObject(connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
                .optJSONArray("alerts") ?: return emptyList()
            (0 until list.length()).map { i ->
                val a = list.getJSONObject(i)
                DeviceAlert(a.optInt("id"), Verdict(
                    alert = true, level = a.optString("level", "high"), label = "danger",
                    say = a.optString("say", "").take(400),
                    incidentId = if (a.isNull("incident_id")) null else a.optInt("incident_id"),
                    sayEn = a.optString("say_en", "").take(400),
                    audioId = a.optString("audio_id", "").takeIf { it.matches(AUDIO_ID) }))
            }
        } catch (e: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }

    private fun post(c: Context, path: String, json: JSONObject, timeoutMs: Int = TIMEOUT_MS): Verdict? {
        val base = Prefs.gatewayUrl(c)
        if (!base.startsWith("https://")) return null
        var connection: HttpURLConnection? = null
        return try {
            val body = json.toString().toByteArray(Charsets.UTF_8)
            connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = timeoutMs
                readTimeout = timeoutMs
                doOutput = true
                instanceFollowRedirects = false
                setFixedLengthStreamingMode(body.size)
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Authorization", "Bearer " + Prefs.deviceToken(c))
            }
            connection.outputStream.use { it.write(body) }
            if (connection.responseCode != 200) return null
            val out = JSONObject(connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
            val numbers = out.optJSONArray("watch_numbers")
            Verdict(
                alert = out.optBoolean("alert", false),
                level = out.optString("level", "info"),
                label = out.optString("label", if (out.optBoolean("alert")) "danger" else "no_known_issues"),
                say = out.optString("say", "").take(400),
                incidentId = if (out.isNull("incident_id")) null else out.optInt("incident_id"),
                watchNumbers = (0 until (numbers?.length() ?: 0)).map { numbers!!.optString(it) },
                sayEn = out.optString("say_en", "").take(400),
                audioId = out.optString("audio_id", "").takeIf { it.matches(AUDIO_ID) },
            )
        } catch (e: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }
}
