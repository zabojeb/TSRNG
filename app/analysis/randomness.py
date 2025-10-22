from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

EPS = 1e-12


@dataclass
class TestResult:
    name: str
    passed: bool
    p_value: Optional[float] = None
    statistic: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "passed": self.passed,
            "p_value": self.p_value,
            "statistic": self.statistic,
            "details": self.details,
        }
        if self.note:
            payload["note"] = self.note
        return payload


def iter_bits(data: bytes, limit_bits: Optional[int] = None):
    count = 0
    for byte in data:
        for shift in range(7, -1, -1):
            if limit_bits is not None and count >= limit_bits:
                return
            yield (byte >> shift) & 1
            count += 1


def trim_to_bits(data: bytes, limit_bits: Optional[int]) -> Tuple[bytes, int]:
    total_bits = len(data) * 8
    if limit_bits is None or limit_bits >= total_bits:
        return data, total_bits
    full_bytes = limit_bits // 8
    extra_bits = limit_bits % 8
    trimmed = bytearray(data[:full_bytes])
    if extra_bits:
        mask = (0xFF << (8 - extra_bits)) & 0xFF
        trimmed.append(data[full_bytes] & mask)
    return bytes(trimmed), limit_bits


def regularized_gamma_q(a: float, x: float) -> float:
    if a <= 0 or x < 0:
        raise ValueError("invalid arguments for gamma Q")
    if x == 0:
        return 1.0
    # series representation when x < a + 1
    if x < a + 1:
        term = 1.0 / a
        summation = term
        n = 1
        while n < 1000:
            term *= x / (a + n)
            summation += term
            if abs(term) < abs(summation) * 1e-12:
                break
            n += 1
        log_gamma_a = math.lgamma(a)
        p = summation * math.exp(-x + a * math.log(x) - log_gamma_a)
        return max(0.0, min(1.0, 1.0 - p))
    # continued fraction for Q
    log_gamma_a = math.lgamma(a)
    b = x + 1.0 - a
    c = 1.0 / EPS
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < EPS:
            d = EPS
        c = b + an / c
        if abs(c) < EPS:
            c = EPS
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    q = h * math.exp(-x + a * math.log(x) - log_gamma_a)
    return max(0.0, min(1.0, q))


def monobit_test(bit_length: int, ones: int, zeros: int) -> TestResult:
    if bit_length == 0:
        return TestResult("monobit", False, note="empty sequence")
    s_obs = abs(ones - zeros) / math.sqrt(bit_length)
    p_value = math.erfc(s_obs / math.sqrt(2))
    passed = p_value >= 0.01
    return TestResult(
        name="monobit_frequency",
        passed=passed,
        p_value=p_value,
        statistic=s_obs,
        details={"ones": ones, "zeros": zeros, "bit_length": bit_length},
    )


def runs_test(bit_length: int, ones: int, runs: int) -> TestResult:
    if bit_length == 0:
        return TestResult("runs", False, note="empty sequence")
    pi = ones / bit_length
    tau = 2.0 / math.sqrt(bit_length)
    if abs(pi - 0.5) >= tau:
        return TestResult(
            name="runs",
            passed=False,
            p_value=0.0,
            statistic=pi,
            details={"pi": pi, "tau": tau, "runs": runs, "bit_length": bit_length},
            note="proportion of ones too far from 0.5",
        )
    numerator = abs(runs - 2 * bit_length * pi * (1 - pi))
    denominator = 2 * math.sqrt(2 * bit_length) * pi * (1 - pi)
    if denominator == 0:
        return TestResult("runs", False, note="degenerate denominator")
    p_value = math.erfc(numerator / denominator)
    passed = p_value >= 0.01
    return TestResult(
        name="runs",
        passed=passed,
        p_value=p_value,
        statistic=runs,
        details={"pi": pi, "runs": runs, "bit_length": bit_length},
    )


def block_frequency_test(bit_length: int, block_counts: List[int], block_size: int) -> TestResult:
    num_blocks = len(block_counts)
    if num_blocks == 0:
        return TestResult(
            name="block_frequency",
            passed=False,
            note="insufficient data for at least one full block",
            details={"bit_length": bit_length, "block_size": block_size},
        )
    chi_sq = 0.0
    for cnt in block_counts:
        pi = cnt / block_size
        chi_sq += (pi - 0.5) ** 2
    chi_sq *= 4.0 * block_size
    p_value = regularized_gamma_q(num_blocks / 2.0, chi_sq / 2.0)
    passed = p_value >= 0.01
    return TestResult(
        name="block_frequency",
        passed=passed,
        p_value=p_value,
        statistic=chi_sq,
        details={"blocks": num_blocks, "block_size": block_size},
    )


def byte_distribution_test(byte_counts: List[int], total_bytes: int) -> TestResult:
    if total_bytes == 0:
        return TestResult("byte_distribution", False, note="no full bytes to analyse")
    expected = total_bytes / 256.0
    chi_sq = 0.0
    for cnt in byte_counts:
        chi_sq += (cnt - expected) ** 2 / expected
    df = 255.0
    p_value = regularized_gamma_q(df / 2.0, chi_sq / 2.0)
    passed = p_value >= 0.01
    top_symbols = sorted(
        ((val, cnt) for val, cnt in enumerate(byte_counts)),
        key=lambda x: x[1],
        reverse=True,
    )[:5]
    return TestResult(
        name="byte_distribution",
        passed=passed,
        p_value=p_value,
        statistic=chi_sq,
        details={"total_bytes": total_bytes, "top_symbols": top_symbols},
    )


def compute_entropy_per_byte(byte_counts: List[int], total_bytes: int) -> Optional[float]:
    if total_bytes == 0:
        return None
    entropy = 0.0
    for cnt in byte_counts:
        if cnt == 0:
            continue
        p = cnt / total_bytes
        entropy -= p * math.log2(p)
    return entropy


def run_basic_tests(data: bytes, limit_bits: Optional[int] = None, block_size: int = 128) -> Dict[str, Any]:
    trimmed, bit_length = trim_to_bits(data, limit_bits)
    if bit_length == 0:
        return {
            "bit_length": 0,
            "byte_length": 0,
            "ones": 0,
            "zeros": 0,
            "proportion_ones": 0.0,
            "entropy_per_byte": None,
            "tests": [TestResult("monobit_frequency", False, note="empty sequence").to_dict()],
            "all_passed": False,
        }

    ones = 0
    runs = 0
    longest_run = 0
    current_run = 0
    prev_bit = None
    block_counts: List[int] = []
    block_ones = 0
    block_cursor = 0

    for bit in iter_bits(trimmed, bit_length):
        ones += bit
        if prev_bit is None:
            prev_bit = bit
            current_run = 1
            runs = 1
        else:
            if bit == prev_bit:
                current_run += 1
            else:
                longest_run = max(longest_run, current_run)
                current_run = 1
                prev_bit = bit
                runs += 1
        block_ones += bit
        block_cursor += 1
        if block_cursor == block_size:
            block_counts.append(block_ones)
            block_cursor = 0
            block_ones = 0

    longest_run = max(longest_run, current_run)

    zeros = bit_length - ones
    tests: List[TestResult] = [
        monobit_test(bit_length, ones, zeros),
        runs_test(bit_length, ones, runs),
        block_frequency_test(bit_length, block_counts, block_size),
    ]

    full_bytes = bit_length // 8
    byte_counts = [0] * 256
    for b in trimmed[:full_bytes]:
        byte_counts[b] += 1
    tests.append(byte_distribution_test(byte_counts, full_bytes))

    entropy = compute_entropy_per_byte(byte_counts, full_bytes)

    all_passed = all(t.passed for t in tests if t.p_value is not None)

    return {
        "bit_length": bit_length,
        "byte_length": full_bytes,
        "ones": ones,
        "zeros": zeros,
        "proportion_ones": ones / bit_length,
        "longest_run": longest_run,
        "entropy_per_byte": entropy,
        "tests": [t.to_dict() for t in tests],
        "all_passed": all_passed,
    }
