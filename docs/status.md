# SunoSafe — feature status

Legend: ✅ Implemented & tested · 🟡 Implemented, untested · 📋 Planned · 🔒 Needs platform privilege or an institution (bank, telecom, police)

| Area | Feature | Status | Evidence |
|---|---|---|---|
| URL safety | Link extraction from message text | ✅ | `backend/tests/test_url_normalize.py` |
| URL safety | Normalisation (defang, punycode, disguised IPs, `@` trick, shorteners, UPI links) | ✅ | `backend/tests/test_url_normalize.py` |
| URL safety | SSRF guard (schemes, ports, internal names, private/metadata IPs, DNS answers, IP pinning) | ✅ | `backend/tests/test_ssrf_guard.py` |
| URL safety | Pinned safe fetch (IP pinning, TLS verified, headers only, no body) | ✅ | `tests/test_redirects.py`; live: example.com, google.com, sbi.co.in reached |
| URL safety | Redirect tracer (every hop SSRF-checked; loops, limits, app-link redirects) | ✅ | `tests/test_redirects.py`; live: http://github.com → https |
| URL safety | TLS certificate check (valid / expired / hostname mismatch / self-signed, cert age) | ✅ | `tests/test_dns_rdap_tls.py`; live: badssl.com test sites |
| URL safety | DNS (A/AAAA/CNAME/NS/MX via 1.1.1.1 / 8.8.8.8; NXDOMAIN vs server failure) | ✅ | `tests/test_dns_rdap_tls.py`; live |
| URL safety | Domain age via RDAP (IANA bootstrap, registrable domain via Public Suffix List) | ✅ | `tests/test_dns_rdap_tls.py`; live: google.com 1997, sbi.co.in 2002 |
| URL safety | Google Safe Browsing reputation (whole redirect chain) | 🟡 | Mocked tests pass; live check needs `SAFE_BROWSING_API_KEY` |
| URL safety | Investigation orchestrator + `POST /api/investigate/url` (parallel tools, provenance, tool-run status, rate limit) | ✅ | `tests/test_investigate.py`; live HTTP call |
| URL safety | JavaScript / meta-tag redirects inside pages | 📋 | Not visible without rendering pages, which we deliberately never do |
| Messages | Scam-pattern rules: OTP / PIN / credential requests (negation-aware), PIN-to-receive-money, remote-access & APK lures, urgency, account / authority threats, KYC, prize/job lures, callback numbers, brand-vs-link impersonation (incl. `.bank.in`) | ✅ | `tests/test_message_rules.py`; genuine bank OTP SMS gives zero signals |
| Messages | Hindi / Hinglish keywords (partial) | 🟡 | A few words tested; Malayalam / Kannada / Tamil rules planned |
| Messages | Known limitation: a message naming two brands (e.g. "Amazon gift card from SBI") checks the link against each brand separately, which can give a false "not official" signal | 📋 | To fix: only compare against the brand the link's text claims |
| Privacy | PII redaction before storage (card, Aadhaar, PAN, OTP codes, user phone numbers) | ✅ | `tests/test_message_rules.py`, `tests/test_service.py` |
| Mini-SOC | Evidence-based severity (rules R1–R9, confidence, uncertainties; never says "safe") | ✅ | `tests/test_message_rules.py` |
| Mini-SOC | SQLite event store, incidents, indicators, steps, notes, blocklist | ✅ | `tests/test_service.py` |
| Mini-SOC | Correlation C1 (shared domain / URL / phone within 7 days), severity recomputed from all evidence | ✅ | `tests/test_service.py`; live: SMS + call from same number linked |
| Response | Approval-gated blocklist (domain-wide only with strong evidence; never official/shortener domains) | ✅ | `tests/test_service.py`, `tests/test_api_soc.py`; live |
| Response | Protected-browser check endpoint (`/api/protect/check`) | ✅ | Tests + live; Android browser itself is Milestone 5 |
| Response | Recovery plans (1930, bank, passwords, remote app, cybercrime.gov.in, Chakshu, guardian opt-in), step tracking, 1930 report summary (defanged links) | ✅ | `tests/test_service.py` |
| Calls | User-reported suspicious call (number + what the caller asked for), correlated with messages | ✅ | `tests/test_service.py`; live |
| Guardian | Guardian Web View (`/guardian`): incidents, rationale, steps, indicators, timeline with provenance, notes, 1930 summary | ✅ | Live in browser; attacker text rendered only as text (CSP + no innerHTML), checked with an injected `<script>` |
| Security | API access control (Bearer `API_TOKEN`, or localhost only), validation, rate limits | ✅ | `tests/test_api_soc.py` |
| Voice | Agent brain: `/llm/chat/completions` (OpenAI format, streaming), 7 tools, case notes for follow-ups, model fallback, 3-sentence spoken replies | ✅ | `tests/test_agent.py`; live text run with Groq (`openai/gpt-oss-20b`): 1–3.5 s per turn |
| Voice | Policy gate: blocking needs an investigated link AND the user's own clear words (short yes, or "block it"); questions and loose words are not consent | ✅ | `tests/test_agent.py`; live |
| Voice | Prompt-injection limits: the LLM never sees the scam message or full link addresses, only our findings and labels like "link 1" | ✅ | `tests/test_agent.py` |
| Voice | Shared-message inbox (`/api/inbox`), expires after 10 minutes | ✅ | `tests/test_agent.py`. Known limitation: one inbox for the whole backend (single-user prototype); per-user inbox comes with the Android app |
| Voice | Agent brain connected to Agora Conversational AI (custom LLM) + Murf Falcon, by voice | ✅ | Spoken test in Chrome on 2026-11-19: Agora's cloud called the gateway once per turn; link blocked with `approved_via=voice`; protected-browser check returned block |
| Security | Public voice gateway (port 8001): only `/health` and `/llm/chat/completions`, mandatory `GATEWAY_TOKEN`, body-size limit, rate limit after auth, wrong-token limit, API docs off; private API (8000) never exposed | ✅ | `tests/test_gateway.py`; checked through Cloudflare: health 200, no/wrong token 401, private routes 404, 429 after 30 wrong tokens |
| Security | Tunnel: cloudflared 2026.11.1 quick tunnel to 127.0.0.1:8001 (binary verified by SHA-256 and Cloudflare's signature); streaming replies arrive in separate pieces | ✅ | Live. Limits: address changes on every restart; no uptime guarantee; needs a fixed host for real use |
| Privacy | Shared message is deleted from the inbox once analysed or expired; only the masked copy in the event log remains | ✅ | `tests/test_gateway.py` |
| Voice | Voice web client listens on the laptop only (not the Wi-Fi network) | ✅ | Live check on the Wi-Fi address |
| URL safety | Open issue: one investigation of a self-signed test site recorded no findings while later runs recorded the certificate problem | 📋 | Cause not yet found |
| Voice | LLM provider: Groq free tier (1,000 requests, 8,000 tokens/min per model seen on 2026-11-19); Gemini free tier measured at 7–16 s per call, kept as fallback setting | 🟡 | Rate limits may slow rapid back-to-back checks |
| Privacy | The user's transcribed words and our findings are sent to the LLM provider (Groq) | 📋 | Fine for synthetic demo data; real users need informed consent or a self-hosted model |
| Security | Requests arriving through a tunnel/proxy are never treated as local; remote access requires `API_TOKEN` | ✅ | `tests/test_agent.py`; live |
| Voice | Murf Falcon 2.1 voices for en-IN, hi-IN, ml-IN, kn-IN, ta-IN | ✅ (voice list) | Murf voices API, 2026-11-18: e.g. `hi-IN-jaya` supports all five |
| Voice | Speech recognition for ml / kn / ta | 📋 | Must test full speech-in → speech-out loop |
| Android | Talk / Check message / I was scammed / Protected Browser | 📋 | Milestone 5 |
| Response | 1930 dialer intent and opening official portals from the phone | 📋 | Milestone 5 (Android) |
| Calls | Agora RTC call with private warning | 📋 | After MVP |
| Calls | Cellular call screening (number only) | 📋 | Needs call-screening role |
| Calls | Cellular call audio / reversing UPI / freezing accounts | 🔒 | Not possible for an app; guide user to bank, 1930, cybercrime.gov.in |

## Update 20 Nov 2026 — Intervention Intelligence build

| Area | Feature | Status | Evidence |
|---|---|---|---|
| Android | Native NotificationListenerService, explicit access, per-app on/off, hidden-text handling, on-phone pre-filter, de-duplication | 🟡 Built, compiles, unit tests pass | Not yet run on the S24 (phone was not connected during the build) |
| Android | Call screening (CallScreeningService + caller-ID role): never blocks; instant local check against numbers from scam messages; backend correlation | 🟡 Built, compiles | Backend side tested live through the tunnel; phone side not yet run |
| Android | Instant spoken warnings (phone voice) in English or Hindi; tap opens the briefed Agora voice agent or the evidence | 🟡 Built | Hindi phrase returned by the live backend; phone playback not yet tested |
| Mini-SIEM | C2 impersonation-story correlation (same claimed brand, only for suspicious events); C3 cross-channel escalation (message + call) | ✅ | `tests/test_intervention.py`; live end-to-end run through the tunnel |
| Mini-SIEM | Call screening endpoint `/device/calls`; ordinary caller numbers are not stored | ✅ | Tests + live run |
| Voice | Agent opened from an incident is briefed (greeting + evidence + link labels) and can block by voice with user approval | ✅ (text) / 🟡 (spoken) | Live run through the tunnel: answer 1.6 s, block approved, audit "approved by voice"; Agora agent started with this config (RUNNING) in English and Hindi |
| Voice | New tools: investigate_url, check_caller_risk, get_incident_details, get_security_timeline, recommend_protective_action, record_user_action | ✅ | Tests |
| Voice | Scam-call practice drill (no tools, never collects data) | ✅ (text) / 🟡 (spoken) | Tests; Agora agent RUNNING in drill mode |
| Voice | Preferred language: replies + Murf locale in en/hi/ml/kn/ta; listening en + hi (Deepgram) | 🟡 | Agent accepted Hindi config; spoken Hindi not yet tested by a person |
| Web app | Evidence timeline on the phone, "Hear SunoSafe explain this", deep links from the companion, Intervention demo (simulated inputs, real engine) | ✅ | Checked at phone size in the browser |
| Known issue | Phone Chrome voice error (InvalidModificationError); fixes applied: Agora SDK 4.24.10, ENABLE_PREALLOC_PC off, and a guard that retries `setConfiguration` keeping fixed settings | 🟡 | Still failed on the S24 before the guard; guard not yet tested on the phone |
| Not possible | Listening to or transcribing ordinary cellular calls; reversing payments | 🔒 | Android/bank limits; SunoSafe warns while ringing and guides recovery instead |

## Update 20 Nov 2026 (evening) — Hindi voice fix and Call shield

| Area | Feature | Status | Evidence |
|---|---|---|---|
| Android | Spoken warning when Hindi is chosen: prefers Google's speech engine, checks that a Hindi voice is really installed, otherwise speaks the English copy (`say_en`) and tells the user how to add Hindi; speaks a sample when the language is changed | 🟡 Built (0.3.0), compiles | Cause found on the S24: Hindi was chosen and the phone stayed silent; English worked. Fix not yet run on the phone |
| Mini-SIEM | Call shield screening: caller's words checked by SunoSafe's rules, `call_shielded` event only when scam signs appear, R12 (caller asks for OTP/PIN/remote access) high, correlation with earlier messages, one phone alert per call | ✅ | `tests/test_call_shield.py` (7 tests); live through the tunnel with Groq: 0.8 s per turn, joined the SBI SMS incident, injection attempt refused, 401 without tokens |
| Voice | Shield mode for the Agora agent (`mode=shield`): no tools, knows nothing about the user, calm scripted goals | ✅ (text) / 🟡 (spoken) | Live text run; browser test page `/talk?mode=shield` renders; spoken test not yet done |
| Android | Companion fetches call-shield warnings (`/device/alerts`, every 10 s) and speaks them | 🟡 Built, compiles | Not yet run on the phone |
| Calls | Real forwarded calls via Vobiz number → Agora inbound agent | 📋 Needs setup | Needs the Vobiz number, SIP trunk and Agora inbound agent (see demo-and-setup.md); cost to be confirmed by the account owner |

## Update 20 Nov 2026 (night) — live call screening through Agora's phone agent

| Area | Feature | Status | Evidence |
|---|---|---|---|
| Finding | A saved Agora phone agent refuses non-approved LLM addresses ("Provider endpoint is not approved"); SunoSafe therefore screens through a function tool | ✅ Verified | Agora's own validator: our gateway, example.com and Groq refused, api.openai.com accepted |
| Calls | Agora phone agent "SunoSafe Call Shield" (Deepgram, gpt-4.1-mini, Murf) created and updated through the platform REST API; number imported and routed to it | ✅ Configured | `scripts/agora_shield.py status`: 1 agent, 1 number with inbound agent |
| Calls | Live screening tool `/agora/tools/screen`: every caller sentence checked by SunoSafe's rules, fixed refusal text returned, Mini-SIEM event, correlation, one phone alert | ✅ | `tests/test_agora_tool.py`; voice test of the real agent in an RTC session with recorded Hindi caller audio: 2 tool calls answered 200, `call_shielded` (high) joined the SBI SMS incident, alert queued |
| Calls | The same over a real phone line (Vobiz → Agora SBC → agent) | 🟡 Not yet tested | Needs the Vobiz inbound trunk pointed at Agora and a test call |
| Messages / calls | Scam rules on Hindi, Malayalam, Kannada and Tamil script (word lists in `app/security/indic.py`), incl. "do not share" forms; card-number, "code sent to your phone", lottery-fee and digital-arrest payment rules (R13–R15) | ✅ | `tests/test_indic.py`. Malayalam, Kannada, Tamil lists not reviewed by a native speaker |
| Voice | Spoken phone warnings with Murf Falcon in 5 languages (`/device/speech/<id>`), phone voice only as fallback | ✅ backend / 🟡 phone | Audio fetched through the tunnel in all 5 languages; playback on the S24 not yet tested |
| Android | Companion 0.3.0: Murf audio playback, 5-language picker, call-shield alert poller | 🟡 Built, compiles | Not yet installed on the S24 |

## Update 21 Nov 2026 — current state (supersedes earlier rows where they differ)

| Area | Feature | Status | Evidence |
|---|---|---|---|
| Android | Notification warning spoken with Murf voice, 5 languages | ✅ | S24: warnings spoken; all 5 voice samples heard by the user |
| Android | Caller check while ringing (number from an earlier scam message) | ✅ | S24 log "Warned you about a call from a number seen in a scam message" during Vobiz test calls (bank and courier stories) |
| Android | New-SMS reader, SMS inbox scan | 🟡 | Permission granted, inbox scan ran once; not yet confirmed with a real incoming scam SMS |
| Android | Screen checking (WhatsApp/SMS opened or scrolled) | 🟡 | Enabled; screens scanned on the S24; a warning from on-screen text not yet confirmed |
| Android | Share → SunoSafe / check copied message | 🟡 | Built, not yet tested on the phone |
| Android | Always-on protection service, restart on boot, shared dedupe | ✅ service running | `dumpsys` on the S24 |
| Web | Phone Chrome voice: microphone sent silence (ENABLE_AUDIO_PTS set after the connection existed) | 🟡 fixed, not yet confirmed | Laptop voice works |
| Calls | Agora phone agent with SunoSafe screening tool | ✅ in an RTC voice test | Tool called twice, `call_shielded` high, alert queued |
| Calls | Real calls to the Vobiz number reaching the phone agent | ❌ | Zero Agora sessions; Preview-platform inbound address not documented |
| Rules | Native-script rules hi/ml/kn/ta; R12–R16 (incl. electricity-bill scam) | ✅ | `tests/test_indic.py` |
| Voice | Agent greeting describes the latest story in an incident | ✅ | `tests/test_intervention.py` |
| Hosting | Backend on Render (token-locked), website on Vercel | ✅ backend checked from outside; website deployed (login page and refusals checked) | |
| Tests | Backend | ✅ 306 passing | `pytest -q` |
