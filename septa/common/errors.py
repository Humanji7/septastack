"""Error types for all SeptaStack stages."""

from septa.common.locations import SourceLocation


class SeptaError(Exception):
    """Base error for all SeptaStack errors."""

    def __init__(self, message: str, location: SourceLocation | None = None):
        self.location = location
        if location:
            super().__init__(f"{location}: {message}")
        else:
            super().__init__(message)


class LexerError(SeptaError):
    pass


class ParserError(SeptaError):
    pass


class SemanticError(SeptaError):
    pass


class CodegenError(SeptaError):
    pass


class AssemblerError(SeptaError):
    pass


class VMError(SeptaError):
    pass
