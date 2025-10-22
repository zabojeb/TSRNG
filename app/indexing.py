from __future__ import annotations

import hashlib
from typing import List


def prng_blocks(domain: bytes, S: bytes, root: bytes):
    counter = 0
    while True:
        blk = hashlib.sha3_256(domain + S + root + counter.to_bytes(8, "big")).digest()
        for i in range(0, 32, 8):
            yield int.from_bytes(blk[i:i+8], "big")
        counter += 1


def _uniform_numbers(count: int, range_size: int, domain: bytes, S: bytes, root: bytes) -> List[int]:
    if range_size <= 0:
        raise ValueError("range_size must be positive")
    if count < 0:
        raise ValueError("count must be non-negative")
    if count > range_size:
        raise ValueError("count cannot exceed range size")

    seen = set()
    out: List[int] = []
    modulus = 1 << 64
    if range_size >= modulus:
        threshold = None
    else:
        threshold = (modulus // range_size) * range_size

    for rnd in prng_blocks(domain, S, root):
        if threshold is not None and rnd >= threshold:
            continue
        value = rnd % range_size
        if value not in seen:
            seen.add(value)
            out.append(value)
            if len(out) >= count:
                break
    return out


def unique_indices(count: int, universe: int, domain: bytes, S: bytes, root: bytes) -> list[int]:
    return _uniform_numbers(count, universe, domain, S, root)


def unique_range(count: int, start: int, end: int, domain: bytes, S: bytes, root: bytes) -> list[int]:
    if end < start:
        raise ValueError("end must be >= start")
    range_size = end - start + 1
    offsets = _uniform_numbers(count, range_size, domain, S, root)
    return [start + off for off in offsets]
