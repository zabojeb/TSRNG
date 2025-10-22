
from __future__ import annotations
import os, json, uuid, zipfile
from typing import Any
from .utils import ensure_dir

DATA_ROOT = os.environ.get("TSRNG_DATA", "./data")

def new_round_dir() -> tuple[str, str]:
    rid = uuid.uuid4().hex
    path = os.path.join(DATA_ROOT, "rounds", rid)
    ensure_dir(path)
    return rid, path

def round_dir(round_id: str) -> str:
    return os.path.join(DATA_ROOT, "rounds", round_id)

def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_bytes(path: str, b: bytes) -> None:
    with open(path, "wb") as f:
        f.write(b)

def read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def zip_dir(src_dir: str, out_zip: str) -> None:
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src_dir):
            for fn in files:
                full = os.path.join(base, fn)
                arc = os.path.relpath(full, src_dir)
                z.write(full, arc)
