from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Dict, Optional

from ..utils import now_iso, ensure_dir
from ..storage import round_dir, write_json, read_bytes


class HeavyTestError(RuntimeError):
    """Raised when an external heavy test fails to execute or returns an error."""


def run_dieharder_on_data(data: bytes, test_args: Optional[list[str]] = None) -> Dict:
    if test_args is None:
        test_args = ["-a", "-g", "201"]

    with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
        tmp_in.write(data)
        tmp_in_path = tmp_in.name

    try:
        cmd = ["dieharder", *test_args, "-f", tmp_in_path]
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError as exc:
            raise HeavyTestError("dieharder executable not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise HeavyTestError("dieharder timed out") from exc

        result = {
            "command": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if completed.returncode != 0:
            raise HeavyTestError(f"dieharder failed with code {completed.returncode}")
        return result
    finally:
        try:
            os.unlink(tmp_in_path)
        except OSError:
            pass


def store_heavy_test(round_id: str, name: str, payload: Dict) -> str:
    rdir = round_dir(round_id)
    heavy_dir = os.path.join(rdir, "analysis", "heavy")
    ensure_dir(heavy_dir)
    ts = now_iso().replace(":", "-")
    filename = f"{ts}_{name}.json"
    path = os.path.join(heavy_dir, filename)
    payload = dict(payload)
    payload["round_id"] = round_id
    payload["test_name"] = name
    payload["timestamp"] = now_iso()
    write_json(path, payload)
    index_path = os.path.join(heavy_dir, "index.json")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        idx = {"entries": []}
    idx["entries"].append({"file": filename, "timestamp": payload["timestamp"], "test_name": name})
    write_json(index_path, idx)
    return path


def load_round_output(round_id: str) -> bytes:
    rdir = round_dir(round_id)
    out_path = os.path.join(rdir, "output.bin")
    if not os.path.isfile(out_path):
        raise HeavyTestError("Round output not found; finalize the round first")
    return read_bytes(out_path)
