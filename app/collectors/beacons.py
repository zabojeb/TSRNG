from __future__ import annotations
from typing import Tuple, List
import httpx

from .util_leaf import CollectedLeaf, leaf_from_bytes


async def fetch_json(client: httpx.AsyncClient, url: str) -> Tuple[bytes, dict]:
    r = await client.get(url, timeout=10)
    r.raise_for_status()
    return r.content, {"status_code": r.status_code}


async def drand_quicknet_latest(client: httpx.AsyncClient) -> CollectedLeaf:
    url = "https://api.drand.sh/v2/beacons/quicknet/rounds/latest"
    raw, meta = await fetch_json(client, url)
    meta.update({"source": "drand_quicknet_latest", "url": url})
    return leaf_from_bytes(raw, meta)


async def nist_beacon_last(client: httpx.AsyncClient) -> CollectedLeaf:
    urls = [
        "https://beacon.nist.gov/beacon/2.0/pulse/last",
        "https://beacon.nist.gov/beacon/2.0/chain/1/last",
    ]
    last_error: str | None = None
    for url in urls:
        try:
            raw, meta = await fetch_json(client, url)
            meta.update({"source": "nist_beacon_last", "url": url})
            return leaf_from_bytes(raw, meta)
        except Exception as exc:
            last_error = str(exc)
            continue
    return leaf_from_bytes(
        b"nist_unavailable",
        {"source": "nist_beacon_last", "error": last_error or "unreachable", "urls": urls},
    )


async def generic_beacons(client: httpx.AsyncClient, urls: List[str]) -> List[CollectedLeaf]:
    out: List[CollectedLeaf] = []
    for u in urls:
        try:
            raw, meta = await fetch_json(client, u)
            meta.update({"source": "generic_beacon", "url": u})
            out.append(leaf_from_bytes(raw, meta))
        except Exception as exc:
            out.append(
                leaf_from_bytes(
                    f"error:{u}".encode(),
                    {"source": "generic_beacon", "url": u, "error": str(exc)},
                )
            )
    return out
