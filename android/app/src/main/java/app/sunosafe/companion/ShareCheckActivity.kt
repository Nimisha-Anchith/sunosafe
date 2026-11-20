package app.sunosafe.companion

import android.app.Activity
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Check one message on demand.
 *
 *  - From WhatsApp / Messages: press and hold a message → Share → SunoSafe (ACTION_SEND text).
 *  - From the SunoSafe app: "Check a message" → uses what you copied (clipboard).
 *
 * The text goes to the SunoSafe backend (same rules and mini-SIEM as automatic checks),
 * and the answer is shown large and spoken in the chosen language.
 */
class ShareCheckActivity : Activity() {

    private val bg = Color.parseColor("#07130F")
    private val surface = Color.parseColor("#11251F")
    private val border = Color.parseColor("#1F3B33")
    private val ink = Color.parseColor("#E7F3EE")
    private val muted = Color.parseColor("#93ADA5")
    private lateinit var title: TextView
    private lateinit var body: TextView
    private lateinit var evidence: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        setContentView(buildScreen())
        val shared = if (intent?.action == Intent.ACTION_SEND) intent.getStringExtra(Intent.EXTRA_TEXT) else null
        val text = (shared ?: clipboardText()).orEmpty().trim()
        if (text.isEmpty()) {
            show("Nothing to check", "Copy a message first (press and hold it → Copy), or use Share → SunoSafe from the chat.", muted)
            return
        }
        if (!Prefs.isPaired(this)) {
            show("Not connected", "Connect SunoSafe first: open the SunoSafe website → Profile → Connect Android app.", Color.parseColor("#FBBF24"))
            return
        }
        check(text.take(4000), "share")
    }

    private fun clipboardText(): String? = try {
        getSystemService(ClipboardManager::class.java)?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString()
    } catch (e: Exception) {
        null
    }

    private fun check(text: String, source: String) {
        show("Checking…", "SunoSafe is checking the message and any link in it. This takes a few seconds.", muted)
        val app = applicationContext
        Thread {
            val verdict = Backend.report(app, "app.sunosafe.companion", "Checked by you", text, source = source)
            runOnUiThread {
                when {
                    verdict == null -> show("Could not check", "No connection to SunoSafe. This does not mean the message is safe.", Color.parseColor("#FBBF24"))
                    verdict.alert -> {
                        val danger = verdict.label == "danger"
                        show(if (danger) "⛔  Danger: this looks like a scam" else "⚠  Be careful", verdict.say,
                            if (danger) Color.parseColor("#FF8A80") else Color.parseColor("#FBBF24"))
                        Prefs.addWatchNumbers(app, verdict.watchNumbers, verdict.incidentId)
                        Prefs.setLastIncident(app, verdict.incidentId)
                        if (Prefs.speakOn(app)) Speaker.say(app, verdict.say, Prefs.lang(app), verdict.sayEn, verdict.audioId)
                        verdict.incidentId?.let { id ->
                            evidence.visibility = Button.VISIBLE
                            evidence.setOnClickListener {
                                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("${Prefs.appUrl(this)}/?incident=$id")))
                            }
                        }
                    }
                    else -> show("✔  No strong warning signs",
                        "SunoSafe found no known scam signs. Still never share an OTP or PIN with anyone.", Color.parseColor("#5FD3A5"))
                }
            }
        }.start()
    }

    private fun show(heading: String, text: String, color: Int) {
        title.text = heading
        title.setTextColor(color)
        body.text = text
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun buildScreen(): ScrollView {
        fun button(label: String, primary: Boolean, onClick: () -> Unit) = Button(this).apply {
            text = label
            textSize = 18f
            isAllCaps = false
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(if (primary) Color.parseColor("#031B13") else ink)
            background = GradientDrawable().apply {
                setColor(if (primary) Color.parseColor("#10B981") else surface)
                cornerRadius = dp(18).toFloat()
                if (!primary) setStroke(dp(1), border)
            }
            minimumHeight = dp(60)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                .apply { topMargin = dp(12) }
            setOnClickListener { onClick() }
        }
        title = TextView(this).apply { textSize = 26f; setTypeface(typeface, Typeface.BOLD); setPadding(0, dp(8), 0, dp(8)) }
        body = TextView(this).apply { textSize = 19f; setTextColor(ink); setLineSpacing(0f, 1.2f) }
        evidence = button("See the evidence", false) {}.apply { visibility = Button.GONE }
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(36), dp(22), dp(36))
            addView(TextView(this@ShareCheckActivity).apply {
                text = "🛡  SunoSafe message check"; textSize = 17f; setTextColor(muted); gravity = Gravity.START
            })
            addView(title)
            addView(body)
            addView(evidence)
            addView(button("Done", true) { finish() })
        }
        return ScrollView(this).apply { setBackgroundColor(bg); addView(column) }
    }
}
