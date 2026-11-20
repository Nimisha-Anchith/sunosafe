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
 (only /health, /llm/chat/completions, /agora/tools/screen,   ▲
  /device/notifications, /device/calls, /device/alerts, /device/speech)       Agora cloud ───┘ (calls /llm on the gateway with GATEWAY_TOKEN)
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
| `backend/.env` | `GROQ_API_KEY` (LLM), `GATEWAY_TOKEN`, `DEVICE_TOKEN`, `MURF_API_KEY` (spoken phone warnings), optional `SAFE_BROWSING_API_KEY`, `GEMINI_API_KEY` (fallback) |
| `sunosafe-voice/.env.local` | `NEXT_PUBLIC_AGORA_APP_ID`, `NEXT_AGORA_APP_CERTIFICATE`, `NEXT_MURF_API_KEY`, optional `NEXT_SARVAM_API_KEY` (Malayalam listening), `NEXT_SUNOSAFE_LLM_URL`, `NEXT_SUNOSAFE_LLM_KEY` (= `GATEWAY_TOKEN`), `SUNOSAFE_APP_PIN`, `SUNOSAFE_SESSION_SECRET`, `SUNOSAFE_DEVICE_TOKEN` (= `DEVICE_TOKEN`), `SUNOSAFE_APK_PATH` |

## Android companion

Build: `cd sunosafe/android && JAVA_HOME=C:/Users/Dell/tools/jdk17 ANDROID_HOME=C:/Users/Dell/tools/android-sdk C:/Users/Dell/tools/gradle-8.10.2/bin/gradle testDebugUnitTest assembleDebug`

APK: `sunosafe/android/app/build/outputs/apk/debug/app-debug.apk` (version 0.3.0)

Install (USB debugging on):
```bash
C:/Users/Dell/tools/android-sdk/platform-tools/adb.exe install -r sunosafe/android/app/build/outputs/apk/debug/app-debug.apk
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

## Call shield: SunoSafe answers suspicious calls (Vobiz + Agora)

```
scam caller ─► your mobile ── declined / not answered ──► call forwarding (**67* / **61*)
                                                            │
                                                            ▼
                         Vobiz +91 number ─► Vobiz inbound trunk ─► Agora SBC (sbc-ap-south.viblinx.com)
                                                                            │
                     Agora phone agent "SunoSafe Call Shield"  (Deepgram hears ─► Agora's LLM ─► Murf speaks)
                                                                            │  after EVERY caller sentence:
                                                                            ▼  POST /agora/tools/screen {callerWords}
                         gateway ─► SunoSafe rules screen the words (in code), in 5 languages incl. native script
                                   ├─ scam signs? record `call_shielded`, correlate (same SBI story as the SMS)
                                   ├─ tell the agent exactly what to say (a fixed, reviewed refusal)
                                   └─ queue one warning ─► phone companion fetches /device/alerts every 10 s
                                                           ─► speaks it calmly with the Murf voice
```

### Why a tool and not SunoSafe as the agent's brain
Tested against Agora's API on 20 Nov 2026: a saved phone agent only accepts approved LLM providers. Our gateway,
example.com and Groq were all refused with `Provider endpoint is not approved`; only `api.openai.com` was accepted.
The visual Agent Studio has no custom-LLM field either. Agora's agents do support **function tools** that call an
HTTPS endpoint during the call, so the agent's model is Agora-managed (`gpt-4.1-mini`) and SunoSafe decides through
the `screenCaller` tool. The decision is made by SunoSafe's rules; the model only relays it.

Agora sends a tool's arguments only where they are mapped with `{{args.<name>}}` (the body is empty otherwise).

### Managing it: `scripts/agora_shield.py`
```bash
backend/.venv/Scripts/python scripts/agora_shield.py status            # read-only
backend/.venv/Scripts/python scripts/agora_shield.py setup --lang=hi   # create/update the secret set and the agent
backend/.venv/Scripts/python scripts/agora_shield.py sync  --lang=hi   # after a tunnel restart: new tool address
backend/.venv/Scripts/python scripts/agora_shield.py number            # import the number, route inbound calls to the agent
backend/.venv/Scripts/python scripts/agora_shield.py unroute           # stop answering calls (number stays imported)
backend/.venv/Scripts/python scripts/agora_shield.py remove --yes      # delete the number and the agent
```
It uses Agora's Conversational AI platform REST API (Preview): `https://preview.ai.agora.io/conversational-ai/v1/projects/{appid}`,
Basic auth with the RESTful API key. Settings it reads from `sunosafe-voice/.env.local` (never printed): `AGORA_CUSTOMER_ID`,
`AGORA_CUSTOMER_SECRET`, `VOBIZ_NUMBER` (E.164), `VOBIZ_SIP_DOMAIN` (`<trunk-id>.sip.vobiz.ai`), `VOBIZ_SIP_USERNAME`,
`VOBIZ_SIP_PASSWORD`; from `backend/.env`: `GATEWAY_TOKEN`. The Murf key is stored at Agora as a secret set (`sunosafe_shield`).

### Vobiz side (account owner; from https://www.vobiz.ai/docs/integrations/agora)
1. Origination URIs → create: URI `sbc-ap-south.viblinx.com` (no `sip:`), Transport **UDP**, Active **On**.
2. Inbound Trunks → Create inbound trunk → Primary URI = that URI → Link Numbers → pick the number.
   Status must be Enabled and show Linked Numbers (1).
   (Vobiz's "Applications" screen with an answer URL is a different feature and is not used.)
3. Test: call the Vobiz number from another phone. Vobiz → Call Logs shows the call; `agora_shield.py status` and the
   gateway log show whether it reached the agent and the tool.
The SBC address comes from Vobiz's guide for Agora's console flow; it is not confirmed in Agora's API docs for
numbers imported through the API.

### Phone
Dial `**67*<SunoSafe number>#` (busy or declined) and `**61*<SunoSafe number>#` (not answered). `##002#` turns it off.
`NEXT_PUBLIC_SUNOSAFE_SHIELD_NUMBER` in `sunosafe-voice/.env.local` makes the Calls screen show the codes.

### Testing without a phone line
- The same agent by voice: start a session of the agent in an RTC channel (`POST .../sessions`, `transport.type: "rtc"`)
  and join the channel as the caller. Done on 20 Nov 2026 with recorded Hindi caller sentences: Agora called the tool
  after each sentence, SunoSafe flagged the OTP request as high, recorded `call_shielded` in the SMS's incident and
  queued the phone warning.
- Web app → Calls → **Test it now: you play the caller** (`/talk?mode=shield`) uses the web voice agent (SunoSafe as the
  brain, which Agora allows for web sessions) and the same screening rules.

### Honest limits
- SunoSafe answers the call *instead of* the user. It cannot listen in on a call the user answers.
- Agora sends no call id or caller number with a tool call, so calls are told apart by time (90 s gap) and a shielded
  call is linked by its story (claimed brand, numbers or links the caller says), not by the caller's number. Two calls
  at the same moment would be screened as one (single-user prototype).
- The agent's model is asked to call the tool after every caller sentence and did so in the test, but a model can skip
  a tool call; then that sentence is not screened. Not yet verified: the exact words the agent spoke after the tool
  answered (Agora gives transcripts only through webhooks).
- What the caller says goes to Deepgram (speech-to-text) and OpenAI (through Agora), and to SunoSafe. During Agora's
  Preview, agent sessions run in North America, which adds delay. Agora bills agent minutes ($0.10/min after 300 free).
- The quick-tunnel address changes on every restart: run `agora_shield.py sync` afterwards, or calls reach the agent
  but the tool does not answer (the agent then speaks the fixed refusal).
- Not yet tested over a real phone line.

## Languages (English, Hindi, Malayalam, Kannada, Tamil)

| What | How | Status |
|---|---|---|
| Spoken warnings on the phone | Murf Falcon audio fetched from the backend (`/device/speech/<id>`), cached on the phone; the phone's own voice only if Murf cannot be reached | Audio tested through the tunnel in all 5 languages; playback on the S24 not yet tested |
| Voice agent speaking | Murf Falcon, locale per language | Agent starts in all 5 |
| Voice agent listening | en, hi: Deepgram; kn, ta: Agora ARES; ml: needs `NEXT_SARVAM_API_KEY` (Agora's own recognizers have no Malayalam), otherwise it listens with the English recognizer | Agents start (RUNNING); understanding real speech needs a person to test, especially Malayalam |
| Sentences | Fixed, reviewed text in `backend/app/soc/phrases.py` | Native-speaker review of ml, kn, ta wording is recommended before real users |
