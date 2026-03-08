"""Radix arithmetic and conversion utilities.

Constants (computed from active RadixConfig):
  BASE, SEPTITS_PER_WORD, MAX_WORD, MEMORY_SIZE

Public functions:
  parse_base_n(s)    — parse base-N digit string to int
  parse_decimal(s)   — parse decimal digit string to int, validate word range
  format_base_n(n)   — format int as base-N string
  validate_word(n)   — validate value fits in word range

Legacy aliases (base-7 names): parse_base7, format_base7
"""

from septa.common.config import get_config


def _base() -> int:
    return get_config().base


def _max_word() -> int:
    return get_config().max_word


def _memory_size() -> int:
    return get_config().memory_size


# Legacy constant-style access (properties that read from active config).
# These are module-level getters for backward compatibility.

def __getattr__(name: str):
    """Dynamic module attributes that read from active config."""
    cfg = get_config()
    if name == "BASE":
        return cfg.base
    if name == "SEPTITS_PER_WORD":
        return cfg.word_width
    if name == "MAX_WORD":
        return cfg.max_word
    if name == "MEMORY_SIZE":
        return cfg.memory_size
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def parse_base7(s: str) -> int:
    """Parse a base-N digit string (N from active config). Legacy alias."""
    return parse_base_n(s)


def parse_base_n(s: str) -> int:
    """Parse a base-N digit string to a Python int.

    Raises ValueError if any digit is out of range or string is empty.
    """
    cfg = get_config()
    if not s:
        raise ValueError(f"empty base-{cfg.base} literal")

    result = 0
    for ch in s:
        d = ord(ch) - ord('0')
        if d < 0 or d >= cfg.base:
            raise ValueError(f"invalid base-{cfg.base} digit: '{ch}'")
        result = result * cfg.base + d

    if result > cfg.max_word:
        raise ValueError(
            f"base-{cfg.base} literal '{s}' exceeds {cfg.word_width}-digit word "
            f"(max {format_base_n(cfg.max_word)})"
        )
    return result


def parse_decimal(s: str) -> int:
    """Parse a decimal digit string to a Python int, validate word range."""
    cfg = get_config()
    if not s:
        raise ValueError("empty decimal literal")

    result = int(s)
    if result > cfg.max_word:
        raise ValueError(
            f"decimal literal '{s}' exceeds {cfg.word_width}-digit word "
            f"(max {cfg.max_word})"
        )
    if result < 0:
        raise ValueError(f"negative decimal literal: '{s}'")
    return result


def format_base7(n: int) -> str:
    """Format int in base-N (N from active config). Legacy alias."""
    return format_base_n(n)


def format_base_n(n: int) -> str:
    """Format a non-negative int as a base-N string."""
    cfg = get_config()
    if n < 0:
        raise ValueError(f"cannot format negative value in base-{cfg.base}: {n}")
    if n == 0:
        return "0"

    digits: list[str] = []
    value = n
    while value > 0:
        digits.append(str(value % cfg.base))
        value //= cfg.base
    return "".join(reversed(digits))


def validate_word(n: int) -> int:
    """Ensure value fits in unsigned word range. Returns value if valid."""
    cfg = get_config()
    if n < 0 or n > cfg.max_word:
        raise ValueError(
            f"value {n} out of word range [0, {cfg.max_word}]"
        )
    return n
