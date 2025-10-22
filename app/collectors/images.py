from __future__ import annotations
from typing import List, Dict, Any
import httpx

from .util_leaf import CollectedLeaf, leaf_from_bytes


async def image_leaves(client: httpx.AsyncClient, urls: List[str]) -> CollectedLeaf:
    chunks: list[bytes] = []
    entries: list[Dict[str, Any]] = []
    for u in urls:
        try:
            r = await client.get(u, timeout=15)
            r.raise_for_status()
            payload = r.content[:65536]
            chunks.append(payload)
            entries.append({"url": u, "status": "ok", "bytes": len(payload)})
        except Exception as exc:
            payload = ("err:" + u).encode()
            chunks.append(payload)
            entries.append({"url": u, "status": "error", "error": str(exc), "bytes": len(payload)})
    meta = {"source": "image_leaves", "urls": urls, "entries": entries}
    return leaf_from_bytes(b"|".join(chunks), meta)
