"""Token types and Token dataclass for the SeptaLang lexer."""

from dataclasses import dataclass
from enum import Enum, auto

from septa.common.locations import SourceLocation


class TokenType(Enum):
    """All token types in SeptaLang."""

    # Literals
    NUMBER = auto()          # base-7 numeric literal
    DECIMAL_NUMBER = auto()  # d:prefixed decimal literal
    IDENT = auto()

    # Keywords
    FN = auto()
    LET = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    TRUE = auto()
    FALSE = auto()
    STORE = auto()

    # Type keywords
    WORD = auto()
    BOOL7 = auto()
    ADDR = auto()
    VOID = auto()

    # Operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    BANG = auto()        # !
    ASSIGN = auto()     # =
    EQ = auto()         # ==
    NEQ = auto()        # !=
    GT = auto()         # >
    LT = auto()         # <
    GTE = auto()        # >=
    LTE = auto()        # <=

    # Delimiters
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    COMMA = auto()      # ,
    SEMICOLON = auto()  # ;
    COLON = auto()      # :
    ARROW = auto()      # ->

    # Special
    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "fn": TokenType.FN,
    "let": TokenType.LET,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "store": TokenType.STORE,
    "word": TokenType.WORD,
    "bool7": TokenType.BOOL7,
    "addr": TokenType.ADDR,
    "void": TokenType.VOID,
}


@dataclass(frozen=True, slots=True)
class Token:
    """A single lexical token."""
    type: TokenType
    value: str
    location: SourceLocation

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.location})"
