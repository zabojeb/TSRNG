# app/routers/sources.py
from __future__ import annotations

import asyncio
import base64
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..collectors import beacons as B, images as I, quotes as Q, textfeeds as T, weather as W
from ..collectors.util_leaf import LEAF_SIZE, CollectedLeaf, leaf_from_bytes
from ..models import CommitRequest, CommitResponse
from ..services.rounds import commit_round
from ..storage import read_json, round_dir, write_bytes, write_json
from ..utils import ensure_dir, now_iso


def normalize_locs(raw: Any, default):
    if raw is None:
        return default

    if isinstance(raw, (list, tuple)) and len(raw) == 2 and all(isinstance(x, (int, float)) for x in raw):
        lat, lon = float(raw[0]), float(raw[1])
        return [(lat, lon, "loc0")]

    out = []
    if isinstance(raw, (list, tuple)):
        for i, item in enumerate(raw):
            if isinstance(item, dict):
                lat = item.get("lat") or item.get("latitude")
                lon = item.get("lon") or item.get("lng") or item.get("longitude")
                name = item.get("name") or item.get("label") or f"loc{i}"
                if lat is None or lon is None:
                    continue
                out.append((float(lat), float(lon), str(name)))
                continue
            if isinstance(item, (list, tuple)):
                if len(item) >= 2:
                    lat = float(item[0])
                    lon = float(item[1])
                    name = str(item[2]) if len(item) >= 3 else f"loc{i}"
                    out.append((lat, lon, name))
        if out:
            return out
    return default


def pad_leaves(leaves: List[CollectedLeaf], target: int) -> List[CollectedLeaf]:
    if target <= 0:
        return []
    if not leaves:
        return []
    if len(leaves) >= target:
        return [leaf.clone() for leaf in leaves[:target]]
    out: List[CollectedLeaf] = []
    while len(out) < target:
        for leaf in leaves:
            out.append(leaf.clone())
            if len(out) >= target:
                break
    return out


router = APIRouter(prefix="/sources", tags=["sources"])


class CollectConfig(BaseModel):
    round_label: str = "tsrng"
    leaf_size_bytes: int = LEAF_SIZE
    counts: Dict[str, int] = {"beacons": 8, "quotes": 32, "weather": 16, "text": 16, "images": 8}
    beacons: Dict[str, List[str]] = {"generic": []}
    quotes: Dict[str, List[str]] = {
        "coinbase": ["BTC-USD", "ETH-USD"],
        "stooq": ["AAPL.US", "MSFT.US", "GOOGL.US"],
        "fx_base": ["USD"],
        "fx_symbols": ["EUR", "GBP", "JPY", "RUB"],
    }
    weather_locations: Optional[List[List[float]]] = None
    textfeeds: Dict[str, int] = {"wikipedia_en_limit": 100, "github_events": 100}
    images: List[str] = []
    persist_raw: bool = True


async def gather_beacons(client: httpx.AsyncClient, cfg: CollectConfig) -> List[CollectedLeaf]:
    out: List[CollectedLeaf] = []
    try:
        out.append(await B.drand_quicknet_latest(client))
    except Exception as exc:
        out.append(leaf_from_bytes(b"drand_err", {"source": "drand_quicknet_latest", "error": str(exc)}))
    try:
        out.append(await B.nist_beacon_last(client))
    except Exception as exc:
        out.append(leaf_from_bytes(b"nist_err", {"source": "nist_beacon_last", "error": str(exc)}))
    if cfg.beacons and cfg.beacons.get("generic"):
        out.extend(await B.generic_beacons(client, cfg.beacons["generic"]))
    return pad_leaves(out, cfg.counts.get("beacons", 0))


async def gather_quotes(client: httpx.AsyncClient, cfg: CollectConfig) -> List[CollectedLeaf]:
    out: List[CollectedLeaf] = []
    if "coinbase" in cfg.quotes:
        out.append(await Q.coinbase_products(client, cfg.quotes["coinbase"]))
    if "stooq" in cfg.quotes:
        out.append(await Q.stooq_quotes(client, cfg.quotes["stooq"]))
    base = cfg.quotes.get("fx_base", ["USD"])[0]
    symbols = cfg.quotes.get("fx_symbols", ["EUR", "GBP", "JPY"])
    out.append(await Q.fx_exrates(client, base, symbols))
    return pad_leaves(out, cfg.counts.get("quotes", 0))


async def gather_weather(client: httpx.AsyncClient, cfg: CollectConfig) -> List[CollectedLeaf]:
    locs = normalize_locs(cfg.weather_locations, W.DEFAULT_LOCS)
    leaf = await W.open_meteo_current(client, locs)
    return pad_leaves([leaf], cfg.counts.get("weather", 0))


async def gather_text(client: httpx.AsyncClient, cfg: CollectConfig) -> List[CollectedLeaf]:
    out: List[CollectedLeaf] = []
    try:
        out.append(await T.wikipedia_recent_changes(client, "en", limit=cfg.textfeeds.get("wikipedia_en_limit", 50)))
    except Exception as exc:
        out.append(leaf_from_bytes(b"wikipedia_err", {"source": "wikipedia_recent_changes", "error": str(exc)}))
    try:
        out.append(await T.github_public_events(client, per_page=cfg.textfeeds.get("github_events", 50)))
    except Exception as exc:
        out.append(leaf_from_bytes(b"github_err", {"source": "github_public_events", "error": str(exc)}))
    return pad_leaves(out, cfg.counts.get("text", 0))


async def gather_images(client: httpx.AsyncClient, cfg: CollectConfig) -> List[CollectedLeaf]:
    if cfg.images:
        leaf = await I.image_leaves(client, cfg.images)
        return pad_leaves([leaf], cfg.counts.get("images", 0))
    return []


def persist_raw_payloads(round_id: str, collected: Dict[str, List[CollectedLeaf]]) -> None:
    rdir = round_dir(round_id)
    raw_root = os.path.join(rdir, "raw")
    ensure_dir(raw_root)

    summary: Dict[str, Any] = {"streams": {}, "generated_iso": now_iso()}

    for stream, leaves in collected.items():
        sdir = os.path.join(raw_root, stream)
        ensure_dir(sdir)
        entries: List[Dict[str, Any]] = []
        for idx, leaf in enumerate(leaves):
            write_bytes(os.path.join(sdir, f"{idx}.raw"), leaf.raw)
            leaf_meta = dict(leaf.meta)
            leaf_meta.setdefault("hash_hex", leaf.hash_hex())
            leaf_meta.setdefault("raw_size", len(leaf.raw))
            write_json(os.path.join(sdir, f"{idx}.meta.json"), leaf_meta)
            entries.append(
                {
                    "index": idx,
                    "hash_hex": leaf.hash_hex(),
                    "raw_size": len(leaf.raw),
                    "meta_path": f"{stream}/{idx}.meta.json",
                    "raw_path": f"{stream}/{idx}.raw",
                }
            )
        summary["streams"][stream] = {
            "count": len(leaves),
            "entries": entries,
        }

    write_json(os.path.join(raw_root, "summary.json"), summary)

    manifest_path = os.path.join(rdir, "manifest.json")
    manifest = read_json(manifest_path)
    manifest["raw_capture"] = {
        "available": True,
        "stream_counts": {k: len(v) for k, v in collected.items()},
        "summary_path": "raw/summary.json",
    }
    write_json(manifest_path, manifest)


@router.post("/collect-and-commit", response_model=CommitResponse)
async def collect_and_commit(cfg: CollectConfig):
    collected_streams: Dict[str, List[CollectedLeaf]] = {}

    async with httpx.AsyncClient() as client:
        bea, quo, wea, tex, img = await asyncio.gather(
            gather_beacons(client, cfg),
            gather_quotes(client, cfg),
            gather_weather(client, cfg),
            gather_text(client, cfg),
            gather_images(client, cfg),
        )

    def adjust(leaves: List[CollectedLeaf]) -> List[CollectedLeaf]:
        return [leaf.with_leaf_size(cfg.leaf_size_bytes) for leaf in leaves]

    if bea:
        collected_streams["beacons"] = adjust(bea)
    if quo:
        collected_streams["quotes"] = adjust(quo)
    if wea:
        collected_streams["weather"] = adjust(wea)
    if tex:
        collected_streams["text"] = adjust(tex)
    if img:
        collected_streams["images"] = adjust(img)

    if not collected_streams:
        raise HTTPException(400, "No leaves collected; adjust config.")

    leaves_streams: Dict[str, List[str]] = {
        stream: [leaf.to_b64() for leaf in leaves] for stream, leaves in collected_streams.items()
    }

    req = CommitRequest(round_label=cfg.round_label, streams=leaves_streams, leaf_size_bytes=cfg.leaf_size_bytes)
    commit_resp = commit_round(req)

    if cfg.persist_raw:
        persist_raw_payloads(commit_resp.round_id, collected_streams)

    return commit_resp
