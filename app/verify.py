from __future__ import annotations

import json
import zipfile
from typing import Dict, Tuple

from .merkle import verify_proof
from .utils import hkdf_sha3, parse_seed, sha3_512
from .vdf import derive_prime, int_from_seed, vdf_verify_sloth


def verify_package(zip_path: str) -> Tuple[bool, str]:
    with zipfile.ZipFile(zip_path, "r") as z:
        try:
            manifest = json.loads(z.read("manifest.json"))
            merkle_root = bytes.fromhex(manifest["merkle_root_hex"])
            _ = json.loads(z.read("leaves_meta.json"))
            selected = json.loads(z.read("selected.json"))
            out_bytes = z.read("output.bin")
        except KeyError as e:
            return False, f"Missing entry in zip: {e}"

        S = parse_seed(manifest.get("S_canonical_hex") or manifest.get("S_hex") or "")

        try:
            vdf_info = json.loads(z.read("vdf/proof.json"))
        except KeyError:
            return False, "Missing VDF proof"

        p = int(vdf_info["p_hex"], 16)
        y = int(vdf_info["y_hex"], 16)
        T = int(vdf_info["T"])
        expected_prime = derive_prime(b"TSRNG/modulus/" + S, bits=manifest.get("modulus_bits") or p.bit_length())
        if p != expected_prime:
            return False, "VDF prime mismatch"
        x = int_from_seed(S, p)
        if not vdf_verify_sloth(x, y, T, p):
            return False, "VDF verification failed"
        if vdf_info.get("S_hex") and vdf_info["S_hex"].lower().lstrip("0x") != S.hex():
            return False, "Seed mismatch between manifest and VDF proof"

        leaf_cache: Dict[tuple[str, int], bytes] = {}
        for stream, idxs in selected["indices"].items():
            for i in idxs:
                idx_int = int(i)
                leaf_b = z.read(f"leaves/{stream}/{idx_int}.leaf")
                proof = json.loads(z.read(f"proofs/{stream}/{idx_int}.proof"))
                siblings = [(bytes.fromhex(h), d) for h, d in proof]
                if not verify_proof(leaf_b, siblings, merkle_root):
                    return False, f"Merkle proof failed for {stream}:{idx_int}"
                leaf_cache[(stream, idx_int)] = leaf_b

        flat_leaves = [leaf_cache[(stream, int(i))] for stream, idxs in selected["indices"].items() for i in idxs]
        r_raw = sha3_512(b"".join(flat_leaves))
        expected = hkdf_sha3(r_raw, S, len(out_bytes))
        if expected != out_bytes:
            return False, "Extractor mismatch"

        raw_verified = False
        leaf_size = int(manifest.get("leaf_size_bytes", len(flat_leaves[0]) if flat_leaves else 0))
        try:
            _ = json.loads(z.read("raw/summary.json"))
            raw_available = True
        except KeyError:
            raw_available = False

        if raw_available:
            for (stream, idx), stored_leaf in leaf_cache.items():
                raw_name = f"raw/{stream}/{idx}.raw"
                meta_name = f"raw/{stream}/{idx}.meta.json"
                try:
                    raw_bytes = z.read(raw_name)
                    raw_meta = json.loads(z.read(meta_name))
                except KeyError as exc:
                    return False, f"Missing raw payload entry: {exc}"
                derived_leaf = sha3_512(raw_bytes)[:leaf_size]
                if derived_leaf != stored_leaf:
                    return False, f"Raw payload hash mismatch for {stream}:{idx}"
                meta_hash = raw_meta.get("leaf_hash_hex")
                if meta_hash and bytes.fromhex(meta_hash) != stored_leaf:
                    return False, f"Metadata hash mismatch for {stream}:{idx}"
            raw_verified = True

        msg = "OK (raw verified)" if raw_verified else "OK"
        return True, msg
