# app/services/rounds.py
from __future__ import annotations
import os
from typing import Dict, List
from ..models import CommitRequest, CommitResponse
from ..utils import now_iso, b64d, ensure_dir, parse_seed, sha3_512, hkdf_sha3
from ..merkle import build_merkle
from ..storage import new_round_dir, write_json, write_bytes, round_dir, read_json, read_bytes


def commit_round(req: CommitRequest) -> CommitResponse:
    rid, rdir = new_round_dir()
    t0 = now_iso()

    # decode leaves
    streams: Dict[str, List[bytes]] = {}
    for s, arr in req.streams.items():
        dec = [b64d(x) for x in arr]
        if any(len(b) != req.leaf_size_bytes for b in dec):
            raise ValueError(f"Leaf size mismatch in stream '{s}'")
        streams[s] = dec

    # flatten for Merkle
    leaves_data: List[bytes] = []
    index_map: Dict[str, List[int]] = {}
    for s, arr in streams.items():
        index_map[s] = list(
            range(len(leaves_data), len(leaves_data) + len(arr)))
        leaves_data.extend(arr)

    root_hash, levels = build_merkle(leaves_data)

    # persist leaves per stream
    for s, arr in streams.items():
        sdir = os.path.join(rdir, "leaves", s)
        ensure_dir(sdir)
        for i, b in enumerate(arr):
            write_bytes(os.path.join(sdir, f"{i}.leaf"), b)

    # meta
    write_bytes(os.path.join(rdir, "merkle_root.bin"), root_hash)
    write_json(os.path.join(rdir, "index_map.json"), index_map)
    write_json(os.path.join(rdir, "levels_meta.json"), {
               "levels": len(levels), "leaf_count": len(levels[0])})

    manifest = {
        "round_id": rid,
        "round_label": req.round_label,
        "t0_iso": t0,
        "merkle_root_hex": root_hash.hex(),
        "leaf_size_bytes": req.leaf_size_bytes,
        "streams": {k: len(v) for k, v in streams.items()},
        "storage_dir": rdir,
    }
    write_json(os.path.join(rdir, "manifest.json"), manifest)

    return CommitResponse(
        round_id=rid,
        merkle_root_hex=manifest["merkle_root_hex"],
        t0_iso=t0,
        manifest=manifest,
    )


def derive_round_output(round_id: str, output_bits: int) -> bytes:
    rdir = round_dir(round_id)
    manifest_path = os.path.join(rdir, "manifest.json")
    selected_path = os.path.join(rdir, "selected.json")
    if not os.path.isfile(manifest_path) or not os.path.isfile(selected_path):
        raise ValueError("Round is not finalized")
    manifest = read_json(manifest_path)
    if "S_hex" not in manifest and "S_canonical_hex" not in manifest:
        raise ValueError("Round does not have a beacon seed")
    selected = read_json(selected_path).get("indices") or {}
    leaves: list[bytes] = []
    for stream, idxs in selected.items():
        for idx in idxs:
            path = os.path.join(rdir, "leaves", stream, f"{idx}.leaf")
            if not os.path.isfile(path):
                raise ValueError(f"Missing leaf file for {stream}:{idx}")
            leaves.append(read_bytes(path))
    if not leaves:
        raise ValueError("No selected leaves available")
    r_raw = sha3_512(b"".join(leaves))
    S = parse_seed(manifest.get("S_canonical_hex") or manifest.get("S_hex") or "")
    return hkdf_sha3(r_raw, S, length=(output_bits + 7) // 8)
