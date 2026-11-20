package app.sunosafe.companion

import android.content.Context
import android.content.SharedPreferences
import java.util.UUID

/**
 * Small settings store, private to this app (Android keeps other apps out of it).
 * Prototype note: the device token is stored as plain app-private data; a
 * production build should keep it in the Android Keystore.
 */
object Prefs {
    /** Messaging apps whose notifications can be looked at. The user can switch each off. */
    val WATCHED_APPS: Map<String, String> = linkedMapOf(
        "com.whatsapp" to "WhatsApp",
        "com.whatsapp.w4b" to "WhatsApp Business",
        "com.google.android.apps.messaging" to "Google Messages",
        "com.samsung.android.messaging" to "Samsung Messages",
        "com.android.mms" to "Messages",
        "org.telegram.messenger" to "Telegram",
    )

    val LANGUAGES: Map<String, String> = linkedMapOf("en" to "English", "hi" to "हिंदी")

    private const val WATCH_DAYS = 7L

    private fun sp(c: Context): SharedPreferences = c.getSharedPreferences("sunosafe", Context.MODE_PRIVATE)

    fun gatewayUrl(c: Context): String = sp(c).getString("gateway", "") ?: ""
    fun deviceToken(c: Context): String = sp(c).getString("token", "") ?: ""
    fun appUrl(c: Context): String = sp(c).getString("app", "") ?: ""
    fun isPaired(c: Context): Boolean = gatewayUrl(c).startsWith("https://") && deviceToken(c).length >= 20

    fun savePairing(c: Context, gateway: String, token: String, app: String) {
        sp(c).edit().putString("gateway", gateway.trimEnd('/')).putString("token", token)
            .putString("app", app.trimEnd('/')).apply()
    }

    fun monitoringOn(c: Context): Boolean = sp(c).getBoolean("on", true)
    fun setMonitoring(c: Context, on: Boolean) = sp(c).edit().putBoolean("on", on).apply()

    fun speakOn(c: Context): Boolean = sp(c).getBoolean("speak", true)
    fun setSpeak(c: Context, on: Boolean) = sp(c).edit().putBoolean("speak", on).apply()

    fun lang(c: Context): String = sp(c).getString("lang", "en") ?: "en"
    fun setLang(c: Context, lang: String) = sp(c).edit().putString("lang", lang).apply()

    fun appEnabled(c: Context, pkg: String): Boolean = !(sp(c).getStringSet("off_apps", emptySet()) ?: emptySet()).contains(pkg)
    fun setAppEnabled(c: Context, pkg: String, on: Boolean) {
        val off = (sp(c).getStringSet("off_apps", emptySet()) ?: emptySet()).toMutableSet()
        if (on) off.remove(pkg) else off.add(pkg)
        sp(c).edit().putStringSet("off_apps", off).apply()
    }

    /** Random id for this install: lets the backend tell repeats apart. Not tied to the person. */
    fun deviceId(c: Context): String {
        val existing = sp(c).getString("device", null)
        if (existing != null) return existing
        val fresh = "android-" + UUID.randomUUID().toString().replace("-", "").take(20)
        sp(c).edit().putString("device", fresh).apply()
        return fresh
    }

    fun count(c: Context, key: String): Int = sp(c).getInt("n_$key", 0)
    fun bump(c: Context, key: String) = sp(c).edit().putInt("n_$key", count(c, key) + 1).apply()

    fun lastResult(c: Context): String = sp(c).getString("last", "Nothing checked yet.") ?: ""
    fun setLastResult(c: Context, text: String) = sp(c).edit().putString("last", text).apply()

    fun lastIncident(c: Context): Int = sp(c).getInt("incident", 0)
    fun setLastIncident(c: Context, id: Int?) { if (id != null && id > 0) sp(c).edit().putInt("incident", id).apply() }

    /**
     * Numbers written inside dangerous messages, kept on the phone for 7 days so an
     * incoming call from one of them can be recognised instantly, with no network.
     * Stored as "number|expiryMillis".
     */
    fun addWatchNumbers(c: Context, numbers: List<String>, incidentId: Int?) {
        if (numbers.isEmpty()) return
        val now = System.currentTimeMillis()
        val keep = watchEntries(c, now).toMutableMap()
        numbers.mapNotNull { PhoneNumbers.normalize(it) }.forEach {
            keep[it] = (now + WATCH_DAYS * 86_400_000L) to (incidentId ?: 0)
        }
        sp(c).edit().putStringSet("watch", keep.entries.take(200).map { "${it.key}|${it.value.first}|${it.value.second}" }.toSet()).apply()
    }

    /** Incident id linked to a watched number, or null if the number is not on the list. */
    fun watchedIncident(c: Context, raw: String?): Int? {
        val number = PhoneNumbers.normalize(raw) ?: return null
        return watchEntries(c, System.currentTimeMillis())[number]?.second
    }

    private fun watchEntries(c: Context, now: Long): Map<String, Pair<Long, Int>> =
        (sp(c).getStringSet("watch", emptySet()) ?: emptySet()).mapNotNull { entry ->
            val parts = entry.split("|")
            val expiry = parts.getOrNull(1)?.toLongOrNull() ?: return@mapNotNull null
            if (expiry < now) null else parts[0] to (expiry to (parts.getOrNull(2)?.toIntOrNull() ?: 0))
        }.toMap()

    fun watchCount(c: Context): Int = watchEntries(c, System.currentTimeMillis()).size
}
