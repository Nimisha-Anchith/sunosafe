# SunoSafe — how to test everything (20 Nov 2026)

Do the tests in this order. Each one says what to do, what you should see, and where to look if it fails.

## 0. Before you start (laptop)

All of these must be running. If one has stopped, restart it (see `docs/demo-and-setup.md`).

| What | Check | Good result |
|---|---|---|
| Backend (8000), gateway (8001), web app (3002) | `curl http://127.0.0.1:8001/health` | `{"status":"ok"}` |
| Gateway tunnel | `curl http://127.0.0.1:20241/quicktunnel` | a `*.trycloudflare.com` name |
| App tunnel | `curl http://127.0.0.1:20242/quicktunnel` | a `*.trycloudflare.com` name |
| Agora agent + number | `backend/.venv/Scripts/python scripts/agora_shield.py status` | 1 agent, 1 number with `inbound.agent` set |

If a tunnel restarted, its address changed. Then:
1. Put the new gateway address in `sunosafe-voice/.env.local` (`NEXT_SUNOSAFE_LLM_URL`) and restart the web app.
2. Run `scripts/agora_shield.py sync --lang=hi` (points the phone agent's tool at the new address).
3. On the phone: web app → Profile → Connect Android app (the companion learns the new address).

## 1. New look (web app)

1. Open the app address on the phone (or `http://localhost:3002` on the laptop) and unlock with your PIN.
2. **Home**: dark green screen, night-landscape card "Your personal call guardian", a **Call Shield** switch showing your
   SunoSafe number (masked), tiles *Live monitor, Call history, Threat logs, SIEM dashboard, Settings*, **Recent activity**,
   and the round green **Talk** button in the bottom bar.
3. **SIEM dashboard** (tile or *Reports* in the bottom bar): four counters, *Threats timeline* bars, *Threat types* ring,
   *Recent incidents* table, *Live call monitor*. Change *Last 7 days* to *Last 30 days*: numbers update.
   Every number comes from the event store; with an empty store everything shows 0 (nothing is invented).
4. Tap a row in *Recent incidents*: the incident with its evidence opens.
5. **Live monitor**: shows the last call SunoSafe answered (caller's words masked, SunoSafe's answer, *Scam detected* card).

## 2. Real phone call to the SunoSafe number (the main demo)

1. From any phone, call your Vobiz number.
2. **Expect**: within a few seconds the agent answers with the greeting (Hindi by default:
   "नमस्ते, यह सुनोसेफ़ कॉल असिस्टेंट है…").
3. Say: **"Hello, main SBI bank se bol raha hoon."** → the agent asks who you are / why you are calling.
4. Say: **"Aapka account aaj band ho jayega. Phone par jo OTP aaya hai woh abhi bataiye."**
5. **Expect**: the agent refuses calmly ("माफ़ कीजिए… असली बैंक कभी ये नहीं माँगते… सुनोसेफ़ ने इस कॉल को दर्ज कर लिया है").
6. While the call is on, open **Live monitor** in the app: green *Live* dot, your words (masked), *Scam detected, Risk High*.
7. After the call: **SIEM dashboard** → *Scams stopped* +1, a new row in *Call log*, the incident updated.
8. If the companion is installed and paired: within ~10 s the phone speaks
   "सुनोसेफ़ ने आपके लिए एक कॉल उठाया… यह धोखाधड़ी लगती है…" in the Murf voice.

**If it fails**
| Symptom | Where to look | Likely cause |
|---|---|---|
| Call does not connect / rings out | Vobiz → Call Logs | inbound trunk not linked, wrong origination URI (`sbc-ap-south.viblinx.com`, UDP), trial-account limit |
| Connects, silence or drops | Vobiz Call Logs; `agora_shield.py status` | SBC region or transport mismatch; number not assigned to the agent |
| Agent talks but never refuses | gateway log (`preview_logs` / terminal) for `POST /agora/tools/screen` | tunnel address changed → run `agora_shield.py sync`; or 401 (token) |
| `POST /agora/tools/screen … 422` in the log | gateway log warning line | the tool's arguments did not arrive; tell me the logged structure |

Try other languages by re-running `agora_shield.py setup --lang=en` (or `ta`, `kn`, `ml`) and calling again.
Kannada/Tamil/Malayalam listening on phone calls uses Deepgram's English recogniser in the agent today; Hindi and English are the reliable demo languages.

## 3. Test the call shield without a phone call

1. App → *Live monitor* → **Test it now: you play the caller** (or *Profile → Call tools*).
2. Allow the microphone, start, and say the same two sentences as above.
3. **Expect**: the same refusal, and the Live monitor / dashboard update.
   (This uses the web voice agent with SunoSafe as its brain, the same rules as the phone agent.)

## 4. Scam message detection (Android companion)

1. Connect the S24 by USB (USB debugging on) and install the new companion:
   `C:/Users/Dell/tools/android-sdk/platform-tools/adb.exe install -r sunosafe/android/app/build/outputs/apk/debug/app-debug.apk`
2. In the companion: choose **हिंदी** → you should **hear a Hindi sample in the Murf voice** (this was silent before).
   Try മലയാളം, ಕನ್ನಡ, தமிழ் too.
3. Send yourself an SMS/WhatsApp from another phone (or the ADB command in `demo-and-setup.md`):
   *"Dear SBI customer, your account will be BLOCKED today. Update KYC at https://wrong.host.badssl.com/kyc and share the OTP. Call 8089389249"*
4. **Expect**: red warning notification, vibration, the warning spoken in your language; the incident appears on the
   dashboard. Also try a Hindi-script message: *"आपका खाता आज बंद हो जाएगा, अभी ओटीपी बताइए"*.
5. **Genuine message check**: *"Your OTP is 482913. Do not share it with anyone."* → no warning.

## 5. Caller-ID warning while the phone rings

1. Companion step 4: make SunoSafe the *Caller ID & spam* app.
2. Call the S24 from the number that was inside the scam message (8089389249 in the test above), or any number from a scam
   message you received.
3. **Expect**: while it rings, the phone says "सावधान। यह नंबर पहले आए एक धोखाधड़ी संदेश में था…"; the dashboard shows a
   *Caller-ID check* call joined to the same incident.

## 6. Voice agent (Talk to SunoSafe)

1. Tap the round **Talk** button on the phone. Allow the microphone.
2. **Expect**: the agent greets you (Murf voice). Ask "Is this message safe?" after checking one.
3. This failed on the S24 before with `InvalidModificationError`; a fix is in place but not yet confirmed on the phone.
   If it still fails, read the error shown on screen and tell me.
4. Open Talk from a warning (*Talk to SunoSafe* on the notification): the agent starts already briefed on that incident.
   Say "Yes, block it" → the link is blocked, *Scams stopped* rises, the timeline says "approved by voice".

## 7. Forwarding real calls to SunoSafe (optional, for the full story)

On the S24 dial `**67*<SunoSafe number>#` (declined/busy) and `**61*<SunoSafe number>#` (unanswered).
Then decline an incoming call: it goes to the SunoSafe agent. Turn off with `##002#`.
Your operator may charge for forwarded calls.

## 8. Before the demo

- The event store contains today's test data (test calls count as "scams stopped"). For a clean demo, stop the backend
  and move `backend/data/sunosafe.db` into `backend/data/archive/`, then start it again.
- Keep the laptop awake and the tunnels running; check step 0 again just before presenting.
