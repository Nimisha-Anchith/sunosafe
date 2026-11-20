"""One process for hosting (Render): the private API and the public gateway together.

On the laptop they run as two programs (8000 private, 8001 public through a tunnel).
On a host there is only one public address, so:

    https://<host>/            private API  -> every route needs API_TOKEN (Bearer), checked in main.py
    https://<host>/gw/...      gateway      -> /gw/llm/chat/completions and /gw/agora/tools/screen need
                                               GATEWAY_TOKEN; /gw/device/* need DEVICE_TOKEN

API_TOKEN must be set when hosted (without it every remote request is refused, which is safe but useless).
Start: uvicorn app.hosted:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips '*'
"""
from __future__ import annotations

from app import gateway, main

app = main.app
app.mount("/gw", gateway.app)
