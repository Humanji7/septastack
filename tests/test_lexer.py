"""Tests for the SeptaLang lexer."""

import pytest
from septa.common.errors import LexerError
from septa.common.locations import SourceLocation
from septa.lexer.lexer import Lexer
from septa.lexer.tokens import TokenType


def lex(source: str) -> list[tuple[TokenType, str]]:
    """Helper: tokenize and return list of (type, value) pairs, excluding EOF."""
    tokens = Lexer(source).tokenize()
    return [(t.type, t.value) for t in tokens if t.type is not TokenType.EOF]


def lex_types(source: str) -> list[TokenType]:
    """Helper: return just token types, excluding EOF."""
    return [t.type for t in Lexer(source).tokenize() if t.type is not TokenType.EOF]


class TestEmpty:
    def test_empty_source(self):
        tokens = Lexer("").tokenize()
        assert len(tokens) == 1
        assert tokens[0].type is TokenType.EOF

    def test_whitespace_only(self):
        tokens = Lexer("   \n\t\r  ").tokenize()
        assert len(tokens) == 1
        assert tokens[0].type is TokenType.EOF

    def test_comment_only(self):
        tokens = Lexer("// this is a comment").tokenize()
        assert len(tokens) == 1
        assert tokens[0].type is TokenType.EOF


class TestNumbers:
    def test_base7_single_digit(self):
        assert lex("0") == [(TokenType.NUMBER, "0")]
        assert lex("6") == [(TokenType.NUMBER, "6")]

    def test_base7_multi_digit(self):
        assert lex("10") == [(TokenType.NUMBER, "10")]
        assert lex("123") == [(TokenType.NUMBER, "123")]
        assert lex("666") == [(TokenType.NUMBER, "666")]

    def test_base7_invalid_digit(self):
        with pytest.raises(LexerError, match="invalid base-7 digit: '7'"):
            Lexer("17").tokenize()

        with pytest.raises(LexerError, match="invalid base-7 digit: '8'"):
            Lexer("8").tokenize()

        with pytest.raises(LexerError, match="invalid base-7 digit: '9'"):
            Lexer("9").tokenize()

    def test_decimal_literal(self):
        assert lex("d:10") == [(TokenType.DECIMAL_NUMBER, "10")]
        assert lex("d:42") == [(TokenType.DECIMAL_NUMBER, "42")]
        assert lex("d:0") == [(TokenType.DECIMAL_NUMBER, "0")]
        assert lex("d:99") == [(TokenType.DECIMAL_NUMBER, "99")]

    def test_d_not_followed_by_colon_is_ident(self):
        assert lex("d") == [(TokenType.IDENT, "d")]

    def test_d_colon_not_followed_by_digit(self):
        # d is an ident, : is a colon, x is an ident
        result = lex("d:x")
        assert result == [
            (TokenType.IDENT, "d"),
            (TokenType.COLON, ":"),
            (TokenType.IDENT, "x"),
        ]


class TestKeywords:
    @pytest.mark.parametrize("kw,tt", [
        ("fn", TokenType.FN),
        ("let", TokenType.LET),
        ("return", TokenType.RETURN),
        ("if", TokenType.IF),
        ("else", TokenType.ELSE),
        ("while", TokenType.WHILE),
        ("true", TokenType.TRUE),
        ("false", TokenType.FALSE),
        ("store", TokenType.STORE),
        ("word", TokenType.WORD),
        ("bool7", TokenType.BOOL7),
        ("addr", TokenType.ADDR),
        ("void", TokenType.VOID),
    ])
    def test_keyword(self, kw: str, tt: TokenType):
        assert lex(kw) == [(tt, kw)]

    def test_keyword_prefix_is_ident(self):
        # "function" is not a keyword, should be IDENT
        assert lex("function") == [(TokenType.IDENT, "function")]
        assert lex("letters") == [(TokenType.IDENT, "letters")]
        assert lex("ifelse") == [(TokenType.IDENT, "ifelse")]


class TestOperators:
    def test_single_char_ops(self):
        assert lex("+ - ! =") == [
            (TokenType.PLUS, "+"),
            (TokenType.MINUS, "-"),
            (TokenType.BANG, "!"),
            (TokenType.ASSIGN, "="),
        ]

    def test_comparison_ops(self):
        assert lex("> < >= <=") == [
            (TokenType.GT, ">"),
            (TokenType.LT, "<"),
            (TokenType.GTE, ">="),
            (TokenType.LTE, "<="),
        ]

    def test_equality_ops(self):
        assert lex("== !=") == [
            (TokenType.EQ, "=="),
            (TokenType.NEQ, "!="),
        ]

    def test_arrow(self):
        assert lex("->") == [(TokenType.ARROW, "->")]

    def test_minus_vs_arrow(self):
        # "- >" should be MINUS then GT
        assert lex("- >") == [
            (TokenType.MINUS, "-"),
            (TokenType.GT, ">"),
        ]
        # "->" should be ARROW
        assert lex("->") == [(TokenType.ARROW, "->")]


class TestDelimiters:
    def test_all_delimiters(self):
        assert lex("( ) { } [ ] , ; :") == [
            (TokenType.LPAREN, "("),
            (TokenType.RPAREN, ")"),
            (TokenType.LBRACE, "{"),
            (TokenType.RBRACE, "}"),
            (TokenType.LBRACKET, "["),
            (TokenType.RBRACKET, "]"),
            (TokenType.COMMA, ","),
            (TokenType.SEMICOLON, ";"),
            (TokenType.COLON, ":"),
        ]


class TestIdentifiers:
    def test_simple_idents(self):
        assert lex("x") == [(TokenType.IDENT, "x")]
        assert lex("foo") == [(TokenType.IDENT, "foo")]
        assert lex("bar_baz") == [(TokenType.IDENT, "bar_baz")]

    def test_ident_with_digits(self):
        assert lex("x1") == [(TokenType.IDENT, "x1")]
        assert lex("var2name") == [(TokenType.IDENT, "var2name")]

    def test_underscore_ident(self):
        assert lex("_x") == [(TokenType.IDENT, "_x")]
        assert lex("__init") == [(TokenType.IDENT, "__init")]


class TestComments:
    def test_inline_comment(self):
        assert lex("x // comment") == [(TokenType.IDENT, "x")]

    def test_comment_before_newline(self):
        result = lex("x // comment\ny")
        assert result == [
            (TokenType.IDENT, "x"),
            (TokenType.IDENT, "y"),
        ]

    def test_multiple_comments(self):
        source = """
        // first comment
        x
        // second comment
        y
        """
        assert lex(source) == [
            (TokenType.IDENT, "x"),
            (TokenType.IDENT, "y"),
        ]


class TestLocations:
    def test_first_token_location(self):
        tokens = Lexer("x").tokenize()
        assert tokens[0].location.line == 1
        assert tokens[0].location.col == 1

    def test_second_line(self):
        tokens = Lexer("x\ny").tokenize()
        y_tok = tokens[1]
        assert y_tok.location.line == 2
        assert y_tok.location.col == 1

    def test_column_tracking(self):
        tokens = Lexer("  x  y").tokenize()
        assert tokens[0].location.col == 3
        assert tokens[1].location.col == 6

    def test_filename(self):
        tokens = Lexer("x", "test.septa").tokenize()
        assert tokens[0].location.file == "test.septa"


class TestComplex:
    def test_function_signature(self):
        source = "fn add(a: word, b: word) -> word {"
        types = lex_types(source)
        assert types == [
            TokenType.FN, TokenType.IDENT,
            TokenType.LPAREN,
            TokenType.IDENT, TokenType.COLON, TokenType.WORD, TokenType.COMMA,
            TokenType.IDENT, TokenType.COLON, TokenType.WORD,
            TokenType.RPAREN, TokenType.ARROW, TokenType.WORD,
            TokenType.LBRACE,
        ]

    def test_let_statement(self):
        source = "let x: word = 10;"
        types = lex_types(source)
        assert types == [
            TokenType.LET, TokenType.IDENT, TokenType.COLON,
            TokenType.WORD, TokenType.ASSIGN, TokenType.NUMBER,
            TokenType.SEMICOLON,
        ]

    def test_store_access(self):
        source = "store[d:100]"
        types = lex_types(source)
        assert types == [
            TokenType.STORE, TokenType.LBRACKET,
            TokenType.DECIMAL_NUMBER, TokenType.RBRACKET,
        ]

    def test_if_else(self):
        source = "if x == 0 { y } else { z }"
        types = lex_types(source)
        assert types == [
            TokenType.IF, TokenType.IDENT, TokenType.EQ,
            TokenType.NUMBER,
            TokenType.LBRACE, TokenType.IDENT, TokenType.RBRACE,
            TokenType.ELSE,
            TokenType.LBRACE, TokenType.IDENT, TokenType.RBRACE,
        ]

    def test_while_loop(self):
        source = "while i > 0 { i = i - 1; }"
        types = lex_types(source)
        assert types == [
            TokenType.WHILE, TokenType.IDENT, TokenType.GT, TokenType.NUMBER,
            TokenType.LBRACE,
            TokenType.IDENT, TokenType.ASSIGN, TokenType.IDENT,
            TokenType.MINUS, TokenType.NUMBER, TokenType.SEMICOLON,
            TokenType.RBRACE,
        ]

    def test_full_program(self):
        source = """
        // Add two numbers
        fn main() -> void {
            let a: word = 3;
            let b: word = 4;
            let sum: word = a + b;
            print(sum);
        }
        """
        tokens = Lexer(source, "test.septa").tokenize()
        # Should not raise, and should end with EOF
        assert tokens[-1].type is TokenType.EOF
        # Check some key tokens
        types = [t.type for t in tokens if t.type is not TokenType.EOF]
        assert TokenType.FN in types
        assert TokenType.LET in types
        assert TokenType.PLUS in types


class TestOperatorDisambiguation:
    """Ensure two-char operators are distinguished from single-char ones."""

    def test_bang_vs_neq(self):
        # !x → BANG IDENT
        assert lex("!x") == [
            (TokenType.BANG, "!"),
            (TokenType.IDENT, "x"),
        ]
        # != → NEQ
        assert lex("!=") == [(TokenType.NEQ, "!=")]

    def test_assign_vs_eq(self):
        # = → ASSIGN
        assert lex("=") == [(TokenType.ASSIGN, "=")]
        # == → EQ
        assert lex("==") == [(TokenType.EQ, "==")]
        # = = → ASSIGN ASSIGN (no merge across space)
        assert lex("= =") == [
            (TokenType.ASSIGN, "="),
            (TokenType.ASSIGN, "="),
        ]

    def test_gt_vs_gte(self):
        assert lex(">") == [(TokenType.GT, ">")]
        assert lex(">=") == [(TokenType.GTE, ">=")]

    def test_lt_vs_lte(self):
        assert lex("<") == [(TokenType.LT, "<")]
        assert lex("<=") == [(TokenType.LTE, "<=")]

    def test_minus_vs_arrow_detailed(self):
        assert lex("-") == [(TokenType.MINUS, "-")]
        assert lex("->") == [(TokenType.ARROW, "->")]
        # -1 → MINUS NUMBER
        assert lex("-1") == [
            (TokenType.MINUS, "-"),
            (TokenType.NUMBER, "1"),
        ]


class TestDecimalEdgeCases:
    def test_d_colon_eof(self):
        # d: at end of input → IDENT COLON (no digit follows)
        assert lex("d:") == [
            (TokenType.IDENT, "d"),
            (TokenType.COLON, ":"),
        ]

    def test_d_colon_space_digit(self):
        # d: 5 → IDENT COLON NUMBER (space breaks the d: prefix)
        assert lex("d: 5") == [
            (TokenType.IDENT, "d"),
            (TokenType.COLON, ":"),
            (TokenType.NUMBER, "5"),
        ]

    def test_d_in_identifier(self):
        # "data" should be a single IDENT, not d: prefix
        assert lex("data") == [(TokenType.IDENT, "data")]

    def test_d_colon_non_digit(self):
        # d:word → IDENT COLON WORD_keyword
        assert lex("d:word") == [
            (TokenType.IDENT, "d"),
            (TokenType.COLON, ":"),
            (TokenType.WORD, "word"),
        ]


class TestEOFEdgeCases:
    def test_eof_location(self):
        tokens = Lexer("x").tokenize()
        eof = tokens[-1]
        assert eof.type is TokenType.EOF
        assert eof.location.line == 1
        assert eof.location.col == 2

    def test_eof_after_newline(self):
        tokens = Lexer("x\n").tokenize()
        eof = tokens[-1]
        assert eof.type is TokenType.EOF
        assert eof.location.line == 2
        assert eof.location.col == 1

    def test_operator_at_eof(self):
        assert lex("+") == [(TokenType.PLUS, "+")]
        assert lex(">=") == [(TokenType.GTE, ">=")]

    def test_number_at_eof(self):
        assert lex("123") == [(TokenType.NUMBER, "123")]

    def test_comment_at_eof_no_newline(self):
        tokens = Lexer("x // end").tokenize()
        assert len(tokens) == 2  # x + EOF
        assert tokens[0].type is TokenType.IDENT


class TestLocationAcrossNewlines:
    def test_multiline_locations(self):
        source = "x\ny\nz"
        tokens = Lexer(source).tokenize()
        assert tokens[0].location.line == 1
        assert tokens[0].location.col == 1
        assert tokens[1].location.line == 2
        assert tokens[1].location.col == 1
        assert tokens[2].location.line == 3
        assert tokens[2].location.col == 1

    def test_location_after_comment_line(self):
        source = "x\n// comment\ny"
        tokens = Lexer(source).tokenize()
        assert tokens[0].location.line == 1
        assert tokens[1].location.line == 3

    def test_mixed_indentation_locations(self):
        source = "  x\n    y\n  z"
        tokens = Lexer(source).tokenize()
        assert tokens[0].location == SourceLocation("<input>", 1, 3)
        assert tokens[1].location == SourceLocation("<input>", 2, 5)
        assert tokens[2].location == SourceLocation("<input>", 3, 3)

    def test_operator_location_multiline(self):
        source = "a\n  +\n    b"
        tokens = Lexer(source).tokenize()
        assert tokens[0].location.line == 1  # a
        assert tokens[1].location.line == 2  # +
        assert tokens[1].location.col == 3
        assert tokens[2].location.line == 3  # b


class TestBase7InvalidDigits:
    """Additional coverage for invalid base-7 digits in various positions."""

    def test_invalid_digit_at_start(self):
        with pytest.raises(LexerError, match="invalid base-7 digit: '7'"):
            Lexer("7").tokenize()

    def test_invalid_digit_mid_number(self):
        with pytest.raises(LexerError, match="invalid base-7 digit: '9'"):
            Lexer("129").tokenize()

    def test_invalid_digit_after_valid(self):
        with pytest.raises(LexerError, match="invalid base-7 digit: '8'"):
            Lexer("008").tokenize()

    def test_all_invalid_digits(self):
        for d in "789":
            with pytest.raises(LexerError):
                Lexer(d).tokenize()


class TestErrors:
    def test_unexpected_character(self):
        with pytest.raises(LexerError, match="unexpected character"):
            Lexer("@").tokenize()

    def test_error_includes_location(self):
        try:
            Lexer("  @", "test.septa").tokenize()
            pytest.fail("Should have raised LexerError")
        except LexerError as e:
            assert e.location is not None
            assert e.location.file == "test.septa"
            assert e.location.line == 1
            assert e.location.col == 3

    def test_base7_digit_error_location(self):
        try:
            Lexer("12\n  18").tokenize()
            pytest.fail("Should have raised LexerError")
        except LexerError as e:
            assert e.location is not None
            assert e.location.line == 2
            assert e.location.col == 4  # '8' is at column 4
