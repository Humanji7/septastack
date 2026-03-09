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
    """Ensure value fits in word range (unsigned or balanced). Returns value if valid."""
    cfg = get_config()
    if n < cfg.word_min or n > cfg.word_max:
        raise ValueError(
            f"value {n} out of word range [{cfg.word_min}, {cfg.word_max}]"
        )
    return n


# --- Balanced representation ---

# Negative digit chars: A=-1, B=-2, C=-3, D=-4, ...
# Special: for base-3, T=-1 (Knuth convention)

_NEG_DIGITS = "ABCDEFGHIJ"  # A=-1, B=-2, ..., up to base-21


def _digit_to_char(d: int, base: int) -> str:
    """Convert a balanced digit value to its character representation."""
    if d >= 0:
        return str(d)
    # Negative digit
    neg_idx = (-d) - 1  # A=-1 -> idx 0, B=-2 -> idx 1, ...
    if base == 3 and d == -1:
        return "T"  # Knuth convention for balanced ternary
    return _NEG_DIGITS[neg_idx]


def _char_to_digit(ch: str, base: int) -> int:
    """Convert a balanced digit character to its integer value."""
    if ch.isdigit():
        d = int(ch)
        half = (base - 1) // 2
        if d > half:
            raise ValueError(f"invalid balanced base-{base} digit: '{ch}'")
        return d
    if base == 3 and ch == "T":
        return -1
    idx = _NEG_DIGITS.find(ch)
    if idx < 0:
        raise ValueError(f"invalid balanced base-{base} digit: '{ch}'")
    return -(idx + 1)


def format_balanced(n: int) -> str:
    """Format an integer in balanced base-N notation.

    Uses current active config (must have balanced=True).
    Positive digits: 0..half. Negative digits: A=-1, B=-2, etc.
    Base-3 uses T=-1 (Knuth convention).
    """
    cfg = get_config()
    if n == 0:
        return "0"

    half = (cfg.base - 1) // 2
    negative = n < 0
    value = abs(n)

    digits: list[int] = []
    while value > 0:
        rem = value % cfg.base
        if rem > half:
            rem -= cfg.base  # carry: rem becomes negative, value increases
            value = (value - rem) // cfg.base
        else:
            value //= cfg.base
        digits.append(rem)

    if negative:
        digits = [-d for d in digits]

    return "".join(_digit_to_char(d, cfg.base) for d in reversed(digits))


def parse_balanced(s: str) -> int:
    """Parse a balanced base-N string to a Python int.

    Uses current active config (must have balanced=True).
    Validates result within [word_min, word_max].
    """
    cfg = get_config()
    if not s:
        raise ValueError(f"empty balanced base-{cfg.base} literal")

    result = 0
    for ch in s:
        d = _char_to_digit(ch, cfg.base)
        result = result * cfg.base + d

    if result < cfg.word_min or result > cfg.word_max:
        raise ValueError(
            f"balanced base-{cfg.base} literal '{s}' out of range "
            f"[{cfg.word_min}, {cfg.word_max}]"
        )
    return result
