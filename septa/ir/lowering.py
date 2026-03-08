"""AST to IR lowering for SeptaLang v0.1.

Transforms a semantically-analyzed AST into flat IR instructions.
Assumes semantic analysis has already passed (types valid, names resolved).

Design:
  - Expression lowering returns the slot name containing the result.
  - Temporaries are allocated per-function with incrementing counters.
  - Labels are generated per-function with incrementing counters.
  - Scope tracking handles variable shadowing by renaming locals.
  - Builtins (print, printd, halt) are lowered to dedicated IR ops.
  - User function calls use ARG + CALL instructions.

Evaluation order is explicit: left-to-right for binary ops, arguments
evaluated in order before the call.

Public API:
  lower(program) -> IRProgram
"""

from septa.common.errors import CodegenError
from septa.ir.ir import Instr, IRFunction, IRGlobal, IRProgram, Op
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

_BOOL_TRUE = 6
_BOOL_FALSE = 0

_ARITH_OPS = {
    "+": Op.ADD,
    "-": Op.SUB,
}

_CMP_OPS = {
    "==": Op.CMP_EQ,
    "!=": Op.CMP_NE,
    ">": Op.CMP_GT,
    "<": Op.CMP_LT,
    ">=": Op.CMP_GE,
    "<=": Op.CMP_LE,
}

_BUILTINS = {"print", "printd", "halt"}


def lower(program: Program) -> IRProgram:
    """Lower a parsed+analyzed program AST to IR."""
    return _Lowering().run(program)


class _Lowering:
    def __init__(self) -> None:
        self._globals: dict[str, IRGlobal] = {}

    def run(self, program: Program) -> IRProgram:
        # Collect globals and function return types
        fn_return_types: dict[str, str] = {}
        for decl in program.declarations:
            if isinstance(decl, GlobalDecl):
                self._collect_global(decl)
            elif isinstance(decl, FunctionDecl):
                fn_return_types[decl.name] = decl.return_type

        # Lower each function
        functions: list[IRFunction] = []
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                functions.append(self._lower_function(decl, fn_return_types))

        return IRProgram(
            globals=list(self._globals.values()),
            functions=functions,
        )

    def _collect_global(self, decl: GlobalDecl) -> None:
        if isinstance(decl.value, NumberLiteral):
            value = decl.value.value
        elif isinstance(decl.value, BoolLiteral):
            value = _BOOL_TRUE if decl.value.value else _BOOL_FALSE
        else:
            raise CodegenError(
                "non-constant global initializer", decl.location
            )
        slot = f"global:{decl.name}"
        self._globals[decl.name] = IRGlobal(decl.name, slot, value)

    def _lower_function(
        self, decl: FunctionDecl, fn_return_types: dict[str, str]
    ) -> IRFunction:
        ctx = _FnContext(
            fn_name=decl.name,
            global_names=set(self._globals),
            fn_return_types=fn_return_types,
        )

        # Define params
        for param in decl.params:
            ctx.define_param(param.name)

        # Lower body
        for stmt in decl.body.statements:
            ctx.lower_statement(stmt)

        # Ensure function ends with a return
        body = ctx.instructions
        if not body or body[-1].op not in (Op.RETURN, Op.RETURN_VOID):
            body.append(Instr(Op.RETURN_VOID))

        return IRFunction(
            name=decl.name,
            params=ctx.param_slots,
            local_slots=ctx.local_slots,
            temp_count=ctx.temp_counter,
            body=body,
        )


class _FnContext:
    """Lowering context for a single function."""

    def __init__(
        self,
        fn_name: str,
        global_names: set[str],
        fn_return_types: dict[str, str],
    ) -> None:
        self._fn_name = fn_name
        self._global_names = global_names
        self._fn_return_types = fn_return_types
        self.instructions: list[Instr] = []
        self.temp_counter = 0
        self._label_counter = 0

        # Scope: list of frames, each maps source name -> slot
        self._scope_frames: list[dict[str, str]] = [{}]
        self.param_slots: list[str] = []
        self.local_slots: list[str] = []
        self._name_counters: dict[str, int] = {}

    # --- slot management ---

    def _new_temp(self) -> str:
        slot = f"temp:{self.temp_counter}"
        self.temp_counter += 1
        return slot

    def _new_label(self) -> str:
        label = f"L{self._label_counter}"
        self._label_counter += 1
        return label

    def define_param(self, name: str) -> str:
        slot = f"param:{name}"
        self._scope_frames[-1][name] = slot
        self.param_slots.append(slot)
        return slot

    def _define_local(self, name: str) -> str:
        if name in self._name_counters:
            n = self._name_counters[name]
            self._name_counters[name] = n + 1
            slot = f"local:{name}_{n}"
        else:
            self._name_counters[name] = 1
            slot = f"local:{name}"
        self._scope_frames[-1][name] = slot
        self.local_slots.append(slot)
        return slot

    def _resolve(self, name: str) -> str:
        for frame in reversed(self._scope_frames):
            if name in frame:
                return frame[name]
        if name in self._global_names:
            return f"global:{name}"
        raise CodegenError(f"unresolved variable '{name}' in {self._fn_name}")

    def _push_scope(self) -> None:
        self._scope_frames.append({})

    def _pop_scope(self) -> None:
        self._scope_frames.pop()

    def _emit(self, instr: Instr) -> None:
        self.instructions.append(instr)

    # --- statement lowering ---

    def lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStmt):
            self._lower_let(stmt)
        elif isinstance(stmt, AssignStmt):
            self._lower_assign(stmt)
        elif isinstance(stmt, IfStmt):
            self._lower_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._lower_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._lower_return(stmt)
        elif isinstance(stmt, ExprStmt):
            self._lower_expr(stmt.expr)  # result discarded

    def _lower_let(self, stmt: LetStmt) -> None:
        value_slot = self._lower_expr(stmt.value)
        local_slot = self._define_local(stmt.name)
        self._emit(Instr(Op.COPY, dst=local_slot, src=value_slot))

    def _lower_assign(self, stmt: AssignStmt) -> None:
        if isinstance(stmt.target, Ident):
            target_slot = self._resolve(stmt.target.name)
            value_slot = self._lower_expr(stmt.value)
            self._emit(Instr(Op.COPY, dst=target_slot, src=value_slot))
        elif isinstance(stmt.target, StoreAccess):
            addr_slot = self._lower_expr(stmt.target.index)
            value_slot = self._lower_expr(stmt.value)
            self._emit(Instr(Op.MEM_STORE, dst=addr_slot, src=value_slot))

    def _lower_if(self, stmt: IfStmt) -> None:
        cond_slot = self._lower_expr(stmt.condition)

        if stmt.else_block is not None:
            else_label = self._new_label()
            end_label = self._new_label()
            self._emit(Instr(Op.JUMP_Z, src=cond_slot, label=else_label))
            self._lower_block(stmt.then_block)
            self._emit(Instr(Op.JUMP, label=end_label))
            self._emit(Instr(Op.LABEL, label=else_label))
            self._lower_block(stmt.else_block)
            self._emit(Instr(Op.LABEL, label=end_label))
        else:
            end_label = self._new_label()
            self._emit(Instr(Op.JUMP_Z, src=cond_slot, label=end_label))
            self._lower_block(stmt.then_block)
            self._emit(Instr(Op.LABEL, label=end_label))

    def _lower_while(self, stmt: WhileStmt) -> None:
        loop_label = self._new_label()
        end_label = self._new_label()
        self._emit(Instr(Op.LABEL, label=loop_label))
        cond_slot = self._lower_expr(stmt.condition)
        self._emit(Instr(Op.JUMP_Z, src=cond_slot, label=end_label))
        self._lower_block(stmt.body)
        self._emit(Instr(Op.JUMP, label=loop_label))
        self._emit(Instr(Op.LABEL, label=end_label))

    def _lower_return(self, stmt: ReturnStmt) -> None:
        if stmt.value is None:
            self._emit(Instr(Op.RETURN_VOID))
        else:
            value_slot = self._lower_expr(stmt.value)
            self._emit(Instr(Op.RETURN, src=value_slot))

    def _lower_block(self, block: Block) -> None:
        self._push_scope()
        for stmt in block.statements:
            self.lower_statement(stmt)
        self._pop_scope()

    # --- expression lowering ---

    def _lower_expr(self, expr: Expr) -> str:
        """Lower an expression, return the slot containing the result."""
        if isinstance(expr, NumberLiteral):
            return self._lower_number(expr)
        if isinstance(expr, BoolLiteral):
            return self._lower_bool(expr)
        if isinstance(expr, Ident):
            return self._resolve(expr.name)
        if isinstance(expr, StoreAccess):
            return self._lower_store_read(expr)
        if isinstance(expr, UnaryExpr):
            return self._lower_unary(expr)
        if isinstance(expr, BinaryExpr):
            return self._lower_binary(expr)
        if isinstance(expr, FnCall):
            return self._lower_call(expr)
        raise CodegenError("unsupported expression in lowering")

    def _lower_number(self, expr: NumberLiteral) -> str:
        tmp = self._new_temp()
        self._emit(Instr(Op.CONST, dst=tmp, imm=expr.value))
        return tmp

    def _lower_bool(self, expr: BoolLiteral) -> str:
        tmp = self._new_temp()
        value = _BOOL_TRUE if expr.value else _BOOL_FALSE
        self._emit(Instr(Op.CONST, dst=tmp, imm=value))
        return tmp

    def _lower_store_read(self, expr: StoreAccess) -> str:
        addr_slot = self._lower_expr(expr.index)
        tmp = self._new_temp()
        self._emit(Instr(Op.MEM_LOAD, dst=tmp, src=addr_slot))
        return tmp

    def _lower_unary(self, expr: UnaryExpr) -> str:
        operand_slot = self._lower_expr(expr.operand)
        tmp = self._new_temp()
        if expr.op == "-":
            self._emit(Instr(Op.NEG, dst=tmp, src=operand_slot))
        elif expr.op == "!":
            self._emit(Instr(Op.NOT, dst=tmp, src=operand_slot))
        return tmp

    def _lower_binary(self, expr: BinaryExpr) -> str:
        left_slot = self._lower_expr(expr.left)
        right_slot = self._lower_expr(expr.right)
        tmp = self._new_temp()

        if expr.op in _ARITH_OPS:
            self._emit(Instr(
                _ARITH_OPS[expr.op],
                dst=tmp, src=left_slot, src2=right_slot,
            ))
        elif expr.op in _CMP_OPS:
            self._emit(Instr(
                _CMP_OPS[expr.op],
                dst=tmp, src=left_slot, src2=right_slot,
            ))

        return tmp

    def _lower_call(self, expr: FnCall) -> str:
        """Lower a function call (builtin or user-defined)."""
        # Builtins: dedicated IR ops, no ARG/CALL
        if expr.name == "print":
            arg_slot = self._lower_expr(expr.args[0])
            self._emit(Instr(Op.PRINT, src=arg_slot))
            return ""
        if expr.name == "printd":
            arg_slot = self._lower_expr(expr.args[0])
            self._emit(Instr(Op.PRINTD, src=arg_slot))
            return ""
        if expr.name == "halt":
            self._emit(Instr(Op.HALT))
            return ""

        # User function: evaluate args, emit ARG + CALL
        for i, arg in enumerate(expr.args):
            arg_slot = self._lower_expr(arg)
            self._emit(Instr(Op.ARG, imm=i, src=arg_slot))

        ret_type = self._fn_return_types.get(expr.name, "void")
        if ret_type != "void":
            tmp = self._new_temp()
            self._emit(Instr(Op.CALL, dst=tmp, label=expr.name))
            return tmp
        else:
            self._emit(Instr(Op.CALL, label=expr.name))
            return ""
