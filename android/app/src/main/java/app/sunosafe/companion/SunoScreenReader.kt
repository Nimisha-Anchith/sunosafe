package app.sunosafe.companion

import android.accessibilityservice.AccessibilityService
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.Executors

/**
 * Checks the messages you can SEE on screen in WhatsApp and SMS apps, including old ones you
 * scroll through, not only new notifications.
 *
 *   you open or scroll a chat ─► (pause 1.2 s) ─► read the message bubbles on screen
 *        ─► Prefilter: link or scam wording? ─► no: forget it, nothing leaves the phone
 *                                              └► yes: SunoSafe backend ─► mini-SIEM ─► spoken warning
 *
 * Android allows this only through an accessibility service that the user switches on
 * themselves (Settings → Accessibility → Installed apps → SunoSafe). It is limited to the
 * messaging apps listed in res/xml/screen_reader.xml, never reads password fields, and
 * checks each message text only once.
 */
class SunoScreenReader : AccessibilityService() {

    private val handler = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private var pendingPackage: String? = null

    // Texts already checked (by hash), so scrolling up and down does not re-send them.
    private val seen = object : LinkedHashMap<Int, Boolean>(256, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Boolean>?) = size > 1000
    }

    private val scan = Runnable { pendingPackage?.let { scanScreen(it) } }

    override fun onServiceConnected() {
        Prefs.setLastResult(this, "Screen checking is on: SunoSafe checks messages you open in WhatsApp and SMS.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val pkg = event?.packageName?.toString() ?: return
        if (pkg !in Prefs.WATCHED_APPS || !Prefs.appEnabled(this, pkg)) return
        if (!Prefs.monitoringOn(this) || !Prefs.isPaired(this)) return
        // Wait until scrolling settles, then read the screen once.
        pendingPackage = pkg
        handler.removeCallbacks(scan)
        handler.postDelayed(scan, SETTLE_MS)
    }

    override fun onInterrupt() {}

    private fun scanScreen(pkg: String) {
        val root = try { rootInActiveWindow } catch (e: Exception) { null } ?: return
        if (root.packageName?.toString() != pkg) return
        val texts = LinkedHashSet<String>()
        collect(root, texts, 0)
        Prefs.bump(this, "screen_scans")
        val fresh = texts.filter { text ->
            val key = (pkg + "\n" + text).hashCode()
            synchronized(seen) { if (seen.containsKey(key)) false else { seen[key] = true; true } }
        }
        if (fresh.isEmpty()) return
        Prefs.bump(this, "screen_seen")
        val suspicious = fresh.filter { Prefilter.reason(it) != null && Checker.firstTime(it) }.take(MAX_PER_SCAN)
        val appName = Prefs.WATCHED_APPS[pkg] ?: "a messaging app"
        if (suspicious.isEmpty()) {
            Prefs.setLastResult(this, "Checked ${fresh.size} message(s) on screen in $appName: nothing suspicious.")
            return
        }
        val context = applicationContext
        for (text in suspicious) {
            Prefs.bump(context, "sent")
            worker.execute {
                val verdict = Backend.report(context, pkg, "On screen", text, source = "screen")
                when {
                    verdict == null -> Prefs.setLastResult(context,
                        "A message on screen in $appName could not be checked (no connection). This does not mean it is safe.")
                    verdict.alert -> {
                        Prefs.bump(context, "alerts")
                        Prefs.bump(context, "screen_alerts")
                        Prefs.addWatchNumbers(context, verdict.watchNumbers, verdict.incidentId)
                        Prefs.setLastResult(context, "Warned you about a message on screen in $appName.")
                        val heading = if (verdict.label == "danger") "Danger: scam message on screen in $appName"
                                      else "Be careful: message on screen in $appName"
                        Alerts.warn(context, heading, verdict)
                    }
                    else -> Prefs.setLastResult(context, "Checked a message on screen in $appName: no strong warning signs.")
                }
            }
        }
    }

    /** Message bubbles are TextViews; keep texts long enough to be a message. */
    private fun collect(node: AccessibilityNodeInfo?, out: MutableSet<String>, depth: Int) {
        if (node == null || depth > 40 || out.size >= MAX_TEXTS) return
        if (node.isPassword || node.isEditable) return   // never read what the user is typing or passwords
        val text = node.text?.toString()?.trim().orEmpty()
        if (text.length >= MIN_LENGTH) out.add(text.take(1500))
        for (i in 0 until node.childCount) {
            collect(try { node.getChild(i) } catch (e: Exception) { null }, out, depth + 1)
        }
    }

    override fun onDestroy() {
        handler.removeCallbacks(scan)
        worker.shutdown()
        super.onDestroy()
    }

    private companion object {
        const val SETTLE_MS = 1200L
        const val MIN_LENGTH = 25
        const val MAX_TEXTS = 60
        const val MAX_PER_SCAN = 4
    }
}
