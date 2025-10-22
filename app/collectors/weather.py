from __future__ import annotations
from typing import List, Tuple, Dict, Any
import httpx

from .util_leaf import CollectedLeaf, leaf_from_bytes

DEFAULT_LOCS: list[tuple[float, float, str]] = [
    (52.52, 13.41, "Berlin"),
    (48.85, 2.35, "Paris"),
    (51.5074, -0.1278, "London"),
    (40.7128, -74.0060, "NewYork"),
    (34.0522, -118.2437, "LosAngeles"),
    (35.6895, 139.6917, "Tokyo"),
    (55.7558, 37.6173, "Moscow"),
    (28.6139, 77.2090, "Delhi"),
    (19.0760, 72.8777, "Mumbai"),
    (52.3676, 4.9041, "Amsterdam"),
]


async def open_meteo_current(client: httpx.AsyncClient, locs: List[Tuple[float, float, str]] = DEFAULT_LOCS) -> CollectedLeaf:
    chunks: list[bytes] = []
    entries: list[Dict[str, Any]] = []
    for lat, lon, name in locs:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,wind_speed_10m,relative_humidity_2m"}
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            payload = (name + ":").encode() + r.content
            chunks.append(payload)
            entries.append({"location": name, "status": "ok", "bytes": len(payload)})
        except Exception as exc:
            payload = (name + ":err").encode()
            chunks.append(payload)
            entries.append({"location": name, "status": "error", "error": str(exc), "bytes": len(payload)})
    meta = {
        "source": "open_meteo_current",
        "locations": [{"lat": lat, "lon": lon, "name": name} for lat, lon, name in locs],
        "entries": entries,
    }
    return leaf_from_bytes(b"|".join(chunks), meta)
