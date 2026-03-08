"""Integration tests: SeptaLang source -> IR -> assembly -> image.

Tests the full compilation pipeline up to image generation.
"""

import json
import pytest
from septa.asm.assembler import assemble
from septa.asm.image import build_image
from septa.asm.parser import parse_asm
from septa.codegen.addresses import DATA_BASE, allocate
from septa.codegen.codegen import generate
from septa.ir.lowering import lower
from septa.lexer.lexer import Lexer
from septa.parser.parser import Parser
from septa.semantic.analyzer import analyze


def compile_to_image(source: str) -> dict:
    """Full pipeline: source -> tokens -> AST -> IR -> asm -> image."""
    tokens = Lexer(source, "test.septa").tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    ir = lower(program)
    asm_text = generate(ir)
    asm_lines = parse_asm(asm_text, "test.sasm")
    asm_image = assemble(asm_lines)
    addrs = allocate(ir)
    return build_image(asm_image, ir, addrs)


class TestPipelineBasic:
    def test_minimal_program(self):
        img = compile_to_image("fn main() -> void {}")
        assert img["version"] == "0.1"
        assert img["entrypoint"] == 0
        assert len(img["code"]) > 0
        assert "main" in img["symbols"]
        assert "_init" in img["symbols"]

    def test_init_calls_main_then_halts(self):
        img = compile_to_image("fn main() -> void {}")
        code = img["code"]
        # First instructions should be from _init: CALL main, HALT
        main_idx = img["symbols"]["main"]
        call_found = False
        halt_found = False
        for instr in code[:main_idx]:
            if instr[0] == "CALL" and instr[1] == main_idx:
                call_found = True
            if instr[0] == "HALT":
                halt_found = True
        assert call_found, "_init must CALL main"
        assert halt_found, "_init must HALT after main returns"

    def test_halt_after_call(self):
        """HALT should come right after CALL main in _init."""
        img = compile_to_image("fn main() -> void {}")
        code = img["code"]
        main_idx = img["symbols"]["main"]
        # Find CALL main
        for i, instr in enumerate(code):
            if instr[0] == "CALL" and instr[1] == main_idx:
                assert code[i + 1][0] == "HALT"
                break


class TestPipelineGlobals:
    def test_global_in_data(self):
        img = compile_to_image("""
        let g: word = 10;
        fn main() -> void {}
        """)
        assert len(img["data"]) == 1
        addr, value = img["data"][0]
        assert addr == DATA_BASE
        assert value == 7  # 10 in base-7 = 7

    def test_multiple_globals(self):
        img = compile_to_image("""
        let a: word = 1;
        let b: bool7 = true;
        let c: word = d:42;
        fn main() -> void {}
        """)
        assert len(img["data"]) == 3
        values = [d[1] for d in img["data"]]
        assert values == [1, 6, 42]

    def test_global_init_in_code(self):
        """The _init block must contain LI+ST for each global."""
        img = compile_to_image("""
        let g: word = 10;
        fn main() -> void {}
        """)
        code = img["code"]
        # Check that init contains LI with value 7 and ST to DATA_BASE
        li_found = any(
            i[0] == "LI" and i[2] == 7 for i in code
        )
        st_found = any(
            i[0] == "ST" and i[2] == DATA_BASE for i in code
        )
        assert li_found
        assert st_found


class TestPipelineFunctions:
    def test_function_entry_stores_args(self):
        """Function prologue copies R1-R3 to parameter slots."""
        img = compile_to_image("""
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {}
        """)
        code = img["code"]
        add_idx = img["symbols"]["add"]
        # First two instructions after add: should store R1 and R2
        assert code[add_idx][0] == "ST"
        assert code[add_idx][1] == 1  # R1
        assert code[add_idx + 1][0] == "ST"
        assert code[add_idx + 1][1] == 2  # R2

    def test_return_value(self):
        """Return loads value into R0 and RETs."""
        img = compile_to_image("""
        fn seven() -> word { return 10; }
        fn main() -> void {}
        """)
        code = img["code"]
        seven_idx = img["symbols"]["seven"]
        fn_code = code[seven_idx:]
        # Should contain LD R0 somewhere before RET
        r0_loads = [i for i in fn_code if i[0] == "LD" and i[1] == 0]
        rets = [i for i in fn_code if i[0] == "RET"]
        assert len(r0_loads) >= 1
        assert len(rets) >= 1

    def test_call_stores_return(self):
        """Calling a non-void function stores R0 after CALL."""
        img = compile_to_image("""
        fn seven() -> word { return 10; }
        fn main() -> void { let r: word = seven(); }
        """)
        code = img["code"]
        main_idx = img["symbols"]["main"]
        # Find CALL seven within main's code
        for i in range(main_idx, len(code)):
            if code[i][0] == "CALL" and code[i][1] == img["symbols"]["seven"]:
                # Next instruction should be ST R0, [addr]
                assert code[i + 1][0] == "ST"
                assert code[i + 1][1] == 0  # R0
                break
        else:
            pytest.fail("CALL seven not found in main")

    def test_void_call_no_store_r0(self):
        img = compile_to_image("""
        fn noop() -> void {}
        fn main() -> void { noop(); }
        """)
        code = img["code"]
        main_idx = img["symbols"]["main"]
        noop_idx = img["symbols"]["noop"]
        for i in range(main_idx, len(code)):
            if code[i][0] == "CALL" and code[i][1] == noop_idx:
                # Next instruction should NOT be ST R0
                if i + 1 < len(code):
                    next_instr = code[i + 1]
                    if next_instr[0] == "ST":
                        assert next_instr[1] != 0, \
                            "void call should not store R0"
                break


class TestPipelineBuiltins:
    def test_print(self):
        img = compile_to_image("""
        fn main() -> void { print(d:42); }
        """)
        code = img["code"]
        prints = [i for i in code if i[0] == "PRINT"]
        assert len(prints) >= 1
        assert prints[0][1] == 4  # R4

    def test_printd(self):
        img = compile_to_image("""
        fn main() -> void { printd(d:42); }
        """)
        code = img["code"]
        printds = [i for i in code if i[0] == "PRINTD"]
        assert len(printds) >= 1

    def test_halt(self):
        img = compile_to_image("""
        fn main() -> void { halt(); }
        """)
        code = img["code"]
        halts = [i for i in code if i[0] == "HALT"]
        assert len(halts) >= 2  # one from halt(), one from _init


class TestPipelineControlFlow:
    def test_if_compiles(self):
        img = compile_to_image("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 { print(1); }
        }
        """)
        code = img["code"]
        opcodes = [i[0] for i in code]
        assert "CMP" in opcodes

    def test_while_compiles(self):
        img = compile_to_image("""
        fn main() -> void {
            let i: word = 5;
            while i > 0 {
                i = i - 1;
            }
        }
        """)
        code = img["code"]
        opcodes = [i[0] for i in code]
        assert "CMP" in opcodes
        assert "JMP" in opcodes

    def test_if_else_compiles(self):
        img = compile_to_image("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                print(1);
            } else {
                print(0);
            }
        }
        """)
        code = img["code"]
        prints = [i for i in code if i[0] == "PRINT"]
        assert len(prints) == 2


class TestPipelineMemory:
    def test_store_read_write(self):
        img = compile_to_image("""
        fn main() -> void {
            store[0] = d:42;
            let v: word = store[0];
        }
        """)
        code = img["code"]
        opcodes = [i[0] for i in code]
        assert "STR" in opcodes
        assert "LDR" in opcodes


class TestPipelineExamples:
    def test_add_example(self):
        """The add.septa example compiles through the full pipeline."""
        img = compile_to_image("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            print(a + b);
        }
        """)
        assert img["version"] == "0.1"
        assert "main" in img["symbols"]

    def test_countdown(self):
        img = compile_to_image("""
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """)
        assert "main" in img["symbols"]
        opcodes = [i[0] for i in img["code"]]
        assert "PRINT" in opcodes
        assert "SUB" in opcodes

    def test_function_call(self):
        img = compile_to_image("""
        fn double(x: word) -> word {
            return x + x;
        }
        fn main() -> void {
            let r: word = double(3);
            printd(r);
        }
        """)
        assert "double" in img["symbols"]
        assert "main" in img["symbols"]

    def test_memory_operations(self):
        img = compile_to_image("""
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """)
        opcodes = [i[0] for i in img["code"]]
        assert "STR" in opcodes
        assert "LDR" in opcodes
        assert "PRINTD" in opcodes

    def test_globals_with_functions(self):
        img = compile_to_image("""
        let threshold: word = 5;
        fn check(x: word) -> bool7 {
            return x > threshold;
        }
        fn main() -> void {
            let r: bool7 = check(10);
        }
        """)
        assert len(img["data"]) == 1
        assert img["data"][0][1] == 5

    def test_image_is_json_serializable(self):
        img = compile_to_image("""
        fn main() -> void {
            let x: word = d:42;
            print(x);
        }
        """)
        # Should not raise
        text = json.dumps(img)
        roundtrip = json.loads(text)
        assert roundtrip == img

    def test_deterministic_output(self):
        """Same source always produces same image."""
        source = """
        let g: word = 10;
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {
            let r: word = add(3, 4);
            print(r);
        }
        """
        img1 = compile_to_image(source)
        img2 = compile_to_image(source)
        assert img1 == img2
