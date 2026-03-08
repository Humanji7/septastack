"""Source location tracking for error reporting."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Position in source code."""
    file: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"
