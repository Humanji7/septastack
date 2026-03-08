"""Arithmetic/Logic Unit.

All arithmetic is modulo (MAX_WORD + 1).
Overflow and underflow wrap around silently.

CMP sets flags: Z (equal), G (greater), L (less).
ADD/SUB set Z flag if result is zero.
"""

from __future__ import annotations

from septa.common.config import get_config


def alu_add(a: int, b: int) -> tuple[int, bool]:
    """Add two words. Returns (result, is_zero)."""
    modulus = get_config().modulus
    result = (a + b) % modulus
    return result, result == 0


def alu_sub(a: int, b: int) -> tuple[int, bool]:
    """Subtract b from a. Returns (result, is_zero)."""
    modulus = get_config().modulus
    result = (a - b) % modulus
    return result, result == 0


def alu_cmp(a: int, b: int) -> tuple[bool, bool, bool]:
    """Compare two words. Returns (z, g, l) flags."""
    return a == b, a > b, a < b
