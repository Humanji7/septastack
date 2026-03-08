"""VM register file.

7 general-purpose registers (R0-R6) plus special registers:
  PC  — program counter (instruction index)
  SP  — stack pointer (memory address, grows downward)
  FR  — flags (Z, G, L)

Register convention (compiler):
  R0  — return value
  R1-R3 — function arguments
  R4-R6 — scratch
"""

from __future__ import annotations

from dataclasses import dataclass, field

from septa.common.config import get_config

NUM_REGS = 7  # R0-R6

# Flag bits in FR
FLAG_Z = 0b001  # Zero
FLAG_G = 0b010  # Greater
FLAG_L = 0b100  # Less


@dataclass(slots=True)
class Registers:
    """Register file for SeptaVM."""

    gp: list[int] = field(default_factory=lambda: [0] * NUM_REGS)
    pc: int = 0
    sp: int = -1  # sentinel; initialized in __post_init__
    fr: int = 0

    def __post_init__(self) -> None:
        if self.sp == -1:
            self.sp = get_config().memory_size - 1

    def reset(self, entrypoint: int = 0) -> None:
        self.gp = [0] * NUM_REGS
        self.pc = entrypoint
        self.sp = get_config().memory_size - 1
        self.fr = 0

    def get(self, idx: int) -> int:
        return self.gp[idx]

    def set(self, idx: int, value: int) -> None:
        self.gp[idx] = get_config().wrap_word(value)

    @property
    def z(self) -> bool:
        return bool(self.fr & FLAG_Z)

    @property
    def g(self) -> bool:
        return bool(self.fr & FLAG_G)

    @property
    def l(self) -> bool:
        return bool(self.fr & FLAG_L)

    def set_flags(self, *, z: bool = False, g: bool = False,
                  l: bool = False) -> None:
        self.fr = 0
        if z:
            self.fr |= FLAG_Z
        if g:
            self.fr |= FLAG_G
        if l:
            self.fr |= FLAG_L
