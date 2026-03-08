"""Type system for SeptaLang v0.1.

Types:
  word  — 12-septit unsigned integer
  bool7 — seven-state boolean (0=false, 6=true)
  void  — no value

Alias:
  addr  — semantic alias for word in v0.1.
          Declared as a separate keyword in the grammar for future use,
          but resolves to word at the type level. No distinct addr type
          exists at compile time.

Type rules:
  Arithmetic (+, -, unary -): word x word -> word
  Ordered comparison (>, <, >=, <=): word x word -> bool7
  Equality (==, !=): T x T -> bool7  (T in {word, bool7})
  Unary !: any non-void -> bool7
  Conditions (if/while): any non-void
  store[expr]: index must be word, result is word
  No implicit conversions.
"""

from enum import Enum


class SeptaType(Enum):
    WORD = "word"
    BOOL7 = "bool7"
    VOID = "void"


# Build lookup from enum values, then add the addr alias.
_TYPE_NAMES: dict[str, SeptaType] = {t.value: t for t in SeptaType}
_TYPE_NAMES["addr"] = SeptaType.WORD  # v0.1: addr is semantic alias for word


def type_from_name(name: str) -> SeptaType:
    """Convert a type-name string to SeptaType. Raises ValueError if unknown.

    'addr' resolves to SeptaType.WORD (semantic alias in v0.1).
    """
    typ = _TYPE_NAMES.get(name)
    if typ is None:
        raise ValueError(f"unknown type: '{name}'")
    return typ
