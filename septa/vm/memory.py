"""VM memory subsystem.

Word-addressed memory of MEMORY_SIZE (7^5 = 16807) words.
All memory starts zero-initialized. The image 'data' section
is debug metadata only — globals are initialized by _init code.

Layout:
  0..99       — user store[] access
  100+        — compiler-allocated static slots (globals, locals, temps)
  top of mem  — call stack (grows downward from MEMORY_SIZE-1)
"""

from __future__ import annotations

from septa.common.base7 import MAX_WORD, MEMORY_SIZE
from septa.common.errors import VMError


class Memory:
    """Word-addressed VM memory."""

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data = [0] * MEMORY_SIZE

    def load(self, addr: int) -> int:
        if addr < 0 or addr >= MEMORY_SIZE:
            raise VMError(f"memory read out of bounds: {addr}")
        return self._data[addr]

    def store(self, addr: int, value: int) -> None:
        if addr < 0 or addr >= MEMORY_SIZE:
            raise VMError(f"memory write out of bounds: {addr}")
        self._data[addr] = value % (MAX_WORD + 1)

    def reset(self) -> None:
        self._data = [0] * MEMORY_SIZE
