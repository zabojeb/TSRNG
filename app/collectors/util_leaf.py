
from __future__ import annotations
import base64
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

LEAF_SIZE = 64


@dataclass
class CollectedLeaf:
    """
    Bundle raw payload, derived leaf bytes and optional metadata.
    """
    raw: bytes
    leaf: bytes
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_b64(self) -> str:
        return base64.b64encode(self.leaf).decode()

    def hash_hex(self) -> str:
        return self.leaf.hex()

    def clone(self) -> "CollectedLeaf":
        # raw/leaf are immutable bytes, but metadata should be copied
        return CollectedLeaf(raw=self.raw, leaf=self.leaf, meta=dict(self.meta))

    def with_leaf_size(self, leaf_size: int) -> "CollectedLeaf":
        if leaf_size <= 0:
            raise ValueError("leaf_size must be positive")
        if len(self.leaf) == leaf_size:
            return self.clone()
        digest = hashlib.sha3_512(self.raw).digest()[:leaf_size]
        meta = dict(self.meta)
        meta["leaf_size"] = leaf_size
        meta["leaf_hash_hex"] = digest.hex()
        return CollectedLeaf(raw=self.raw, leaf=digest, meta=meta)


def leaf_from_bytes(data: bytes, meta: Optional[Dict[str, Any]] = None, leaf_size: int = LEAF_SIZE) -> CollectedLeaf:
    meta_dict = dict(meta or {})
    meta_dict.setdefault("raw_size", len(data))
    meta_dict.setdefault("hash_alg", "sha3_512")
    meta_dict.setdefault("leaf_size", leaf_size)
    digest = hashlib.sha3_512(data).digest()[:leaf_size]
    meta_dict.setdefault("leaf_hash_hex", digest.hex())
    return CollectedLeaf(raw=data, leaf=digest, meta=meta_dict)
