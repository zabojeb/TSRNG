from __future__ import annotations
import base64
import hashlib
import hmac
import os
import datetime
import json
import binascii


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def sha3_512(data: bytes) -> bytes:
    return hashlib.sha3_512(data).digest()


def hkdf_sha3(ikm: bytes, salt: bytes, length: int) -> bytes:
    # RFC5869-style with HMAC-SHA3-256
    prk = hmac.new(salt, ikm, hashlib.sha3_256).digest()
    okm = b""
    t = b""
    c = 1
    while len(okm) < length:
        counter_bytes = c.to_bytes(4, "big")
        t = hmac.new(prk, t + counter_bytes, hashlib.sha3_256).digest()
        okm += t
        c += 1
        if c > 0xFFFFFFFF:
            raise ValueError("hkdf_sha3 length exceeds counter capacity")
    return okm[:length]


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode())


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def parse_seed(s: str) -> bytes:
    """
    Принимает: hex (с/без 0x), base64/base64url (с/без '='), либо JSON от маяков
    (drand: {"randomness": "..."}; NIST v2: {"pulse":{"outputValue":"..."}}).
    Если не распознали — берём SHA3-256 от строки.
    """
    if s is None:
        raise ValueError("Empty seed")
    s = str(s).strip()

    # JSON?
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and "randomness" in obj:
                s = str(obj["randomness"]).strip()
            elif isinstance(obj, dict) and "pulse" in obj and isinstance(obj["pulse"], dict):
                s = str(obj["pulse"].get("outputValue")
                        or obj["pulse"].get("seedValue") or "").strip()
        except Exception:
            pass

    # 0x-префикс
    if s[:2].lower() == "0x":
        s = s[2:]

    # hex
    try:
        return bytes.fromhex(s)
    except ValueError:
        pass

    # base64/base64url
    def _b64fix(x: str) -> str:
        pad = (-len(x)) % 4
        return x + ("=" * pad)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(_b64fix(s))
        except Exception:
            continue

    # fallback: хэш строки
    return hashlib.sha3_256(s.encode()).digest()
