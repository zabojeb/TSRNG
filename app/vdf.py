
from __future__ import annotations
from .utils import sha3_256

def _is_probable_prime(n: int, k: int = 16) -> bool:
    if n < 2:
        return False
    small = [2,3,5,7,11,13,17,19,23,29,31,37]
    for p in small:
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    import secrets
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        skip = False
        for __ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                skip = True
                break
        if skip:
            continue
        return False
    return True

def derive_prime(seed: bytes, bits: int = 512) -> int:
    import hashlib
    ctr = 0
    while True:
        h = hashlib.sha3_512(seed + ctr.to_bytes(8, "big")).digest()
        x = int.from_bytes(h, "big")
        x |= 1
        x |= (1 << (bits - 1))
        r = x % 4
        if r != 3:
            x += (3 - r)
        if _is_probable_prime(x):
            return x
        ctr += 1

def vdf_encode_sloth(x: int, T: int, p: int) -> int:
    y = x % p
    for _ in range(T):
        y = (y * y) % p
    return y

def vdf_verify_sloth(x: int, y: int, T: int, p: int) -> bool:
    yy = x % p
    for _ in range(T):
        yy = (yy * yy) % p
    return yy == y

def int_from_seed(S: bytes, p: int) -> int:
    return int.from_bytes(sha3_256(S), "big") % p
