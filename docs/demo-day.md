# SunoSafe — demo day guide (21 Nov 2026)

## Where things run

| Part | Address | Notes |
|---|---|---|
| Backend (Mini-SIEM, rules, voice brain, gateway) | https://sunosafe-backend.onrender.com | Render free plan: sleeps after 15 min idle, ~1 min to wake. Open the website 2 minutes before presenting. Data resets when Render restarts. |
| Website (judges and mentors) | Vercel address (after deploy) | PIN-locked; give the PIN only to judges. |
| Agora phone agent "SunoSafe Call Shield" | calls `.../gw/agora/tools/screen` on Render | no laptop needed |
| Android companion | your Samsung S24 | pair it to the hosted website: Profile → Connect Android app |

## What the website can show on its own (laptop or any browser)

1. **Talk to SunoSafe** (round green button): voice agent in your language (Agora Conversational AI + Murf Falcon voice). Ask "is this message safe?", "I shared my OTP, what now?".
2. **Check a message**: paste an SMS/WhatsApp text (or tap *Example*) → verdict, warning signs, link investigation (real destination, domain age, certificate). Works in Hindi, Malayalam, Kannada, Tamil script too.
3. **Check a link**: investigates a link safely; *open through SunoSafe* shows the block screen for dangerous sites.
4. **SIEM dashboard** (Reports): counters, threats timeline, threat types, incidents, call log, live call monitor. Every number is real.
5. **Incidents / Threat logs**: evidence timeline with the source of every event, recovery steps, call 1930, report text for cybercrime.gov.in.
6. **Live monitor → Test it now: you play the caller**: SunoSafe's call assistant answers like a forwarded call; say "I am from SBI, tell me your OTP" → it refuses, records a scam call, dashboard updates live.
7. **Practise: scam call drill**: SunoSafe plays a scammer so the user practises saying no.
8. **Block by voice**: open Talk from an incident, say "yes, block it" → link blocked, timeline says "approved by voice".

## What needs the phone (show on the S24, results appear on the website)

1. **Scam notification** (SMS/WhatsApp) → red warning, vibration, spoken in your language (Murf voice).
2. **Messages you open or scroll** in WhatsApp/SMS (screen checking, switch on in the app, step 5).
3. **Share → SunoSafe** from any message, or *Check the message I copied* in the app → instant spoken verdict.
4. **Caller-ID warning while it rings** when a number from a scam message calls.
5. **"SunoSafe answered a scam call for you"** spoken after the call assistant handled a forwarded call.
6. Five voices: tap a language in the app to hear the sample.

## Suggested 4-minute demo

1. **Problem (20 s)**: elders and blind users can't read small warnings; scammers use SMS + call together.
2. **Proactive detection (60 s)**: run `test_scam.py notify` (or send the SBI text from a second phone). The S24 speaks the warning in Hindi. Open *See evidence*: why it's dangerous, link investigation, timeline.
3. **Cross-channel (45 s)**: run `test_scam.py call`. The call comes from the number in that SMS: the phone warns while it rings; the dashboard shows the same scam by message and call.
4. **Voice (60 s)**: tap *Talk to SunoSafe* on the warning: the agent is already briefed. Ask "why is it dangerous?", then "yes, block it".
5. **Call shield (45 s)**: Live monitor → *Test it now*: play the scammer; SunoSafe refuses calmly; Live monitor shows "Scam detected"; dashboard updates.
6. **Close (10 s)**: SIEM dashboard: everything in one evidence trail, five Indian languages.

## Running the test SMS / call yourself (no AI involved)

Settings once, in `sunosafe-voice/.env.local` (type them yourself): `VOBIZ_AUTH_ID`, `VOBIZ_AUTH_TOKEN` (Vobiz console dashboard), `TEST_TARGET_NUMBER` (your phone, `+91…`). `VOBIZ_NUMBER` is already there.

From `C:\Users\Dell\Downloads\sunosafe`:

```
backend\.venv\Scripts\python.exe scripts\test_scam.py call          # scam call to your phone (Hindi)
backend\.venv\Scripts\python.exe scripts\test_scam.py call --lang=en
backend\.venv\Scripts\python.exe scripts\test_scam.py sms           # scam SMS via Vobiz (India: needs DLT, may be refused)
backend\.venv\Scripts\python.exe scripts\test_scam.py notify        # scam message as a notification over USB (always works)
backend\.venv\Scripts\python.exe scripts\test_scam.py demo          # SMS (or notify), then the call 25 s later
```

The call script is served by Render (`/gw/demo/scam-call.xml`), so it works without the laptop backend.

## Honest limits to say if asked

- SunoSafe can't listen to calls the user answers (Android blocks it); it warns while ringing and answers forwarded calls.
- The Vobiz number → Agora phone agent route is configured but calls are not yet reaching Agora (Preview-platform inbound address to confirm with Agora).
- Indian SMS sending needs DLT registration.
- Malayalam listening needs a Sarvam key; Malayalam/Kannada/Tamil word lists need native-speaker review.
- Free hosting sleeps when idle; demo data resets on restart.
