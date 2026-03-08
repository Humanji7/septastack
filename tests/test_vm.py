"""Tests for the SeptaVM emulator.

Covers: ALU, memory, registers, individual instructions,
machine execution, and end-to-end program execution.
"""

import pytest
from septa.common.base7 import MAX_WORD, MEMORY_SIZE
from septa.common.errors import VMError
from septa.vm.alu import MODULUS, alu_add, alu_cmp, alu_sub
from septa.vm.instructions import execute
from septa.vm.machine import Machine
from septa.vm.memory import Memory
from septa.vm.registers import FLAG_G, FLAG_L, FLAG_Z, Registers
from septa.vm.syscalls import Syscalls

# Helpers for building images and running instructions

from septa.asm.assembler import assemble
from septa.asm.image import build_image
from septa.asm.parser import parse_asm
from septa.codegen.addresses import DATA_BASE, allocate
from septa.codegen.codegen import generate
from septa.ir.lowering import lower
from septa.lexer.lexer import Lexer
from septa.parser.parser import Parser
from septa.semantic.analyzer import analyze


def compile_and_run(source: str) -> list[str]:
    """Full pipeline: source -> tokens -> AST -> IR -> asm -> image -> VM."""
    tokens = Lexer(source, "test.septa").tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    ir = lower(program)
    asm_text = generate(ir)
    asm_lines = parse_asm(asm_text, "test.sasm")
    asm_image = assemble(asm_lines)
    addrs = allocate(ir)
    image = build_image(asm_image, ir, addrs)
    vm = Machine(image)
    return vm.run()


def make_vm(code: list[list], symbols: dict | None = None) -> Machine:
    """Create a VM from raw encoded instructions."""
    return Machine({
        "version": "0.1",
        "entrypoint": 0,
        "code": code,
        "symbols": symbols or {},
    })


def exec_one(instr: list, regs: Registers | None = None,
             mem: Memory | None = None,
             sys: Syscalls | None = None) -> tuple[Registers, Memory, Syscalls]:
    """Execute a single instruction and return state."""
    regs = regs or Registers()
    mem = mem or Memory()
    sys = sys or Syscalls()
    execute(instr, regs, mem, sys)
    return regs, mem, sys


# ================================================================
# ALU
# ================================================================

class TestALU:
    def test_add_simple(self):
        result, is_zero = alu_add(3, 4)
        assert result == 7
        assert not is_zero

    def test_add_zero_result(self):
        result, is_zero = alu_add(0, 0)
        assert result == 0
        assert is_zero

    def test_add_overflow_wraps(self):
        result, _ = alu_add(MAX_WORD, 1)
        assert result == 0

    def test_add_overflow_wraps_more(self):
        result, _ = alu_add(MAX_WORD, 10)
        assert result == 9

    def test_add_large_values(self):
        result, _ = alu_add(MAX_WORD - 5, MAX_WORD - 3)
        # (MAX_WORD - 5) + (MAX_WORD - 3) = 2*MAX_WORD - 8
        # modulo MODULUS (= MAX_WORD + 1) = MAX_WORD - 9
        assert result == MAX_WORD - 9

    def test_sub_simple(self):
        result, is_zero = alu_sub(7, 3)
        assert result == 4
        assert not is_zero

    def test_sub_zero_result(self):
        result, is_zero = alu_sub(5, 5)
        assert result == 0
        assert is_zero

    def test_sub_underflow_wraps(self):
        result, _ = alu_sub(0, 1)
        assert result == MAX_WORD

    def test_sub_underflow_wraps_more(self):
        result, _ = alu_sub(3, 10)
        assert result == MAX_WORD - 6

    def test_cmp_equal(self):
        z, g, l = alu_cmp(5, 5)
        assert z is True
        assert g is False
        assert l is False

    def test_cmp_greater(self):
        z, g, l = alu_cmp(10, 3)
        assert z is False
        assert g is True
        assert l is False

    def test_cmp_less(self):
        z, g, l = alu_cmp(3, 10)
        assert z is False
        assert g is False
        assert l is True

    def test_modulus_value(self):
        assert MODULUS == MAX_WORD + 1
        assert MODULUS == 7**12


# ================================================================
# Memory
# ================================================================

class TestMemory:
    def test_zero_initialized(self):
        mem = Memory()
        for i in [0, 50, 99, DATA_BASE, MEMORY_SIZE - 1]:
            assert mem.load(i) == 0

    def test_store_and_load(self):
        mem = Memory()
        mem.store(42, 1234)
        assert mem.load(42) == 1234

    def test_store_wraps_overflow(self):
        mem = Memory()
        mem.store(0, MAX_WORD + 1)
        assert mem.load(0) == 0

    def test_store_wraps_large(self):
        mem = Memory()
        mem.store(0, MAX_WORD + 10)
        assert mem.load(0) == 9

    def test_out_of_bounds_read(self):
        mem = Memory()
        with pytest.raises(VMError, match="out of bounds"):
            mem.load(MEMORY_SIZE)

    def test_out_of_bounds_write(self):
        mem = Memory()
        with pytest.raises(VMError, match="out of bounds"):
            mem.store(MEMORY_SIZE, 0)

    def test_negative_address_read(self):
        mem = Memory()
        with pytest.raises(VMError, match="out of bounds"):
            mem.load(-1)

    def test_negative_address_write(self):
        mem = Memory()
        with pytest.raises(VMError, match="out of bounds"):
            mem.store(-1, 0)

    def test_reset(self):
        mem = Memory()
        mem.store(100, 42)
        mem.reset()
        assert mem.load(100) == 0


# ================================================================
# Registers
# ================================================================

class TestRegisters:
    def test_initial_state(self):
        regs = Registers()
        for i in range(7):
            assert regs.get(i) == 0
        assert regs.pc == 0
        assert regs.sp == MEMORY_SIZE - 1
        assert regs.fr == 0

    def test_set_and_get(self):
        regs = Registers()
        regs.set(4, 42)
        assert regs.get(4) == 42

    def test_set_wraps_overflow(self):
        regs = Registers()
        regs.set(0, MAX_WORD + 1)
        assert regs.get(0) == 0

    def test_flags_z(self):
        regs = Registers()
        regs.set_flags(z=True)
        assert regs.z is True
        assert regs.g is False
        assert regs.l is False
        assert regs.fr == FLAG_Z

    def test_flags_g(self):
        regs = Registers()
        regs.set_flags(g=True)
        assert regs.g is True
        assert regs.z is False
        assert regs.l is False
        assert regs.fr == FLAG_G

    def test_flags_l(self):
        regs = Registers()
        regs.set_flags(l=True)
        assert regs.l is True
        assert regs.z is False
        assert regs.g is False
        assert regs.fr == FLAG_L

    def test_flags_cleared_on_set(self):
        regs = Registers()
        regs.set_flags(z=True, g=True)
        regs.set_flags(l=True)
        assert regs.l is True
        assert regs.z is False
        assert regs.g is False

    def test_reset(self):
        regs = Registers()
        regs.set(0, 100)
        regs.pc = 50
        regs.sp = 10
        regs.set_flags(z=True)
        regs.reset(entrypoint=5)
        assert regs.get(0) == 0
        assert regs.pc == 5
        assert regs.sp == MEMORY_SIZE - 1
        assert regs.fr == 0


# ================================================================
# Individual Instructions
# ================================================================

class TestInstructions:
    def test_li(self):
        regs, _, _ = exec_one(["LI", 4, 42])
        assert regs.get(4) == 42
        assert regs.pc == 1

    def test_mov(self):
        regs = Registers()
        regs.set(5, 99)
        regs, _, _ = exec_one(["MOV", 0, 5], regs)
        assert regs.get(0) == 99

    def test_ld(self):
        mem = Memory()
        mem.store(100, 42)
        regs, _, _ = exec_one(["LD", 4, 100], mem=mem)
        assert regs.get(4) == 42

    def test_st(self):
        regs = Registers()
        regs.set(4, 77)
        _, mem, _ = exec_one(["ST", 4, 200], regs, Memory())
        assert mem.load(200) == 77

    def test_ldr(self):
        regs = Registers()
        regs.set(4, 50)  # R4 holds address 50
        mem = Memory()
        mem.store(50, 999)
        regs, _, _ = exec_one(["LDR", 5, 4], regs, mem)
        assert regs.get(5) == 999

    def test_str(self):
        regs = Registers()
        regs.set(4, 60)  # R4 holds address 60
        regs.set(5, 123)
        _, mem, _ = exec_one(["STR", 5, 4], regs, Memory())
        assert mem.load(60) == 123

    def test_add(self):
        regs = Registers()
        regs.set(4, 10)
        regs.set(5, 20)
        regs, _, _ = exec_one(["ADD", 4, 4, 5], regs)
        assert regs.get(4) == 30
        assert not regs.z

    def test_add_sets_z_flag(self):
        regs = Registers()
        regs.set(4, 0)
        regs.set(5, 0)
        regs, _, _ = exec_one(["ADD", 4, 4, 5], regs)
        assert regs.z

    def test_sub(self):
        regs = Registers()
        regs.set(4, 20)
        regs.set(5, 7)
        regs, _, _ = exec_one(["SUB", 4, 4, 5], regs)
        assert regs.get(4) == 13

    def test_sub_underflow(self):
        regs = Registers()
        regs.set(4, 0)
        regs.set(5, 1)
        regs, _, _ = exec_one(["SUB", 4, 4, 5], regs)
        assert regs.get(4) == MAX_WORD

    def test_cmp_equal(self):
        regs = Registers()
        regs.set(4, 5)
        regs.set(5, 5)
        regs, _, _ = exec_one(["CMP", 4, 5], regs)
        assert regs.z
        assert not regs.g
        assert not regs.l

    def test_cmp_greater(self):
        regs = Registers()
        regs.set(4, 10)
        regs.set(5, 3)
        regs, _, _ = exec_one(["CMP", 4, 5], regs)
        assert not regs.z
        assert regs.g
        assert not regs.l

    def test_cmp_less(self):
        regs = Registers()
        regs.set(4, 3)
        regs.set(5, 10)
        regs, _, _ = exec_one(["CMP", 4, 5], regs)
        assert not regs.z
        assert not regs.g
        assert regs.l

    def test_jmp(self):
        regs, _, _ = exec_one(["JMP", 42])
        assert regs.pc == 42

    def test_jz_taken(self):
        regs = Registers()
        regs.set_flags(z=True)
        regs, _, _ = exec_one(["JZ", 10], regs)
        assert regs.pc == 10

    def test_jz_not_taken(self):
        regs = Registers()
        regs.set_flags(z=False)
        regs, _, _ = exec_one(["JZ", 10], regs)
        assert regs.pc == 1

    def test_jnz_taken(self):
        regs = Registers()
        regs.set_flags(z=False)
        regs, _, _ = exec_one(["JNZ", 10], regs)
        assert regs.pc == 10

    def test_jnz_not_taken(self):
        regs = Registers()
        regs.set_flags(z=True)
        regs, _, _ = exec_one(["JNZ", 10], regs)
        assert regs.pc == 1

    def test_jg_taken(self):
        regs = Registers()
        regs.set_flags(g=True)
        regs, _, _ = exec_one(["JG", 10], regs)
        assert regs.pc == 10

    def test_jg_not_taken(self):
        regs = Registers()
        regs.set_flags(l=True)
        regs, _, _ = exec_one(["JG", 10], regs)
        assert regs.pc == 1

    def test_jl_taken(self):
        regs = Registers()
        regs.set_flags(l=True)
        regs, _, _ = exec_one(["JL", 10], regs)
        assert regs.pc == 10

    def test_jl_not_taken(self):
        regs = Registers()
        regs.set_flags(g=True)
        regs, _, _ = exec_one(["JL", 10], regs)
        assert regs.pc == 1

    def test_jge_taken_on_greater(self):
        regs = Registers()
        regs.set_flags(g=True)
        regs, _, _ = exec_one(["JGE", 10], regs)
        assert regs.pc == 10

    def test_jge_taken_on_equal(self):
        regs = Registers()
        regs.set_flags(z=True)
        regs, _, _ = exec_one(["JGE", 10], regs)
        assert regs.pc == 10

    def test_jge_not_taken(self):
        regs = Registers()
        regs.set_flags(l=True)
        regs, _, _ = exec_one(["JGE", 10], regs)
        assert regs.pc == 1

    def test_jle_taken_on_less(self):
        regs = Registers()
        regs.set_flags(l=True)
        regs, _, _ = exec_one(["JLE", 10], regs)
        assert regs.pc == 10

    def test_jle_taken_on_equal(self):
        regs = Registers()
        regs.set_flags(z=True)
        regs, _, _ = exec_one(["JLE", 10], regs)
        assert regs.pc == 10

    def test_jle_not_taken(self):
        regs = Registers()
        regs.set_flags(g=True)
        regs, _, _ = exec_one(["JLE", 10], regs)
        assert regs.pc == 1

    def test_call(self):
        regs = Registers()
        regs.pc = 5
        mem = Memory()
        regs, mem, _ = exec_one(["CALL", 20], regs, mem)
        # Return address (5+1=6) pushed, SP decremented
        assert regs.pc == 20
        assert regs.sp == MEMORY_SIZE - 2
        assert mem.load(MEMORY_SIZE - 1) == 6

    def test_ret(self):
        regs = Registers()
        mem = Memory()
        # Simulate CALL: push return address 42
        mem.store(MEMORY_SIZE - 1, 42)
        regs.sp = MEMORY_SIZE - 2
        regs, _, _ = exec_one(["RET"], regs, mem)
        assert regs.pc == 42
        assert regs.sp == MEMORY_SIZE - 1

    def test_call_ret_roundtrip(self):
        regs = Registers()
        regs.pc = 10
        mem = Memory()
        # CALL target=50
        execute(["CALL", 50], regs, mem, Syscalls())
        assert regs.pc == 50
        old_sp = regs.sp
        # RET
        execute(["RET"], regs, mem, Syscalls())
        assert regs.pc == 11  # return to 10+1
        assert regs.sp == old_sp + 1

    def test_nested_calls(self):
        regs = Registers()
        regs.pc = 0
        mem = Memory()
        sys = Syscalls()
        # CALL 10 from PC=0
        execute(["CALL", 10], regs, mem, sys)
        assert regs.pc == 10
        sp_after_first = regs.sp
        # CALL 20 from PC=10
        execute(["CALL", 20], regs, mem, sys)
        assert regs.pc == 20
        assert regs.sp == sp_after_first - 1
        # RET from 20 -> back to 11
        execute(["RET"], regs, mem, sys)
        assert regs.pc == 11
        # RET from 10 -> back to 1
        execute(["RET"], regs, mem, sys)
        assert regs.pc == 1

    def test_print(self):
        regs = Registers()
        regs.set(4, 7)  # 7 in decimal = 10 in base-7
        sys = Syscalls()
        _, _, sys = exec_one(["PRINT", 4], regs, sys=sys)
        assert sys.output == ["10"]

    def test_printd(self):
        regs = Registers()
        regs.set(4, 42)
        sys = Syscalls()
        _, _, sys = exec_one(["PRINTD", 4], regs, sys=sys)
        assert sys.output == ["42"]

    def test_halt(self):
        sys = Syscalls()
        _, _, sys = exec_one(["HALT"], sys=sys)
        assert sys.halted

    def test_nop(self):
        regs, _, _ = exec_one(["NOP"])
        assert regs.pc == 1

    def test_unknown_opcode(self):
        with pytest.raises(VMError, match="unknown opcode"):
            exec_one(["FOO", 1])


# ================================================================
# Machine
# ================================================================

class TestMachine:
    def test_minimal_program(self):
        vm = make_vm([["HALT"]])
        output = vm.run()
        assert output == []
        assert vm.halted
        assert vm.steps == 1

    def test_step_interface(self):
        vm = make_vm([["NOP"], ["HALT"]])
        assert vm.step() is True  # NOP, still running
        assert vm.step() is False  # HALT, stopped
        assert vm.halted

    def test_step_after_halt(self):
        vm = make_vm([["HALT"]])
        vm.step()
        assert vm.step() is False

    def test_pc_out_of_bounds(self):
        vm = make_vm([["JMP", 100]])
        with pytest.raises(VMError, match="PC out of bounds"):
            vm.run()

    def test_max_steps_exceeded(self):
        # Infinite loop
        vm = make_vm([["JMP", 0]])
        with pytest.raises(VMError, match="exceeded"):
            vm.run(max_steps=100)

    def test_version_check(self):
        with pytest.raises(VMError, match="unsupported image version"):
            Machine({"version": "99.0", "code": []})

    def test_memory_zero_initialized(self):
        vm = make_vm([["HALT"]])
        for addr in [0, 50, 99, DATA_BASE]:
            assert vm.mem.load(addr) == 0

    def test_data_section_not_loaded(self):
        """Image 'data' is debug metadata — not auto-loaded into memory."""
        image = {
            "version": "0.1",
            "entrypoint": 0,
            "code": [["HALT"]],
            "data": [[100, 42], [101, 99]],
            "symbols": {},
        }
        vm = Machine(image)
        # Memory should still be zero — data section is NOT loaded
        assert vm.mem.load(100) == 0
        assert vm.mem.load(101) == 0

    def test_output_property(self):
        vm = make_vm([
            ["LI", 4, 42],
            ["PRINTD", 4],
            ["HALT"],
        ])
        vm.run()
        assert vm.output == ["42"]

    def test_li_st_ld_program(self):
        vm = make_vm([
            ["LI", 4, 100],
            ["ST", 4, 50],
            ["LD", 5, 50],
            ["PRINTD", 5],
            ["HALT"],
        ])
        output = vm.run()
        assert output == ["100"]

    def test_add_program(self):
        vm = make_vm([
            ["LI", 4, 10],
            ["LI", 5, 20],
            ["ADD", 4, 4, 5],
            ["PRINTD", 4],
            ["HALT"],
        ])
        assert vm.run() == ["30"]

    def test_sub_program(self):
        vm = make_vm([
            ["LI", 4, 50],
            ["LI", 5, 20],
            ["SUB", 4, 4, 5],
            ["PRINTD", 4],
            ["HALT"],
        ])
        assert vm.run() == ["30"]

    def test_cmp_and_branch(self):
        """CMP + JG should jump when first > second."""
        vm = make_vm([
            ["LI", 4, 10],
            ["LI", 5, 3],
            ["CMP", 4, 5],
            ["JG", 5],          # jump to PRINTD
            ["HALT"],           # not reached
            ["PRINTD", 4],
            ["HALT"],
        ])
        assert vm.run() == ["10"]

    def test_call_ret_program(self):
        """CALL pushes return address, RET pops it."""
        vm = make_vm([
            # 0: CALL 3
            ["CALL", 3],
            # 1: PRINTD R0
            ["PRINTD", 0],
            # 2: HALT
            ["HALT"],
            # 3: function: LI R0, 42
            ["LI", 0, 42],
            # 4: RET
            ["RET"],
        ])
        assert vm.run() == ["42"]

    def test_ldr_str_program(self):
        """Indirect memory access via LDR/STR."""
        vm = make_vm([
            ["LI", 4, 10],      # address 10
            ["LI", 5, 999],
            ["STR", 5, 4],      # store 999 at address 10
            ["LI", 5, 0],       # clear R5
            ["LDR", 5, 4],      # load from address 10
            ["PRINTD", 5],
            ["HALT"],
        ])
        assert vm.run() == ["999"]

    def test_loop_program(self):
        """Simple countdown loop."""
        vm = make_vm([
            # R4 = counter, R5 = 0, R6 = 1
            ["LI", 4, 3],       # 0: counter = 3
            ["LI", 6, 1],       # 1: decrement value
            # loop start:
            ["LI", 5, 0],       # 2: R5 = 0
            ["CMP", 4, 5],      # 3: compare counter to 0
            ["JZ", 8],          # 4: if zero, exit loop
            ["PRINTD", 4],      # 5: print counter
            ["SUB", 4, 4, 6],   # 6: counter -= 1
            ["JMP", 2],         # 7: back to loop start
            ["HALT"],           # 8: done
        ])
        assert vm.run() == ["3", "2", "1"]

    def test_stack_overflow(self):
        """Deeply nested calls should eventually overflow the stack."""
        # Create a function that calls itself (address 0)
        vm = make_vm([["CALL", 0]])
        with pytest.raises(VMError):
            vm.run(max_steps=100_000)

    def test_steps_counter(self):
        vm = make_vm([["NOP"], ["NOP"], ["NOP"], ["HALT"]])
        vm.run()
        assert vm.steps == 4


# ================================================================
# End-to-end: source -> compile -> VM execute
# ================================================================

class TestVMEndToEnd:
    def test_add_example(self):
        """3 + 4 = 7 decimal, 10 in base-7."""
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let sum: word = a + b;
            print(sum);
            printd(sum);
        }
        """)
        assert output == ["10", "7"]

    def test_hello_example(self):
        """d:42 = 42 decimal = 60 in base-7."""
        output = compile_and_run("""
        fn main() -> void {
            print(d:42);
        }
        """)
        assert output == ["60"]

    def test_printd(self):
        output = compile_and_run("""
        fn main() -> void {
            printd(d:42);
        }
        """)
        assert output == ["42"]

    def test_subtraction(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 10;
            let b: word = 3;
            let diff: word = a - b;
            printd(diff);
        }
        """)
        # 10 base-7 = 7 decimal, 3 base-7 = 3 decimal, diff = 4
        assert output == ["4"]

    def test_negation(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 5;
            let y: word = -x;
            printd(y);
        }
        """)
        # -5 mod 7^12 = MAX_WORD - 4
        assert output == [str(MAX_WORD - 4)]

    def test_comparison_true(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 5;
            let b: word = 3;
            if a > b { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["1"]

    def test_comparison_false(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 5;
            if a > b { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["0"]

    def test_not_true(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 0;
            let r: bool7 = !x;
            if r { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["1"]  # !0 = true

    def test_not_false(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 5;
            let r: bool7 = !x;
            if r { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["0"]  # !nonzero = false

    def test_if_true_branch(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                printd(1);
            } else {
                printd(0);
            }
        }
        """)
        assert output == ["1"]

    def test_if_false_branch(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 2;
            if x > 3 {
                printd(1);
            } else {
                printd(0);
            }
        }
        """)
        assert output == ["0"]

    def test_while_countdown(self):
        output = compile_and_run("""
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """)
        assert output == ["6", "5", "4", "3", "2", "1"]

    def test_function_call_return(self):
        output = compile_and_run("""
        fn double(x: word) -> word {
            return x + x;
        }
        fn main() -> void {
            let r: word = double(3);
            printd(r);
        }
        """)
        assert output == ["6"]

    def test_function_two_args(self):
        output = compile_and_run("""
        fn add(a: word, b: word) -> word {
            return a + b;
        }
        fn main() -> void {
            let r: word = add(d:10, d:20);
            printd(r);
        }
        """)
        assert output == ["30"]

    def test_function_three_args(self):
        output = compile_and_run("""
        fn sum3(a: word, b: word, c: word) -> word {
            return a + b + c;
        }
        fn main() -> void {
            let r: word = sum3(d:10, d:20, d:30);
            printd(r);
        }
        """)
        assert output == ["60"]

    def test_void_function(self):
        output = compile_and_run("""
        fn greet() -> void {
            printd(d:42);
        }
        fn main() -> void {
            greet();
        }
        """)
        assert output == ["42"]

    def test_globals_initialized_by_init(self):
        output = compile_and_run("""
        let g: word = d:42;
        fn main() -> void {
            printd(g);
        }
        """)
        assert output == ["42"]

    def test_global_modified_by_function(self):
        output = compile_and_run("""
        let counter: word = 0;
        fn inc() -> void {
            counter = counter + 1;
        }
        fn main() -> void {
            inc();
            inc();
            inc();
            printd(counter);
        }
        """)
        assert output == ["3"]

    def test_store_memory_read_write(self):
        output = compile_and_run("""
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """)
        assert output == ["300"]

    def test_halt_stops_execution(self):
        output = compile_and_run("""
        fn main() -> void {
            printd(1);
            halt();
            printd(2);
        }
        """)
        # halt() should stop before second printd
        assert output == ["1"]

    def test_bool_true_literal(self):
        output = compile_and_run("""
        fn main() -> void {
            let t: bool7 = true;
            if t { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["1"]

    def test_bool_false_literal(self):
        output = compile_and_run("""
        fn main() -> void {
            let f: bool7 = false;
            if f { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["0"]

    def test_all_comparisons(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 5;
            let b: word = 3;
            let c: word = 5;
            if a == c { printd(1); } else { printd(0); }
            if a != b { printd(1); } else { printd(0); }
            if a > b { printd(1); } else { printd(0); }
            if b < a { printd(1); } else { printd(0); }
            if a >= c { printd(1); } else { printd(0); }
            if b <= a { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["1", "1", "1", "1", "1", "1"]

    def test_comparisons_false(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 5;
            if a == b { printd(1); } else { printd(0); }
            if a != a { printd(1); } else { printd(0); }
            if a > b { printd(1); } else { printd(0); }
            if b < a { printd(1); } else { printd(0); }
        }
        """)
        assert output == ["0", "0", "0", "0"]

    def test_multiple_prints(self):
        output = compile_and_run("""
        fn main() -> void {
            printd(1);
            printd(2);
            printd(3);
        }
        """)
        assert output == ["1", "2", "3"]

    def test_deterministic_execution(self):
        """Same source always produces same output."""
        source = """
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {
            let r: word = add(3, 4);
            printd(r);
        }
        """
        out1 = compile_and_run(source)
        out2 = compile_and_run(source)
        assert out1 == out2

    def test_nested_if(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 10;
            if x > 5 {
                if x > 6 {
                    printd(1);
                } else {
                    printd(2);
                }
            } else {
                printd(3);
            }
        }
        """)
        # x=10 (base7) = 7 (decimal), 7>5 and 7>6
        assert output == ["1"]

    def test_while_with_function(self):
        output = compile_and_run("""
        fn dec(x: word) -> word {
            return x - 1;
        }
        fn main() -> void {
            let i: word = 3;
            while i > 0 {
                printd(i);
                i = dec(i);
            }
        }
        """)
        assert output == ["3", "2", "1"]

    def test_global_bool(self):
        output = compile_and_run("""
        let flag: bool7 = true;
        fn main() -> void {
            if flag {
                printd(d:42);
            }
        }
        """)
        assert output == ["42"]


# ================================================================
# Example programs from examples/ directory
# ================================================================

class TestVMExamples:
    def test_add_septa(self):
        output = compile_and_run("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let sum: word = a + b;
            print(sum);
            printd(sum);
        }
        """)
        assert output == ["10", "7"]

    def test_hello_septa(self):
        output = compile_and_run("""
        fn main() -> void {
            print(d:42);
        }
        """)
        assert output == ["60"]

    def test_functions_septa(self):
        output = compile_and_run("""
        fn add(a: word, b: word) -> word {
            return a + b;
        }
        fn main() -> void {
            let result: word = add(3, 4);
            print(result);
            printd(result);
        }
        """)
        assert output == ["10", "7"]

    def test_if_else_septa(self):
        output = compile_and_run("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                print(1);
            } else {
                print(0);
            }
        }
        """)
        assert output == ["1"]

    def test_while_loop_septa(self):
        output = compile_and_run("""
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """)
        assert output == ["6", "5", "4", "3", "2", "1"]

    def test_memory_septa(self):
        output = compile_and_run("""
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """)
        assert output == ["300"]
