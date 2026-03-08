"""Symbol table and scope management for SeptaLang.

Symbol kinds: "global", "parameter", "variable"

Scope rules:
  - Global scope holds globals (visible everywhere)
  - Function scope holds parameters + top-level body variables
  - Block scopes (if/while bodies) are children of the enclosing scope
  - Shadowing across scopes is allowed
  - Redeclaration within the same scope is an error
"""

from __future__ import annotations

from dataclasses import dataclass, field

from septa.common.errors import SemanticError
from septa.common.locations import SourceLocation
from septa.semantic.typesys import SeptaType


@dataclass(slots=True)
class Symbol:
    """A declared name (variable, parameter, or global)."""
    name: str
    type: SeptaType
    kind: str  # "global", "parameter", "variable"
    location: SourceLocation | None


@dataclass(slots=True)
class FunctionSig:
    """Signature of a function (user-defined or builtin)."""
    name: str
    param_types: list[SeptaType] = field(default_factory=list)
    return_type: SeptaType = SeptaType.VOID
    location: SourceLocation | None = None
    builtin: bool = False


class Scope:
    """Lexical scope with optional parent link for name resolution."""
    __slots__ = ("_symbols", "parent")

    def __init__(self, parent: Scope | None = None):
        self._symbols: dict[str, Symbol] = {}
        self.parent = parent

    def define(self, symbol: Symbol) -> None:
        """Add a symbol. Raises SemanticError on redeclaration in this scope."""
        existing = self._symbols.get(symbol.name)
        if existing is not None:
            msg = f"redeclaration of '{symbol.name}'"
            if existing.location:
                msg += f" (previously declared at {existing.location})"
            raise SemanticError(msg, symbol.location)
        self._symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol | None:
        """Resolve a name through the scope chain."""
        sym = self._symbols.get(name)
        if sym is not None:
            return sym
        if self.parent is not None:
            return self.parent.lookup(name)
        return None
