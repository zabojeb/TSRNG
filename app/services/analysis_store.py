from __future__ import annotations

import os
from typing import Dict

from ..storage import read_json, round_dir, write_json
from ..utils import ensure_dir, now_iso


def store_round_analysis(round_id: str, payload: dict, source: Dict) -> str:
    rdir = round_dir(round_id)
    analysis_dir = os.path.join(rdir, "analysis")
    ensure_dir(analysis_dir)
    timestamp = now_iso()
    record = {"generated_iso": timestamp, "result": payload, "source": source}

    # persist per-run history entry
    history_dir = os.path.join(analysis_dir, "history")
    ensure_dir(history_dir)
    safe_ts = timestamp.replace(":", "-")
    history_file = os.path.join(history_dir, f"{safe_ts}.json")
    write_json(history_file, record)

    index_path = os.path.join(history_dir, "index.json")
    try:
        index_obj = read_json(index_path)
    except FileNotFoundError:
        index_obj = {"entries": []}
    entry_summary = {
        "file": os.path.basename(history_file),
        "timestamp": timestamp,
        "bit_length": payload.get("bit_length"),
        "all_passed": payload.get("all_passed"),
        "limit_bits": source.get("limit_bits"),
    }
    index_obj.setdefault("entries", []).append(entry_summary)
    write_json(index_path, index_obj)

    latest_path = os.path.join(analysis_dir, "latest.json")
    write_json(latest_path, record)

    manifest_path = os.path.join(rdir, "manifest.json")
    try:
        manifest = read_json(manifest_path)
    except FileNotFoundError:
        manifest = {}
    manifest["analysis"] = {
        "latest_path": "analysis/latest.json",
        "bit_length": payload.get("bit_length"),
        "all_passed": payload.get("all_passed"),
        "updated_iso": record["generated_iso"],
        "history_index": "analysis/history/index.json",
    }
    write_json(manifest_path, manifest)
    return latest_path
