"""SeptaASM assembler — assembly to executable image.

Two-pass assembly:
  Pass 1: collect label addresses (instruction index)
  Pass 2: encode instructions, resolve labels to indices

Instruction encoding: each instruction is a list [opcode, arg1, arg2, ...]
  - Registers Rn -> integer n
  - Immediates -> integer
  - Memory addresses [N] -> integer N
  - Indirect [Rn] -> integer n (distinguished by opcode context)
  - Labels -> resolved to instruction index

Public API:
  assemble(lines) -> dict  (image dict)
"""

from septa.asm.parser import AsmInstr, AsmLabel, AsmLine
from septa.common.errors import AssemblerError

# Opcodes that take a label operand (last operand is a label)
_BRANCH_OPCODES = frozenset({
    "JMP", "JZ", "JNZ", "JG", "JL", "JGE", "JLE", "CALL",
})

# Opcodes with no operands
_NO_OPERAND_OPCODES = frozenset({"RET", "HALT", "NOP"})

# Opcodes with one register operand
_ONE_REG_OPCODES = frozenset({"PRINT", "PRINTD"})


def assemble(lines: list[AsmLine]) -> dict:
    """Assemble parsed assembly lines into an image dict."""
    labels, instructions = _pass1(lines)
    code = _pass2(instructions, labels)
    return {
        "version": "0.1",
        "entrypoint": 0,
        "code": code,
        "symbols": labels,
    }


def _pass1(
    lines: list[AsmLine],
) -> tuple[dict[str, int], list[AsmInstr]]:
    """Collect labels and build instruction list."""
    labels: dict[str, int] = {}
    instructions: list[AsmInstr] = []

    for item in lines:
        if isinstance(item, AsmLabel):
            if item.name in labels:
                raise AssemblerError(
                    f"duplicate label '{item.name}' "
                    f"(first at instruction {labels[item.name]})"
                )
            labels[item.name] = len(instructions)
        elif isinstance(item, AsmInstr):
            instructions.append(item)

    return labels, instructions


def _pass2(
    instructions: list[AsmInstr], labels: dict[str, int]
) -> list[list]:
    """Encode instructions, resolving labels."""
    code: list[list] = []
    for instr in instructions:
        code.append(_encode(instr, labels))
    return code


def _parse_register(text: str) -> int:
    """Parse 'R0'..'R6' -> 0..6."""
    t = text.upper()
    if len(t) == 2 and t[0] == "R" and t[1].isdigit():
        n = int(t[1])
        if 0 <= n <= 6:
            return n
    raise AssemblerError(f"invalid register '{text}'")


def _parse_bracket_addr(text: str) -> int:
    """Parse '[123]' -> 123 (direct memory address)."""
    t = text.strip()
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        try:
            return int(inner)
        except ValueError:
            raise AssemblerError(f"invalid address '{text}'")
    raise AssemblerError(f"expected [addr], got '{text}'")


def _parse_bracket_reg(text: str) -> int:
    """Parse '[R4]' -> 4 (indirect register reference)."""
    t = text.strip()
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        return _parse_register(inner)
    raise AssemblerError(f"expected [Rn], got '{text}'")


def _encode(instr: AsmInstr, labels: dict[str, int]) -> list:
    """Encode a single instruction."""
    op = instr.opcode
    operands = instr.operands

    # No operands
    if op in _NO_OPERAND_OPCODES:
        return [op]

    # One register: PRINT Rn, PRINTD Rn
    if op in _ONE_REG_OPCODES:
        return [op, _parse_register(operands[0])]

    # Branch/call: opcode label
    if op in _BRANCH_OPCODES:
        label = operands[0].strip()
        if label not in labels:
            raise AssemblerError(
                f"undefined label '{label}' at line {instr.line}"
            )
        return [op, labels[label]]

    # LI Rn, imm
    if op == "LI":
        return [op, _parse_register(operands[0]), int(operands[1])]

    # MOV Rn, Rm
    if op == "MOV":
        return [op, _parse_register(operands[0]), _parse_register(operands[1])]

    # LD Rn, [addr]
    if op == "LD":
        return [op, _parse_register(operands[0]), _parse_bracket_addr(operands[1])]

    # ST Rn, [addr]
    if op == "ST":
        return [op, _parse_register(operands[0]), _parse_bracket_addr(operands[1])]

    # LDR Rn, [Rm]
    if op == "LDR":
        return [op, _parse_register(operands[0]), _parse_bracket_reg(operands[1])]

    # STR Rn, [Rm]
    if op == "STR":
        return [op, _parse_register(operands[0]), _parse_bracket_reg(operands[1])]

    # ADD Rn, Rm, Rk
    if op == "ADD":
        return [
            op,
            _parse_register(operands[0]),
            _parse_register(operands[1]),
            _parse_register(operands[2]),
        ]

    # SUB Rn, Rm, Rk
    if op == "SUB":
        return [
            op,
            _parse_register(operands[0]),
            _parse_register(operands[1]),
            _parse_register(operands[2]),
        ]

    # CMP Rm, Rk
    if op == "CMP":
        return [op, _parse_register(operands[0]), _parse_register(operands[1])]

    raise AssemblerError(f"unhandled opcode '{op}' at line {instr.line}")
