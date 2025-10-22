from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from ..analysis.randomness import run_basic_tests
from ..analysis.heavy import (
    HeavyTestError,
    load_round_output,
    run_dieharder_on_data,
    store_heavy_test,
)
from ..models import (
    AnalysisOptions,
    AnalysisResult,
    RandomnessTestResult,
    SequenceAnalysisRequest,
    HeavyTestRequest,
    HeavyTestResponse,
)
from ..services.analysis_store import store_round_analysis
from ..storage import DATA_ROOT, read_bytes, round_dir, write_bytes
from ..utils import ensure_dir

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _bits_to_bytes(bit_string: str) -> Tuple[bytes, int]:
    cleaned = "".join(ch for ch in bit_string.strip() if ch in "01")
    if not cleaned:
        raise ValueError("bit string is empty or invalid")
    pad = (-len(cleaned)) % 8
    padded = cleaned + ("0" * pad)
    out = bytearray()
    for i in range(0, len(padded), 8):
        out.append(int(padded[i : i + 8], 2))
    return bytes(out), len(cleaned)


def _build_analysis_result(raw: dict, source: dict) -> AnalysisResult:
    tests = [RandomnessTestResult(**item) for item in raw.get("tests", [])]
    return AnalysisResult(
        bit_length=raw["bit_length"],
        byte_length=raw["byte_length"],
        ones=raw["ones"],
        zeros=raw["zeros"],
        proportion_ones=raw["proportion_ones"],
        longest_run=raw["longest_run"],
        entropy_per_byte=raw.get("entropy_per_byte"),
        tests=tests,
        all_passed=raw["all_passed"],
        source=source,
    )


@router.post("/round/{round_id}", response_model=AnalysisResult)
async def analyze_round(round_id: str, opts: AnalysisOptions):
    rdir = round_dir(round_id)
    if not os.path.isdir(rdir):
        raise HTTPException(404, "Round not found")
    output_path = os.path.join(rdir, "output.bin")
    if not os.path.isfile(output_path):
        raise HTTPException(400, "Round has not been finalized yet")
    data = read_bytes(output_path)
    result_raw = run_basic_tests(data, limit_bits=opts.limit_bits)
    source = {
        "type": "round_output",
        "round_id": round_id,
        "output_path": output_path,
        "limit_bits": opts.limit_bits,
    }
    store_round_analysis(round_id, result_raw, source)
    return _build_analysis_result(result_raw, source)


@router.post("/sequence", response_model=AnalysisResult)
async def analyze_sequence(req: SequenceAnalysisRequest):
    data: bytes
    default_bits: int
    if req.data_hex:
        try:
            data = bytes.fromhex(req.data_hex.strip())
        except ValueError as exc:
            raise HTTPException(400, f"Invalid hex payload: {exc}") from exc
        default_bits = len(data) * 8
    elif req.data_base64:
        try:
            data = base64.b64decode(req.data_base64.strip())
        except Exception as exc:
            raise HTTPException(400, f"Invalid base64 payload: {exc}") from exc
        default_bits = len(data) * 8
    elif req.data_bits:
        try:
            data, default_bits = _bits_to_bytes(req.data_bits)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    elif req.data_numbers is not None:
        if not req.data_numbers:
            raise HTTPException(400, "data_numbers is empty")
        if all(x in (0, 1) for x in req.data_numbers):
            bit_string = "".join("1" if x else "0" for x in req.data_numbers)
            data, default_bits = _bits_to_bytes(bit_string)
        elif all(isinstance(x, int) and 0 <= x <= 255 for x in req.data_numbers):
            data = bytes(req.data_numbers)
            default_bits = len(data) * 8
        else:
            raise HTTPException(
                400, "data_numbers must contain only bytes (0-255) or bit values (0/1)"
            )
    else:
        raise HTTPException(400, "Provide data_hex, data_base64, data_bits, or data_numbers")

    limit = req.limit_bits or default_bits
    result_raw = run_basic_tests(data, limit_bits=limit)
    source = {"type": "inline_sequence", "length_bits": default_bits, "limit_bits": limit}
    return _build_analysis_result(result_raw, source)


@router.post("/round/{round_id}/heavy", response_model=HeavyTestResponse)
async def analyze_heavy(round_id: str, req: HeavyTestRequest):
    try:
        data = load_round_output(round_id)
    except HeavyTestError as exc:
        raise HTTPException(400, str(exc)) from exc

    if req.test != "dieharder":
        raise HTTPException(400, f"Unsupported heavy test: {req.test}")

    try:
        result = run_dieharder_on_data(data, req.dieharder_args)
        path = store_heavy_test(round_id, req.test, {"raw_result": result})
        rel_path = os.path.relpath(path, round_dir(round_id))
        return HeavyTestResponse(
            round_id=round_id,
            test=req.test,
            status="completed",
            result_path=rel_path,
            result=result,
        )
    except HeavyTestError as exc:
        return HeavyTestResponse(round_id=round_id, test=req.test, status="failed", error=str(exc))


@router.post("/upload", response_model=AnalysisResult)
async def analyze_upload(file: UploadFile = File(...), limit_bits: Optional[int] = Query(default=None, ge=8)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    total_bits = len(data) * 8
    limit = limit_bits or total_bits
    result_raw = run_basic_tests(data, limit_bits=limit)
    sha = hashlib.sha3_256(data).hexdigest()
    uploads_dir = os.path.join(DATA_ROOT, "uploads")
    ensure_dir(uploads_dir)
    stored_path = os.path.join(uploads_dir, f"{sha}.bin")
    if not os.path.isfile(stored_path):
        write_bytes(stored_path, data)
    source = {
        "type": "upload",
        "filename": file.filename,
        "sha3_256": sha,
        "stored_path": stored_path,
        "limit_bits": limit,
    }
    return _build_analysis_result(result_raw, source)
