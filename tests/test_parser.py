"""Tests for the SeptaLang recursive descent parser."""

import pytest
from septa.common.errors import ParserError
from septa.lexer.lexer import Lexer
from septa.parser.ast import (
    AssignStmt,
    BinaryExpr,
    Block,
    BoolLiteral,
    ExprStmt,
    FnCall,
    FunctionDecl,
    GlobalDecl,
    Ident,
    IfStmt,
    LetStmt,
    NumberLiteral,
    Program,
    ReturnStmt,
    StoreAccess,
    UnaryExpr,
    WhileStmt,
)
from septa.parser.parser import Parser


def parse(source: str) -> Program:
    """Helper: lex + parse source string."""
    tokens = Lexer(source, "test.septa").tokenize()
    return Parser(tokens).parse()


def parse_expr(source: str):
    """Helper: parse a single expression from 'fn _()->void{ expr; }'."""
    prog = parse(f"fn _() -> void {{ {source}; }}")
    assert len(prog.declarations) == 1
    fn = prog.declarations[0]
    assert isinstance(fn, FunctionDecl)
    assert len(fn.body.statements) == 1
    stmt = fn.body.statements[0]
    assert isinstance(stmt, ExprStmt)
    return stmt.expr


def parse_stmt(source: str):
    """Helper: parse a single statement inside a function body."""
    prog = parse(f"fn _() -> void {{ {source} }}")
    assert len(prog.declarations) == 1
    fn = prog.declarations[0]
    assert isinstance(fn, FunctionDecl)
    assert len(fn.body.statements) == 1
    return fn.body.statements[0]


# --- Programs ---

class TestProgram:
    def test_empty_program(self):
        prog = parse("")
        assert isinstance(prog, Program)
        assert prog.declarations == []

    def test_single_function(self):
        prog = parse("fn main() -> void {}")
        assert len(prog.declarations) == 1
        fn = prog.declarations[0]
        assert isinstance(fn, FunctionDecl)
        assert fn.name == "main"
        assert fn.params == []
        assert fn.return_type == "void"
        assert fn.body.statements == []

    def test_multiple_functions(self):
        source = """
        fn foo() -> word { return 1; }
        fn bar() -> void {}
        """
        prog = parse(source)
        assert len(prog.declarations) == 2
        assert prog.declarations[0].name == "foo"
        assert prog.declarations[1].name == "bar"

    def test_global_decl(self):
        source = "let x: word = 10;"
        prog = parse(source)
        assert len(prog.declarations) == 1
        g = prog.declarations[0]
        assert isinstance(g, GlobalDecl)
        assert g.name == "x"
        assert g.type_name == "word"
        assert isinstance(g.value, NumberLiteral)
        assert g.value.value == 7  # 10 in base-7 = 7

    def test_mixed_declarations(self):
        source = """
        let g: word = 0;
        fn main() -> void {}
        """
        prog = parse(source)
        assert len(prog.declarations) == 2
        assert isinstance(prog.declarations[0], GlobalDecl)
        assert isinstance(prog.declarations[1], FunctionDecl)

    def test_full_program(self):
        source = """
        fn add(a: word, b: word) -> word {
            return a + b;
        }

        fn main() -> void {
            let result: word = add(3, 4);
            print(result);
        }
        """
        prog = parse(source)
        assert len(prog.declarations) == 2
        add_fn = prog.declarations[0]
        assert isinstance(add_fn, FunctionDecl)
        assert add_fn.name == "add"
        assert len(add_fn.params) == 2
        assert add_fn.params[0].name == "a"
        assert add_fn.params[0].type_name == "word"
        assert add_fn.return_type == "word"


# --- Function declarations ---

class TestFunctionDecl:
    def test_no_params(self):
        prog = parse("fn f() -> void {}")
        fn = prog.declarations[0]
        assert isinstance(fn, FunctionDecl)
        assert fn.params == []

    def test_one_param(self):
        prog = parse("fn f(x: word) -> word { return x; }")
        fn = prog.declarations[0]
        assert len(fn.params) == 1
        assert fn.params[0].name == "x"
        assert fn.params[0].type_name == "word"

    def test_multiple_params(self):
        prog = parse("fn f(a: word, b: bool7, c: addr) -> void {}")
        fn = prog.declarations[0]
        assert len(fn.params) == 3
        assert fn.params[0].type_name == "word"
        assert fn.params[1].type_name == "bool7"
        assert fn.params[2].type_name == "addr"

    def test_all_return_types(self):
        for t in ["word", "bool7", "addr", "void"]:
            prog = parse(f"fn f() -> {t} {{}}")
            fn = prog.declarations[0]
            assert fn.return_type == t

    def test_body_with_statements(self):
        prog = parse("""
        fn f() -> void {
            let x: word = 1;
            let y: word = 2;
        }
        """)
        fn = prog.declarations[0]
        assert len(fn.body.statements) == 2


# --- Let statements ---

class TestLetStmt:
    def test_simple_let(self):
        stmt = parse_stmt("let x: word = 5;")
        assert isinstance(stmt, LetStmt)
        assert stmt.name == "x"
        assert stmt.type_name == "word"
        assert isinstance(stmt.value, NumberLiteral)
        assert stmt.value.value == 5

    def test_let_with_expression(self):
        stmt = parse_stmt("let sum: word = a + b;")
        assert isinstance(stmt, LetStmt)
        assert isinstance(stmt.value, BinaryExpr)

    def test_let_with_decimal(self):
        stmt = parse_stmt("let x: word = d:42;")
        assert isinstance(stmt, LetStmt)
        assert isinstance(stmt.value, NumberLiteral)
        assert stmt.value.value == 42

    def test_let_bool7_type(self):
        stmt = parse_stmt("let flag: bool7 = true;")
        assert isinstance(stmt, LetStmt)
        assert stmt.type_name == "bool7"
        assert isinstance(stmt.value, BoolLiteral)
        assert stmt.value.value is True


# --- Assignment ---

class TestAssignment:
    def test_simple_assign(self):
        stmt = parse_stmt("x = 5;")
        assert isinstance(stmt, AssignStmt)
        assert isinstance(stmt.target, Ident)
        assert stmt.target.name == "x"
        assert isinstance(stmt.value, NumberLiteral)

    def test_store_assign(self):
        stmt = parse_stmt("store[0] = d:100;")
        assert isinstance(stmt, AssignStmt)
        assert isinstance(stmt.target, StoreAccess)
        assert isinstance(stmt.target.index, NumberLiteral)
        assert stmt.target.index.value == 0
        assert isinstance(stmt.value, NumberLiteral)
        assert stmt.value.value == 100

    def test_store_assign_with_expr_index(self):
        stmt = parse_stmt("store[a + 1] = b;")
        assert isinstance(stmt, AssignStmt)
        assert isinstance(stmt.target, StoreAccess)
        assert isinstance(stmt.target.index, BinaryExpr)

    def test_assign_expression(self):
        stmt = parse_stmt("x = a + b;")
        assert isinstance(stmt, AssignStmt)
        assert isinstance(stmt.value, BinaryExpr)


# --- If / else ---

class TestIfStmt:
    def test_if_no_else(self):
        stmt = parse_stmt("if x > 0 { print(x); }")
        assert isinstance(stmt, IfStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.op == ">"
        assert len(stmt.then_block.statements) == 1
        assert stmt.else_block is None

    def test_if_else(self):
        stmt = parse_stmt("if x == 0 { print(1); } else { print(0); }")
        assert isinstance(stmt, IfStmt)
        assert stmt.else_block is not None
        assert len(stmt.else_block.statements) == 1

    def test_nested_if(self):
        source = """
        if a > 0 {
            if b > 0 {
                print(1);
            }
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, IfStmt)
        inner = stmt.then_block.statements[0]
        assert isinstance(inner, IfStmt)

    def test_if_with_multiple_statements(self):
        source = """
        if x > 0 {
            let a: word = 1;
            let b: word = 2;
            print(a + b);
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, IfStmt)
        assert len(stmt.then_block.statements) == 3


# --- While ---

class TestWhileStmt:
    def test_simple_while(self):
        stmt = parse_stmt("while i > 0 { i = i - 1; }")
        assert isinstance(stmt, WhileStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.op == ">"
        assert len(stmt.body.statements) == 1

    def test_while_with_multiple_stmts(self):
        source = """
        while x != 0 {
            print(x);
            x = x - 1;
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, WhileStmt)
        assert len(stmt.body.statements) == 2

    def test_nested_while(self):
        source = """
        while a > 0 {
            while b > 0 {
                b = b - 1;
            }
            a = a - 1;
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, WhileStmt)
        inner = stmt.body.statements[0]
        assert isinstance(inner, WhileStmt)


# --- Return ---

class TestReturnStmt:
    def test_return_value(self):
        stmt = parse_stmt("return 5;")
        assert isinstance(stmt, ReturnStmt)
        assert isinstance(stmt.value, NumberLiteral)
        assert stmt.value.value == 5

    def test_return_expression(self):
        stmt = parse_stmt("return a + b;")
        assert isinstance(stmt, ReturnStmt)
        assert isinstance(stmt.value, BinaryExpr)

    def test_return_void(self):
        stmt = parse_stmt("return;")
        assert isinstance(stmt, ReturnStmt)
        assert stmt.value is None


# --- Expression statements ---

class TestExprStmt:
    def test_function_call_stmt(self):
        stmt = parse_stmt("print(x);")
        assert isinstance(stmt, ExprStmt)
        assert isinstance(stmt.expr, FnCall)
        assert stmt.expr.name == "print"

    def test_bare_ident_stmt(self):
        stmt = parse_stmt("x;")
        assert isinstance(stmt, ExprStmt)
        assert isinstance(stmt.expr, Ident)


# --- Expressions: numbers and booleans ---

class TestLiterals:
    def test_base7_number(self):
        expr = parse_expr("10")
        assert isinstance(expr, NumberLiteral)
        assert expr.value == 7  # 10 in base-7

    def test_base7_zero(self):
        expr = parse_expr("0")
        assert isinstance(expr, NumberLiteral)
        assert expr.value == 0

    def test_decimal_number(self):
        expr = parse_expr("d:42")
        assert isinstance(expr, NumberLiteral)
        assert expr.value == 42

    def test_true(self):
        expr = parse_expr("true")
        assert isinstance(expr, BoolLiteral)
        assert expr.value is True

    def test_false(self):
        expr = parse_expr("false")
        assert isinstance(expr, BoolLiteral)
        assert expr.value is False


# --- Expressions: identifiers ---

class TestIdentExpr:
    def test_simple_ident(self):
        expr = parse_expr("x")
        assert isinstance(expr, Ident)
        assert expr.name == "x"


# --- Expressions: store access ---

class TestStoreAccess:
    def test_store_read(self):
        expr = parse_expr("store[0]")
        assert isinstance(expr, StoreAccess)
        assert isinstance(expr.index, NumberLiteral)
        assert expr.index.value == 0

    def test_store_with_expression_index(self):
        expr = parse_expr("store[a + 1]")
        assert isinstance(expr, StoreAccess)
        assert isinstance(expr.index, BinaryExpr)

    def test_store_with_decimal_index(self):
        expr = parse_expr("store[d:100]")
        assert isinstance(expr, StoreAccess)
        assert isinstance(expr.index, NumberLiteral)
        assert expr.index.value == 100


# --- Expressions: function calls ---

class TestFnCallExpr:
    def test_no_args(self):
        expr = parse_expr("foo()")
        assert isinstance(expr, FnCall)
        assert expr.name == "foo"
        assert expr.args == []

    def test_one_arg(self):
        expr = parse_expr("print(x)")
        assert isinstance(expr, FnCall)
        assert len(expr.args) == 1
        assert isinstance(expr.args[0], Ident)

    def test_multiple_args(self):
        expr = parse_expr("add(1, 2, 3)")
        assert isinstance(expr, FnCall)
        assert len(expr.args) == 3

    def test_expression_args(self):
        expr = parse_expr("foo(a + b, c)")
        assert isinstance(expr, FnCall)
        assert isinstance(expr.args[0], BinaryExpr)
        assert isinstance(expr.args[1], Ident)

    def test_nested_call(self):
        expr = parse_expr("foo(bar(x))")
        assert isinstance(expr, FnCall)
        assert len(expr.args) == 1
        inner = expr.args[0]
        assert isinstance(inner, FnCall)
        assert inner.name == "bar"


# --- Expressions: unary ---

class TestUnaryExpr:
    def test_negate(self):
        expr = parse_expr("-x")
        assert isinstance(expr, UnaryExpr)
        assert expr.op == "-"
        assert isinstance(expr.operand, Ident)

    def test_not(self):
        expr = parse_expr("!x")
        assert isinstance(expr, UnaryExpr)
        assert expr.op == "!"
        assert isinstance(expr.operand, Ident)

    def test_double_negate(self):
        expr = parse_expr("--x")
        assert isinstance(expr, UnaryExpr)
        assert expr.op == "-"
        inner = expr.operand
        assert isinstance(inner, UnaryExpr)
        assert inner.op == "-"

    def test_negate_number(self):
        expr = parse_expr("-5")
        assert isinstance(expr, UnaryExpr)
        assert expr.op == "-"
        assert isinstance(expr.operand, NumberLiteral)
        assert expr.operand.value == 5


# --- Expressions: binary operators ---

class TestBinaryExpr:
    def test_addition(self):
        expr = parse_expr("a + b")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "+"
        assert isinstance(expr.left, Ident)
        assert isinstance(expr.right, Ident)

    def test_subtraction(self):
        expr = parse_expr("a - b")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "-"

    def test_comparison_ops(self):
        for op in [">", "<", ">=", "<="]:
            expr = parse_expr(f"a {op} b")
            assert isinstance(expr, BinaryExpr)
            assert expr.op == op

    def test_equality_ops(self):
        for op in ["==", "!="]:
            expr = parse_expr(f"a {op} b")
            assert isinstance(expr, BinaryExpr)
            assert expr.op == op


# --- Precedence ---

class TestPrecedence:
    def test_addition_left_associative(self):
        # a + b + c → (a + b) + c
        expr = parse_expr("a + b + c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "+"
        assert isinstance(expr.right, Ident)
        assert expr.right.name == "c"
        left = expr.left
        assert isinstance(left, BinaryExpr)
        assert left.op == "+"

    def test_subtraction_left_associative(self):
        # a - b - c → (a - b) - c
        expr = parse_expr("a - b - c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "-"
        assert isinstance(expr.left, BinaryExpr)

    def test_comparison_binds_tighter_than_equality(self):
        # a == b > c → a == (b > c)
        expr = parse_expr("a == b > c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "=="
        assert isinstance(expr.left, Ident)
        right = expr.right
        assert isinstance(right, BinaryExpr)
        assert right.op == ">"

    def test_arithmetic_binds_tighter_than_comparison(self):
        # a > b + c → a > (b + c)
        expr = parse_expr("a > b + c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == ">"
        assert isinstance(expr.left, Ident)
        right = expr.right
        assert isinstance(right, BinaryExpr)
        assert right.op == "+"

    def test_unary_binds_tightest(self):
        # -a + b → (-a) + b
        expr = parse_expr("-a + b")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "+"
        left = expr.left
        assert isinstance(left, UnaryExpr)
        assert left.op == "-"

    def test_parentheses_override_precedence(self):
        # (a + b) == c → grouped correctly
        expr = parse_expr("(a + b) == c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "=="
        left = expr.left
        assert isinstance(left, BinaryExpr)
        assert left.op == "+"

    def test_complex_precedence(self):
        # a + b > c - d == e != f
        # → ((a + b) > (c - d)) == e parsed first, then != f
        # Actually: equality is left-assoc: (((a+b) > (c-d)) == e) != f
        expr = parse_expr("a + b > c - d == e != f")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "!="  # outermost
        assert isinstance(expr.right, Ident)
        inner = expr.left
        assert isinstance(inner, BinaryExpr)
        assert inner.op == "=="  # second outermost

    def test_not_with_comparison(self):
        # !a == b → (!a) == b
        expr = parse_expr("!a == b")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "=="
        left = expr.left
        assert isinstance(left, UnaryExpr)
        assert left.op == "!"


# --- Nested blocks ---

class TestNestedBlocks:
    def test_if_in_while(self):
        source = """
        while x > 0 {
            if x == 1 {
                print(x);
            }
            x = x - 1;
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, WhileStmt)
        assert len(stmt.body.statements) == 2
        inner_if = stmt.body.statements[0]
        assert isinstance(inner_if, IfStmt)

    def test_while_in_if_else(self):
        source = """
        if flag == true {
            while i > 0 {
                i = i - 1;
            }
        } else {
            print(0);
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, IfStmt)
        assert isinstance(stmt.then_block.statements[0], WhileStmt)
        assert stmt.else_block is not None

    def test_deeply_nested(self):
        source = """
        if a > 0 {
            if b > 0 {
                if c > 0 {
                    print(1);
                }
            }
        }
        """
        stmt = parse_stmt(source)
        assert isinstance(stmt, IfStmt)
        inner1 = stmt.then_block.statements[0]
        assert isinstance(inner1, IfStmt)
        inner2 = inner1.then_block.statements[0]
        assert isinstance(inner2, IfStmt)


# --- Full example programs ---

class TestExamplePrograms:
    def test_hello(self):
        source = """
        fn main() -> void {
            print(d:42);
        }
        """
        prog = parse(source)
        assert len(prog.declarations) == 1
        fn = prog.declarations[0]
        assert isinstance(fn, FunctionDecl)
        call = fn.body.statements[0]
        assert isinstance(call, ExprStmt)
        assert isinstance(call.expr, FnCall)
        assert call.expr.name == "print"

    def test_add(self):
        source = """
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let sum: word = a + b;
            print(sum);
            printd(sum);
        }
        """
        prog = parse(source)
        fn = prog.declarations[0]
        assert len(fn.body.statements) == 5

    def test_while_countdown(self):
        source = """
        fn main() -> void {
            let i: word = 6;
            while i > 0 {
                print(i);
                i = i - 1;
            }
        }
        """
        prog = parse(source)
        fn = prog.declarations[0]
        stmts = fn.body.statements
        assert len(stmts) == 2
        assert isinstance(stmts[0], LetStmt)
        assert isinstance(stmts[1], WhileStmt)

    def test_memory(self):
        source = """
        fn main() -> void {
            store[0] = d:100;
            store[1] = d:200;
            let sum: word = store[0] + store[1];
            printd(sum);
        }
        """
        prog = parse(source)
        fn = prog.declarations[0]
        stmts = fn.body.statements
        assert len(stmts) == 4
        assert isinstance(stmts[0], AssignStmt)
        assert isinstance(stmts[0].target, StoreAccess)
        assert isinstance(stmts[2], LetStmt)
        # store[0] + store[1]
        add_expr = stmts[2].value
        assert isinstance(add_expr, BinaryExpr)
        assert isinstance(add_expr.left, StoreAccess)
        assert isinstance(add_expr.right, StoreAccess)

    def test_functions(self):
        source = """
        fn add(a: word, b: word) -> word {
            return a + b;
        }

        fn main() -> void {
            let result: word = add(3, 4);
            print(result);
            printd(result);
        }
        """
        prog = parse(source)
        assert len(prog.declarations) == 2
        add_fn = prog.declarations[0]
        assert add_fn.name == "add"
        assert len(add_fn.params) == 2
        ret_stmt = add_fn.body.statements[0]
        assert isinstance(ret_stmt, ReturnStmt)
        assert isinstance(ret_stmt.value, BinaryExpr)


# --- Source locations ---

class TestParserLocations:
    def test_function_location(self):
        prog = parse("fn main() -> void {}")
        fn = prog.declarations[0]
        assert fn.location.line == 1
        assert fn.location.col == 1

    def test_let_location(self):
        stmt = parse_stmt("let x: word = 0;")
        assert isinstance(stmt, LetStmt)
        assert stmt.location is not None

    def test_error_location(self):
        try:
            parse("fn main() -> void { let x: word }")
            pytest.fail("Should have raised ParserError")
        except ParserError as e:
            assert e.location is not None


# --- Error cases ---

class TestParserErrors:
    def test_missing_fn_name(self):
        with pytest.raises(ParserError, match="expected IDENT"):
            parse("fn () -> void {}")

    def test_missing_arrow(self):
        with pytest.raises(ParserError, match="expected ARROW"):
            parse("fn main() void {}")

    def test_missing_return_type(self):
        with pytest.raises(ParserError, match="expected type"):
            parse("fn main() -> {}")

    def test_missing_lbrace(self):
        with pytest.raises(ParserError, match="expected LBRACE"):
            parse("fn main() -> void")

    def test_missing_rbrace(self):
        with pytest.raises(ParserError, match="expected RBRACE"):
            parse("fn main() -> void { let x: word = 0;")

    def test_missing_semicolon_in_let(self):
        with pytest.raises(ParserError, match="expected SEMICOLON"):
            parse("fn main() -> void { let x: word = 0 }")

    def test_missing_colon_in_let(self):
        with pytest.raises(ParserError, match="expected COLON"):
            parse("fn main() -> void { let x word = 0; }")

    def test_invalid_type(self):
        with pytest.raises(ParserError, match="expected type"):
            parse("fn main() -> void { let x: int = 0; }")

    def test_missing_assign_in_let(self):
        with pytest.raises(ParserError, match="expected ASSIGN"):
            parse("fn main() -> void { let x: word; }")

    def test_invalid_assignment_target(self):
        with pytest.raises(ParserError, match="invalid assignment target"):
            parse("fn main() -> void { 5 = x; }")

    def test_missing_rparen_in_call(self):
        with pytest.raises(ParserError, match="expected RPAREN"):
            parse("fn main() -> void { foo(x; }")

    def test_missing_rbracket_in_store(self):
        with pytest.raises(ParserError, match="expected RBRACKET"):
            parse("fn main() -> void { store[0; }")

    def test_unexpected_token_in_expression(self):
        with pytest.raises(ParserError, match="expected expression"):
            parse("fn main() -> void { let x: word = ; }")

    def test_unexpected_top_level(self):
        with pytest.raises(ParserError, match="expected function or global"):
            parse("x = 5;")

    def test_missing_lparen_in_fn(self):
        with pytest.raises(ParserError, match="expected LPAREN"):
            parse("fn main -> void {}")

    def test_missing_rparen_in_fn_decl(self):
        with pytest.raises(ParserError, match="expected RPAREN"):
            parse("fn main(x: word -> void {}")

    def test_missing_semicolon_in_return(self):
        with pytest.raises(ParserError, match="expected SEMICOLON"):
            parse("fn main() -> void { return 5 }")

    def test_expression_assign_literal_target(self):
        with pytest.raises(ParserError, match="invalid assignment target"):
            parse("fn main() -> void { (a + b) = 5; }")

    def test_binary_assign_target(self):
        with pytest.raises(ParserError, match="invalid assignment target"):
            parse("fn main() -> void { a + b = 5; }")


# --- Grouped expressions ---

class TestGroupedExpr:
    def test_simple_group(self):
        expr = parse_expr("(x)")
        assert isinstance(expr, Ident)
        assert expr.name == "x"

    def test_group_changes_precedence(self):
        # (a + b) == c
        expr = parse_expr("(a + b) == c")
        assert isinstance(expr, BinaryExpr)
        assert expr.op == "=="
        assert isinstance(expr.left, BinaryExpr)
        assert expr.left.op == "+"

    def test_nested_groups(self):
        expr = parse_expr("((a))")
        assert isinstance(expr, Ident)
        assert expr.name == "a"
