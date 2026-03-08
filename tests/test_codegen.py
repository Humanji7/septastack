"""Tests for address allocation and IR-to-assembly code generation."""

import pytest
from septa.codegen.addresses import DATA_BASE, AddressMap, allocate
from septa.codegen.codegen import generate
from septa.ir.ir import Instr, IRFunction, IRGlobal, IRProgram, Op
from septa.ir.lowering import lower
from septa.lexer.lexer import Lexer
from septa.parser.parser import Parser
from septa.semantic.analyzer import analyze


def lower_source(source: str) -> IRProgram:
    tokens = Lexer(source, "test.septa").tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    return lower(program)


def gen(source: str) -> str:
    """Source -> IR -> assembly text."""
    return generate(lower_source(source))


def asm_lines(source: str) -> list[str]:
    """Return non-empty, non-comment assembly lines."""
    text = gen(source)
    return [
        ln.strip() for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith(";")
    ]


# ================================================================
# Address allocation
# ================================================================

class TestAddressAllocation:
    def test_globals_start_at_data_base(self):
        ir = lower_source("""
        let a: word = 1;
        let b: word = 2;
        fn main() -> void {}
        """)
        addrs = allocate(ir)
        assert addrs.global_addrs["global:a"] == DATA_BASE
        assert addrs.global_addrs["global:b"] == DATA_BASE + 1

    def test_function_slots_after_globals(self):
        ir = lower_source("""
        let g: word = 0;
        fn main() -> void {
            let x: word = 1;
        }
        """)
        addrs = allocate(ir)
        # global at DATA_BASE, main's slots start at DATA_BASE+1
        main_map = addrs.fn_addrs["main"]
        first_addr = min(main_map.values())
        assert first_addr == DATA_BASE + 1

    def test_no_overlap(self):
        ir = lower_source("""
        let g: word = 0;
        fn foo(a: word) -> void { let x: word = 1; }
        fn main() -> void { let y: word = 2; }
        """)
        addrs = allocate(ir)
        all_addrs: list[int] = list(addrs.global_addrs.values())
        for fn_map in addrs.fn_addrs.values():
            all_addrs.extend(fn_map.values())
        assert len(all_addrs) == len(set(all_addrs)), "address overlap detected"

    def test_function_slot_order(self):
        """Params first, then locals, then temps."""
        ir = lower_source("""
        fn foo(a: word, b: word) -> void {
            let x: word = 1;
            let y: word = a + b;
        }
        fn main() -> void {}
        """)
        addrs = allocate(ir)
        fm = addrs.fn_addrs["foo"]
        assert fm["param:a"] < fm["param:b"]
        assert fm["param:b"] < fm["local:x"]
        assert fm["local:x"] < fm["local:y"]
        # temps after locals
        if "temp:0" in fm:
            assert fm["local:y"] < fm["temp:0"]

    def test_deterministic(self):
        source = """
        let g: word = 0;
        fn foo(x: word) -> word { return x; }
        fn main() -> void { let r: word = foo(1); }
        """
        ir1 = lower_source(source)
        ir2 = lower_source(source)
        a1 = allocate(ir1)
        a2 = allocate(ir2)
        assert a1.global_addrs == a2.global_addrs
        assert a1.fn_addrs == a2.fn_addrs

    def test_addr_lookup(self):
        ir = lower_source("""
        let g: word = 0;
        fn main() -> void { let x: word = 1; }
        """)
        addrs = allocate(ir)
        assert addrs.addr("global:g") == DATA_BASE
        assert addrs.addr("local:x", "main") == addrs.fn_addrs["main"]["local:x"]

    def test_multiple_functions_separate_slots(self):
        ir = lower_source("""
        fn foo() -> void { let x: word = 1; }
        fn bar() -> void { let x: word = 2; }
        fn main() -> void {}
        """)
        addrs = allocate(ir)
        foo_x = addrs.fn_addrs["foo"]["local:x"]
        bar_x = addrs.fn_addrs["bar"]["local:x"]
        assert foo_x != bar_x


# ================================================================
# Codegen: core constructs
# ================================================================

class TestCodegen:
    def test_init_block_present(self):
        text = gen("fn main() -> void {}")
        assert "_init:" in text
        assert "CALL main" in text
        assert "HALT" in text

    def test_global_initialization(self):
        text = gen("""
        let g: word = 10;
        fn main() -> void {}
        """)
        # 10 in base-7 = 7 decimal
        assert "LI R4, 7" in text
        assert f"ST R4, [{DATA_BASE}]" in text

    def test_function_label(self):
        text = gen("""
        fn foo() -> void {}
        fn main() -> void {}
        """)
        assert "foo:" in text
        assert "main:" in text

    def test_function_entry_copies_args(self):
        text = gen("""
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {}
        """)
        lines = text.splitlines()
        # After 'add:' label, first instructions should be ST R1/R2
        add_idx = next(i for i, l in enumerate(lines) if l.strip() == "add:")
        after_label = [l.strip() for l in lines[add_idx+1:add_idx+3]]
        assert after_label[0].startswith("ST R1,")
        assert after_label[1].startswith("ST R2,")

    def test_const_emits_li_st(self):
        lines = asm_lines("fn main() -> void { let x: word = d:42; }")
        # Should contain LI R4, 42 and ST R4, [addr]
        assert any("LI R4, 42" in l for l in lines)
        assert any("ST R4," in l for l in lines)

    def test_copy_emits_ld_st(self):
        lines = asm_lines("""
        fn main() -> void {
            let x: word = 1;
            let y: word = x;
        }
        """)
        # COPY lowers to LD + ST
        ld_count = sum(1 for l in lines if l.startswith("LD R4,"))
        st_count = sum(1 for l in lines if l.startswith("ST R4,"))
        assert ld_count >= 1
        assert st_count >= 2

    def test_add_emits_ld_ld_add_st(self):
        lines = asm_lines("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let c: word = a + b;
        }
        """)
        assert any("ADD R4, R4, R5" in l for l in lines)

    def test_sub_emits_sub(self):
        lines = asm_lines("""
        fn main() -> void {
            let a: word = 5;
            let b: word = 3;
            let c: word = a - b;
        }
        """)
        assert any("SUB R4, R4, R5" in l for l in lines)

    def test_neg_emits_li_ld_sub(self):
        lines = asm_lines("""
        fn main() -> void {
            let x: word = 5;
            let y: word = -x;
        }
        """)
        assert any("LI R4, 0" in l for l in lines)
        assert any("SUB R4, R4, R5" in l for l in lines)

    def test_not_emits_cmp_branch(self):
        text = gen("""
        fn main() -> void {
            let x: word = 5;
            let f: bool7 = !x;
        }
        """)
        assert "CMP R4, R5" in text
        assert "JZ" in text
        assert "LI R4, 6" in text
        assert "LI R4, 0" in text

    def test_comparison_materializes_bool(self):
        text = gen("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let r: bool7 = a > b;
        }
        """)
        assert "CMP R4, R5" in text
        assert "JG" in text

    def test_mem_load_uses_ldr(self):
        text = gen("""
        fn main() -> void {
            let v: word = store[0];
        }
        """)
        assert "LDR R5, [R4]" in text

    def test_mem_store_uses_str(self):
        text = gen("""
        fn main() -> void {
            store[0] = d:42;
        }
        """)
        assert "STR R5, [R4]" in text

    def test_if_emits_jump_z(self):
        text = gen("""
        fn main() -> void {
            let x: word = 5;
            if x { print(1); }
        }
        """)
        assert "JZ main.L0" in text
        assert "main.L0:" in text

    def test_if_else_emits_jumps(self):
        text = gen("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                print(1);
            } else {
                print(0);
            }
        }
        """)
        # Should have both conditional and unconditional jumps
        assert "JZ" in text or "JNZ" in text or "JG" in text
        assert "JMP" in text

    def test_while_emits_loop(self):
        text = gen("""
        fn main() -> void {
            let i: word = 5;
            while i > 0 {
                i = i - 1;
            }
        }
        """)
        assert "main.L0:" in text  # loop label
        assert "JMP main.L0" in text  # back-edge
        assert "main.L1:" in text  # end label

    def test_call_emits_ld_arg_call_st(self):
        text = gen("""
        fn id(x: word) -> word { return x; }
        fn main() -> void {
            let r: word = id(5);
        }
        """)
        assert "CALL id" in text
        assert "ST R0," in text  # store return value

    def test_void_call_no_st_r0(self):
        text = gen("""
        fn noop() -> void {}
        fn main() -> void { noop(); }
        """)
        lines = text.splitlines()
        call_idx = next(
            i for i, l in enumerate(lines) if "CALL noop" in l
        )
        # Next non-empty line after CALL should NOT be ST R0
        for l in lines[call_idx + 1:]:
            stripped = l.strip()
            if stripped and not stripped.startswith(";"):
                assert not stripped.startswith("ST R0,"), \
                    "void call should not store R0"
                break

    def test_return_loads_r0(self):
        text = gen("""
        fn seven() -> word { return 10; }
        fn main() -> void {}
        """)
        assert "LD R0," in text
        assert "RET" in text

    def test_return_void_emits_ret(self):
        text = gen("""
        fn main() -> void { return; }
        """)
        assert "RET" in text

    def test_print_emits_ld_print(self):
        text = gen("""
        fn main() -> void { print(d:42); }
        """)
        assert "PRINT R4" in text

    def test_printd_emits_ld_printd(self):
        text = gen("""
        fn main() -> void { printd(d:42); }
        """)
        assert "PRINTD R4" in text

    def test_halt_emits_halt(self):
        text = gen("""
        fn main() -> void { halt(); }
        """)
        # Should have HALT from the builtin AND from _init
        assert text.count("HALT") >= 2

    def test_header_comments(self):
        text = gen("""
        let g: word = 10;
        fn main() -> void {}
        """)
        assert "; global g @" in text
        assert "; fn main:" in text

    def test_3_arg_function(self):
        text = gen("""
        fn f(a: word, b: word, c: word) -> word {
            return a + b + c;
        }
        fn main() -> void {
            let r: word = f(1, 2, 3);
        }
        """)
        lines = text.splitlines()
        # Function entry should copy R1, R2, R3
        f_idx = next(i for i, l in enumerate(lines) if l.strip() == "f:")
        after = [l.strip() for l in lines[f_idx+1:f_idx+4]]
        assert after[0].startswith("ST R1,")
        assert after[1].startswith("ST R2,")
        assert after[2].startswith("ST R3,")
        # Caller should load args into R1, R2, R3
        assert "LD R1," in text
        assert "LD R2," in text
        assert "LD R3," in text
