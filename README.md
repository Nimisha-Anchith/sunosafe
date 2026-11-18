# SunoSafe

**Protect. Investigate. Explain. Respond.**

SunoSafe is a voice-first digital safety companion for people who find it hard to tell a real link or message from a fake one: senior citizens, people with visual impairments and first-time smartphone users. Users talk to it in their own language. Behind the conversation, a lightweight security engine investigates suspicious messages and links, keeps an incident record, and guides the user through protection and recovery.

Built for **Build with Agora – Bengaluru 2026** (track PS51: From Conversations to Autonomous Action) with Agora Conversational AI and Murf AI Falcon TTS.

```
Detect → Investigate → Explain → Protect → Respond → Follow up
```

## Status

Work in progress, built milestone by milestone. See [docs/status.md](docs/status.md) for what is tested, untested, planned, or impossible without a bank or telecom.

- ✅ Milestone 1: link extraction, URL normalisation (defanged links, look-alike Unicode, disguised IPs, `@` trick, shorteners, UPI links) and an SSRF guard with DNS pinning

## Run the tests

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -v
```

All demo data is synthetic. API keys live only in local `.env` files, never in this repository.
