# SunoSafe — setup, run and demo guide (hackathon build, 20 Nov 2026)

## What runs where

```
Android companion (Samsung S24)          Phone browser / installed web app (PWA)
 ├─ notification listener                 ├─ PIN lock
 ├─ call screening (caller-ID role)       ├─ check message / link, incidents, evidence timeline
 └─ instant spoken warnings               └─ Talk: Agora Conversational AI + Murf Falcon
        │ HTTPS + DEVICE_TOKEN                     │ HTTPS (PIN session)
        ▼                                          ▼
 gateway tunnel ─► voice gateway :8001       app tunnel ─► web app :3002 ─► private backend :8000 (never public)
 (only /health, /llm/chat/completions,                       ▲
  /device/notifications, /device/calls)       Agora cloud ───┘ (calls /llm on the gateway with GATEWAY_TOKEN)
```

## Start everything (Windows, Git Bash)

```bash
# 1. Private backend (port 8000, localhost only)
cd C:/Users/Dell/Downloads/sunosafe/backend
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Public voice/device gateway (port 8001, localhost only; exposed only through the tunnel)
.venv/Scripts/python -m uvicorn app.gateway:app --host 127.0.0.1 --port 8001

# 3. Tunnels (each prints a new https://<random>.trycloudflare.com address on every start)
C:/Users/Dell/tools/cloudflared/cloudflared.exe tunnel --no-autoupdate --metrics 127.0.0.1:20241 --url http://127.0.0.1:8001
C:/Users/Dell/tools/cloudflared/cloudflared.exe tunnel --no-autoupdate --metrics 127.0.0.1:20242 --url http://127.0.0.1:3002
curl -s http://127.0.0.1:20241/quicktunnel   # gateway address
curl -s http://127.0.0.1:20242/quicktunnel   # app address

# 4. Put the GATEWAY address into the web app, then start it
#    sunosafe-voice/.env.local:  NEXT_SUNOSAFE_LLM_URL=https://<gateway-address>/llm/chat/completions
cd C:/Users/Dell/Downloads/sunosafe-voice
pnpm dev --port 3002          # package.json binds it to 127.0.0.1
```

After a tunnel restart the address changes: update `NEXT_SUNOSAFE_LLM_URL`, restart the web app, and on the phone tap
**Settings → Connect Android app** again so the companion learns the new gateway address.

## Settings that must exist (values never go in git or chat)

| File | Keys |
|---|---|
| `backend/.env` | `GROQ_API_KEY` (LLM), `GATEWAY_TOKEN`, `DEVICE_TOKEN`, optional `SAFE_BROWSING_API_KEY`, `GEMINI_API_KEY` (fallback) |
| `sunosafe-voice/.env.local` | `NEXT_PUBLIC_AGORA_APP_ID`, `NEXT_AGORA_APP_CERTIFICATE`, `NEXT_MURF_API_KEY`, `NEXT_SUNOSAFE_LLM_URL`, `NEXT_SUNOSAFE_LLM_KEY` (= `GATEWAY_TOKEN`), `SUNOSAFE_APP_PIN`, `SUNOSAFE_SESSION_SECRET`, `SUNOSAFE_DEVICE_TOKEN` (= `DEVICE_TOKEN`), `SUNOSAFE_APK_PATH` |

## Android companion

Build: `cd sunosafe/android && JAVA_HOME=C:/Users/Dell/tools/jdk17 ANDROID_HOME=C:/Users/Dell/tools/android-sdk C:/Users/Dell/tools/gradle-8.10.2/bin/gradle testDebugUnitTest assembleDebug`

APK: `sunosafe/android/app/build/outputs/apk/debug/app-debug.apk` (copy: `C:\Users\Dell\Downloads\SunoSafe-companion-0.2.0.apk`)

Install (USB debugging on):
```bash
C:/Users/Dell/tools/android-sdk/platform-tools/adb.exe install -r C:/Users/Dell/Downloads/SunoSafe-companion-0.2.0.apk
```

### Samsung Galaxy S24 permissions
1. Open **SunoSafe** → **1. Turn on notification access** → find SunoSafe → switch on → **Allow**.
   (Or: Settings → Notifications → Advanced settings → Notification access → SunoSafe.) If the switch is greyed out,
   open Settings → Apps → SunoSafe → ⋮ → **Allow restricted settings**, then try again.
2. **2. Allow SunoSafe to show warnings** → Allow.
3. On the phone, open the SunoSafe web app → Settings → **Connect Android app** → in the companion, **Yes, connect**.
4. **4. Let SunoSafe check unknown callers** → choose SunoSafe as the Caller ID & spam app.
   (Samsung: Phone app → ⋮ → Settings → Caller ID and spam protection.)
5. **Keep SunoSafe running (battery)** → Settings → Apps → SunoSafe → Battery → **Unrestricted**.

Test the listener over ADB (debug build only):
```bash
adb shell cmd notification post -S bigtext -t "VM-SBIKYC" sunosafe-test "Dear SBI customer, your account will be BLOCKED today. Update KYC at https://wrong.host.badssl.com/kyc and share the OTP. Call 9876543210."
```

## Demo script (about 3 minutes)

1. **Proactive detection.** A fake SBI KYC SMS arrives (from a second phone, or the ADB command above). Without opening
   anything, the phone shows "Danger: scam message", vibrates and speaks the warning (Hindi if chosen).
2. **Evidence.** Tap **See evidence**: the incident shows why (secret request, brand-vs-link mismatch, pressure,
   certificate or reachability result) and a timeline with the source of every event.
3. **Cross-channel.** The number from that SMS (98765 43210) calls the phone. While it rings, SunoSafe says "Careful.
   This caller's number appeared in a scam message you received." The incident gains a *call screened* event and a
   *same scam by message and call* event; severity rises with the reason shown.
   (Without a second phone: Calls tab → **Intervention demo**, labelled simulated, runs the same engine.)
4. **Voice.** Tap **Talk to SunoSafe** on the warning. The Agora agent opens already briefed: "A message and a phone call
   pretending to be State Bank of India reached you…" in the Murf Falcon voice. Ask "Why is it dangerous?".
5. **Approved action.** Say "Yes, block it." The policy gate checks the user's own words, blocks the link, and the
   timeline records "approved by voice". Opening the link through SunoSafe now shows the red block screen.
6. **Recovery.** "I already typed my OTP" → recovery plan: call 1930 (tap to dial), call the bank's official number,
   report at cybercrime.gov.in, with a shareable incident report.
7. **Practice.** Home → **Practise: scam call drill**: SunoSafe plays a scam caller and teaches the user to say no.

## Vobiz (evaluated, not integrated)

Vobiz-style programmable telephony (SIP numbers) could later give SunoSafe its own phone number that elderly users can
forward a suspicious caller to, or call for help, connected to the same voice agent. It cannot give an Android app access
to ordinary cellular call audio. It was not integrated: it would add an account, a number and cost without changing the
core demo, and could not be tested in time. The gateway's `/llm` endpoint is provider-neutral, so a SIP bridge could be
added later without changing the security engine.
