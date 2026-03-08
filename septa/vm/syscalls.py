"""VM built-in operations (syscalls).

PRINT  — output value in active base
PRINTD — output value in decimal
HALT   — stop execution

Output is collected in a list for testability.
"""

from __future__ import annotations

from septa.common.base7 import format_base_n


class Syscalls:
    """Handles VM built-in operations. Collects output for testing."""

    __slots__ = ("_output", "_halted")

    def __init__(self) -> None:
        self._output: list[str] = []
        self._halted = False

    @property
    def output(self) -> list[str]:
        return self._output

    @property
    def halted(self) -> bool:
        return self._halted

    def print_base7(self, value: int) -> None:
        self._output.append(format_base_n(value))

    def print_decimal(self, value: int) -> None:
        self._output.append(str(value))

    def halt(self) -> None:
        self._halted = True

    def reset(self) -> None:
        self._output.clear()
        self._halted = False
