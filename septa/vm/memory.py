"""VM memory subsystem.

Word-addressed memory. Size determined by active RadixConfig.
All memory starts zero-initialized. The image 'data' section
is debug metadata only — globals are initialized by _init code.

Layout:
  0..99       — user store[] access
  100+        — compiler-allocated static slots (globals, locals, temps)
  top of mem  — call stack (grows downward)
"""

from __future__ import annotations

from septa.common.config import get_config
from septa.common.errors import VMError


class Memory:
    """Word-addressed VM memory."""

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data = [0] * get_config().memory_size

    def load(self, addr: int) -> int:
        if addr < 0 or addr >= len(self._data):
            raise VMError(f"memory read out of bounds: {addr}")
        return self._data[addr]

    def store(self, addr: int, value: int) -> None:
        if addr < 0 or addr >= len(self._data):
            raise VMError(f"memory write out of bounds: {addr}")
        self._data[addr] = value % get_config().modulus

    def reset(self) -> None:
        self._data = [0] * get_config().memory_size
