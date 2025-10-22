
from __future__ import annotations
from typing import List, Tuple
from .utils import sha3_256

LEAF_PREFIX = b'\x00'
NODE_PREFIX = b'\x01'

def _hash_leaf(data: bytes) -> bytes:
    return sha3_256(LEAF_PREFIX + data)

def _hash_node(left: bytes, right: bytes) -> bytes:
    return sha3_256(NODE_PREFIX + left + right)

def build_merkle(leaves_data: List[bytes]) -> tuple[bytes, list[list[bytes]]]:
    if not leaves_data:
        raise ValueError("No leaves")
    level = [_hash_leaf(d) for d in leaves_data]
    levels = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i+1] if i+1 < len(level) else level[i]
            nxt.append(_hash_node(a, b))
        levels.append(nxt)
        level = nxt
    return level[0], levels

def merkle_proof(levels: list[list[bytes]], index: int) -> list[tuple[bytes, str]]:
    proof: list[tuple[bytes, str]] = []
    idx = index
    for lvl in range(len(levels)-1):
        level = levels[lvl]
        if idx % 2 == 0:
            sib_idx = idx + 1 if idx+1 < len(level) else idx
            proof.append((level[sib_idx], "R"))
        else:
            sib_idx = idx - 1
            proof.append((level[sib_idx], "L"))
        idx //= 2
    return proof

def verify_proof(leaf_data: bytes, proof: list[tuple[bytes, str]], root: bytes) -> bool:
    h = _hash_leaf(leaf_data)
    for sib, dirc in proof:
        if dirc == "R":
            h = _hash_node(h, sib)
        else:
            h = _hash_node(sib, h)
    return h == root
