"""Two-pass semantic analyzer for SeptaLang.

Pass 1 — collect:
  - Register builtin functions (print, printd, halt)
  - Register all user function signatures
  - Register all global variables (constant initializers only)
  - Detect duplicate top-level names

Pass 2 — validate:
  - Type-check every function body
  - Verify expressions, assignments, returns, conditions
  - Enforce scope rules (shadowing OK, redeclaration in same scope = error)

Post-pass:
  - Verify main() exists with signature fn main() -> void

Type alias:
  'addr' resolves to 'word' at the semantic level (v0.1).
  No distinct addr type exists. See semantic/typesys.py.

Public API:
  analyze(program) — raises SemanticError on first error

Dependencies: parser/ast.py, semantic/symbols.py, semantic/typesys.py
"""

from septa.common.errors import SemanticError
from septa.common.locations import SourceLocation
from septa.parser.ast import (
    AssignStmt,
    BinaryExpr,
    Block,
    BoolLiteral,
    Expr,
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
    Statement,
    StoreAccess,
    UnaryExpr,
    WhileStmt,
)
from septa.semantic.symbols import FunctionSig, Scope, Symbol
from septa.semantic.typesys import SeptaType, type_from_name

# Operators grouped by kind
_ARITHMETIC_OPS = {"+", "-"}
_ORDERED_CMP_OPS = {">", "<", ">=", "<="}
_EQUALITY_OPS = {"==", "!="}


def analyze(program: Program) -> None:
    """Analyze a parsed program. Raises SemanticError on first error."""
    _Analyzer().run(program)


class _Analyzer:
    def __init__(self) -> None:
        self._functions: dict[str, FunctionSig] = {}
        self._global_scope = Scope()
        self._current_scope: Scope = self._global_scope
        self._current_fn_return_type: SeptaType | None = None
        # Track all top-level names (functions + globals) for cross-checking
        self._global_names: dict[str, SourceLocation | None] = {}

    def run(self, program: Program) -> None:
        self._register_builtins()
        self._pass1(program)
        self._pass2(program)
        self._check_main()

    # --- builtins ---

    def _register_builtins(self) -> None:
        builtins = [
            FunctionSig("print", [SeptaType.WORD], SeptaType.VOID, None, True),
            FunctionSig("printd", [SeptaType.WORD], SeptaType.VOID, None, True),
            FunctionSig("halt", [], SeptaType.VOID, None, True),
        ]
        for sig in builtins:
            self._functions[sig.name] = sig
            self._global_names[sig.name] = None

    # --- pass 1: collect declarations ---

    def _pass1(self, program: Program) -> None:
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self._register_function(decl)
            elif isinstance(decl, GlobalDecl):
                self._register_global(decl)

    def _register_function(self, decl: FunctionDecl) -> None:
        # Check name collision with any top-level name
        if decl.name in self._global_names:
            prev = self._global_names[decl.name]
            msg = f"duplicate declaration of '{decl.name}'"
            if prev:
                msg += f" (previously declared at {prev})"
            raise SemanticError(msg, decl.location)

        # Check duplicate parameter names
        seen_params: set[str] = set()
        param_types: list[SeptaType] = []
        for param in decl.params:
            if param.name in seen_params:
                raise SemanticError(
                    f"duplicate parameter '{param.name}'", param.location
                )
            seen_params.add(param.name)
            param_types.append(type_from_name(param.type_name))

        ret_type = type_from_name(decl.return_type)
        sig = FunctionSig(decl.name, param_types, ret_type, decl.location)
        self._functions[decl.name] = sig
        self._global_names[decl.name] = decl.location

    def _register_global(self, decl: GlobalDecl) -> None:
        # Check name collision
        if decl.name in self._global_names:
            prev = self._global_names[decl.name]
            msg = f"duplicate declaration of '{decl.name}'"
            if prev:
                msg += f" (previously declared at {prev})"
            raise SemanticError(msg, decl.location)

        # Validate constant initializer and infer type
        init_type = self._constant_type(decl.value)
        declared_type = type_from_name(decl.type_name)
        if init_type != declared_type:
            raise SemanticError(
                f"type mismatch in global '{decl.name}': "
                f"declared '{declared_type.value}' "
                f"but initializer is '{init_type.value}'",
                decl.location,
            )

        sym = Symbol(decl.name, declared_type, "global", decl.location)
        self._global_scope.define(sym)
        self._global_names[decl.name] = decl.location

    def _constant_type(self, expr: Expr) -> SeptaType:
        """Check that expr is a constant (literal only) and return its type."""
        if isinstance(expr, NumberLiteral):
            return SeptaType.WORD
        if isinstance(expr, BoolLiteral):
            return SeptaType.BOOL7
        raise SemanticError(
            "global initializer must be a constant (literal value)",
            expr.location,
        )

    # --- pass 2: validate function bodies ---

    def _pass2(self, program: Program) -> None:
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self._analyze_function(decl)

    def _analyze_function(self, decl: FunctionDecl) -> None:
        fn_scope = Scope(parent=self._global_scope)

        for param in decl.params:
            typ = type_from_name(param.type_name)
            fn_scope.define(
                Symbol(param.name, typ, "parameter", param.location)
            )

        prev_scope = self._current_scope
        prev_ret = self._current_fn_return_type
        self._current_scope = fn_scope
        self._current_fn_return_type = type_from_name(decl.return_type)

        for stmt in decl.body.statements:
            self._analyze_statement(stmt)

        self._current_scope = prev_scope
        self._current_fn_return_type = prev_ret

    # --- blocks and statements ---

    def _analyze_block(self, block: Block) -> None:
        """Analyze a nested block (if/while body). Creates a child scope."""
        child = Scope(parent=self._current_scope)
        prev = self._current_scope
        self._current_scope = child
        for stmt in block.statements:
            self._analyze_statement(stmt)
        self._current_scope = prev

    def _analyze_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStmt):
            self._analyze_let(stmt)
        elif isinstance(stmt, AssignStmt):
            self._analyze_assign(stmt)
        elif isinstance(stmt, IfStmt):
            self._analyze_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._analyze_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._analyze_return(stmt)
        elif isinstance(stmt, ExprStmt):
            self._infer_type(stmt.expr)

    def _analyze_let(self, stmt: LetStmt) -> None:
        declared_type = type_from_name(stmt.type_name)
        value_type = self._infer_type(stmt.value)
        if declared_type != value_type:
            raise SemanticError(
                f"type mismatch in let '{stmt.name}': "
                f"declared '{declared_type.value}' "
                f"but initializer is '{value_type.value}'",
                stmt.location,
            )
        self._current_scope.define(
            Symbol(stmt.name, declared_type, "variable", stmt.location)
        )

    def _analyze_assign(self, stmt: AssignStmt) -> None:
        if isinstance(stmt.target, Ident):
            sym = self._current_scope.lookup(stmt.target.name)
            if sym is None:
                raise SemanticError(
                    f"undefined variable '{stmt.target.name}'",
                    stmt.target.location,
                )
            target_type = sym.type
        elif isinstance(stmt.target, StoreAccess):
            idx_type = self._infer_type(stmt.target.index)
            if idx_type != SeptaType.WORD:
                raise SemanticError(
                    f"store index must be word, got '{idx_type.value}'",
                    stmt.target.location,
                )
            target_type = SeptaType.WORD
        else:
            raise SemanticError("invalid assignment target", stmt.location)

        value_type = self._infer_type(stmt.value)
        if target_type != value_type:
            raise SemanticError(
                f"type mismatch in assignment: "
                f"target is '{target_type.value}' "
                f"but value is '{value_type.value}'",
                stmt.location,
            )

    def _analyze_if(self, stmt: IfStmt) -> None:
        cond_type = self._infer_type(stmt.condition)
        if cond_type == SeptaType.VOID:
            raise SemanticError(
                "condition cannot be void", stmt.condition.location
            )
        self._analyze_block(stmt.then_block)
        if stmt.else_block is not None:
            self._analyze_block(stmt.else_block)

    def _analyze_while(self, stmt: WhileStmt) -> None:
        cond_type = self._infer_type(stmt.condition)
        if cond_type == SeptaType.VOID:
            raise SemanticError(
                "condition cannot be void", stmt.condition.location
            )
        self._analyze_block(stmt.body)

    def _analyze_return(self, stmt: ReturnStmt) -> None:
        ret = self._current_fn_return_type
        if ret == SeptaType.VOID:
            if stmt.value is not None:
                raise SemanticError(
                    "void function cannot return a value", stmt.location
                )
        else:
            if stmt.value is None:
                raise SemanticError(
                    f"non-void function must return a value "
                    f"of type '{ret.value}'",
                    stmt.location,
                )
            value_type = self._infer_type(stmt.value)
            if value_type != ret:
                raise SemanticError(
                    f"return type mismatch: expected '{ret.value}', "
                    f"got '{value_type.value}'",
                    stmt.location,
                )

    # --- type inference ---

    def _infer_type(self, expr: Expr) -> SeptaType:
        """Infer the type of an expression. Raises SemanticError on failure."""
        if isinstance(expr, NumberLiteral):
            return SeptaType.WORD

        if isinstance(expr, BoolLiteral):
            return SeptaType.BOOL7

        if isinstance(expr, Ident):
            sym = self._current_scope.lookup(expr.name)
            if sym is None:
                raise SemanticError(
                    f"undefined variable '{expr.name}'", expr.location
                )
            return sym.type

        if isinstance(expr, StoreAccess):
            idx_type = self._infer_type(expr.index)
            if idx_type != SeptaType.WORD:
                raise SemanticError(
                    f"store index must be word, got '{idx_type.value}'",
                    expr.location,
                )
            return SeptaType.WORD

        if isinstance(expr, UnaryExpr):
            return self._infer_unary(expr)

        if isinstance(expr, BinaryExpr):
            return self._infer_binary(expr)

        if isinstance(expr, FnCall):
            return self._infer_call(expr)

        raise SemanticError(
            "cannot determine type of expression", expr.location
        )

    def _infer_unary(self, expr: UnaryExpr) -> SeptaType:
        operand_type = self._infer_type(expr.operand)

        if expr.op == "-":
            if operand_type != SeptaType.WORD:
                raise SemanticError(
                    f"unary '-' requires word, got '{operand_type.value}'",
                    expr.location,
                )
            return SeptaType.WORD

        if expr.op == "!":
            if operand_type == SeptaType.VOID:
                raise SemanticError(
                    "cannot negate void expression", expr.location
                )
            return SeptaType.BOOL7

        raise SemanticError(f"unknown unary operator '{expr.op}'", expr.location)

    def _infer_binary(self, expr: BinaryExpr) -> SeptaType:
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)

        if expr.op in _ARITHMETIC_OPS:
            if left_type != SeptaType.WORD or right_type != SeptaType.WORD:
                raise SemanticError(
                    f"arithmetic requires word operands, "
                    f"got '{left_type.value}' and '{right_type.value}'",
                    expr.location,
                )
            return SeptaType.WORD

        if expr.op in _ORDERED_CMP_OPS:
            if left_type != SeptaType.WORD or right_type != SeptaType.WORD:
                raise SemanticError(
                    f"ordered comparison requires word operands, "
                    f"got '{left_type.value}' and '{right_type.value}'",
                    expr.location,
                )
            return SeptaType.BOOL7

        if expr.op in _EQUALITY_OPS:
            if left_type != right_type:
                raise SemanticError(
                    f"equality requires same types, "
                    f"got '{left_type.value}' and '{right_type.value}'",
                    expr.location,
                )
            if left_type == SeptaType.VOID:
                raise SemanticError(
                    "cannot compare void values", expr.location
                )
            return SeptaType.BOOL7

        raise SemanticError(
            f"unknown binary operator '{expr.op}'", expr.location
        )

    def _infer_call(self, expr: FnCall) -> SeptaType:
        sig = self._functions.get(expr.name)
        if sig is None:
            raise SemanticError(
                f"undefined function '{expr.name}'", expr.location
            )

        if len(expr.args) != len(sig.param_types):
            raise SemanticError(
                f"function '{expr.name}' expects {len(sig.param_types)} "
                f"argument(s), got {len(expr.args)}",
                expr.location,
            )

        for i, (arg, expected) in enumerate(
            zip(expr.args, sig.param_types, strict=True)
        ):
            arg_type = self._infer_type(arg)
            if arg_type != expected:
                raise SemanticError(
                    f"argument {i + 1} of '{expr.name}': "
                    f"expected '{expected.value}', got '{arg_type.value}'",
                    expr.location,
                )

        return sig.return_type

    # --- main check ---

    def _check_main(self) -> None:
        sig = self._functions.get("main")
        if sig is None:
            raise SemanticError("missing 'main' function")
        if sig.param_types:
            raise SemanticError(
                "'main' must take no parameters", sig.location
            )
        if sig.return_type != SeptaType.VOID:
            raise SemanticError("'main' must return void", sig.location)
