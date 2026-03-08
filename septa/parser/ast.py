"""AST node definitions for SeptaLang.

Node hierarchy:
  Node
  ├── Expr
  │   ├── NumberLiteral   — integer value (base-7 or decimal, stored as int)
  │   ├── BoolLiteral     — true (6) or false (0)
  │   ├── Ident           — variable reference
  │   ├── StoreAccess     — store[expr]
  │   ├── UnaryExpr       — -expr, !expr
  │   ├── BinaryExpr      — expr op expr
  │   └── FnCall          — name(args...)
  ├── Statement
  │   ├── LetStmt         — let name: type = expr;
  │   ├── AssignStmt      — lvalue = expr;
  │   ├── IfStmt          — if expr block [else block]
  │   ├── WhileStmt       — while expr block
  │   ├── ReturnStmt      — return [expr];
  │   └── ExprStmt        — expr;
  ├── Block               — { statements... }
  ├── Param               — name: type
  ├── Declaration
  │   ├── FunctionDecl    — fn name(params) -> type block
  │   └── GlobalDecl      — let name: type = expr;  (top-level)
  └── Program             — list of declarations
"""

from __future__ import annotations

from dataclasses import dataclass, field

from septa.common.locations import SourceLocation


# --- Base classes ---

class Node:
    """Base class for all AST nodes."""
    pass


class Expr(Node):
    """Base class for expression nodes."""
    pass


class Statement(Node):
    """Base class for statement nodes."""
    pass


class Declaration(Node):
    """Base class for top-level declaration nodes."""
    pass


# --- Expressions ---

@dataclass(slots=True)
class NumberLiteral(Expr):
    value: int
    location: SourceLocation
    was_decimal: bool = False


@dataclass(slots=True)
class BoolLiteral(Expr):
    value: bool
    location: SourceLocation


@dataclass(slots=True)
class Ident(Expr):
    name: str
    location: SourceLocation


@dataclass(slots=True)
class StoreAccess(Expr):
    index: Expr
    location: SourceLocation


@dataclass(slots=True)
class UnaryExpr(Expr):
    op: str
    operand: Expr
    location: SourceLocation


@dataclass(slots=True)
class BinaryExpr(Expr):
    left: Expr
    op: str
    right: Expr
    location: SourceLocation


@dataclass(slots=True)
class FnCall(Expr):
    name: str
    args: list[Expr] = field(default_factory=list)
    location: SourceLocation = field(default=None)  # type: ignore[assignment]


# --- Statements ---

@dataclass(slots=True)
class LetStmt(Statement):
    name: str
    type_name: str
    value: Expr
    location: SourceLocation


@dataclass(slots=True)
class AssignStmt(Statement):
    target: Ident | StoreAccess
    value: Expr
    location: SourceLocation


@dataclass(slots=True)
class Block(Node):
    statements: list[Statement] = field(default_factory=list)
    location: SourceLocation = field(default=None)  # type: ignore[assignment]


@dataclass(slots=True)
class IfStmt(Statement):
    condition: Expr
    then_block: Block
    else_block: Block | None
    location: SourceLocation


@dataclass(slots=True)
class WhileStmt(Statement):
    condition: Expr
    body: Block
    location: SourceLocation


@dataclass(slots=True)
class ReturnStmt(Statement):
    value: Expr | None
    location: SourceLocation


@dataclass(slots=True)
class ExprStmt(Statement):
    expr: Expr
    location: SourceLocation


# --- Declarations ---

@dataclass(slots=True)
class Param(Node):
    name: str
    type_name: str
    location: SourceLocation


@dataclass(slots=True)
class FunctionDecl(Declaration):
    name: str
    params: list[Param]
    return_type: str
    body: Block
    location: SourceLocation


@dataclass(slots=True)
class GlobalDecl(Declaration):
    name: str
    type_name: str
    value: Expr
    location: SourceLocation


# --- Program ---

@dataclass(slots=True)
class Program(Node):
    declarations: list[Declaration] = field(default_factory=list)
    location: SourceLocation = field(default=None)  # type: ignore[assignment]
