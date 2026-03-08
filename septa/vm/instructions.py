"""Instruction execution for SeptaVM.

Dispatches encoded instructions to the appropriate handler.
Each handler updates registers, memory, flags, and PC.
"""

from __future__ import annotations

from septa.common.config import get_config
from septa.common.errors import VMError
from septa.vm.alu import alu_add, alu_cmp, alu_sub
from septa.vm.memory import Memory
from septa.vm.registers import Registers
from septa.vm.syscalls import Syscalls


def execute(
    instr: list,
    regs: Registers,
    mem: Memory,
    sys: Syscalls,
) -> None:
    """Execute a single instruction. Updates PC."""
    opcode = instr[0]
    handler = _DISPATCH.get(opcode)
    if handler is None:
        raise VMError(f"unknown opcode: {opcode}")
    handler(instr, regs, mem, sys)


# --- Instruction handlers ---

def _exec_li(instr, regs, mem, sys):
    regs.set(instr[1], instr[2])
    regs.pc += 1


def _exec_mov(instr, regs, mem, sys):
    regs.set(instr[1], regs.get(instr[2]))
    regs.pc += 1


def _exec_ld(instr, regs, mem, sys):
    regs.set(instr[1], mem.load(instr[2]))
    regs.pc += 1


def _exec_st(instr, regs, mem, sys):
    mem.store(instr[2], regs.get(instr[1]))
    regs.pc += 1


def _exec_ldr(instr, regs, mem, sys):
    addr = regs.get(instr[2])
    regs.set(instr[1], mem.load(addr))
    regs.pc += 1


def _exec_str(instr, regs, mem, sys):
    addr = regs.get(instr[2])
    mem.store(addr, regs.get(instr[1]))
    regs.pc += 1


def _exec_add(instr, regs, mem, sys):
    a = regs.get(instr[2])
    b = regs.get(instr[3])
    result, is_zero = alu_add(a, b)
    regs.set(instr[1], result)
    regs.set_flags(z=is_zero)
    regs.pc += 1


def _exec_sub(instr, regs, mem, sys):
    a = regs.get(instr[2])
    b = regs.get(instr[3])
    result, is_zero = alu_sub(a, b)
    regs.set(instr[1], result)
    regs.set_flags(z=is_zero)
    regs.pc += 1


def _exec_cmp(instr, regs, mem, sys):
    a = regs.get(instr[1])
    b = regs.get(instr[2])
    z, g, l = alu_cmp(a, b)
    regs.set_flags(z=z, g=g, l=l)
    regs.pc += 1


def _exec_jmp(instr, regs, mem, sys):
    regs.pc = instr[1]


def _exec_jz(instr, regs, mem, sys):
    regs.pc = instr[1] if regs.z else regs.pc + 1


def _exec_jnz(instr, regs, mem, sys):
    regs.pc = instr[1] if not regs.z else regs.pc + 1


def _exec_jg(instr, regs, mem, sys):
    regs.pc = instr[1] if regs.g else regs.pc + 1


def _exec_jl(instr, regs, mem, sys):
    regs.pc = instr[1] if regs.l else regs.pc + 1


def _exec_jge(instr, regs, mem, sys):
    regs.pc = instr[1] if regs.g or regs.z else regs.pc + 1


def _exec_jle(instr, regs, mem, sys):
    regs.pc = instr[1] if regs.l or regs.z else regs.pc + 1


def _exec_call(instr, regs, mem, sys):
    """Push return address onto stack, jump to target."""
    mem.store(regs.sp, regs.pc + 1)
    regs.sp -= 1
    if regs.sp < 0:
        raise VMError("stack overflow")
    regs.pc = instr[1]


def _exec_ret(instr, regs, mem, sys):
    """Pop return address from stack, jump to it."""
    regs.sp += 1
    if regs.sp >= get_config().memory_size:
        raise VMError("stack underflow")
    regs.pc = mem.load(regs.sp)


def _exec_print(instr, regs, mem, sys):
    sys.print_base7(regs.get(instr[1]))
    regs.pc += 1


def _exec_printd(instr, regs, mem, sys):
    sys.print_decimal(regs.get(instr[1]))
    regs.pc += 1


def _exec_halt(instr, regs, mem, sys):
    sys.halt()
    regs.pc += 1


def _exec_nop(instr, regs, mem, sys):
    regs.pc += 1


_DISPATCH: dict[str, callable] = {
    "LI": _exec_li,
    "MOV": _exec_mov,
    "LD": _exec_ld,
    "ST": _exec_st,
    "LDR": _exec_ldr,
    "STR": _exec_str,
    "ADD": _exec_add,
    "SUB": _exec_sub,
    "CMP": _exec_cmp,
    "JMP": _exec_jmp,
    "JZ": _exec_jz,
    "JNZ": _exec_jnz,
    "JG": _exec_jg,
    "JL": _exec_jl,
    "JGE": _exec_jge,
    "JLE": _exec_jle,
    "CALL": _exec_call,
    "RET": _exec_ret,
    "PRINT": _exec_print,
    "PRINTD": _exec_printd,
    "HALT": _exec_halt,
    "NOP": _exec_nop,
}
