"""Tests for the SeptaASM parser and assembler."""

import json
import pytest
from septa.asm.assembler import assemble
from septa.asm.parser import AsmInstr, AsmLabel, parse_asm
from septa.common.errors import AssemblerError


# ================================================================
# Assembly parser
# ================================================================

class TestAsmParser:
    def test_empty(self):
        assert parse_asm("") == []

    def test_comment_only(self):
        assert parse_asm("; this is a comment") == []

    def test_label(self):
        lines = parse_asm("main:")
        assert len(lines) == 1
        assert isinstance(lines[0], AsmLabel)
        assert lines[0].name == "main"

    def test_label_with_spaces(self):
        lines = parse_asm("  main  :")
        assert lines[0].name == "main"

    def test_instruction_no_operands(self):
        lines = parse_asm("    HALT")
        assert len(lines) == 1
        assert isinstance(lines[0], AsmInstr)
        assert lines[0].opcode == "HALT"
        assert lines[0].operands == []

    def test_instruction_one_operand(self):
        lines = parse_asm("    PRINT R4")
        assert lines[0].operands == ["R4"]

    def test_instruction_two_operands(self):
        lines = parse_asm("    LI R4, 42")
        assert lines[0].opcode == "LI"
        assert lines[0].operands == ["R4", "42"]

    def test_instruction_three_operands(self):
        lines = parse_asm("    ADD R4, R4, R5")
        assert lines[0].operands == ["R4", "R4", "R5"]

    def test_bracket_operand(self):
        lines = parse_asm("    LD R4, [100]")
        assert lines[0].operands == ["R4", "[100]"]

    def test_indirect_operand(self):
        lines = parse_asm("    LDR R5, [R4]")
        assert lines[0].operands == ["R5", "[R4]"]

    def test_label_operand(self):
        lines = parse_asm("    JMP main")
        assert lines[0].operands == ["main"]

    def test_inline_comment(self):
        lines = parse_asm("    LI R4, 7 ; load seven")
        assert lines[0].opcode == "LI"
        assert lines[0].operands == ["R4", "7"]

    def test_mixed_labels_and_instrs(self):
        source = """
        _init:
            LI R4, 7
            ST R4, [100]
            CALL main
            HALT
        main:
            RET
        """
        lines = parse_asm(source)
        labels = [l for l in lines if isinstance(l, AsmLabel)]
        instrs = [l for l in lines if isinstance(l, AsmInstr)]
        assert len(labels) == 2
        assert len(instrs) == 5
        assert labels[0].name == "_init"
        assert labels[1].name == "main"

    def test_case_insensitive_opcode(self):
        lines = parse_asm("    halt")
        assert lines[0].opcode == "HALT"

    def test_unknown_opcode_raises(self):
        with pytest.raises(AssemblerError, match="unknown opcode"):
            parse_asm("    FOO R4")

    def test_empty_label_raises(self):
        with pytest.raises(AssemblerError, match="empty label"):
            parse_asm(":")

    def test_line_numbers(self):
        lines = parse_asm("HALT\n; comment\nRET")
        assert lines[0].line == 1
        assert lines[1].line == 3


# ================================================================
# Assembler
# ================================================================

class TestAssembler:
    def _asm(self, source: str) -> dict:
        lines = parse_asm(source)
        return assemble(lines)

    def test_minimal(self):
        img = self._asm("HALT")
        assert img["version"] == "0.1"
        assert img["entrypoint"] == 0
        assert img["code"] == [["HALT"]]

    def test_label_resolves(self):
        img = self._asm("""
        start:
            JMP end
        end:
            HALT
        """)
        # JMP end -> target is instruction index 1
        assert img["code"][0] == ["JMP", 1]
        assert img["symbols"]["start"] == 0
        assert img["symbols"]["end"] == 1

    def test_li_encoding(self):
        img = self._asm("    LI R4, 42")
        assert img["code"][0] == ["LI", 4, 42]

    def test_ld_encoding(self):
        img = self._asm("    LD R4, [100]")
        assert img["code"][0] == ["LD", 4, 100]

    def test_st_encoding(self):
        img = self._asm("    ST R4, [100]")
        assert img["code"][0] == ["ST", 4, 100]

    def test_ldr_encoding(self):
        img = self._asm("    LDR R5, [R4]")
        assert img["code"][0] == ["LDR", 5, 4]

    def test_str_encoding(self):
        img = self._asm("    STR R5, [R4]")
        assert img["code"][0] == ["STR", 5, 4]

    def test_add_encoding(self):
        img = self._asm("    ADD R4, R4, R5")
        assert img["code"][0] == ["ADD", 4, 4, 5]

    def test_sub_encoding(self):
        img = self._asm("    SUB R4, R4, R5")
        assert img["code"][0] == ["SUB", 4, 4, 5]

    def test_cmp_encoding(self):
        img = self._asm("    CMP R4, R5")
        assert img["code"][0] == ["CMP", 4, 5]

    def test_mov_encoding(self):
        img = self._asm("    MOV R0, R4")
        assert img["code"][0] == ["MOV", 0, 4]

    def test_print_encoding(self):
        img = self._asm("    PRINT R4")
        assert img["code"][0] == ["PRINT", 4]

    def test_printd_encoding(self):
        img = self._asm("    PRINTD R4")
        assert img["code"][0] == ["PRINTD", 4]

    def test_ret_encoding(self):
        img = self._asm("    RET")
        assert img["code"][0] == ["RET"]

    def test_call_encoding(self):
        img = self._asm("""
        main:
            CALL main
        """)
        assert img["code"][0] == ["CALL", 0]

    def test_conditional_jumps(self):
        source = """
        start:
            JZ start
            JNZ start
            JG start
            JL start
            JGE start
            JLE start
        """
        img = self._asm(source)
        for instr in img["code"]:
            assert instr[1] == 0  # all jump to start (index 0)

    def test_duplicate_label_raises(self):
        with pytest.raises(AssemblerError, match="duplicate label"):
            self._asm("""
            foo:
            foo:
                HALT
            """)

    def test_undefined_label_raises(self):
        with pytest.raises(AssemblerError, match="undefined label"):
            self._asm("    JMP nonexistent")

    def test_symbols_in_image(self):
        img = self._asm("""
        _init:
            HALT
        main:
            RET
        """)
        assert img["symbols"]["_init"] == 0
        assert img["symbols"]["main"] == 1

    def test_multiline_program(self):
        img = self._asm("""
        _init:
            LI R4, 7
            ST R4, [100]
            CALL main
            HALT
        main:
            LD R4, [100]
            PRINT R4
            RET
        """)
        assert len(img["code"]) == 7
        assert img["symbols"]["_init"] == 0
        assert img["symbols"]["main"] == 4
