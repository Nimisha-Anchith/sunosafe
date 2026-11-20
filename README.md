# 🛡️ SunoSafe: voice-first scam guardian with a mini security-operations centre

> **Hear the warning. Understand the threat. Take action.**
> Built for **Build with Agora – Bengaluru 2026** (18–21 Nov 2026) · Agora Conversational AI · Murf Falcon
> Track: **PS51 — From Conversations to Autonomous Action** (also fits **PS11 — Breaking Language Barriers**)

**SunoSafe** ("Listen Safe") protects **elderly and visually impaired people in India** from scam SMS, WhatsApp messages,
phishing links and scam calls. A companion app on the phone watches messages and callers automatically (after the user
allows it), a backend investigates links and joins the evidence into incidents, and SunoSafe **speaks the warning** in the
user's language: English, Hindi, Malayalam, Kannada or Tamil. When the user is worried, they just talk to it.

**Live:** website https://sunosafe.vercel.app (PIN-protected) · backend https://sunosafe-backend.onrender.com

Status labels used below (evidence in [docs/status.md](docs/status.md)):
✅ working and tested (automated tests, live checks or on a real phone) · 🟡 built, not yet confirmed end to end ·
❌ not working yet · 🔒 not possible for an app (needs a bank, telecom operator or the police)

---

## How it works

```text
 Android companion (the user's phone)            Website (sunosafe.vercel.app, PIN lock)
  new SMS · WhatsApp/SMS notifications            Talk to SunoSafe (Agora voice agent + Murf voice)
  messages opened/scrolled on screen              check a message / a link · SIEM dashboard
  caller check while the phone rings              incidents & evidence · recovery help · call-shield test
  spoken warnings (Murf voice)                     │
        │ HTTPS + device token                     │ HTTPS (server side, backend token)
        ▼                                          ▼
 ┌──────────────────── Backend (FastAPI, hosted on Render) ─────────────────────┐
 │ public gateway /gw: device routes · voice brain /llm · call-screening tool  │
 │ private API (token): message & link checks, incidents, dashboard            │
 │ Threat intelligence: scam rules in 5 languages, URL normaliser, SSRF guard,  │
 │   redirects, DNS, domain age (RDAP), TLS certificate, Safe Browsing (key)    │
 │ Mini-SIEM (SQLite): events, correlation, severity rules, incidents, steps    │
 └──────────────────────────────────────────────────────────────────────────────┘
        ▲ Agora Conversational AI calls /llm (web voice agent) and the screening tool (phone agent)
```

### Agora, Murf and the other services

| Service | What SunoSafe uses it for |
|---|---|
| **Agora Conversational AI** | The voice agent on the website (Agora RTC in the browser). Its LLM is SunoSafe's own `/llm` endpoint, so every decision runs in our backend. Also a phone agent ("SunoSafe Call Shield") created through Agora's platform API. |
| **Murf Falcon** (`hi-IN-jaya`) | Every voice: the voice agent and the spoken warnings on the phone, in en/hi/ml/kn/ta. |
| **Deepgram / Agora ARES** | Speech recognition for the voice agent: Deepgram for English and Hindi, ARES for Kannada and Tamil. |
| **Groq** (`openai/gpt-oss-20b`, fallback `gpt-oss-120b`) | The language model behind `/llm`. It phrases answers and suggests tool calls; it never decides on its own. |
| **Vobiz** | A +91 phone number, used by the test script to place scam test calls. |
| **Render / Vercel** | Hosting of the backend / the website. |

---

## What is implemented

### On the phone (Android companion, Kotlin, no third-party libraries)

| Feature | Status |
|---|---|
| Spoken warning when a scam **notification** arrives (SMS, WhatsApp, Telegram), with vibration and a red alert; only messages with a link or scam wording leave the phone | ✅ verified on a Samsung S24 |
| Warnings spoken with the **Murf voice in 5 languages** (fetched from the backend, cached on the phone); the phone's own voice only as fallback | ✅ all 5 voices confirmed on the S24 |
| **Caller check while the phone rings**: warns aloud when a number from an earlier scam message calls (call-screening role) | ✅ verified on the S24 with a test call |
| **Every new SMS** checked on arrival, even when the SMS app hides the text in its notification (SMS permission) | 🟡 built and permission granted; not yet confirmed with a real incoming scam SMS |
| **SMS inbox scan** (last 30 days, one summary warning) | 🟡 ran once on the S24; result not yet reviewed |
| **Messages opened or scrolled** in WhatsApp / SMS apps checked on screen (accessibility service the user switches on; never reads passwords or typing) | 🟡 enabled and scanning on the S24; a warning from a scam shown on screen not yet confirmed |
| **Share → SunoSafe** from any message, and "Check the message I copied" | 🟡 built, not yet tested on the phone |
| Always-on **protection service** ("SunoSafe protection is on"), restarts after reboot; one warning per message even if seen as SMS, notification and on screen | ✅ service running on the S24 |
| Instant spoken warnings: standard warnings fetched to the phone in advance | ✅ audio cached on the S24 |
| Pairing with the user's own SunoSafe through a confirmed link; tokens never in the app's code | ✅ |
| "SunoSafe answered a scam call for you" alerts fetched from the backend | ✅ backend side tested; 🟡 on the phone (depends on the phone agent below) |

### Website (Next.js, PIN lock)

| Feature | Status |
|---|---|
| **Talk to SunoSafe**: voice agent in 5 languages, briefed on an incident when opened from a warning; answers "why is it dangerous?", blocks a link only after the user's own spoken "yes" | ✅ on a laptop browser · 🟡 on phone Chrome (fix applied for silent microphone, not yet confirmed) |
| **Check a message**: paste (or Example), verdict, warning signs, link investigation; Open WhatsApp / Messages helpers | ✅ |
| **Check a link** and open it through SunoSafe (block screen for blocked links) | ✅ |
| **SIEM dashboard**: counters, threats timeline, threat types, incidents, call log, live call monitor; only real stored events, nothing invented | ✅ |
| **Incidents**: evidence timeline with the source of every event, recovery steps, call 1930, report text for cybercrime.gov.in | ✅ |
| **Call-shield test**: you play the scam caller; SunoSafe answers, screens every sentence, refuses with a fixed reviewed sentence | ✅ |
| **Scam call practice drill** (SunoSafe plays the scammer, never collects data) | ✅ |
| Dark night-green design, phone and desktop layouts | ✅ checked in the browser |
| Guardian Web View (`/guardian` on the backend) | ✅ |

### Backend (FastAPI)

| Feature | Status |
|---|---|
| URL extraction and normalisation (defanged links, punycode, disguised IPs, `brand@evil`, shorteners, UPI links) | ✅ |
| SSRF guard (schemes, ports, internal names, private/metadata IPs, DNS answers, IP pinning) and safe redirect tracing | ✅ |
| DNS, domain age (RDAP), TLS certificate checks | ✅ |
| Google Safe Browsing across the redirect chain | 🟡 tested with mocks; needs an API key for live use |
| Scam rules: OTP/PIN/credential requests (negation-aware, so "never share your OTP" is not a request), urgency, account and police threats, KYC, prizes, money demands, remote-access apps, brand-vs-link impersonation, electricity-bill scam | ✅ |
| **Native-script rules** for Hindi, Malayalam, Kannada and Tamil (reviewed word lists mapped to the rules) | ✅ tests; Malayalam/Kannada/Tamil lists not reviewed by a native speaker |
| Evidence-based severity (rules R1–R16) with reasons and uncertainties; never says "safe" | ✅ |
| Mini-SIEM: events, indicators, incidents, steps, notes, blocklist; correlation by shared link/domain/phone, same impersonated brand, and message + call | ✅ |
| PII redaction before storage (card, Aadhaar, PAN, OTP codes, phone numbers) | ✅ |
| Voice brain `/llm` (OpenAI format, streaming) with tools behind a policy gate; the LLM sees link labels, never raw scam text | ✅ |
| Call-screening tool for the Agora phone agent (`/gw/agora/tools/screen`) | ✅ tested, including a voice test of the real agent with recorded Hindi caller audio |
| Spoken warnings as Murf audio (`/gw/device/speech/<id>`); only sentences SunoSafe produced can be spoken | ✅ |
| Hosting: private API locked with a token, gateway under `/gw`, Render blueprint (`render.yaml`) | ✅ checked from outside |

306 automated backend tests (`backend/tests`), plus Android unit tests.

### Scripts (no AI involved)

| Script | What it does |
|---|---|
| `scripts/test_scam.py` | Sends **your own number** a test scam message (USB notification, or SMS via Vobiz) and a test scam call from the Vobiz number that waits for your answer; two stories (`--topic=bank`, `--topic=courier`). |
| `scripts/agora_shield.py` | Creates and maintains the Agora phone agent and routes the phone number to it (status / setup / sync / number / unroute / remove). |

---

## What does not work yet, and what SunoSafe cannot do

- ❌ **Forwarded calls to the Vobiz number reaching the Agora phone agent.** The number is imported and routed to the agent
  through Agora's platform API, and the agent works in a voice test, but real calls do not reach it yet (the inbound
  address for numbers on Agora's Preview platform is not documented; to confirm with Agora).
- ❌ **Sending scam test SMS to Indian numbers through Vobiz**: needs DLT registration (TRAI). The test script uses a USB
  notification or a message from a second phone instead.
- ❌ **Listening in Malayalam**: needs a Sarvam API key (Agora's managed recognisers have no Malayalam). Kannada and Tamil
  listening start correctly but have not been tested with a speaker.
- 🔒 **Listening to ordinary phone calls** the user answers: Android does not allow apps to hear call audio. SunoSafe warns
  while the phone rings and can answer calls that are forwarded to it.
- 🔒 **WhatsApp chats that are never opened**: WhatsApp gives no access to other apps. SunoSafe sees new notifications and
  chats the user opens or scrolls.
- 🔒 **Reversing payments, freezing accounts, blocking SIMs**: SunoSafe guides to 1930, the bank's official channel and
  cybercrime.gov.in.
- Free hosting sleeps after 15 minutes idle (first request takes about a minute) and the hosted event store resets when
  the server restarts. The laptop setup uses temporary Cloudflare tunnel addresses.

---

## Security & privacy

| Risk | Control |
|---|---|
| SSRF (`http://169.254.169.254/`, `localhost`) | scheme/port allow-list, internal names blocked, every DNS answer must be public, IP pinning, every redirect re-checked |
| Prompt injection ("ignore your rules") in messages, pages or a caller's words | decisions are made by fixed rules in code; the LLM sees our findings and link labels, not raw scam text; the phone agent's refusal is fixed text from SunoSafe |
| Unapproved actions | blocking needs an investigated link **and** the user's own words ("yes, block it"); every action is in the audit trail |
| Secrets | only in git-ignored `.env` files and the hosts' settings; three separate tokens (website→API, Agora→gateway, phone→gateway) |
| Personal data | ordinary messages stay on the phone; stored text is masked; ordinary callers' numbers are never stored |
| Abuse | rate limits, body-size limits, wrong-token limits; the speech endpoint only speaks sentences SunoSafe produced |

---

## Run it yourself

Requirements: Python 3.12+, Node 22 + pnpm, and for the phone app JDK 17 + Android SDK + Gradle (see
[docs/demo-and-setup.md](docs/demo-and-setup.md)).

```bash
git clone https://github.com/Nimisha-Anchith/sunosafe.git
cd sunosafe/backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt     # Windows (macOS/Linux: .venv/bin/python)
.venv\Scripts\python -m pytest -q                               # 306 tests, no internet needed
.venv\Scripts\python -m uvicorn app.main:app --port 8000        # private API (local only)
.venv\Scripts\python -m uvicorn app.gateway:app --port 8001     # public gateway
```

Settings: copy `backend/.env.example` to `backend/.env` and `voice-web/env.local.example` to `voice-web/.env.local`, then
fill in your own keys. Never put keys in code, chat or git.

More: [docs/demo-day.md](docs/demo-day.md) (demo script and judge tour) · [docs/testing-guide.md](docs/testing-guide.md) ·
[docs/demo-and-setup.md](docs/demo-and-setup.md) · [docs/status.md](docs/status.md)

## Project structure

```text
sunosafe/
├── backend/            FastAPI: app/security (URL, SSRF, DNS, RDAP, TLS, rules, indic), app/soc (Mini-SIEM, severity,
│                       phrases, speech, dashboard), app/agent (voice brain, policy gate, call shield), gateway.py,
│                       hosted.py; tests/
├── android/            Kotlin companion: notification listener, SMS reader, screen reader, call screener,
│                       protection service, share check, spoken warnings
├── voice-web/          Next.js website (copy of the running app): PIN lock, Agora voice client, dashboard
├── scripts/            test_scam.py, agora_shield.py
├── docs/               demo guide, testing guide, setup, status
└── render.yaml         backend hosting blueprint
```

## Acknowledgements

[Agora](https://www.agora.io/) (Conversational AI, RTC, quickstarts) · [Murf AI](https://murf.ai/) (Falcon voices) ·
[KNOTiC](https://luma.com/2g5vcgrr) (Build with Agora – Bengaluru 2026) · India's cyber-crime helpline **1930** and
[cybercrime.gov.in](https://cybercrime.gov.in)

*Safety note: SunoSafe gives guidance, not legal or financial advice. In an emergency, call **1930** or your bank's
official helpline.*
