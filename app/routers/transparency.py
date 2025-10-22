from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..storage import DATA_ROOT, read_bytes, read_json, round_dir

router = APIRouter(prefix="/rounds", tags=["transparency"])


def _round_manifest(round_id: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")
    manifest_path = os.path.join(rdir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise HTTPException(404, "Manifest not found")
    return read_json(manifest_path)


def _resolve_stage(manifest: Dict[str, Any]) -> str:
    if manifest.get("t2_iso"):
        return "finalized"
    if manifest.get("S_hex") or manifest.get("S_canonical_hex"):
        return "beaconed"
    return "committed"


@router.get("", summary="List existing rounds")
def list_rounds(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    root = os.path.join(DATA_ROOT, "rounds")
    if not os.path.isdir(root):
        return []
    items: List[Dict[str, Any]] = []
    for rid in os.listdir(root):
        path = os.path.join(root, rid)
        if not os.path.isdir(path):
            continue
        manifest_path = os.path.join(path, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        try:
            manifest = read_json(manifest_path)
        except Exception:
            continue
        entry = {
            "round_id": rid,
            "round_label": manifest.get("round_label"),
            "stage": _resolve_stage(manifest),
            "t0_iso": manifest.get("t0_iso"),
            "t1_iso": manifest.get("t1_iso"),
            "t2_iso": manifest.get("t2_iso"),
            "streams": manifest.get("streams"),
            "output_bits": manifest.get("output_bits"),
        }
        items.append(entry)
    items.sort(key=lambda x: x.get("t0_iso") or "", reverse=True)
    return items[:limit]


@router.get("/{round_id}/manifest", summary="Get manifest JSON")
def get_manifest(round_id: str) -> Dict[str, Any]:
    return _round_manifest(round_id)


@router.get("/{round_id}/selected", summary="Selected indices and leaves metadata")
def get_selected(round_id: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")
    selected_path = os.path.join(rdir, "selected.json")
    if not os.path.isfile(selected_path):
        raise HTTPException(404, "Selection not available (finalize round first)")
    leaves_meta_path = os.path.join(rdir, "leaves_meta.json")
    leaves_meta = read_json(leaves_meta_path) if os.path.isfile(leaves_meta_path) else None
    selected = read_json(selected_path)
    return {"round_id": round_id, "selected": selected, "leaves_meta": leaves_meta}


@router.get("/{round_id}/analysis/latest", summary="Latest analysis result")
def get_latest_analysis(round_id: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    path = os.path.join(rdir, "analysis", "latest.json")
    if not os.path.isfile(path):
        raise HTTPException(404, "Analysis not found")
    return read_json(path)


@router.get("/{round_id}/analysis/history", summary="Analysis history entries")
def get_analysis_history(round_id: str, limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    index_path = os.path.join(rdir, "analysis", "history", "index.json")
    if not os.path.isfile(index_path):
        return {"round_id": round_id, "entries": []}
    idx = read_json(index_path)
    entries = idx.get("entries", [])
    if limit:
        entries = entries[-limit:]
    return {"round_id": round_id, "entries": entries}


@router.get(
    "/{round_id}/analysis/history/{entry}",
    summary="Specific analysis history record",
)
def get_analysis_history_entry(round_id: str, entry: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    history_dir = os.path.join(rdir, "analysis", "history")
    if not os.path.isdir(history_dir):
        raise HTTPException(404, "Analysis history not found")
    fn = entry if entry.endswith(".json") else f"{entry}.json"
    safe_name = os.path.basename(fn)
    path = os.path.join(history_dir, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "History entry not found")
    return read_json(path)


@router.get("/{round_id}/vdf", summary="VDF proof information")
def get_vdf(round_id: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    path = os.path.join(rdir, "vdf", "proof.json")
    if not os.path.isfile(path):
        raise HTTPException(404, "VDF proof not found")
    return read_json(path)


@router.get("/{round_id}/raw/summary", summary="Raw entropy summary")
def get_raw_summary(round_id: str) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    path = os.path.join(rdir, "raw", "summary.json")
    if not os.path.isfile(path):
        raise HTTPException(404, "Raw capture summary not found")
    data = read_json(path)
    data["round_id"] = round_id
    return data


@router.get("/{round_id}/raw/{stream}/{index}", summary="Raw entropy entry")
def get_raw_entry(
    round_id: str,
    stream: str,
    index: int,
    include_raw: bool = Query(False, description="Return base64-encoded raw payload"),
) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    stream_dir = os.path.join(rdir, "raw", stream)
    if not os.path.isdir(stream_dir):
        raise HTTPException(404, "Stream not found")
    meta_path = os.path.join(stream_dir, f"{index}.meta.json")
    if not os.path.isfile(meta_path):
        raise HTTPException(404, "Entry metadata not found")
    meta = read_json(meta_path)
    response = {
        "round_id": round_id,
        "stream": stream,
        "index": index,
        "meta": meta,
    }
    if include_raw:
        raw_path = os.path.join(stream_dir, f"{index}.raw")
        if not os.path.isfile(raw_path):
            raise HTTPException(404, "Raw payload not found")
        raw_bytes = read_bytes(raw_path)
        response["raw_base64"] = base64.b64encode(raw_bytes).decode()
    return response


@router.get("/{round_id}/random-range/history", summary="Random range requests history")
def random_range_history(
    round_id: str,
    limit: int = Query(20, ge=1, le=200),
) -> Dict[str, Any]:
    rdir = round_dir(round_id)
    history_path = os.path.join(rdir, "random_ranges.jsonl")
    if not os.path.isfile(history_path):
        return {"round_id": round_id, "entries": []}
    entries: List[Dict[str, Any]] = []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        raise HTTPException(500, f"Failed to read history: {exc}") from exc
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"round_id": round_id, "entries": entries}
