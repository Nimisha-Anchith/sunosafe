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
