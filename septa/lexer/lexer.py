"""Hand-written lexer for SeptaLang.

Produces a stream of Token objects from source text.
All numeric literals without prefix are base-7.
Decimal literals use d: prefix (e.g. d:42).

Dependencies: tokens.py, common/errors.py, common/locations.py
"""

from septa.common.errors import LexerError
from septa.common.locations import SourceLocation
from septa.lexer.tokens import KEYWORDS, Token, TokenType

# Characters that start a two-char operator
_TWO_CHAR_OPS: dict[tuple[str, str], TokenType] = {
    ("=", "="): TokenType.EQ,
    ("!", "="): TokenType.NEQ,
    (">", "="): TokenType.GTE,
    ("<", "="): TokenType.LTE,
    ("-", ">"): TokenType.ARROW,
}

_SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "!": TokenType.BANG,
    "=": TokenType.ASSIGN,
    ">": TokenType.GT,
    "<": TokenType.LT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    ":": TokenType.COLON,
}


class Lexer:
    """Tokenize SeptaLang source code.

    Usage:
        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()  # returns list[Token]
    """

    def __init__(self, source: str, filename: str = "<input>"):
        self._source = source
        self._filename = filename
        self._pos = 0
        self._line = 1
        self._col = 1

    def tokenize(self) -> list[Token]:
        """Tokenize entire source. Returns list ending with EOF token."""
        tokens: list[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.type is TokenType.EOF:
                break
        return tokens

    def _loc(self) -> SourceLocation:
        return SourceLocation(self._filename, self._line, self._col)

    def _current(self) -> str:
        if self._pos >= len(self._source):
            return "\0"
        return self._source[self._pos]

    def _peek(self, offset: int = 1) -> str:
        idx = self._pos + offset
        if idx >= len(self._source):
            return "\0"
        return self._source[idx]

    def _advance(self) -> str:
        ch = self._current()
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._source):
            ch = self._current()
            if ch in (" ", "\t", "\r", "\n"):
                self._advance()
            elif ch == "/" and self._peek() == "/":
                # Line comment — skip to end of line
                while self._pos < len(self._source) and self._current() != "\n":
                    self._advance()
            else:
                break

    def _next_token(self) -> Token:
        self._skip_whitespace_and_comments()

        if self._pos >= len(self._source):
            return Token(TokenType.EOF, "", self._loc())

        loc = self._loc()
        ch = self._current()

        # Decimal literal: d:DIGITS
        if ch == "d" and self._peek() == ":" and self._peek(2).isdigit():
            return self._lex_decimal_number(loc)

        # Base-7 number
        if ch.isdigit():
            return self._lex_base7_number(loc)

        # Identifier or keyword
        if ch.isalpha() or ch == "_":
            return self._lex_identifier(loc)

        # Two-character operators
        pair = (ch, self._peek())
        if pair in _TWO_CHAR_OPS:
            self._advance()
            self._advance()
            return Token(_TWO_CHAR_OPS[pair], ch + pair[1], loc)

        # Single-character tokens
        if ch in _SINGLE_CHAR_TOKENS:
            self._advance()
            return Token(_SINGLE_CHAR_TOKENS[ch], ch, loc)

        raise LexerError(f"unexpected character: '{ch}'", loc)

    def _lex_base7_number(self, loc: SourceLocation) -> Token:
        start = self._pos
        while self._current().isdigit():
            digit = self._current()
            if digit > "6":
                raise LexerError(
                    f"invalid base-7 digit: '{digit}'",
                    self._loc(),
                )
            self._advance()
        value = self._source[start : self._pos]
        return Token(TokenType.NUMBER, value, loc)

    def _lex_decimal_number(self, loc: SourceLocation) -> Token:
        self._advance()  # skip 'd'
        self._advance()  # skip ':'
        start = self._pos
        while self._current().isdigit():
            self._advance()
        value = self._source[start : self._pos]
        return Token(TokenType.DECIMAL_NUMBER, value, loc)

    def _lex_identifier(self, loc: SourceLocation) -> Token:
        start = self._pos
        while self._current().isalnum() or self._current() == "_":
            self._advance()
        text = self._source[start : self._pos]
        token_type = KEYWORDS.get(text, TokenType.IDENT)
        return Token(token_type, text, loc)
