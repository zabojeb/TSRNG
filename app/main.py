from __future__ import annotations
from .routers.sources import router as sources_router
from .routers.analysis import router as analysis_router
from .routers.transparency import router as transparency_router
from .services.rounds import commit_round
from .services.analysis_store import store_round_analysis
from .analysis.randomness import run_basic_tests
import os
import base64
import json
from fastapi import FastAPI, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from .models import *
from .utils import now_iso, b64d, sha3_256, sha3_512, hkdf_sha3, ensure_dir, parse_seed
from .merkle import build_merkle, merkle_proof
from .vdf import derive_prime, vdf_encode_sloth
from .indexing import unique_indices, unique_range
from .storage import new_round_dir, round_dir, write_json, write_bytes, read_json, read_bytes, zip_dir
from .verify import verify_package

# ВАЖНО: импортируем роутер ПОСЛЕ объявления app, и НЕТ обратного импорта из роутера сюда
app = FastAPI(title="TSRNG (Time-Sandwich RNG) — MVP", version="0.1.0")

# >>> добавляем сервис и роутер
app.include_router(sources_router)
app.include_router(analysis_router)
app.include_router(transparency_router)
# <<<


@app.get("/")
def root():
    return {"name": "TSRNG FastAPI MVP", "version": "0.1.0"}

# Заменяем прямую реализацию на вызов сервисной функции


@app.post("/rounds/commit", response_model=CommitResponse)
def commit(req: CommitRequest):
    try:
        return commit_round(req)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/rounds/demo/commit", response_model=CommitResponse)
def demo_commit(req: DemoCommitRequest):
    streams: dict[str, list[str]] = {}
    for s in req.streams:
        arr = [os.urandom(req.leaf_size_bytes)
               for _ in range(req.leaves_per_stream)]
        streams[s] = [base64.b64encode(x).decode() for x in arr]
    return commit(CommitRequest(round_label=req.round_label, streams=streams, leaf_size_bytes=req.leaf_size_bytes))


@app.post("/rounds/{round_id}/beacon", response_model=BeaconResponse)
def beacon(round_id: str, req: BeaconRequest, background_tasks: BackgroundTasks):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")

    try:
        S = parse_seed(req.S_hex)
    except ValueError as e:
        raise HTTPException(400, f"Invalid seed format: {e}. "
                            f"Allowed: hex (with/without 0x), base64/base64url, or JSON from drand/NIST.")

    t1 = now_iso()

    p = derive_prime(b"TSRNG/modulus/" + S, bits=req.modulus_bits)
    x = int.from_bytes(sha3_256(S), "big") % p
    y = vdf_encode_sloth(x, req.vdf_T, p)

    vdf_info = {"S_hex": req.S_hex, "T": req.vdf_T, "p_hex": format(
        p, "x"), "y_hex": format(y, "x"), "t1_iso": t1}
    ensure_dir(os.path.join(rdir, "vdf"))
    write_json(os.path.join(rdir, "vdf", "proof.json"), vdf_info)

    manifest = read_json(os.path.join(rdir, "manifest.json"))
    manifest.update({
        "S_hex": req.S_hex,                      # как прислали (для аудита)
        "S_canonical_hex": S.hex(),              # канонический hex
        "t1_iso": t1,
        "vdf_T": req.vdf_T,
        "modulus_bits": req.modulus_bits
    })
    write_json(os.path.join(rdir, "manifest.json"), manifest)

    return BeaconResponse(round_id=round_id, S_hex=req.S_hex, vdf_T=req.vdf_T, modulus_bits=req.modulus_bits,
                          p_hex=vdf_info["p_hex"], y_hex=vdf_info["y_hex"], t1_iso=t1)


@app.post("/rounds/{round_id}/finalize", response_model=FinalizeResponse)
def finalize(round_id: str, req: FinalizeRequest):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")

    manifest = read_json(os.path.join(rdir, "manifest.json"))
    if "S_hex" not in manifest:
        raise HTTPException(400, "Beacon not set")

    index_map = read_json(os.path.join(rdir, "index_map.json"))
    all_streams = list(index_map.keys())

    leaves_linear: list[bytes] = []
    stream_offsets: dict[str, int] = {}
    off = 0
    for s in all_streams:
        stream_offsets[s] = off
        sdir = os.path.join(rdir, "leaves", s)
        count = len(os.listdir(sdir))
        for i in range(count):
            leaves_linear.append(read_bytes(os.path.join(sdir, f"{i}.leaf")))
        off += count

    root_hash, levels = build_merkle(leaves_linear)
    stored_root = bytes.fromhex(manifest["merkle_root_hex"])
    if root_hash != stored_root:
        raise HTTPException(500, "Merkle root mismatch")

    S = parse_seed(manifest.get("S_canonical_hex") or manifest.get("S_hex") or "")

    root = stored_root
    quotas = req.quotas or {s: 1.0 / len(all_streams) for s in all_streams}
    leaf_size = manifest["leaf_size_bytes"]
    bits_per_leaf = leaf_size * 8
    need_leaves = max(1, (req.output_bits + bits_per_leaf - 1) // bits_per_leaf)

    selected: dict[str, list[int]] = {}
    for s in all_streams:
        M = len(os.listdir(os.path.join(rdir, "leaves", s)))
        if M == 0:
            selected[s] = []
            continue
        cnt = max(1, int(need_leaves * quotas.get(s, 0)))
        if cnt > M:
            cnt = M
        idxs = unique_indices(
            cnt, M, domain=b"TSRNG/idx/" + s.encode(), S=S, root=root)
        selected[s] = idxs

    proofs_dir = os.path.join(rdir, "proofs")
    ensure_dir(proofs_dir)

    selected_chunks: list[bytes] = []
    for s, idxs in selected.items():
        sdir = os.path.join(rdir, "leaves", s)
        pdir = os.path.join(proofs_dir, s)
        ensure_dir(pdir)
        for i in idxs:
            leaf_b = read_bytes(os.path.join(sdir, f"{i}.leaf"))
            from .merkle import merkle_proof
            global_index = stream_offsets[s] + i
            proof = merkle_proof(levels, global_index)
            proof_json = [(h.hex(), d) for (h, d) in proof]
            from .storage import write_json
            write_json(os.path.join(pdir, f"{i}.proof"), proof_json)
            selected_chunks.append(leaf_b)

    r_raw = sha3_512(b"".join(selected_chunks))
    out_bytes = hkdf_sha3(r_raw, salt=S, length=(req.output_bits + 7)//8)
    write_bytes(os.path.join(rdir, "output.bin"), out_bytes)

    leaves_meta = {s: len(os.listdir(os.path.join(rdir, "leaves", s)))
                   for s in all_streams}
    write_json(os.path.join(rdir, "leaves_meta.json"), leaves_meta)
    write_json(os.path.join(rdir, "selected.json"), {"indices": selected})

    analysis_raw = run_basic_tests(out_bytes, limit_bits=req.output_bits)
    analysis_source = {
        "type": "finalize",
        "round_id": round_id,
        "limit_bits": req.output_bits,
        "selected_counts": {s: len(idxs) for s, idxs in selected.items()},
    }
    store_round_analysis(round_id, analysis_raw, analysis_source)
    analysis_model = AnalysisResult(
        bit_length=analysis_raw["bit_length"],
        byte_length=analysis_raw["byte_length"],
        ones=analysis_raw["ones"],
        zeros=analysis_raw["zeros"],
        proportion_ones=analysis_raw["proportion_ones"],
        longest_run=analysis_raw["longest_run"],
        entropy_per_byte=analysis_raw.get("entropy_per_byte"),
        tests=[RandomnessTestResult(**item) for item in analysis_raw.get("tests", [])],
        all_passed=analysis_raw["all_passed"],
        source=analysis_source,
    )

    dist = os.path.join(rdir, "artifact")
    ensure_dir(dist)
    import shutil
    shutil.copy(os.path.join(rdir, "manifest.json"),
                os.path.join(dist, "manifest.json"))
    ensure_dir(os.path.join(dist, "vdf"))
    shutil.copy(os.path.join(rdir, "vdf", "proof.json"),
                os.path.join(dist, "vdf", "proof.json"))
    for s, idxs in selected.items():
        s_leaves_out = os.path.join(dist, "leaves", s)
        s_proofs_out = os.path.join(dist, "proofs", s)
        ensure_dir(s_leaves_out)
        ensure_dir(s_proofs_out)
        for i in idxs:
            shutil.copy(os.path.join(rdir, "leaves", s, f"{i}.leaf"), os.path.join(
                s_leaves_out, f"{i}.leaf"))
            shutil.copy(os.path.join(rdir, "proofs", s, f"{i}.proof"), os.path.join(
                s_proofs_out, f"{i}.proof"))
    raw_src = os.path.join(rdir, "raw")
    if os.path.isdir(raw_src):
        raw_dist = os.path.join(dist, "raw")
        ensure_dir(raw_dist)
        summary_src = os.path.join(raw_src, "summary.json")
        if os.path.isfile(summary_src):
            shutil.copy(summary_src, os.path.join(raw_dist, "summary.json"))
        for s, idxs in selected.items():
            s_raw_src = os.path.join(raw_src, s)
            if not os.path.isdir(s_raw_src):
                continue
            s_raw_dist = os.path.join(raw_dist, s)
            ensure_dir(s_raw_dist)
            for i in idxs:
                for suffix in (".raw", ".meta.json"):
                    src = os.path.join(s_raw_src, f"{i}{suffix}")
                    if os.path.isfile(src):
                        shutil.copy(src, os.path.join(s_raw_dist, f"{i}{suffix}"))
    shutil.copy(os.path.join(rdir, "leaves_meta.json"),
                os.path.join(dist, "leaves_meta.json"))
    shutil.copy(os.path.join(rdir, "selected.json"),
                os.path.join(dist, "selected.json"))
    shutil.copy(os.path.join(rdir, "output.bin"),
                os.path.join(dist, "output.bin"))

    zip_path = os.path.join(rdir, "artifact.zip")
    zip_dir(dist, zip_path)

    t2 = now_iso()
    manifest["t2_iso"] = t2
    manifest["selected_indices"] = selected
    manifest["output_bits"] = req.output_bits
    manifest["output_bytes"] = len(out_bytes)
    manifest["artifact"] = {
        "dir": dist,
        "zip_path": zip_path,
        "raw_exported": os.path.isdir(os.path.join(dist, "raw")),
    }
    write_json(os.path.join(rdir, "manifest.json"), manifest)
    ensure_output_text(round_id, manifest, out_bytes)

    return FinalizeResponse(
        round_id=round_id,
        output_hex=out_bytes.hex(),
        selected_indices=selected,
        t2_iso=t2,
        analysis=analysis_model,
    )


@app.post("/rounds/{round_id}/random-range", response_model=RandomRangeResponse)
def random_range(round_id: str, req: RandomRangeRequest):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")

    if req.end < req.start:
        raise HTTPException(400, "end must be >= start")

    manifest = read_json(os.path.join(rdir, "manifest.json"))
    seed_hex = manifest.get("S_canonical_hex") or manifest.get("S_hex")
    if not seed_hex:
        raise HTTPException(400, "Beacon not set for this round")

    range_size = req.end - req.start + 1
    if req.count > range_size:
        raise HTTPException(400, "count cannot exceed range size")

    try:
        S = parse_seed(seed_hex)
    except ValueError as exc:
        raise HTTPException(500, f"Failed to parse seed: {exc}") from exc

    try:
        root = bytes.fromhex(manifest["merkle_root_hex"])
    except KeyError:
        raise HTTPException(500, "Manifest missing merkle_root_hex")
    except ValueError as exc:
        raise HTTPException(500, f"Invalid merkle root hex: {exc}") from exc

    domain_parts = [b"TSRNG/range", round_id.encode()]
    domain_label = (req.domain or "default").encode()
    domain_parts.append(domain_label)
    if req.context:
        domain_parts.append(req.context.encode())
    if req.salt_hex:
        try:
            salt_bytes = bytes.fromhex(req.salt_hex)
        except ValueError as exc:
            raise HTTPException(400, f"Invalid salt_hex: {exc}") from exc
        domain_parts.append(salt_bytes)
    domain_bytes = b"|".join(domain_parts)

    try:
        numbers = unique_range(req.count, req.start, req.end, domain_bytes, S, root)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    info = {
        "seed_hex": seed_hex,
        "merkle_root_hex": manifest["merkle_root_hex"],
        "domain_hex": domain_bytes.hex(),
        "range_size": range_size,
    }
    if req.salt_hex:
        info["salt_hex"] = req.salt_hex.lower()

    history_path = os.path.join(rdir, "random_ranges.jsonl")
    entry = {
        "round_id": round_id,
        "requested_at": now_iso(),
        "start": req.start,
        "end": req.end,
        "count": req.count,
        "numbers": numbers,
        "domain_hex": domain_bytes.hex(),
        "domain": req.domain or "default",
        "context": req.context,
        "salt_hex": req.salt_hex.lower() if req.salt_hex else None,
    }
    try:
        with open(history_path, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")
    except Exception:
        # не прерываем выдачу результата, но сохраняем информацию в ответе
        info["history_write_failed"] = True
    else:
        info["history_path"] = history_path

    return RandomRangeResponse(
        round_id=round_id,
        start=req.start,
        end=req.end,
        count=req.count,
        numbers=numbers,
        domain=req.domain or "default",
        context=req.context,
        info=info,
    )


def ensure_output_text(round_id: str, manifest: dict | None = None, out_bytes: bytes | None = None) -> str:
    rdir = round_dir(round_id)
    txt_path = os.path.join(rdir, "output_bits.txt")
    if manifest is None:
        manifest = read_json(os.path.join(rdir, "manifest.json"))
    output_bits = int(manifest.get("output_bits") or 0)
    bin_path = os.path.join(rdir, "output.bin")
    if out_bytes is None:
        out_bytes = read_bytes(bin_path)
    if output_bits <= 0:
        output_bits = len(out_bytes) * 8

    if os.path.isfile(txt_path):
        try:
            if os.path.getsize(txt_path) >= output_bits:
                return txt_path
        except OSError:
            pass

    bits_written = 0
    buffer: list[str] = []
    flush_threshold = 8192
    with open(txt_path, "w", encoding="utf-8") as f:
        for byte in out_bytes:
            for bit in range(7, -1, -1):
                if bits_written >= output_bits:
                    break
                buffer.append("1" if (byte >> bit) & 1 else "0")
                bits_written += 1
                if len(buffer) >= flush_threshold:
                    f.write("".join(buffer))
                    buffer.clear()
            if bits_written >= output_bits:
                break
        if buffer:
            f.write("".join(buffer))
    return txt_path


@app.get("/rounds/{round_id}/output.txt")
def get_output_text(round_id: str):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")
    manifest = read_json(os.path.join(rdir, "manifest.json"))
    if "t2_iso" not in manifest:
        raise HTTPException(400, "Round not finalized yet")
    txt_path = ensure_output_text(round_id, manifest=manifest)
    return FileResponse(txt_path, media_type="text/plain", filename=f"tsrng_round_{round_id}_bits.txt")


@app.get("/rounds/{round_id}/package.zip")
def get_package(round_id: str):
    rdir = round_dir(round_id)
    zip_path = os.path.join(rdir, "artifact.zip")
    if not os.path.isfile(zip_path):
        raise HTTPException(404, "Package not found; finalize the round first")
    return FileResponse(zip_path, media_type="application/zip", filename=f"tsrng_round_{round_id}.zip")


@app.get("/rounds/{round_id}/status", response_model=StatusResponse)
def status(round_id: str):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")
    manifest = read_json(os.path.join(rdir, "manifest.json"))
    if "t2_iso" in manifest:
        stage = "finalized"
    elif "S_hex" in manifest:
        stage = "beaconed"
    else:
        stage = "committed"
    return StatusResponse(round_id=round_id, stage=stage, info=manifest)


@app.post("/verify")
def verify(upload: UploadFile):
    import tempfile
    import os
    if not upload.filename.endswith(".zip"):
        raise HTTPException(400, "Please upload a .zip package")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
        data = upload.file.read()
        f.write(data)
        tmp = f.name
    ok, msg = verify_package(tmp)
    os.unlink(tmp)
    return {"ok": ok, "message": msg}
