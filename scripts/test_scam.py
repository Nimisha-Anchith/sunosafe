"""Send yourself a TEST scam SMS or a TEST scam call, any time, to demo SunoSafe.

No AI involved; plain Python standard library. It only ever contacts YOUR OWN number
(TEST_TARGET_NUMBER), so it cannot be used to message anyone else.

    python scripts/test_scam.py call              # scam message first, then 20 s later the scam call (Hindi)
    python scripts/test_scam.py call --call-only  # only the call (no warning while ringing: number unknown)
    python scripts/test_scam.py call --lang=en    # same, English
    python scripts/test_scam.py sms               # Vobiz sends the scam SMS (India: needs DLT, see below)
    python scripts/test_scam.py notify            # USB alternative: posts the scam message as a phone notification
    python scripts/test_scam.py demo              # sms (or notify) first, then 25 s later the call

The SMS text contains your Vobiz number, and the call comes FROM that number, so SunoSafe
first warns about the message and then warns again while the call rings (cross-channel).

Settings (in sunosafe-voice/.env.local; add them yourself, never paste them into chat):
    VOBIZ_AUTH_ID, VOBIZ_AUTH_TOKEN   Vobiz console dashboard
    VOBIZ_NUMBER                      your Vobiz number, E.164 (already there)
    TEST_TARGET_NUMBER                YOUR phone, E.164, e.g. +9198XXXXXXXX
    TEST_CALL_XML_URL                 optional; default: <gateway>/demo/scam-call.xml
    VOBIZ_DLT_ENTITY_ID, VOBIZ_DLT_HEADER_ID, VOBIZ_DLT_TEMPLATE_ID   optional, for SMS to Indian numbers

India SMS: TRAI requires a DLT-registered sender header and template for every commercial SMS. Without
them Vobiz will likely refuse the SMS or it will not be delivered; the script prints Vobiz's answer.
Use `notify` (USB) or forward the text from another phone instead.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_ENV = ROOT.parent / "sunosafe-voice" / ".env.local"
ADB = Path("C:/Users/Dell/tools/android-sdk/platform-tools/adb.exe")
API = "https://api.vobiz.ai/api/v1"


def env() -> dict[str, str]:
    out = {}
    if WEB_ENV.is_file():
        for line in WEB_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


E = env()


def need(key: str) -> str:
    v = E.get(key, "")
    if not v:
        sys.exit(f"Missing {key} in {WEB_ENV}. Add it there yourself (do not paste secrets into chat).")
    return v


def e164(key: str) -> str:
    v = need(key).replace(" ", "")
    if not re.fullmatch(r"\+\d{10,14}", v):
        sys.exit(f"{key} must look like +9198XXXXXXXX")
    return v


def spoken(number: str) -> str:
    """+918012345678 -> 080-1234-5678 style, as a scammer would write it."""
    d = number.removeprefix("+91")
    return f"0{d[:2]}-{d[2:6]}-{d[6:]}" if len(d) == 10 else number


def vobiz(path: str, body: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{API}/Account/{need('VOBIZ_AUTH_ID')}{path}", method="POST",
        data=json.dumps(body).encode(),
        headers={"X-Auth-ID": need("VOBIZ_AUTH_ID"), "X-Auth-Token": need("VOBIZ_AUTH_TOKEN"),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def scam_text() -> str:
    return (f"Dear SBI customer, your account will be BLOCKED today. Update KYC at "
            f"https://wrong.host.badssl.com/kyc and share the OTP. Call {spoken(e164('VOBIZ_NUMBER'))}")


def xml_url(lang: str) -> str:
    if E.get("TEST_CALL_XML_URL"):
        return E["TEST_CALL_XML_URL"]
    base = E.get("SUNOSAFE_PUBLIC_GATEWAY", "").rstrip("/") or         need("NEXT_SUNOSAFE_LLM_URL").split("?")[0].removesuffix("/llm/chat/completions")
    return base + f"/demo/scam-call.xml?lang={lang}"


def do_call(lang: str) -> bool:
    url = xml_url(lang)
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            ok = r.status == 200 and b"<Response>" in r.read()
    except Exception as e:      # noqa: BLE001 - show any reason
        ok = False
        print("  call script page not reachable:", e)
    if not ok:
        print(f"  The call script page {url} must be reachable from the internet (gateway running?).")
        return False
    status, text = vobiz("/Call/", {"from": e164("VOBIZ_NUMBER").lstrip("+"), "to": e164("TEST_TARGET_NUMBER").lstrip("+"),
                                    "answer_url": url, "answer_method": "GET", "time_limit": 90,
                                    "caller_name": "SBI KYC"})
    print(f"CALL  -> Vobiz HTTP {status}: {text[:300]}")
    if status == 402:
        print("  Vobiz says the balance is too low: add funds in the Vobiz console.")
    return 200 <= status < 300


def do_sms() -> bool:
    body = {"from": E.get("VOBIZ_DLT_HEADER_ID") or e164("VOBIZ_NUMBER"), "to": [e164("TEST_TARGET_NUMBER")],
            "channel": "sms", "text": scam_text()}
    for key, field in (("VOBIZ_DLT_ENTITY_ID", "dltEntityId"), ("VOBIZ_DLT_HEADER_ID", "dltHeaderId"),
                       ("VOBIZ_DLT_TEMPLATE_ID", "dltTemplateId")):
        if E.get(key):
            body[field] = E[key]
    status, text = vobiz("/Sms/Message/", body)
    print(f"SMS   -> Vobiz HTTP {status}: {text[:300]}")
    if not (200 <= status < 300) and not E.get("VOBIZ_DLT_TEMPLATE_ID"):
        print("  Indian SMS need DLT registration (TRAI). Use `notify` over USB, or send the text from another phone.")
    return 200 <= status < 300


def adb_connected() -> bool:
    if not ADB.is_file():
        return False
    r = subprocess.run([str(ADB), "devices"], capture_output=True, text=True, timeout=15)
    return any(line.endswith("	device") for line in r.stdout.splitlines())


def do_notify() -> bool:
    if not ADB.is_file():
        print("  adb not found at", ADB)
        return False
    text = scam_text().replace("'", "")
    cmd = [str(ADB), "shell", f"cmd notification post -S bigtext -t 'VM-SBIKYC' sunosafe-test '{text}'"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    ok = r.returncode == 0
    print("NOTIFY-> " + ("posted on the phone (needs the debug companion and USB debugging)" if ok
                         else f"failed: {(r.stderr or r.stdout).strip()[:200]}"))
    return ok


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lang = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--lang=")), "hi")
    if lang not in ("hi", "en"):
        sys.exit("--lang must be hi or en")
    action = args[0] if args else ""
    print(f"Target: your phone {e164('TEST_TARGET_NUMBER')[:5]}*****{e164('TEST_TARGET_NUMBER')[-2:]}")
    if action == "call":
        if "--call-only" not in sys.argv:
            # The ringing warning needs the number to be known from a scam message first (as in real life).
            print("First the scam message that mentions this number (so the phone can warn while it rings):")
            if not (adb_connected() and do_notify()) and not do_sms():
                print("  Could not deliver the message (no USB phone, SMS refused). The call will ring without a warning.")
            print("Calling in 20 seconds...")
            time.sleep(20)
        do_call(lang)
    elif action == "sms":
        do_sms()
    elif action == "notify":
        do_notify()
    elif action == "demo":
        if not do_sms():
            print("  SMS did not go through; trying the USB notification instead.")
            do_notify()
        print("Calling in 25 seconds (time to look at the message warning)...")
        time.sleep(25)
        do_call(lang)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
