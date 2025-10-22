
from __future__ import annotations
import httpx
from .util_leaf import CollectedLeaf, leaf_from_bytes

async def wikipedia_recent_changes(client: httpx.AsyncClient, lang="en", limit=50) -> CollectedLeaf:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action":"query",
        "list":"recentchanges",
        "rcprop":"title|ids|sizes|flags|user|timestamp|comment",
        "rcshow":"!bot",
        "rclimit": str(limit),
        "format":"json",
    }
    r = await client.get(url, params=params, timeout=10)
    r.raise_for_status()
    meta = {"source": "wikipedia_recent_changes", "url": url, "params": params}
    return leaf_from_bytes(r.content, meta)

async def github_public_events(client: httpx.AsyncClient, per_page=50) -> CollectedLeaf:
    url = "https://api.github.com/events"
    headers = {"Accept":"application/vnd.github+json","User-Agent":"tsrng/0.1"}
    params = {"per_page": str(per_page)}
    r = await client.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    meta = {"source": "github_public_events", "url": url, "params": params, "headers": headers}
    return leaf_from_bytes(r.content, meta)
