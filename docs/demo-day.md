# SunoSafe — demo day guide

## 1. What SunoSafe is (say this in one breath)

> "SunoSafe is a voice-first scam guardian for elderly and visually-impaired people in India. It watches SMS, WhatsApp
> and calls on the phone automatically, investigates links and callers, joins the evidence into one incident, and
> **speaks** the warning in the user's own language — English, Hindi, Malayalam, Kannada or Tamil. When they're worried,
> they just talk to it."

Three parts, one system:

| Part | Runs on | Role |
|---|---|---|
| **Android companion** | the user's phone (your S24) | the *ears*: reads new SMS, WhatsApp notifications, chats on screen, checks callers while ringing, speaks warnings |
| **Backend / Mini-SIEM** | Render (`sunosafe-backend.onrender.com`) | the *brain*: scam rules (5 languages), link investigation, incidents and evidence, voice agent's brain |
| **Website** | Vercel (`sunosafe.vercel.app`) | the *face*: talk to SunoSafe (Agora + Murf), check messages/links, SIEM dashboard, evidence, recovery help |

Tech to name when asked: Agora Conversational AI (voice agent, phone agent), Murf Falcon (all voices), Deepgram / Agora
ARES (listening), Groq LLM, FastAPI + SQLite Mini-SIEM, Next.js, native Android (Kotlin), Vobiz (phone number).

## 2. Before you present (15 minutes before)

1. Laptop on, charger in. Phone charged, **volume up**, not on silent (silent mode mutes spoken warnings on purpose).
2. Phone paired to the hosted site: on the phone open `https://sunosafe.vercel.app` → Profile → Connect Android app →
   *Yes, connect*. (Then nothing depends on the laptop.)
3. In the SunoSafe app, the status card shows all ✔ (notification access, warnings, connected, callers, screen checking,
   SMS, protection running). Language: हिंदी (or the judges' language).
4. Open `https://sunosafe.vercel.app` on the laptop **2 minutes before** (wakes the free server) and log in. Open two
   tabs: *Home* and *Reports (SIEM dashboard)*.
5. Optional clean start: if the dashboard shows old test data, that's fine — it proves the history. Or let Render restart.
6. Test once: `backend\.venv\Scripts\python.exe scripts\test_scam.py call --topic=courier` (phone on USB) → message
   warning, then warning while it rings. Hang up.
7. USB cable plugged in (for the `notify` step), or a second phone ready to send the scam SMS.

## 3. The 5-minute demo script

**[0:00 – 0:30] The problem**
> "Last year Indians lost thousands of crores to scams — fake KYC, courier 'customs' calls, electricity-bill threats,
> digital arrest. The people hit hardest are elderly and blind users: they can't read tiny warnings, and scammers use
> an SMS *and* a phone call together. SunoSafe hears the threat for them."

**[0:30 – 1:30] It warns by itself — no app open**
- Show the phone's home screen (SunoSafe *closed*; only "SunoSafe protection is on" in the status bar).
- Laptop: `scripts\test_scam.py notify --topic=courier` (or send the courier SMS from the second phone).
- The phone shows the red warning, vibrates and **speaks in Hindi**.
> "I never opened the app. SunoSafe read the message, found a police threat plus a money demand plus 'call this
> number', and warned in Hindi — out loud, so a blind user hears it."
- Tap **See evidence** → incident: *why* it's dangerous (each sign), the timeline with the source of every event.

**[1:30 – 2:30] The scammer calls — cross-channel**
- Laptop: `scripts\test_scam.py call --topic=courier --call-only`
- While it rings the phone says: "सावधान। यह नंबर पहले आए एक धोखाधड़ी संदेश में था…"
> "This number was inside the scam SMS a minute ago. SunoSafe remembered it and warns *before* she answers."
- Answer briefly: the "scammer" demands a fine — hang up.
- Laptop: **SIEM dashboard** → the incident now has *message + call*, severity high, "same scam by message and call".
> "One incident, one evidence trail — a mini security-operations centre for a family."

**[2:30 – 3:30] She talks to SunoSafe**
- On the warning (or the round green button): **Talk to SunoSafe**. It opens already briefed on this scam.
- Ask: "Is this a real police case?" → explains calmly. Say: **"Yes, block it."** → link blocked, timeline says
  "approved by voice".
> "No typing, no menus — Agora's voice agent with a Murf voice, in her language. Nothing happens without her yes."

**[3:30 – 4:30] SunoSafe answers scam calls for her (call shield)**
- Laptop: **Live monitor → Test it now: you play the caller**. Play the scammer: "Main SBI se bol raha hoon, OTP bataiye."
- SunoSafe refuses calmly; Live monitor shows **Scam detected**; dashboard counter goes up.
> "With call forwarding, calls she declines go to SunoSafe. It never reveals anything about her, screens every
> sentence with the same rules, and tells her afterwards what happened."

**[4:30 – 5:00] Close**
- Show Threat types + the five language buttons.
> "SunoSafe: hear the warning, understand the threat, take action — in five Indian languages, before the money is gone."

## 4. What judges can try on the website alone

Give them `https://sunosafe.vercel.app` + the PIN.

- **Talk to SunoSafe** — voice conversation in any of 5 languages.
- **Check a message** — tap *Example*, or paste any SMS/WhatsApp text (Hindi/Tamil script works).
- **Check a link** — see where it really goes, domain age, certificate; dangerous sites get the block screen.
- **SIEM dashboard** — every number is real; click an incident for the evidence.
- **Live monitor → Test it now** — be the scammer.
- **Practise: scam call drill** — SunoSafe plays a scammer to train the user.

Phone-only features (show on your S24): automatic SMS/WhatsApp warnings, screen checking, Share → SunoSafe, the
caller-ID warning, the five spoken voices.

## 5. Commands (from `C:\Users\Dell\Downloads\sunosafe`, no AI involved)

```
backend\.venv\Scripts\python.exe scripts\test_scam.py call                      # SBI KYC message, then call
backend\.venv\Scripts\python.exe scripts\test_scam.py call --topic=courier      # courier/police message, then call
backend\.venv\Scripts\python.exe scripts\test_scam.py notify --topic=courier    # only the message (USB)
backend\.venv\Scripts\python.exe scripts\test_scam.py call --topic=courier --call-only   # only the call
backend\.venv\Scripts\python.exe scripts\test_scam.py call --lang=en            # English call
```

Without the USB cable, send the scam text from a second phone instead of `notify`; it must contain your Vobiz number
written as `+91 80XXXXXXXX`, then run the `--call-only` command.

## 6. Questions judges may ask — honest answers

| Question | Answer |
|---|---|
| Does it listen to my calls? | No. Android doesn't allow that, and we don't want it. It warns while the phone rings, and answers only calls you forward to it. |
| Does it read all my messages? | Only on the phone. Ordinary messages never leave the phone; only ones with a link or scam wording are sent for a full check, and stored masked (numbers, OTPs, card numbers hidden). |
| Can it be tricked by the scammer's text ("ignore your rules")? | The decision is made by fixed rules in code, not by the AI. The AI never sees raw scam text or full links, and can't act without the user's spoken yes. |
| Can it reverse a payment? | No. It guides to 1930, the bank and cybercrime.gov.in, with a ready report. |
| What's not finished? | Forwarded phone calls reaching the Agora phone agent (number configured, inbound address to confirm with Agora); Indian SMS sending needs DLT; Malayalam listening needs one more speech service; native-speaker review of three languages. |

## 7. If something fails on stage

| Problem | Do this |
|---|---|
| Website slow / blank | Free server waking up: wait 30–60 s and reload. |
| No spoken warning | Phone on silent? Volume? Status card all ✔? Show the red notification and the dashboard instead. |
| Test call doesn't ring | Vobiz balance? Use **Live monitor → Test it now** for the call story. |
| Voice agent won't hear on phone | Use the laptop's Talk button (it always works there). |
| Phone not detecting | Check pairing: website → Profile → Connect Android app. |
