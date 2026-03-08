"""SeptaVM — the emulator.

Loads an executable image and runs it instruction by instruction.

Execution model:
  - Memory starts zero-initialized
  - Image 'data' section is debug metadata, NOT auto-loaded
  - PC starts at image entrypoint (always 0 — _init block)
  - _init code initializes globals, calls main, HALTs
  - Execution continues until HALT or max_steps exceeded

Public API:
  Machine(image) — create VM from image dict
  machine.step() -> bool — execute one instruction, True if still running
  machine.run(max_steps) -> list[str] — run until HALT, return output
"""

from __future__ import annotations

from septa.common.errors import VMError
from septa.vm.instructions import execute
from septa.vm.memory import Memory
from septa.vm.registers import Registers
from septa.vm.syscalls import Syscalls

DEFAULT_MAX_STEPS = 100_000


class Machine:
    """SeptaVM emulator."""

    __slots__ = ("_code", "_symbols", "_regs", "_mem", "_sys", "_steps")

    def __init__(self, image: dict) -> None:
        if image.get("version") != "0.1":
            raise VMError(
                f"unsupported image version: {image.get('version')}"
            )
        self._code: list[list] = image["code"]
        self._symbols: dict[str, int] = image.get("symbols", {})
        self._regs = Registers()
        self._mem = Memory()
        self._sys = Syscalls()
        self._steps = 0
        self._regs.pc = image.get("entrypoint", 0)

    @property
    def regs(self) -> Registers:
        return self._regs

    @property
    def mem(self) -> Memory:
        return self._mem

    @property
    def output(self) -> list[str]:
        return self._sys.output

    @property
    def halted(self) -> bool:
        return self._sys.halted

    @property
    def steps(self) -> int:
        return self._steps

    def step(self) -> bool:
        """Execute one instruction. Returns True if still running."""
        if self._sys.halted:
            return False
        if self._regs.pc < 0 or self._regs.pc >= len(self._code):
            raise VMError(
                f"PC out of bounds: {self._regs.pc} "
                f"(code size: {len(self._code)})"
            )
        instr = self._code[self._regs.pc]
        execute(instr, self._regs, self._mem, self._sys)
        self._steps += 1
        return not self._sys.halted

    def run(self, max_steps: int = DEFAULT_MAX_STEPS) -> list[str]:
        """Run until HALT or max_steps exceeded. Returns output list."""
        while self.step():
            if self._steps >= max_steps:
                raise VMError(
                    f"execution exceeded {max_steps} steps (infinite loop?)"
                )
        return self._sys.output
