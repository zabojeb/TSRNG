
from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class CommitRequest(BaseModel):
    round_label: str = "demo"
    streams: Dict[str, List[str]]
    leaf_size_bytes: int = Field(ge=1, default=64)

class CommitResponse(BaseModel):
    round_id: str
    merkle_root_hex: str
    t0_iso: str
    manifest: dict

class DemoCommitRequest(BaseModel):
    round_label: str = "demo"
    streams: List[str] = ["video","text","num"]
    leaves_per_stream: int = 64
    leaf_size_bytes: int = 64

class BeaconRequest(BaseModel):
    S_hex: str
    vdf_T: int = 50
    modulus_bits: int = 512

class BeaconResponse(BaseModel):
    round_id: str
    S_hex: str
    vdf_T: int
    modulus_bits: int
    p_hex: str
    y_hex: str
    t1_iso: str

class FinalizeRequest(BaseModel):
    output_bits: int = 512
    quotas: Optional[Dict[str, float]] = None

class FinalizeResponse(BaseModel):
    round_id: str
    output_hex: str
    selected_indices: dict
    t2_iso: str
    analysis: Optional["AnalysisResult"] = None

class StatusResponse(BaseModel):
    round_id: str
    stage: Literal["committed","beaconed","finalized"]
    info: dict


class AnalysisOptions(BaseModel):
    limit_bits: Optional[int] = Field(default=None, ge=8)


class SequenceAnalysisRequest(BaseModel):
    data_hex: Optional[str] = None
    data_base64: Optional[str] = None
    data_bits: Optional[str] = None
    data_numbers: Optional[List[int]] = None
    limit_bits: Optional[int] = Field(default=None, ge=8)


class RandomnessTestResult(BaseModel):
    name: str
    passed: bool
    p_value: Optional[float] = None
    statistic: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None


class AnalysisResult(BaseModel):
    bit_length: int
    byte_length: int
    ones: int
    zeros: int
    proportion_ones: float
    longest_run: int
    entropy_per_byte: Optional[float] = None
    tests: List[RandomnessTestResult]
    all_passed: bool
    source: Dict[str, Any] = Field(default_factory=dict)


class BitstringExportRequest(BaseModel):
    bits: int = Field(default=1_000_000, ge=1, le=8_000_000)
    refresh_artifact: bool = True


class BitstringExportResponse(BaseModel):
    round_id: str
    bits: int
    file_path: str
    artifact_path: Optional[str] = None


class RandomRangeRequest(BaseModel):
    start: int
    end: int
    count: int = Field(ge=1)
    domain: Optional[str] = "default"
    context: Optional[str] = None
    salt_hex: Optional[str] = None


class RandomRangeResponse(BaseModel):
    round_id: str
    start: int
    end: int
    count: int
    numbers: List[int]
    domain: str
    context: Optional[str] = None
    info: Dict[str, Any]


class HeavyTestRequest(BaseModel):
    test: Literal["dieharder"] = "dieharder"
    dieharder_args: Optional[List[str]] = None


class HeavyTestResponse(BaseModel):
    round_id: str
    test: str
    status: Literal["queued", "running", "completed", "failed"]
    result_path: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


FinalizeResponse.model_rebuild()
