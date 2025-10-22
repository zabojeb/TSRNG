from __future__ import annotations
import httpx
import urllib.parse
from typing import List, Dict, Any

from .util_leaf import CollectedLeaf, leaf_from_bytes


async def coinbase_products(client: httpx.AsyncClient, products: List[str]) -> CollectedLeaf:
    chunks: list[bytes] = []
    results: list[Dict[str, Any]] = []
    headers = {"User-Agent": "tsrng/0.1"}
    for p in products:
        url = f"https://api.exchange.coinbase.com/products/{urllib.parse.quote(p)}/ticker"
        try:
            r = await client.get(url, timeout=10, headers=headers)
            r.raise_for_status()
            chunks.append(r.content)
            results.append({"product": p, "status": "ok", "bytes": len(r.content)})
        except Exception as exc:
            payload = f"err:{p}".encode()
            chunks.append(payload)
            results.append({"product": p, "status": "error", "error": str(exc), "bytes": len(payload)})
    meta = {
        "source": "coinbase_products",
        "products": products,
        "results": results,
        "headers": headers,
    }
    return leaf_from_bytes(b"|".join(chunks), meta)


async def stooq_quotes(client: httpx.AsyncClient, tickers: List[str]) -> CollectedLeaf:
    chunks: list[bytes] = []
    results: list[Dict[str, Any]] = []
    for t in tickers:
        url = f"https://stooq.com/q/l/?s={urllib.parse.quote(t.lower())}&i=d"
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            chunks.append(r.content)
            results.append({"ticker": t, "status": "ok", "bytes": len(r.content)})
        except Exception as exc:
            payload = f"err:{t}".encode()
            chunks.append(payload)
            results.append({"ticker": t, "status": "error", "error": str(exc), "bytes": len(payload)})
    meta = {
        "source": "stooq_quotes",
        "tickers": tickers,
        "results": results,
    }
    return leaf_from_bytes(b"|".join(chunks), meta)


async def fx_exrates(client: httpx.AsyncClient, base: str, symbols: List[str]) -> CollectedLeaf:
    url = "https://api.exchangerate.host/latest"
    params = {"base": base, "symbols": ",".join(symbols)}
    try:
        r = await client.get(url, params=params, timeout=10)
        r.raise_for_status()
        meta = {"source": "fx_exrates", "url": url, "params": params, "status": "ok"}
        return leaf_from_bytes(r.content, meta)
    except Exception as exc:
        meta = {"source": "fx_exrates", "url": url, "params": params, "status": "error", "error": str(exc)}
        return leaf_from_bytes(b"fx_error", meta)
