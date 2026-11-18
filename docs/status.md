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
| Voice | Agora ConvoAI + custom LLM tool calling + policy gate | 📋 | Milestone 4 |
| Voice | Murf Falcon 2.1 voices for en-IN, hi-IN, ml-IN, kn-IN, ta-IN | ✅ (voice list) | Murf voices API, 2026-11-18: e.g. `hi-IN-jaya` supports all five |
| Voice | Speech recognition for ml / kn / ta | 📋 | Must test full speech-in → speech-out loop |
| Android | Talk / Check message / I was scammed / Protected Browser | 📋 | Milestone 5 |
| Response | 1930 dialer intent and opening official portals from the phone | 📋 | Milestone 5 (Android) |
| Calls | Agora RTC call with private warning | 📋 | After MVP |
| Calls | Cellular call screening (number only) | 📋 | Needs call-screening role |
| Calls | Cellular call audio / reversing UPI / freezing accounts | 🔒 | Not possible for an app; guide user to bank, 1930, cybercrime.gov.in |
