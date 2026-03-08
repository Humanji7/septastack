"""Tests for the SeptaLang semantic analyzer."""

import pytest
from septa.common.errors import SemanticError
from septa.lexer.lexer import Lexer
from septa.parser.parser import Parser
from septa.semantic.analyzer import analyze


def check(source: str) -> None:
    """Lex → parse → analyze. Raises on any error."""
    tokens = Lexer(source, "test.septa").tokenize()
    program = Parser(tokens).parse()
    analyze(program)


def check_err(source: str, match: str) -> None:
    """Assert that analysis raises SemanticError matching pattern."""
    with pytest.raises(SemanticError, match=match):
        check(source)


# ================================================================
# Valid programs
# ================================================================

class TestValidPrograms:
    def test_minimal(self):
        check("fn main() -> void {}")

    def test_hello(self):
        check("fn main() -> void { print(d:42); }")

    def test_printd(self):
        check("fn main() -> void { printd(d:100); }")

    def test_halt(self):
        check("fn main() -> void { halt(); }")

    def test_let_and_print(self):
        check("""
        fn main() -> void {
            let x: word = 3;
            print(x);
        }
        """)

    def test_arithmetic(self):
        check("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let sum: word = a + b;
            let diff: word = a - b;
            print(sum);
        }
        """)

    def test_comparisons(self):
        check("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let g: bool7 = a > b;
            let l: bool7 = a < b;
            let ge: bool7 = a >= b;
            let le: bool7 = a <= b;
        }
        """)

    def test_equality_word(self):
        check("""
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let eq: bool7 = a == b;
            let ne: bool7 = a != b;
        }
        """)

    def test_equality_bool7(self):
        check("""
        fn main() -> void {
            let a: bool7 = true;
            let b: bool7 = false;
            let eq: bool7 = a == b;
        }
        """)

    def test_if_with_word_condition(self):
        check("""
        fn main() -> void {
            let x: word = 5;
            if x { print(x); }
        }
        """)

    def test_if_with_bool7_condition(self):
        check("""
        fn main() -> void {
            let x: word = 5;
            if x > 3 { print(1); } else { print(0); }
        }
        """)

    def test_while(self):
        check("""
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """)

    def test_return_word(self):
        check("""
        fn add(a: word, b: word) -> word {
            return a + b;
        }
        fn main() -> void {
            let r: word = add(3, 4);
            print(r);
        }
        """)

    def test_return_void_explicit(self):
        check("""
        fn main() -> void {
            return;
        }
        """)

    def test_multiple_functions(self):
        check("""
        fn double(x: word) -> word {
            return x + x;
        }
        fn main() -> void {
            print(double(3));
        }
        """)

    def test_store_read_write(self):
        check("""
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """)

    def test_unary_minus(self):
        check("""
        fn main() -> void {
            let x: word = 5;
            let y: word = -x;
            print(y);
        }
        """)

    def test_unary_not_word(self):
        check("""
        fn main() -> void {
            let x: word = 5;
            let f: bool7 = !x;
        }
        """)

    def test_unary_not_bool7(self):
        check("""
        fn main() -> void {
            let f: bool7 = !true;
        }
        """)

    def test_global_variable(self):
        check("""
        let g: word = 10;
        fn main() -> void {
            print(g);
        }
        """)

    def test_global_bool(self):
        check("""
        let flag: bool7 = true;
        fn main() -> void {
            let x: bool7 = flag;
        }
        """)

    def test_nested_if_while(self):
        check("""
        fn main() -> void {
            let i: word = 10;
            while i > 0 {
                if i > 5 {
                    print(i);
                } else {
                    printd(i);
                }
                i = i - 1;
            }
        }
        """)

    def test_forward_call(self):
        """Functions declared after caller should be resolvable (two-pass)."""
        check("""
        fn main() -> void {
            print(foo());
        }
        fn foo() -> word {
            return 1;
        }
        """)

    def test_all_builtins(self):
        check("""
        fn main() -> void {
            print(0);
            printd(0);
            halt();
        }
        """)

    def test_while_with_bool_condition(self):
        check("""
        fn main() -> void {
            let running: bool7 = true;
            while running {
                running = false;
            }
        }
        """)


# ================================================================
# Scope nesting and shadowing
# ================================================================

class TestScopeAndShadowing:
    def test_local_shadows_global(self):
        check("""
        let x: word = 1;
        fn main() -> void {
            let x: word = 2;
            print(x);
        }
        """)

    def test_if_block_shadows_outer(self):
        check("""
        fn main() -> void {
            let x: word = 1;
            if true {
                let x: word = 2;
                print(x);
            }
            print(x);
        }
        """)

    def test_while_block_shadows_outer(self):
        check("""
        fn main() -> void {
            let x: word = 1;
            while x > 0 {
                let x: word = 0;
                print(x);
            }
        }
        """)

    def test_nested_blocks_shadow(self):
        check("""
        fn main() -> void {
            let x: word = 1;
            if true {
                let x: word = 2;
                if true {
                    let x: word = 3;
                    print(x);
                }
            }
        }
        """)

    def test_param_shadows_global(self):
        check("""
        let x: word = 1;
        fn foo(x: word) -> void {
            print(x);
        }
        fn main() -> void {
            foo(2);
        }
        """)

    def test_if_scope_isolation(self):
        """Variable declared in if-block is not visible outside."""
        check_err("""
        fn main() -> void {
            if true {
                let y: word = 1;
            }
            print(y);
        }
        """, "undefined variable 'y'")

    def test_while_scope_isolation(self):
        check_err("""
        fn main() -> void {
            while true {
                let z: word = 1;
            }
            print(z);
        }
        """, "undefined variable 'z'")


# ================================================================
# Duplicate declarations
# ================================================================

class TestDuplicateDeclarations:
    def test_duplicate_function(self):
        check_err("""
        fn foo() -> void {}
        fn foo() -> void {}
        fn main() -> void {}
        """, "duplicate declaration of 'foo'")

    def test_duplicate_global(self):
        check_err("""
        let x: word = 1;
        let x: word = 2;
        fn main() -> void {}
        """, "duplicate declaration of 'x'")

    def test_global_and_function_same_name(self):
        check_err("""
        let foo: word = 1;
        fn foo() -> void {}
        fn main() -> void {}
        """, "duplicate declaration of 'foo'")

    def test_function_and_global_same_name(self):
        check_err("""
        fn foo() -> void {}
        let foo: word = 1;
        fn main() -> void {}
        """, "duplicate declaration of 'foo'")

    def test_redeclare_builtin(self):
        check_err("""
        fn print() -> void {}
        fn main() -> void {}
        """, "duplicate declaration of 'print'")

    def test_duplicate_let_same_scope(self):
        check_err("""
        fn main() -> void {
            let x: word = 1;
            let x: word = 2;
        }
        """, "redeclaration of 'x'")

    def test_duplicate_param_same_name(self):
        check_err("""
        fn foo(a: word, a: word) -> void {}
        fn main() -> void {}
        """, "duplicate parameter 'a'")

    def test_param_and_let_same_scope(self):
        """Parameter and top-level let in function share scope."""
        check_err("""
        fn foo(x: word) -> void {
            let x: word = 1;
        }
        fn main() -> void {}
        """, "redeclaration of 'x'")


# ================================================================
# Wrong arity
# ================================================================

class TestArity:
    def test_too_few_args(self):
        check_err("""
        fn add(a: word, b: word) -> word { return a + b; }
        fn main() -> void { print(add(1)); }
        """, "expects 2 argument.*got 1")

    def test_too_many_args(self):
        check_err("""
        fn id(x: word) -> word { return x; }
        fn main() -> void { print(id(1, 2)); }
        """, "expects 1 argument.*got 2")

    def test_builtin_too_few(self):
        check_err("""
        fn main() -> void { print(); }
        """, "expects 1 argument.*got 0")

    def test_builtin_too_many(self):
        check_err("""
        fn main() -> void { print(1, 2); }
        """, "expects 1 argument.*got 2")

    def test_halt_with_args(self):
        check_err("""
        fn main() -> void { halt(1); }
        """, "expects 0 argument.*got 1")


# ================================================================
# Wrong return type
# ================================================================

class TestReturnType:
    def test_return_value_from_void(self):
        check_err("""
        fn main() -> void { return 5; }
        """, "void function cannot return a value")

    def test_return_void_from_word(self):
        check_err("""
        fn foo() -> word { return; }
        fn main() -> void {}
        """, "non-void function must return a value")

    def test_return_wrong_type(self):
        check_err("""
        fn foo() -> word { return true; }
        fn main() -> void {}
        """, "return type mismatch.*expected 'word'.*got 'bool7'")

    def test_return_bool_from_word_fn(self):
        check_err("""
        fn foo() -> bool7 { return 5; }
        fn main() -> void {}
        """, "return type mismatch.*expected 'bool7'.*got 'word'")


# ================================================================
# Undefined names
# ================================================================

class TestUndefined:
    def test_undefined_variable(self):
        check_err("""
        fn main() -> void { print(x); }
        """, "undefined variable 'x'")

    def test_undefined_function(self):
        check_err("""
        fn main() -> void { foo(); }
        """, "undefined function 'foo'")

    def test_undefined_in_expression(self):
        check_err("""
        fn main() -> void { let y: word = x + 1; }
        """, "undefined variable 'x'")

    def test_undefined_assign_target(self):
        check_err("""
        fn main() -> void { x = 5; }
        """, "undefined variable 'x'")


# ================================================================
# Invalid global initializers
# ================================================================

class TestGlobalInitializers:
    def test_global_with_variable_ref(self):
        check_err("""
        let x: word = 1;
        let y: word = x;
        fn main() -> void {}
        """, "global initializer must be a constant")

    def test_global_with_function_call(self):
        check_err("""
        fn foo() -> word { return 1; }
        let x: word = foo();
        fn main() -> void {}
        """, "global initializer must be a constant")

    def test_global_with_binary_expr(self):
        check_err("""
        let x: word = 1 + 2;
        fn main() -> void {}
        """, "global initializer must be a constant")

    def test_global_with_unary_expr(self):
        check_err("""
        let x: word = -1;
        fn main() -> void {}
        """, "global initializer must be a constant")

    def test_global_type_mismatch(self):
        check_err("""
        let x: word = true;
        fn main() -> void {}
        """, "type mismatch in global 'x'.*declared 'word'.*'bool7'")

    def test_global_bool_type_mismatch(self):
        check_err("""
        let x: bool7 = 5;
        fn main() -> void {}
        """, "type mismatch in global 'x'.*declared 'bool7'.*'word'")

    def test_valid_global_word(self):
        check("""
        let x: word = 0;
        fn main() -> void {}
        """)

    def test_valid_global_bool(self):
        check("""
        let f: bool7 = false;
        fn main() -> void {}
        """)


# ================================================================
# Builtin calls
# ================================================================

class TestBuiltins:
    def test_print_word(self):
        check("fn main() -> void { print(5); }")

    def test_printd_word(self):
        check("fn main() -> void { printd(d:42); }")

    def test_halt_no_args(self):
        check("fn main() -> void { halt(); }")

    def test_print_bool_error(self):
        check_err("""
        fn main() -> void { print(true); }
        """, "argument 1 of 'print'.*expected 'word'.*got 'bool7'")

    def test_printd_bool_error(self):
        check_err("""
        fn main() -> void { printd(false); }
        """, "argument 1 of 'printd'.*expected 'word'.*got 'bool7'")


# ================================================================
# Missing or invalid main
# ================================================================

class TestMain:
    def test_missing_main(self):
        check_err("""
        fn foo() -> void {}
        """, "missing 'main' function")

    def test_main_with_params(self):
        check_err("""
        fn main(x: word) -> void {}
        """, "'main' must take no parameters")

    def test_main_returns_word(self):
        check_err("""
        fn main() -> word { return 0; }
        """, "'main' must return void")

    def test_empty_program_no_main(self):
        check_err("", "missing 'main' function")


# ================================================================
# Type errors
# ================================================================

class TestTypeErrors:
    def test_add_bool_operands(self):
        check_err("""
        fn main() -> void {
            let x: bool7 = true + false;
        }
        """, "arithmetic requires word operands")

    def test_subtract_bool_operands(self):
        check_err("""
        fn main() -> void {
            let x: word = true - false;
        }
        """, "arithmetic requires word operands")

    def test_ordered_cmp_bool(self):
        check_err("""
        fn main() -> void {
            let r: bool7 = true > false;
        }
        """, "ordered comparison requires word operands")

    def test_equality_mixed_types(self):
        check_err("""
        fn main() -> void {
            let x: word = 5;
            let y: bool7 = true;
            let r: bool7 = x == y;
        }
        """, "equality requires same types.*'word'.*'bool7'")

    def test_let_type_mismatch(self):
        check_err("""
        fn main() -> void {
            let x: word = true;
        }
        """, "type mismatch in let 'x'.*'word'.*'bool7'")

    def test_assign_type_mismatch(self):
        check_err("""
        fn main() -> void {
            let x: word = 0;
            x = true;
        }
        """, "type mismatch in assignment.*'word'.*'bool7'")

    def test_if_void_condition(self):
        check_err("""
        fn main() -> void {
            if halt() {}
        }
        """, "condition cannot be void")

    def test_while_void_condition(self):
        check_err("""
        fn main() -> void {
            while halt() {}
        }
        """, "condition cannot be void")

    def test_store_bool_index(self):
        check_err("""
        fn main() -> void {
            let x: word = store[true];
        }
        """, "store index must be word.*'bool7'")

    def test_store_assign_bool_value(self):
        check_err("""
        fn main() -> void {
            store[0] = true;
        }
        """, "type mismatch in assignment.*'word'.*'bool7'")

    def test_unary_minus_on_bool(self):
        check_err("""
        fn main() -> void {
            let x: word = -true;
        }
        """, "unary '-' requires word.*'bool7'")

    def test_argument_type_mismatch(self):
        check_err("""
        fn foo(x: word) -> word { return x; }
        fn main() -> void {
            foo(true);
        }
        """, "argument 1 of 'foo'.*expected 'word'.*got 'bool7'")

    def test_use_void_in_let(self):
        check_err("""
        fn main() -> void {
            let x: word = halt();
        }
        """, "type mismatch in let 'x'.*'word'.*'void'")

    def test_void_equality(self):
        check_err("""
        fn main() -> void {
            let r: bool7 = halt() == halt();
        }
        """, "cannot compare void")

    def test_store_assign_bool_index(self):
        check_err("""
        fn main() -> void {
            store[true] = 5;
        }
        """, "store index must be word.*'bool7'")


# ================================================================
# Edge cases
# ================================================================

class TestEdgeCases:
    def test_function_call_result_type(self):
        """Using function return value in expression."""
        check("""
        fn seven() -> word { return 10; }
        fn main() -> void {
            let x: word = seven() + 1;
            print(x);
        }
        """)

    def test_chained_comparison(self):
        """Chained binary expressions produce correct types."""
        check("""
        fn main() -> void {
            let x: word = 1;
            let y: word = 2;
            let z: word = 3;
            let r: bool7 = x + y > z;
        }
        """)

    def test_nested_function_calls(self):
        check("""
        fn id(x: word) -> word { return x; }
        fn main() -> void {
            print(id(id(5)));
        }
        """)

    def test_expr_stmt_void_ok(self):
        """Expression statement with void result is fine."""
        check("""
        fn main() -> void {
            halt();
        }
        """)

    def test_expr_stmt_word_ok(self):
        """Expression statement with non-void is fine (unused value)."""
        check("""
        fn id(x: word) -> word { return x; }
        fn main() -> void {
            id(5);
        }
        """)

    def test_global_visible_in_all_functions(self):
        check("""
        let g: word = 10;
        fn foo() -> void { print(g); }
        fn bar() -> void { print(g); }
        fn main() -> void {
            foo();
            bar();
        }
        """)

    def test_assign_to_global(self):
        check("""
        let g: word = 0;
        fn main() -> void {
            g = 5;
            print(g);
        }
        """)

    def test_store_with_expr_index(self):
        check("""
        fn main() -> void {
            let i: word = 3;
            store[i + 1] = d:42;
            let v: word = store[i + 1];
            printd(v);
        }
        """)


# ================================================================
# addr alias (v0.1: addr resolves to word)
# ================================================================

class TestAddrAlias:
    def test_addr_let_with_number(self):
        """addr is word, so number literal initializer is valid."""
        check("""
        fn main() -> void {
            let a: addr = 0;
            print(a);
        }
        """)

    def test_addr_param(self):
        """addr parameter accepts word argument."""
        check("""
        fn write_at(a: addr, v: word) -> void {
            store[a] = v;
        }
        fn main() -> void {
            write_at(d:100, d:42);
        }
        """)

    def test_addr_return(self):
        """Function can return addr (= word)."""
        check("""
        fn base() -> addr {
            return d:1000;
        }
        fn main() -> void {
            let b: word = base();
            print(b);
        }
        """)

    def test_addr_arithmetic(self):
        """addr values support arithmetic (since addr = word)."""
        check("""
        fn main() -> void {
            let base: addr = d:100;
            let offset: word = 5;
            let target: addr = base + offset;
            store[target] = d:42;
        }
        """)

    def test_addr_comparison(self):
        """addr values support ordered comparison (word semantics)."""
        check("""
        fn main() -> void {
            let a: addr = d:100;
            let b: addr = d:200;
            let r: bool7 = a < b;
        }
        """)

    def test_addr_equality(self):
        """addr == addr works (both resolve to word)."""
        check("""
        fn main() -> void {
            let a: addr = d:100;
            let b: addr = d:100;
            let eq: bool7 = a == b;
        }
        """)

    def test_addr_word_interop(self):
        """addr and word are interchangeable."""
        check("""
        fn takes_word(x: word) -> word { return x; }
        fn main() -> void {
            let a: addr = d:100;
            let w: word = takes_word(a);
            let b: addr = w;
            print(b);
        }
        """)

    def test_addr_store_index(self):
        """addr can be used as store index (since it is word)."""
        check("""
        fn main() -> void {
            let ptr: addr = 0;
            store[ptr] = d:42;
            let v: word = store[ptr];
            print(v);
        }
        """)

    def test_global_addr(self):
        """Global variable with addr type."""
        check("""
        let base: addr = d:1000;
        fn main() -> void {
            print(base);
        }
        """)
