package app.sunosafe.companion

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.app.role.RoleManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

/**
 * The companion's screen: status, four setup steps, voice actions, controls,
 * activity and a plain statement of what is and is not sent.
 * Built in code with large text and big buttons; every control has a text label
 * so TalkBack reads it.
 */
class MainActivity : Activity() {

    private lateinit var statusCard: LinearLayout
    private lateinit var statusTitle: TextView
    private lateinit var statusBody: TextView
    private lateinit var stats: TextView
    private val bg = Color.parseColor("#07130F")
    private val surface = Color.parseColor("#11251F")
    private val elev = Color.parseColor("#17322A")
    private val border = Color.parseColor("#1F3B33")
    private val green = Color.parseColor("#34D399")
    private val tealMid = Color.parseColor("#10B981")
    private val onGreen = Color.parseColor("#031B13")
    private val amber = Color.parseColor("#F59E0B")
    private val ink = Color.parseColor("#E7F3EE")
    private val muted = Color.parseColor("#93ADA5")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Alerts.ensureChannel(this)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        setContentView(buildScreen())
        handlePairingLink(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handlePairingLink(intent)
    }

    override fun onResume() {
        super.onResume()
        refresh()
        // Keep the "this caller is linked to a scam" warning on the phone, in the chosen language,
        // so it can be spoken at once while a call is ringing, even with a poor connection.
        if (Prefs.isPaired(this)) {
            val app = applicationContext
            val lang = Prefs.lang(app)
            Thread { Backend.fetchSpeech(app, "call-watch-$lang") }.start()
        }
    }

    // ------------------------------------------------------------------ pairing
    /**
     * Pairing arrives as sunosafe://pair?g=<gateway>&t=<token>&a=<web app>, opened from
     * the user's own SunoSafe web app. Any app or web page could try to open such a
     * link, so nothing is saved until the user confirms the address on screen.
     */
    private fun handlePairingLink(intent: Intent?) {
        val data: Uri = intent?.data ?: return
        if (data.scheme != "sunosafe" || data.host != "pair") return
        intent.data = null
        val gateway = data.getQueryParameter("g").orEmpty()
        val token = data.getQueryParameter("t").orEmpty()
        val app = data.getQueryParameter("a").orEmpty()
        val valid = gateway.startsWith("https://") && app.startsWith("https://") &&
            Regex("^[A-Za-z0-9_-]{20,200}$").matches(token)
        if (!valid) {
            Toast.makeText(this, "That connection link is not valid.", Toast.LENGTH_LONG).show()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Connect to your SunoSafe?")
            .setMessage(
                "Suspicious notifications and linked callers will be checked by:\n\n${Uri.parse(gateway).host}\n\n" +
                    "Only say yes if you just tapped \"Connect Android app\" in your own SunoSafe."
            )
            .setPositiveButton("Yes, connect") { _, _ ->
                Prefs.savePairing(this, gateway, token, app)
                Toast.makeText(this, "Connected.", Toast.LENGTH_LONG).show()
                refresh()
            }
            .setNegativeButton("No", null)
            .show()
    }

    // ------------------------------------------------------------------ state
    private fun listenerEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners").orEmpty()
        return enabled.split(":").any { it.startsWith("$packageName/") }
    }

    private fun warningsAllowed(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun screenReaderOn(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES).orEmpty()
        return enabled.split(":").any { it.startsWith("$packageName/") }
    }

    private fun screeningRoleHeld(): Boolean =
        Build.VERSION.SDK_INT >= 29 &&
            getSystemService(RoleManager::class.java)?.isRoleHeld(RoleManager.ROLE_CALL_SCREENING) == true

    private fun refresh() {
        fun mark(ok: Boolean) = if (ok) "✔" else "○"
        val watching = listenerEnabled() && Prefs.isPaired(this) && Prefs.monitoringOn(this)
        statusTitle.text = if (watching) "🛡  Protecting you" else "⚠  Setup needed"
        statusBody.text = buildString {
            append(if (watching) "SunoSafe will warn you aloud when a message or caller looks like a scam.\n\n"
                   else "Finish the steps below so SunoSafe can warn you without being asked.\n\n")
            append("${mark(listenerEnabled())}  Notification access\n")
            append("${mark(warningsAllowed())}  Allowed to show warnings\n")
            append("${mark(Prefs.isPaired(this@MainActivity))}  Connected to your SunoSafe\n")
            append("${mark(screeningRoleHeld())}  Checking incoming callers\n")
            append("${mark(screenReaderOn())}  Checking messages on screen (WhatsApp, SMS)")
        }
        (statusCard.background as GradientDrawable).apply {
            setColor(if (watching) Color.parseColor("#0F2E24") else Color.parseColor("#2A2210"))
            setStroke(dp(1), if (watching) green else amber)
        }
        statusTitle.setTextColor(if (watching) green else Color.parseColor("#FBBF24"))
        stats.text = "Messages looked at on this phone: ${Prefs.count(this, "seen")}\n" +
            "Screens checked in WhatsApp/SMS: ${Prefs.count(this, "screen_scans")} " +
            "(warnings: ${Prefs.count(this, "screen_alerts")})\n" +
            "Hidden by the app (could not check): ${Prefs.count(this, "hidden")}\n" +
            "Sent for a full check: ${Prefs.count(this, "sent")}\n" +
            "Message warnings: ${Prefs.count(this, "alerts")}\n" +
            "Unknown callers checked: ${Prefs.count(this, "calls")}\n" +
            "Caller warnings: ${Prefs.count(this, "call_alerts")}\n" +
            "Scam numbers remembered (7 days): ${Prefs.watchCount(this)}\n\n" +
            "Latest: ${Prefs.lastResult(this)}" +
            (if (Speaker.lastNote.isNotBlank()) "\nVoice: ${Speaker.lastNote}" else "")
    }

    // ------------------------------------------------------------------ actions
    private fun requestScreeningRole() {
        if (Build.VERSION.SDK_INT < 29) {
            Toast.makeText(this, "Caller checking needs Android 10 or newer.", Toast.LENGTH_LONG).show()
            return
        }
        val roles = getSystemService(RoleManager::class.java)
        if (roles == null || !roles.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            Toast.makeText(this, "This phone does not offer caller checking to apps.", Toast.LENGTH_LONG).show()
            return
        }
        if (roles.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)) {
            Toast.makeText(this, "SunoSafe already checks incoming callers.", Toast.LENGTH_SHORT).show()
            return
        }
        @Suppress("DEPRECATION")
        startActivityForResult(roles.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING), 2)
    }

    private fun openWeb(path: String) {
        val app = Prefs.appUrl(this)
        if (!app.startsWith("https://")) {
            Toast.makeText(this, "Connect to your SunoSafe first (step 3).", Toast.LENGTH_LONG).show()
            return
        }
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(app + path)))
    }

    private fun practiceWarning() {
        if (!Prefs.isPaired(this)) {
            Toast.makeText(this, "Connect to your SunoSafe first (step 3).", Toast.LENGTH_LONG).show()
            return
        }
        Toast.makeText(this, "Checking a made-up scam message…", Toast.LENGTH_SHORT).show()
        val sample = "[PRACTICE] Dear SBI customer, your account will be BLOCKED today. " +
            "Update KYC at https://wrong.host.badssl.com/sbi-kyc and share the OTP sent to you. Call 9876543210."
        Thread {
            val verdict = Backend.report(applicationContext, "com.google.android.apps.messaging", "Practice message", sample)
            runOnUiThread {
                if (verdict == null) {
                    Toast.makeText(this, "Could not reach SunoSafe. Check that the laptop and tunnel are running.",
                        Toast.LENGTH_LONG).show()
                } else {
                    Prefs.setLastResult(this, "Practice warning shown.")
                    Prefs.addWatchNumbers(this, verdict.watchNumbers, verdict.incidentId)
                    Alerts.warn(applicationContext, "Practice: scam message in Messages", verdict)
                }
                refresh()
            }
        }.start()
    }

    // ------------------------------------------------------------------ screen
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    private fun rounded(color: Int, radius: Int = 22, stroke: Int? = null) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radius).toFloat()
        if (stroke != null) setStroke(dp(1), stroke)
    }

    private fun text(content: String, size: Float, bold: Boolean = false, color: Int = ink) =
        TextView(this).apply {
            text = content
            textSize = size
            setTextColor(color)
            if (bold) setTypeface(typeface, Typeface.BOLD)
            setPadding(0, dp(4), 0, dp(4))
            setLineSpacing(0f, 1.15f)
        }

    private fun button(label: String, bg: Int = tealMid, fg: Int = onGreen, onClick: () -> Unit) = Button(this).apply {
        text = label
        textSize = 17f
        isAllCaps = false
        setTextColor(fg)
        background = rounded(bg, 18, if (bg == elev) border else null)
        setTypeface(typeface, Typeface.BOLD)
        minimumHeight = dp(60)
        setPadding(dp(16), dp(10), dp(16), dp(10))
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(10) }
        setOnClickListener { onClick() }
    }

    private fun switch(label: String, initial: Boolean, onChange: (Boolean) -> Unit) = Switch(this).apply {
        text = label
        textSize = 17f
        setTextColor(ink)
        isChecked = initial
        minimumHeight = dp(56)
        setOnCheckedChangeListener { _, on -> onChange(on); refresh() }
    }

    private fun card(title: String, vararg children: View): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = rounded(surface, 22, border)
        setPadding(dp(18), dp(16), dp(18), dp(18))
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(14) }
        addView(text(title, 20f, bold = true))
        children.forEach { addView(it) }
    }

    private fun buildScreen(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }

        // Header
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(14))
        }
        header.addView(TextView(this).apply {
            text = "🛡"
            textSize = 26f
            gravity = Gravity.CENTER
            background = rounded(Color.parseColor("#123A2E"), 14)
            layoutParams = LinearLayout.LayoutParams(dp(52), dp(52)).apply { marginEnd = dp(14) }
        })
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(text("SunoSafe", 26f, bold = true))
            addView(text("AI Call Shield", 15f, color = muted))
        })
        root.addView(header)
        root.addView(View(this).apply {
            setBackgroundColor(border)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1))
        })

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(4), dp(16), dp(40))
        }

        statusTitle = text("", 22f, bold = true)
        statusBody = text("", 17f)
        statusCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(Color.parseColor("#2A2210"), 22, amber)
            setPadding(dp(18), dp(16), dp(18), dp(16))
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                .apply { topMargin = dp(16) }
            addView(statusTitle)
            addView(statusBody)
        }
        column.addView(statusCard)

        fun tile(icon: String, label: String, path: String) = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(elev, 18, border)
            minimumHeight = dp(96)
            setPadding(dp(6), dp(12), dp(6), dp(12))
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(8) }
            addView(text(icon, 24f, color = green).apply { gravity = Gravity.CENTER })
            addView(text(label, 14f, bold = true).apply { gravity = Gravity.CENTER })
            isClickable = true
            setOnClickListener { openWeb(path) }
        }
        val tiles = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                .apply { topMargin = dp(14) }
            addView(tile("〰", "Live monitor", "/?tab=live"))
            addView(tile("📞", "Call history", "/?tab=calls"))
            addView(tile("📊", "SIEM dashboard", "/?tab=dashboard"))
        }
        column.addView(tiles)

        column.addView(card("Check a message",
            text("Press and hold a message in WhatsApp or Messages → Share → SunoSafe. Or copy it, come back and tap the green button.", 16f, color = muted),
            button("🔍  Check the message I copied") { startActivity(Intent(this, ShareCheckActivity::class.java)) },
            button("💬  Open WhatsApp", elev, ink) {
                val open = packageManager.getLaunchIntentForPackage("com.whatsapp")
                if (open != null) startActivity(open) else Toast.makeText(this, "WhatsApp is not installed.", Toast.LENGTH_SHORT).show()
            },
            button("✉️  Open Messages", elev, ink) {
                startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_APP_MESSAGING))
            },
        ))

        column.addView(card("Hear SunoSafe",
            text("Talk to the SunoSafe voice agent (Agora Conversational AI with a Murf Falcon voice).", 16f, color = muted),
            button("🎤  Talk about my latest warning") {
                val incident = Prefs.lastIncident(this)
                openWeb("/talk?lang=${Prefs.lang(this)}" + if (incident > 0) "&incident=$incident" else "")
            },
            button("🎭  Practise: scam call drill", elev, ink) { openWeb("/talk?mode=drill&lang=${Prefs.lang(this)}") },
            button("📋  Open incidents and evidence", elev, ink) { openWeb("/?tab=incidents") },
        ))

        column.addView(card("Set up",
            button("1.  Turn on notification access") { startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)) },
            button("2.  Allow SunoSafe to show warnings") {
                if (Build.VERSION.SDK_INT >= 33 && !warningsAllowed()) {
                    requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
                } else Toast.makeText(this, "Warnings are already allowed.", Toast.LENGTH_SHORT).show()
            },
            text("3.  Connect: open your SunoSafe web app on this phone → Settings → \"Connect Android app\".", 16f),
            button("4.  Let SunoSafe check unknown callers") { requestScreeningRole() },
            button("5.  Check messages I open in WhatsApp / SMS") {
                Toast.makeText(this, "Installed apps → SunoSafe screen checking → On. If it is greyed out: " +
                    "App info → ⋮ → Allow restricted settings.", Toast.LENGTH_LONG).show()
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            },
            button("Keep SunoSafe running (battery)", elev, ink) {
                startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
            },
        ))

        // Five languages: two rows so every button stays big enough to read and tap.
        val languageRow = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val rows = listOf(LinearLayout(this), LinearLayout(this)).onEach {
            it.orientation = LinearLayout.HORIZONTAL
            it.gravity = Gravity.CENTER_VERTICAL
            it.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(8) }
            languageRow.addView(it)
        }
        Prefs.LANGUAGES.entries.forEachIndexed { index, (code, name) ->
            rows[if (index < 3) 0 else 1].addView(Button(this).apply {
                text = name
                textSize = 17f
                isAllCaps = false
                val chosen = Prefs.lang(this@MainActivity) == code
                setTextColor(if (chosen) onGreen else ink)
                background = rounded(if (chosen) tealMid else elev, 16, if (chosen) null else border)
                layoutParams = LinearLayout.LayoutParams(0, dp(56), 1f).apply { marginEnd = dp(8) }
                setOnClickListener {
                    Prefs.setLang(this@MainActivity, code)
                    // Speak a sample at once, so the user knows this phone can say warnings in this language.
                    Speaker.say(applicationContext, "SunoSafe", code, "SunoSafe will now warn you in English.",
                        "voice-sample-$code")
                    recreate()
                }
            })
        }

        val appSwitches = Prefs.WATCHED_APPS.entries.distinctBy { it.value }.map { (pkg, name) ->
            switch("Watch $name", Prefs.appEnabled(this, pkg)) { on -> Prefs.setAppEnabled(this, pkg, on) }
        }.toTypedArray()

        column.addView(card("Controls",
            switch("Watch for scam messages", Prefs.monitoringOn(this)) { Prefs.setMonitoring(this, it) },
            switch("Speak warnings aloud", Prefs.speakOn(this)) { Prefs.setSpeak(this, it) },
            text("Warning language", 17f, bold = true),
            languageRow,
            text("Apps to watch", 17f, bold = true),
            *appSwitches,
            button("🔔  Try a practice warning") { practiceWarning() },
        ))

        stats = text("", 15f, color = muted)
        column.addView(card("Activity", stats))

        column.addView(card("What SunoSafe reads and sends",
            text(
                "• Only notifications from the apps switched on above. Only the title and text Android shows. " +
                    "Not your chat history, photos or contacts.\n" +
                    "• A message is sent for checking only if it has a link or wording often used in scams. " +
                    "Ordinary messages never leave this phone.\n" +
                    "• For callers, SunoSafe sees only the number of callers not in your contacts. It never hears calls, " +
                    "never blocks them, and records a number only if it is linked to a scam message.\n" +
                    "• Stored evidence masks phone numbers, card numbers and codes.\n" +
                    "• Turn anything off here, or remove access in Android settings, at any time.", 15f, color = muted)))

        root.addView(column)
        return ScrollView(this).apply { addView(root) }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        refresh()
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        refresh()
    }
}
