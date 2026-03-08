"""Radix configuration for SeptaStack.

All radix-dependent constants derive from a single RadixConfig.
Set once at startup via set_config(). Read anywhere via get_config().

Default: base-7, 12-digit word (original SeptaStack configuration).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadixConfig:
    """Machine parameters derived from a chosen radix and word width."""

    base: int
    word_width: int

    def __post_init__(self) -> None:
        if self.base < 2:
            raise ValueError(f"base must be >= 2, got {self.base}")
        if self.word_width < 1:
            raise ValueError(f"word_width must be >= 1, got {self.word_width}")

    @property
    def max_word(self) -> int:
        return self.base ** self.word_width - 1

    @property
    def modulus(self) -> int:
        return self.base ** self.word_width

    @property
    def memory_size(self) -> int:
        return self.base ** 5

    @property
    def bool_true(self) -> int:
        return self.base - 1

    @property
    def bool_false(self) -> int:
        return 0

    @property
    def max_digit(self) -> str:
        """Highest valid digit character for this base (e.g. '6' for base-7)."""
        return str(self.base - 1)


# --- Module-level active config ---

_active: RadixConfig = RadixConfig(base=7, word_width=12)


def get_config() -> RadixConfig:
    """Return the active radix configuration."""
    return _active


def set_config(cfg: RadixConfig) -> None:
    """Set the active radix configuration. Call once at startup."""
    global _active
    _active = cfg


def reset_config() -> None:
    """Reset to default (base-7, 12-digit word). Mainly for tests."""
    global _active
    _active = RadixConfig(base=7, word_width=12)
