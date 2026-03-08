"""SeptaASM assembly parser.

Parses assembly text into a list of AsmLine items (labels and instructions).
Line-oriented: one instruction or label per line. Comments start with ';'.

Public API:
  parse_asm(source, filename) -> list[AsmLine]
"""

from __future__ import annotations

from dataclasses import dataclass

from septa.common.errors import AssemblerError
from septa.common.locations import SourceLocation

# All valid opcodes in SeptaASM
VALID_OPCODES = frozenset({
    "LI", "MOV", "LD", "ST", "LDR", "STR",
    "ADD", "SUB",
    "CMP",
    "JMP", "JZ", "JNZ", "JG", "JL", "JGE", "JLE",
    "CALL", "RET",
    "PRINT", "PRINTD", "HALT", "NOP",
})


@dataclass(slots=True)
class AsmLabel:
    """A label definition (e.g. 'main:')."""
    name: str
    line: int


@dataclass(slots=True)
class AsmInstr:
    """A single assembly instruction."""
    opcode: str
    operands: list[str]
    line: int


AsmLine = AsmLabel | AsmInstr


def parse_asm(source: str, filename: str = "<asm>") -> list[AsmLine]:
    """Parse assembly text into a list of labels and instructions."""
    result: list[AsmLine] = []

    for lineno, raw in enumerate(source.splitlines(), start=1):
        # Strip comments
        text = raw.split(";", 1)[0].strip()
        if not text:
            continue

        # Label: ends with ':'
        if text.endswith(":"):
            name = text[:-1].strip()
            if not name:
                raise AssemblerError(
                    "empty label name",
                    SourceLocation(filename, lineno, 1),
                )
            result.append(AsmLabel(name=name, line=lineno))
            continue

        # Instruction: opcode followed by comma-separated operands
        parts = text.split(None, 1)
        opcode = parts[0].upper()
        if opcode not in VALID_OPCODES:
            raise AssemblerError(
                f"unknown opcode '{opcode}'",
                SourceLocation(filename, lineno, 1),
            )

        operands: list[str] = []
        if len(parts) > 1:
            operands = [op.strip() for op in parts[1].split(",")]

        result.append(AsmInstr(opcode=opcode, operands=operands, line=lineno))

    return result
