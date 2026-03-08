"""Intermediate representation for SeptaLang v0.1.

Flat, three-address-code-like IR between AST and assembly.
No SSA, no CFG, no optimizer. Explicit and debuggable.

Slot naming convention:
  global:name   — global variable
  param:name    — function parameter
  local:name    — local variable (let-declared)
  local:name_N  — shadowed local (Nth redeclaration of same name)
  temp:N        — compiler-generated temporary

IR instructions operate on named slots, not registers.
Register allocation happens in the codegen phase.

Public types: Op, Instr, IRGlobal, IRFunction, IRProgram
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Op(Enum):
    """IR opcodes."""
    # Constants / moves
    CONST = "const"             # dst <- imm
    COPY = "copy"               # dst <- src

    # Arithmetic
    ADD = "add"                 # dst <- src + src2
    SUB = "sub"                 # dst <- src - src2
    NEG = "neg"                 # dst <- 0 - src (unary minus)

    # Logical
    NOT = "not"                 # dst <- (src == 0) ? 6 : 0

    # Comparison (result: 0=false, 6=true)
    CMP_EQ = "cmp_eq"          # dst <- (src == src2) ? 6 : 0
    CMP_NE = "cmp_ne"          # dst <- (src != src2) ? 6 : 0
    CMP_GT = "cmp_gt"          # dst <- (src >  src2) ? 6 : 0
    CMP_LT = "cmp_lt"          # dst <- (src <  src2) ? 6 : 0
    CMP_GE = "cmp_ge"          # dst <- (src >= src2) ? 6 : 0
    CMP_LE = "cmp_le"          # dst <- (src <= src2) ? 6 : 0

    # Memory (store[] access)
    MEM_LOAD = "mem_load"       # dst <- memory[src]
    MEM_STORE = "mem_store"     # memory[dst] <- src

    # Control flow
    LABEL = "label"             # label marker (label field)
    JUMP = "jump"               # unconditional jump (label field)
    JUMP_Z = "jump_z"           # jump if src == 0 (src, label)
    JUMP_NZ = "jump_nz"         # jump if src != 0 (src, label)

    # Function calls
    ARG = "arg"                 # set call argument: arg[imm] <- src
    CALL = "call"               # dst <- call label() (dst="" if void)
    RETURN = "return"           # return src
    RETURN_VOID = "return_void" # return (void)

    # Builtins (dedicated, not modeled as calls)
    PRINT = "print"             # print src as base-7
    PRINTD = "printd"           # print src as decimal
    HALT = "halt"               # halt execution


@dataclass(slots=True)
class Instr:
    """Single IR instruction.

    Field usage by opcode:
      CONST:       dst, imm
      COPY:        dst, src
      ADD/SUB:     dst, src, src2
      NEG/NOT:     dst, src
      CMP_*:       dst, src, src2
      MEM_LOAD:    dst, src (addr slot)
      MEM_STORE:   dst (addr slot), src (value slot)
      LABEL:       label
      JUMP:        label
      JUMP_Z:      src, label
      JUMP_NZ:     src, label
      ARG:         imm (index), src
      CALL:        dst (empty if void), label (func name)
      RETURN:      src
      RETURN_VOID: (none)
      PRINT:       src
      PRINTD:      src
      HALT:        (none)
    """
    op: Op
    dst: str = ""
    src: str = ""
    src2: str = ""
    imm: int = 0
    label: str = ""

    def __str__(self) -> str:
        op = self.op
        if op is Op.CONST:
            return f"  const {self.dst}, {self.imm}"
        if op is Op.COPY:
            return f"  copy {self.dst}, {self.src}"
        if op in (Op.ADD, Op.SUB):
            return f"  {op.value} {self.dst}, {self.src}, {self.src2}"
        if op in (Op.NEG, Op.NOT):
            return f"  {op.value} {self.dst}, {self.src}"
        if op in (Op.CMP_EQ, Op.CMP_NE, Op.CMP_GT, Op.CMP_LT,
                  Op.CMP_GE, Op.CMP_LE):
            return f"  {op.value} {self.dst}, {self.src}, {self.src2}"
        if op is Op.MEM_LOAD:
            return f"  mem_load {self.dst}, [{self.src}]"
        if op is Op.MEM_STORE:
            return f"  mem_store [{self.dst}], {self.src}"
        if op is Op.LABEL:
            return f"{self.label}:"
        if op is Op.JUMP:
            return f"  jump {self.label}"
        if op in (Op.JUMP_Z, Op.JUMP_NZ):
            return f"  {op.value} {self.src}, {self.label}"
        if op is Op.ARG:
            return f"  arg {self.imm}, {self.src}"
        if op is Op.CALL:
            if self.dst:
                return f"  call {self.dst}, {self.label}"
            return f"  call {self.label}"
        if op is Op.RETURN:
            return f"  return {self.src}"
        if op is Op.RETURN_VOID:
            return "  return_void"
        if op is Op.PRINT:
            return f"  print {self.src}"
        if op is Op.PRINTD:
            return f"  printd {self.src}"
        if op is Op.HALT:
            return "  halt"
        return f"  {op.value}"


@dataclass(slots=True)
class IRGlobal:
    """A global variable with its constant initializer."""
    name: str
    slot: str           # "global:name"
    init_value: int     # word value (bool: true=6, false=0)


@dataclass(slots=True)
class IRFunction:
    """A lowered function."""
    name: str
    params: list[str]           # param slot names in order
    local_slots: list[str]      # all local variable slot names
    temp_count: int             # number of temp slots used
    body: list[Instr] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"fn {self.name}:"]
        if self.params:
            lines.append(f"  ; params: {', '.join(self.params)}")
        if self.local_slots:
            lines.append(f"  ; locals: {', '.join(self.local_slots)}")
        if self.temp_count:
            lines.append(f"  ; temps: {self.temp_count}")
        for instr in self.body:
            lines.append(str(instr))
        return "\n".join(lines)


@dataclass(slots=True)
class IRProgram:
    """Complete lowered program."""
    globals: list[IRGlobal] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)

    def __str__(self) -> str:
        parts: list[str] = []
        for g in self.globals:
            parts.append(f"global {g.slot} = {g.init_value}")
        if self.globals:
            parts.append("")
        for fn in self.functions:
            parts.append(str(fn))
            parts.append("")
        return "\n".join(parts)
