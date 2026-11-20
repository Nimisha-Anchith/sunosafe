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
)

/**
 * Talks to the SunoSafe gateway. Only HTTPS is allowed, the device token goes in
 * the Authorization header, and any failure returns null: a network problem must
 * never crash the listener, and it is shown as "could not check", never "safe".
 */
object Backend {
    private const val TIMEOUT_MS = 20_000

    fun report(c: Context, appPackage: String, title: String, text: String): Verdict? =
        post(c, "/device/notifications", JSONObject()
            .put("app", appPackage)
            .put("title", title.take(200))
            .put("text", text.take(4000))
            .put("device_id", Prefs.deviceId(c))
            .put("lang", Prefs.lang(c)))

    fun reportCall(c: Context, number: String?, timeoutMs: Int = 4_000): Verdict? =
        post(c, "/device/calls", JSONObject()
            .put("number", (number ?: "").filter { it.isDigit() || it == '+' }.take(20))
            .put("device_id", Prefs.deviceId(c))
            .put("lang", Prefs.lang(c)), timeoutMs)

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
            )
        } catch (e: Exception) {
            null
        } finally {
            connection?.disconnect()
        }
    }
}
