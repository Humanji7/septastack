"""Base-7 arithmetic and conversion utilities.

Core constants:
  SEPTITS_PER_WORD = 12  (digits in a base-7 word)
  MAX_WORD = 7**12 - 1   (maximum unsigned word value)
  MEMORY_SIZE = 7**5     (addressable words)

Public functions:
  parse_base7(s)   — parse base-7 digit string to int
  parse_decimal(s) — parse decimal digit string to int, validate word range
  format_base7(n)  — format int as base-7 string
  validate_word(n) — clamp/validate value fits in 12-septit word
"""

SEPTITS_PER_WORD = 12
MAX_WORD = 7**SEPTITS_PER_WORD - 1
MEMORY_SIZE = 7**5
BASE = 7


def parse_base7(s: str) -> int:
    """Parse a base-7 digit string to a Python int.

    Raises ValueError if any digit is not in 0..6 or string is empty.
    """
    if not s:
        raise ValueError("empty base-7 literal")

    result = 0
    for ch in s:
        if ch < '0' or ch > '6':
            raise ValueError(f"invalid base-7 digit: '{ch}'")
        result = result * BASE + int(ch)

    if result > MAX_WORD:
        raise ValueError(
            f"base-7 literal '{s}' exceeds 12-septit word "
            f"(max {format_base7(MAX_WORD)})"
        )
    return result


def parse_decimal(s: str) -> int:
    """Parse a decimal digit string to a Python int, validate word range.

    Raises ValueError if not a valid decimal integer or out of range.
    """
    if not s:
        raise ValueError("empty decimal literal")

    result = int(s)
    if result > MAX_WORD:
        raise ValueError(
            f"decimal literal '{s}' exceeds 12-septit word (max {MAX_WORD})"
        )
    if result < 0:
        raise ValueError(f"negative decimal literal: '{s}'")
    return result


def format_base7(n: int) -> str:
    """Format a non-negative int as a base-7 string."""
    if n < 0:
        raise ValueError(f"cannot format negative value as base-7: {n}")
    if n == 0:
        return "0"

    digits: list[str] = []
    value = n
    while value > 0:
        digits.append(str(value % BASE))
        value //= BASE
    return "".join(reversed(digits))


def validate_word(n: int) -> int:
    """Ensure value fits in an unsigned 12-septit word.

    Returns the value unchanged if valid.
    Raises ValueError otherwise.
    """
    if n < 0 or n > MAX_WORD:
        raise ValueError(
            f"value {n} out of word range [0, {MAX_WORD}]"
        )
    return n
