"""Tests for the SeptaLang IR and lowering."""

import pytest
from septa.ir.ir import Instr, IRProgram, Op
from septa.ir.lowering import lower
from septa.lexer.lexer import Lexer
from septa.parser.parser import Parser
from septa.semantic.analyzer import analyze


def lower_source(source: str) -> IRProgram:
    """Lex -> parse -> analyze -> lower. Returns IR program."""
    tokens = Lexer(source, "test.septa").tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    return lower(program)


def get_fn(ir: IRProgram, name: str):
    """Get an IRFunction by name."""
    for fn in ir.functions:
        if fn.name == name:
            return fn
    raise KeyError(f"no function '{name}' in IR")


def ops(fn) -> list[Op]:
    """Extract opcode sequence from a function."""
    return [instr.op for instr in fn.body]


# ================================================================
# Globals
# ================================================================

class TestGlobals:
    def test_global_word(self):
        ir = lower_source("""
        let g: word = 10;
        fn main() -> void {}
        """)
        assert len(ir.globals) == 1
        assert ir.globals[0].name == "g"
        assert ir.globals[0].slot == "global:g"
        assert ir.globals[0].init_value == 7  # 10 in base-7 = 7

    def test_global_bool_true(self):
        ir = lower_source("""
        let f: bool7 = true;
        fn main() -> void {}
        """)
        assert ir.globals[0].init_value == 6

    def test_global_bool_false(self):
        ir = lower_source("""
        let f: bool7 = false;
        fn main() -> void {}
        """)
        assert ir.globals[0].init_value == 0

    def test_multiple_globals(self):
        ir = lower_source("""
        let a: word = 1;
        let b: word = 2;
        let c: bool7 = true;
        fn main() -> void {}
        """)
        assert len(ir.globals) == 3
        assert [g.name for g in ir.globals] == ["a", "b", "c"]


# ================================================================
# Simple expressions
# ================================================================

class TestExpressions:
    def test_number_literal(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 3;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.body[0] == Instr(Op.CONST, dst="temp:0", imm=3)
        assert fn.body[1] == Instr(Op.COPY, dst="local:x", src="temp:0")

    def test_decimal_literal(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = d:42;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.body[0] == Instr(Op.CONST, dst="temp:0", imm=42)

    def test_bool_true(self):
        ir = lower_source("""
        fn main() -> void {
            let f: bool7 = true;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.body[0] == Instr(Op.CONST, dst="temp:0", imm=6)

    def test_bool_false(self):
        ir = lower_source("""
        fn main() -> void {
            let f: bool7 = false;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.body[0] == Instr(Op.CONST, dst="temp:0", imm=0)

    def test_variable_reference(self):
        """Ident lowers to the variable's slot directly, no COPY."""
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            let y: word = x;
        }
        """)
        fn = get_fn(ir, "main")
        # let x = 5: CONST temp:0, 5; COPY local:x, temp:0
        # let y = x: COPY local:y, local:x  (no temp needed)
        assert fn.body[2] == Instr(Op.COPY, dst="local:y", src="local:x")

    def test_addition(self):
        ir = lower_source("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let c: word = a + b;
        }
        """)
        fn = get_fn(ir, "main")
        # a + b -> ADD temp:2, local:a, local:b
        add_instr = [i for i in fn.body if i.op is Op.ADD][0]
        assert add_instr.src == "local:a"
        assert add_instr.src2 == "local:b"

    def test_subtraction(self):
        ir = lower_source("""
        fn main() -> void {
            let a: word = 5;
            let b: word = 3;
            let c: word = a - b;
        }
        """)
        fn = get_fn(ir, "main")
        sub_instr = [i for i in fn.body if i.op is Op.SUB][0]
        assert sub_instr.src == "local:a"
        assert sub_instr.src2 == "local:b"

    def test_unary_minus(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            let y: word = -x;
        }
        """)
        fn = get_fn(ir, "main")
        neg_instr = [i for i in fn.body if i.op is Op.NEG][0]
        assert neg_instr.src == "local:x"

    def test_unary_not(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            let f: bool7 = !x;
        }
        """)
        fn = get_fn(ir, "main")
        not_instr = [i for i in fn.body if i.op is Op.NOT][0]
        assert not_instr.src == "local:x"

    def test_comparison_gt(self):
        ir = lower_source("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let r: bool7 = a > b;
        }
        """)
        fn = get_fn(ir, "main")
        cmp = [i for i in fn.body if i.op is Op.CMP_GT][0]
        assert cmp.src == "local:a"
        assert cmp.src2 == "local:b"

    def test_all_comparisons(self):
        ir = lower_source("""
        fn main() -> void {
            let a: word = 1;
            let b: word = 2;
            let r1: bool7 = a > b;
            let r2: bool7 = a < b;
            let r3: bool7 = a >= b;
            let r4: bool7 = a <= b;
            let r5: bool7 = a == b;
            let r6: bool7 = a != b;
        }
        """)
        fn = get_fn(ir, "main")
        cmp_ops = [i.op for i in fn.body
                   if i.op.value.startswith("cmp_")]
        assert cmp_ops == [
            Op.CMP_GT, Op.CMP_LT, Op.CMP_GE,
            Op.CMP_LE, Op.CMP_EQ, Op.CMP_NE,
        ]

    def test_complex_expression(self):
        """a + b - 1 lowers left-to-right."""
        ir = lower_source("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let c: word = a + b - 1;
        }
        """)
        fn = get_fn(ir, "main")
        arith = [i for i in fn.body if i.op in (Op.ADD, Op.SUB)]
        assert len(arith) == 2
        # ADD first, then SUB
        assert arith[0].op is Op.ADD
        assert arith[1].op is Op.SUB
        # SUB uses ADD result as its left operand
        assert arith[1].src == arith[0].dst


# ================================================================
# Assignments
# ================================================================

class TestAssignments:
    def test_variable_assign(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 0;
            x = 5;
        }
        """)
        fn = get_fn(ir, "main")
        # x = 5: CONST temp:1, 5; COPY local:x, temp:1
        copies = [i for i in fn.body if i.op is Op.COPY]
        assert copies[-1].dst == "local:x"

    def test_global_assign(self):
        ir = lower_source("""
        let g: word = 0;
        fn main() -> void {
            g = 5;
        }
        """)
        fn = get_fn(ir, "main")
        copies = [i for i in fn.body if i.op is Op.COPY]
        assert copies[0].dst == "global:g"

    def test_param_assign(self):
        ir = lower_source("""
        fn foo(x: word) -> void {
            x = 5;
        }
        fn main() -> void {}
        """)
        fn = get_fn(ir, "foo")
        copies = [i for i in fn.body if i.op is Op.COPY]
        assert copies[0].dst == "param:x"

    def test_self_assign(self):
        """x = x + 1 reads x before writing."""
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            x = x + 1;
        }
        """)
        fn = get_fn(ir, "main")
        add = [i for i in fn.body if i.op is Op.ADD][0]
        assert add.src == "local:x"
        # Final COPY writes back to local:x
        copies = [i for i in fn.body if i.op is Op.COPY]
        assert copies[-1].dst == "local:x"
        assert copies[-1].src == add.dst


# ================================================================
# Store (memory) access
# ================================================================

class TestStoreAccess:
    def test_store_read(self):
        ir = lower_source("""
        fn main() -> void {
            let v: word = store[0];
        }
        """)
        fn = get_fn(ir, "main")
        loads = [i for i in fn.body if i.op is Op.MEM_LOAD]
        assert len(loads) == 1

    def test_store_write(self):
        ir = lower_source("""
        fn main() -> void {
            store[0] = d:42;
        }
        """)
        fn = get_fn(ir, "main")
        stores = [i for i in fn.body if i.op is Op.MEM_STORE]
        assert len(stores) == 1

    def test_store_dynamic_index(self):
        """store[i + 1] uses computed address."""
        ir = lower_source("""
        fn main() -> void {
            let i: word = 3;
            let v: word = store[i + 1];
        }
        """)
        fn = get_fn(ir, "main")
        # i + 1 -> ADD; then MEM_LOAD from result
        add = [i for i in fn.body if i.op is Op.ADD][0]
        load = [i for i in fn.body if i.op is Op.MEM_LOAD][0]
        assert load.src == add.dst

    def test_store_write_dynamic(self):
        ir = lower_source("""
        fn main() -> void {
            let i: word = 3;
            store[i] = d:42;
        }
        """)
        fn = get_fn(ir, "main")
        stores = [i for i in fn.body if i.op is Op.MEM_STORE]
        assert len(stores) == 1
        assert stores[0].dst == "local:i"  # addr slot is the variable

    def test_store_read_write(self):
        """store[0] = store[0] + 1 — read then write."""
        ir = lower_source("""
        fn main() -> void {
            store[0] = store[0] + 1;
        }
        """)
        fn = get_fn(ir, "main")
        assert Op.MEM_LOAD in ops(fn)
        assert Op.MEM_STORE in ops(fn)
        assert Op.ADD in ops(fn)


# ================================================================
# If / Else
# ================================================================

class TestIfElse:
    def test_if_no_else(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            if x { print(1); }
        }
        """)
        fn = get_fn(ir, "main")
        o = ops(fn)
        # JUMP_Z then ... LABEL
        assert Op.JUMP_Z in o
        assert Op.LABEL in o
        # Only one label (end)
        labels = [i for i in fn.body if i.op is Op.LABEL]
        assert len(labels) == 1
        # JUMP_Z references the end label
        jz = [i for i in fn.body if i.op is Op.JUMP_Z][0]
        assert jz.label == labels[0].label

    def test_if_else(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                print(1);
            } else {
                print(0);
            }
        }
        """)
        fn = get_fn(ir, "main")
        o = ops(fn)
        # JUMP_Z, then body, JUMP, LABEL (else), else body, LABEL (end)
        assert Op.JUMP_Z in o
        assert Op.JUMP in o
        labels = [i for i in fn.body if i.op is Op.LABEL]
        assert len(labels) == 2  # else_label and end_label
        jumps = [i for i in fn.body if i.op is Op.JUMP]
        # Unconditional jump goes to end label
        assert jumps[0].label == labels[1].label

    def test_nested_if(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 {
                if x > 4 {
                    print(x);
                }
            }
        }
        """)
        fn = get_fn(ir, "main")
        labels = [i for i in fn.body if i.op is Op.LABEL]
        jz_instrs = [i for i in fn.body if i.op is Op.JUMP_Z]
        assert len(labels) == 2
        assert len(jz_instrs) == 2


# ================================================================
# While
# ================================================================

class TestWhile:
    def test_simple_while(self):
        ir = lower_source("""
        fn main() -> void {
            let i: word = 5;
            while i > 0 {
                i = i - 1;
            }
        }
        """)
        fn = get_fn(ir, "main")
        o = ops(fn)
        # Pattern: LABEL(loop), ..cond.., JUMP_Z(end), ..body.., JUMP(loop), LABEL(end)
        labels = [i for i in fn.body if i.op is Op.LABEL]
        assert len(labels) == 2  # loop and end
        jumps = [i for i in fn.body if i.op is Op.JUMP]
        assert len(jumps) == 1
        # Unconditional jump goes back to loop label
        assert jumps[0].label == labels[0].label
        # Conditional jump goes to end label
        jz = [i for i in fn.body if i.op is Op.JUMP_Z][0]
        assert jz.label == labels[1].label

    def test_while_with_bool_condition(self):
        ir = lower_source("""
        fn main() -> void {
            let running: bool7 = true;
            while running {
                running = false;
            }
        }
        """)
        fn = get_fn(ir, "main")
        jz = [i for i in fn.body if i.op is Op.JUMP_Z][0]
        # Condition is the variable itself
        assert jz.src == "local:running"


# ================================================================
# Function calls
# ================================================================

class TestFunctionCalls:
    def test_call_with_args(self):
        ir = lower_source("""
        fn add(a: word, b: word) -> word {
            return a + b;
        }
        fn main() -> void {
            let r: word = add(3, 4);
        }
        """)
        fn = get_fn(ir, "main")
        args = [i for i in fn.body if i.op is Op.ARG]
        assert len(args) == 2
        assert args[0].imm == 0
        assert args[1].imm == 1
        calls = [i for i in fn.body if i.op is Op.CALL]
        assert len(calls) == 1
        assert calls[0].label == "add"
        assert calls[0].dst != ""  # non-void return

    def test_call_void_function(self):
        ir = lower_source("""
        fn noop() -> void {}
        fn main() -> void {
            noop();
        }
        """)
        fn = get_fn(ir, "main")
        calls = [i for i in fn.body if i.op is Op.CALL]
        assert len(calls) == 1
        assert calls[0].label == "noop"
        assert calls[0].dst == ""  # void return

    def test_call_no_args(self):
        ir = lower_source("""
        fn seven() -> word { return 10; }
        fn main() -> void {
            let x: word = seven();
        }
        """)
        fn = get_fn(ir, "main")
        args = [i for i in fn.body if i.op is Op.ARG]
        assert len(args) == 0

    def test_nested_call(self):
        ir = lower_source("""
        fn id(x: word) -> word { return x; }
        fn main() -> void {
            let r: word = id(id(5));
        }
        """)
        fn = get_fn(ir, "main")
        calls = [i for i in fn.body if i.op is Op.CALL]
        assert len(calls) == 2
        # Inner call result is arg to outer call
        args = [i for i in fn.body if i.op is Op.ARG]
        assert args[1].src == calls[0].dst

    def test_call_arg_evaluation_order(self):
        """Arguments are evaluated left to right."""
        ir = lower_source("""
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {
            let r: word = add(1 + 2, 3 + 4);
        }
        """)
        fn = get_fn(ir, "main")
        adds = [i for i in fn.body if i.op is Op.ADD]
        args = [i for i in fn.body if i.op is Op.ARG]
        # First ADD result -> ARG 0, second ADD result -> ARG 1
        assert args[0].src == adds[0].dst
        assert args[1].src == adds[1].dst


# ================================================================
# Builtins
# ================================================================

class TestBuiltins:
    def test_print(self):
        ir = lower_source("""
        fn main() -> void {
            print(d:42);
        }
        """)
        fn = get_fn(ir, "main")
        prints = [i for i in fn.body if i.op is Op.PRINT]
        assert len(prints) == 1

    def test_printd(self):
        ir = lower_source("""
        fn main() -> void {
            printd(d:42);
        }
        """)
        fn = get_fn(ir, "main")
        printds = [i for i in fn.body if i.op is Op.PRINTD]
        assert len(printds) == 1

    def test_halt(self):
        ir = lower_source("""
        fn main() -> void {
            halt();
        }
        """)
        fn = get_fn(ir, "main")
        halts = [i for i in fn.body if i.op is Op.HALT]
        assert len(halts) == 1

    def test_builtins_not_lowered_as_calls(self):
        """Builtins must NOT produce ARG/CALL instructions."""
        ir = lower_source("""
        fn main() -> void {
            print(1);
            printd(2);
            halt();
        }
        """)
        fn = get_fn(ir, "main")
        assert Op.ARG not in ops(fn)
        assert Op.CALL not in ops(fn)

    def test_print_with_expression(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 3;
            print(x + 1);
        }
        """)
        fn = get_fn(ir, "main")
        prints = [i for i in fn.body if i.op is Op.PRINT]
        adds = [i for i in fn.body if i.op is Op.ADD]
        # print receives the ADD result
        assert prints[0].src == adds[0].dst


# ================================================================
# Returns
# ================================================================

class TestReturns:
    def test_return_value(self):
        ir = lower_source("""
        fn seven() -> word { return 10; }
        fn main() -> void {}
        """)
        fn = get_fn(ir, "seven")
        rets = [i for i in fn.body if i.op is Op.RETURN]
        assert len(rets) == 1

    def test_return_void_explicit(self):
        ir = lower_source("""
        fn main() -> void {
            return;
        }
        """)
        fn = get_fn(ir, "main")
        rets = [i for i in fn.body if i.op is Op.RETURN_VOID]
        assert len(rets) >= 1

    def test_implicit_return_void(self):
        """Void functions without explicit return get RETURN_VOID at end."""
        ir = lower_source("""
        fn main() -> void {
            print(1);
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.body[-1].op is Op.RETURN_VOID

    def test_return_expression(self):
        ir = lower_source("""
        fn add(a: word, b: word) -> word {
            return a + b;
        }
        fn main() -> void {}
        """)
        fn = get_fn(ir, "add")
        adds = [i for i in fn.body if i.op is Op.ADD]
        rets = [i for i in fn.body if i.op is Op.RETURN]
        assert rets[0].src == adds[0].dst


# ================================================================
# Labels and temporaries (stability)
# ================================================================

class TestLabelAndTempStability:
    def test_labels_are_deterministic(self):
        """Same source always produces same labels."""
        source = """
        fn main() -> void {
            let x: word = 5;
            if x > 3 { print(1); }
            while x > 0 { x = x - 1; }
        }
        """
        ir1 = lower_source(source)
        ir2 = lower_source(source)
        fn1 = get_fn(ir1, "main")
        fn2 = get_fn(ir2, "main")
        labels1 = [(i.op, i.label) for i in fn1.body if i.label]
        labels2 = [(i.op, i.label) for i in fn2.body if i.label]
        assert labels1 == labels2

    def test_temps_are_deterministic(self):
        """Same source always produces same temp slots."""
        source = """
        fn main() -> void {
            let a: word = 1;
            let b: word = 2;
            let c: word = a + b;
        }
        """
        ir1 = lower_source(source)
        ir2 = lower_source(source)
        fn1 = get_fn(ir1, "main")
        fn2 = get_fn(ir2, "main")
        assert fn1.body == fn2.body

    def test_label_counter_per_function(self):
        """Each function starts label counting from L0."""
        ir = lower_source("""
        fn foo() -> void {
            if true { print(1); }
        }
        fn bar() -> void {
            if true { print(2); }
        }
        fn main() -> void {}
        """)
        fn_foo = get_fn(ir, "foo")
        fn_bar = get_fn(ir, "bar")
        foo_labels = [i.label for i in fn_foo.body if i.op is Op.LABEL]
        bar_labels = [i.label for i in fn_bar.body if i.op is Op.LABEL]
        # Both start from L0
        assert foo_labels[0] == "L0"
        assert bar_labels[0] == "L0"

    def test_temp_counter_per_function(self):
        """Each function starts temp counting from 0."""
        ir = lower_source("""
        fn foo() -> void { let x: word = 1; }
        fn bar() -> void { let y: word = 2; }
        fn main() -> void {}
        """)
        fn_foo = get_fn(ir, "foo")
        fn_bar = get_fn(ir, "bar")
        assert fn_foo.body[0].dst == "temp:0"
        assert fn_bar.body[0].dst == "temp:0"

    def test_temp_count_tracked(self):
        ir = lower_source("""
        fn main() -> void {
            let a: word = 1;
            let b: word = 2;
            let c: word = a + b;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.temp_count == 3  # temp:0(1), temp:1(2), temp:2(a+b)


# ================================================================
# Local slot generation
# ================================================================

class TestLocalSlots:
    def test_simple_locals(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 1;
            let y: word = 2;
        }
        """)
        fn = get_fn(ir, "main")
        assert fn.local_slots == ["local:x", "local:y"]

    def test_param_slots(self):
        ir = lower_source("""
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void {}
        """)
        fn = get_fn(ir, "add")
        assert fn.params == ["param:a", "param:b"]

    def test_shadowed_locals(self):
        """Shadowed variable gets unique slot name."""
        ir = lower_source("""
        fn main() -> void {
            let x: word = 1;
            if true {
                let x: word = 2;
                print(x);
            }
            print(x);
        }
        """)
        fn = get_fn(ir, "main")
        assert "local:x" in fn.local_slots
        assert "local:x_1" in fn.local_slots

    def test_shadowed_local_uses_correct_slot(self):
        """Inner scope reads from shadowed slot, outer reads from original."""
        ir = lower_source("""
        fn main() -> void {
            let x: word = 1;
            if true {
                let x: word = 2;
                print(x);
            }
            print(x);
        }
        """)
        fn = get_fn(ir, "main")
        prints = [i for i in fn.body if i.op is Op.PRINT]
        # First print (inner): uses local:x_1
        assert prints[0].src == "local:x_1"
        # Second print (outer): uses local:x
        assert prints[1].src == "local:x"

    def test_deeply_shadowed(self):
        ir = lower_source("""
        fn main() -> void {
            let x: word = 1;
            if true {
                let x: word = 2;
                if true {
                    let x: word = 3;
                }
            }
        }
        """)
        fn = get_fn(ir, "main")
        assert "local:x" in fn.local_slots
        assert "local:x_1" in fn.local_slots
        assert "local:x_2" in fn.local_slots

    def test_global_reference_in_function(self):
        ir = lower_source("""
        let g: word = 10;
        fn main() -> void {
            print(g);
        }
        """)
        fn = get_fn(ir, "main")
        prints = [i for i in fn.body if i.op is Op.PRINT]
        assert prints[0].src == "global:g"

    def test_param_reference(self):
        ir = lower_source("""
        fn foo(x: word) -> void { print(x); }
        fn main() -> void {}
        """)
        fn = get_fn(ir, "foo")
        prints = [i for i in fn.body if i.op is Op.PRINT]
        assert prints[0].src == "param:x"


# ================================================================
# Full programs (integration)
# ================================================================

class TestFullPrograms:
    def test_countdown(self):
        ir = lower_source("""
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """)
        fn = get_fn(ir, "main")
        o = ops(fn)
        # Has loop structure and print
        assert Op.LABEL in o
        assert Op.JUMP_Z in o
        assert Op.JUMP in o
        assert Op.PRINT in o
        assert Op.SUB in o

    def test_function_with_return(self):
        ir = lower_source("""
        fn double(x: word) -> word {
            return x + x;
        }
        fn main() -> void {
            let r: word = double(3);
            print(r);
        }
        """)
        fn_double = get_fn(ir, "double")
        fn_main = get_fn(ir, "main")
        # double has ADD and RETURN
        assert Op.ADD in ops(fn_double)
        assert Op.RETURN in ops(fn_double)
        # main has ARG, CALL, PRINT
        assert Op.ARG in ops(fn_main)
        assert Op.CALL in ops(fn_main)
        assert Op.PRINT in ops(fn_main)

    def test_memory_operations(self):
        ir = lower_source("""
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """)
        fn = get_fn(ir, "main")
        stores = [i for i in fn.body if i.op is Op.MEM_STORE]
        loads = [i for i in fn.body if i.op is Op.MEM_LOAD]
        assert len(stores) == 2
        assert len(loads) == 2

    def test_if_else_with_globals(self):
        ir = lower_source("""
        let threshold: word = 5;
        fn main() -> void {
            let x: word = 10;
            if x > threshold {
                print(1);
            } else {
                print(0);
            }
        }
        """)
        fn = get_fn(ir, "main")
        cmp = [i for i in fn.body if i.op is Op.CMP_GT][0]
        assert cmp.src == "local:x"
        assert cmp.src2 == "global:threshold"

    def test_forward_call(self):
        ir = lower_source("""
        fn main() -> void {
            print(seven());
        }
        fn seven() -> word {
            return 10;
        }
        """)
        fn = get_fn(ir, "main")
        calls = [i for i in fn.body if i.op is Op.CALL]
        assert calls[0].label == "seven"


# ================================================================
# IR formatting (__str__)
# ================================================================

class TestFormatting:
    def test_instr_str(self):
        assert str(Instr(Op.CONST, dst="temp:0", imm=42)) == "  const temp:0, 42"
        assert str(Instr(Op.COPY, dst="local:x", src="temp:0")) == \
            "  copy local:x, temp:0"
        assert str(Instr(Op.ADD, dst="temp:1", src="local:a", src2="local:b")) == \
            "  add temp:1, local:a, local:b"
        assert str(Instr(Op.LABEL, label="L0")) == "L0:"
        assert str(Instr(Op.JUMP, label="L1")) == "  jump L1"
        assert str(Instr(Op.JUMP_Z, src="temp:0", label="L1")) == \
            "  jump_z temp:0, L1"
        assert str(Instr(Op.RETURN_VOID)) == "  return_void"
        assert str(Instr(Op.HALT)) == "  halt"
        assert str(Instr(Op.MEM_LOAD, dst="temp:0", src="temp:1")) == \
            "  mem_load temp:0, [temp:1]"
        assert str(Instr(Op.MEM_STORE, dst="temp:0", src="temp:1")) == \
            "  mem_store [temp:0], temp:1"

    def test_function_str(self):
        ir = lower_source("fn main() -> void { print(1); }")
        fn = get_fn(ir, "main")
        s = str(fn)
        assert "fn main:" in s
        assert "print" in s

    def test_program_str(self):
        ir = lower_source("""
        let g: word = 10;
        fn main() -> void { print(g); }
        """)
        s = str(ir)
        assert "global:g = 7" in s
        assert "fn main:" in s
