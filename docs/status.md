# SunoSafe — feature status

Legend: ✅ Implemented & tested · 🟡 Implemented, untested · 📋 Planned · 🔒 Needs platform privilege or an institution (bank, telecom, police)

| Area | Feature | Status | Evidence |
|---|---|---|---|
| URL safety | Link extraction from message text | ✅ | `backend/tests/test_url_normalize.py` |
| URL safety | Normalisation (defang, punycode, disguised IPs, `@` trick, shorteners, UPI links) | ✅ | `backend/tests/test_url_normalize.py` |
| URL safety | SSRF guard (schemes, ports, internal names, private/metadata IPs, DNS answers, IP pinning) | ✅ | `backend/tests/test_ssrf_guard.py` |
| URL safety | Safe redirect follower, DNS, RDAP, TLS, Safe Browsing | 📋 | Milestone 2 |
| Messages | Scam-pattern rules (OTP, UPI PIN, urgency, impersonation, remote-access apps) | 📋 | Milestone 3 |
| Mini-SOC | Events, correlation, incidents, severity, Guardian Web View | 📋 | Milestone 3 |
| Voice | Agora ConvoAI + custom LLM tool calling + policy gate | 📋 | Milestone 4 |
| Voice | Murf Falcon 2.1 voices for en-IN, hi-IN, ml-IN, kn-IN, ta-IN | ✅ (voice list) | Murf voices API, 2026-11-18: e.g. `hi-IN-jaya` supports all five |
| Voice | Speech recognition for ml / kn / ta | 📋 | Must test full speech-in → speech-out loop |
| Android | Talk / Check message / I was scammed / Protected Browser | 📋 | Milestone 5 |
| Response | Block URL in SunoSafe browser, incident, 1930 dialer, cybercrime.gov.in | 📋 | Milestones 3–5 |
| Calls | Agora RTC call with private warning | 📋 | After MVP |
| Calls | Cellular call screening (number only) | 📋 | Needs call-screening role |
| Calls | Cellular call audio / reversing UPI / freezing accounts | 🔒 | Not possible for an app; guide user to bank, 1930, cybercrime.gov.in |
