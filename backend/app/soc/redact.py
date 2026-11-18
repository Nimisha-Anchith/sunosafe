"""Mask personal numbers before anything is written to the database or logs.

The analysis runs on the original text in memory; only the redacted version is
stored. Patterns: card numbers (13-19 digits), Aadhaar (12 digits), PAN,
codes after OTP/PIN/password words, and the middle of phone numbers.
"""
from __future__ import annotations

import re

_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_AADHAAR = re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_SECRET_CODE = re.compile(r"(?i)\b(otp|code|pin|mpin|password|passcode|cvv)\b(\D{0,15}?)(\d{3,8})(?!\d)")
_PHONE = re.compile(r"(?<!\d)(\+?91[\s-]?)?([6-9]\d)(\d{5})(\d{3})(?!\d)")


def _mask_digits(s: str, keep_last: int = 4) -> str:
    digits = [c for c in s if c.isdigit()]
    keep = set(range(len(digits) - keep_last, len(digits)))
    out, i = [], 0
    for c in s:
        if c.isdigit():
            out.append(c if i in keep else "X")
            i += 1
        else:
            out.append(c)
    return "".join(out)


def redact(text: str) -> str:
    if not text:
        return text
    text = _CARD.sub(lambda m: _mask_digits(m.group(0)), text)
    text = _AADHAAR.sub(lambda m: _mask_digits(m.group(0)), text)
    text = _PAN.sub("XXXXX####X", text)
    text = _SECRET_CODE.sub(lambda m: f"{m.group(1)}{m.group(2)}{'X' * len(m.group(3))}", text)
    text = _PHONE.sub(lambda m: f"{m.group(1) or ''}{m.group(2)}XXXXX{m.group(4)}", text)
    return text
