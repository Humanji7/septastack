"""Recursive descent parser for SeptaLang.

Transforms a token list into an AST.
No semantic analysis — only syntactic structure.

Grammar (precedence low→high):
  expr       = equality
  equality   = comparison { ("==" | "!=") comparison }
  comparison = term { (">" | "<" | ">=" | "<=") term }
  term       = factor { ("+" | "-") factor }
  factor     = unary                          (placeholder for future * /)
  unary      = [ "-" | "!" ] primary
  primary    = number | ident | "true" | "false"
             | "store" "[" expr "]"
             | ident "(" [ arguments ] ")"
             | "(" expr ")"

Dependencies: lexer/tokens.py, parser/ast.py, common/errors.py, common/base7.py
"""

from septa.common.base7 import parse_base7, parse_decimal
from septa.common.errors import ParserError
from septa.lexer.tokens import Token, TokenType
from septa.parser.ast import (
    AssignStmt,
    BinaryExpr,
    Block,
    BoolLiteral,
    Declaration,
    ExprStmt,
    Expr,
    FnCall,
    FunctionDecl,
    GlobalDecl,
    Ident,
    IfStmt,
    LetStmt,
    NumberLiteral,
    Param,
    Program,
    ReturnStmt,
    Statement,
    StoreAccess,
    UnaryExpr,
    WhileStmt,
)

VALID_TYPES = {"word", "bool7", "addr", "void"}


class Parser:
    """Parse a token list into a SeptaLang AST.

    Usage:
        parser = Parser(tokens)
        program = parser.parse()
    """

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # --- helpers ---

    def _current(self) -> Token:
        if self._pos >= len(self._tokens):
            return self._tokens[-1]  # EOF
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._current()
        if tok.type is not TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._current().type in types

    def _match(self, *types: TokenType) -> Token | None:
        if self._current().type in types:
            return self._advance()
        return None

    def _expect(self, tt: TokenType) -> Token:
        tok = self._current()
        if tok.type is not tt:
            raise ParserError(
                f"expected {tt.name}, got {tok.type.name} ({tok.value!r})",
                tok.location,
            )
        return self._advance()

    def _error(self, msg: str) -> ParserError:
        return ParserError(msg, self._current().location)

    # --- top level ---

    def parse(self) -> Program:
        loc = self._current().location
        decls: list[Declaration] = []
        while not self._check(TokenType.EOF):
            decls.append(self._parse_declaration())
        return Program(declarations=decls, location=loc)

    def _parse_declaration(self) -> Declaration:
        if self._check(TokenType.FN):
            return self._parse_function_decl()
        if self._check(TokenType.LET):
            return self._parse_global_decl()
        raise self._error(
            f"expected function or global declaration, "
            f"got {self._current().type.name}"
        )

    def _parse_function_decl(self) -> FunctionDecl:
        loc = self._expect(TokenType.FN).location
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)
        params: list[Param] = []
        if not self._check(TokenType.RPAREN):
            params = self._parse_params()
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.ARROW)
        ret_type = self._parse_type()
        body = self._parse_block()
        return FunctionDecl(
            name=name_tok.value,
            params=params,
            return_type=ret_type,
            body=body,
            location=loc,
        )

    def _parse_global_decl(self) -> GlobalDecl:
        loc = self._expect(TokenType.LET).location
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.COLON)
        type_name = self._parse_type()
        self._expect(TokenType.ASSIGN)
        value = self._parse_expr()
        self._expect(TokenType.SEMICOLON)
        return GlobalDecl(
            name=name_tok.value,
            type_name=type_name,
            value=value,
            location=loc,
        )

    def _parse_params(self) -> list[Param]:
        params = [self._parse_param()]
        while self._match(TokenType.COMMA):
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> Param:
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.COLON)
        type_name = self._parse_type()
        return Param(
            name=name_tok.value,
            type_name=type_name,
            location=name_tok.location,
        )

    def _parse_type(self) -> str:
        tok = self._current()
        if tok.type in (TokenType.WORD, TokenType.BOOL7,
                        TokenType.ADDR, TokenType.VOID):
            self._advance()
            return tok.value
        raise ParserError(
            f"expected type (word, bool7, addr, void), "
            f"got {tok.type.name} ({tok.value!r})",
            tok.location,
        )

    # --- blocks and statements ---

    def _parse_block(self) -> Block:
        loc = self._expect(TokenType.LBRACE).location
        stmts: list[Statement] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            stmts.append(self._parse_statement())
        self._expect(TokenType.RBRACE)
        return Block(statements=stmts, location=loc)

    def _parse_statement(self) -> Statement:
        if self._check(TokenType.LET):
            return self._parse_let_stmt()
        if self._check(TokenType.IF):
            return self._parse_if_stmt()
        if self._check(TokenType.WHILE):
            return self._parse_while_stmt()
        if self._check(TokenType.RETURN):
            return self._parse_return_stmt()
        return self._parse_assign_or_expr_stmt()

    def _parse_let_stmt(self) -> LetStmt:
        loc = self._expect(TokenType.LET).location
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.COLON)
        type_name = self._parse_type()
        self._expect(TokenType.ASSIGN)
        value = self._parse_expr()
        self._expect(TokenType.SEMICOLON)
        return LetStmt(
            name=name_tok.value,
            type_name=type_name,
            value=value,
            location=loc,
        )

    def _parse_if_stmt(self) -> IfStmt:
        loc = self._expect(TokenType.IF).location
        cond = self._parse_expr()
        then_block = self._parse_block()
        else_block = None
        if self._match(TokenType.ELSE):
            else_block = self._parse_block()
        return IfStmt(
            condition=cond,
            then_block=then_block,
            else_block=else_block,
            location=loc,
        )

    def _parse_while_stmt(self) -> WhileStmt:
        loc = self._expect(TokenType.WHILE).location
        cond = self._parse_expr()
        body = self._parse_block()
        return WhileStmt(condition=cond, body=body, location=loc)

    def _parse_return_stmt(self) -> ReturnStmt:
        loc = self._expect(TokenType.RETURN).location
        value: Expr | None = None
        if not self._check(TokenType.SEMICOLON):
            value = self._parse_expr()
        self._expect(TokenType.SEMICOLON)
        return ReturnStmt(value=value, location=loc)

    def _parse_assign_or_expr_stmt(self) -> Statement:
        expr = self._parse_expr()

        if self._match(TokenType.ASSIGN):
            if not isinstance(expr, (Ident, StoreAccess)):
                raise ParserError(
                    "invalid assignment target",
                    expr.location,
                )
            value = self._parse_expr()
            self._expect(TokenType.SEMICOLON)
            return AssignStmt(
                target=expr,
                value=value,
                location=expr.location,
            )

        self._expect(TokenType.SEMICOLON)
        return ExprStmt(expr=expr, location=expr.location)

    # --- expressions (precedence climbing) ---

    def _parse_expr(self) -> Expr:
        return self._parse_equality()

    def _parse_equality(self) -> Expr:
        left = self._parse_comparison()
        while tok := self._match(TokenType.EQ, TokenType.NEQ):
            right = self._parse_comparison()
            left = BinaryExpr(
                left=left, op=tok.value, right=right, location=left.location
            )
        return left

    def _parse_comparison(self) -> Expr:
        left = self._parse_term()
        while tok := self._match(TokenType.GT, TokenType.LT,
                                 TokenType.GTE, TokenType.LTE):
            right = self._parse_term()
            left = BinaryExpr(
                left=left, op=tok.value, right=right, location=left.location
            )
        return left

    def _parse_term(self) -> Expr:
        left = self._parse_unary()
        while tok := self._match(TokenType.PLUS, TokenType.MINUS):
            right = self._parse_unary()
            left = BinaryExpr(
                left=left, op=tok.value, right=right, location=left.location
            )
        return left

    def _parse_unary(self) -> Expr:
        if tok := self._match(TokenType.MINUS, TokenType.BANG):
            operand = self._parse_unary()
            return UnaryExpr(op=tok.value, operand=operand, location=tok.location)
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        tok = self._current()

        # Base-7 number
        if tok.type is TokenType.NUMBER:
            self._advance()
            try:
                value = parse_base7(tok.value)
            except ValueError as e:
                raise ParserError(str(e), tok.location) from e
            return NumberLiteral(value=value, location=tok.location)

        # Decimal number (d:prefix already stripped by lexer)
        if tok.type is TokenType.DECIMAL_NUMBER:
            self._advance()
            try:
                value = parse_decimal(tok.value)
            except ValueError as e:
                raise ParserError(str(e), tok.location) from e
            return NumberLiteral(
                value=value, location=tok.location, was_decimal=True
            )

        # Boolean literals
        if tok.type is TokenType.TRUE:
            self._advance()
            return BoolLiteral(value=True, location=tok.location)

        if tok.type is TokenType.FALSE:
            self._advance()
            return BoolLiteral(value=False, location=tok.location)

        # store[expr]
        if tok.type is TokenType.STORE:
            self._advance()
            self._expect(TokenType.LBRACKET)
            index = self._parse_expr()
            self._expect(TokenType.RBRACKET)
            return StoreAccess(index=index, location=tok.location)

        # Identifier or function call
        if tok.type is TokenType.IDENT:
            self._advance()
            # Function call: ident(args...)
            if self._check(TokenType.LPAREN):
                self._advance()  # consume (
                args: list[Expr] = []
                if not self._check(TokenType.RPAREN):
                    args = self._parse_arguments()
                self._expect(TokenType.RPAREN)
                return FnCall(name=tok.value, args=args, location=tok.location)
            return Ident(name=tok.value, location=tok.location)

        # Grouped expression
        if tok.type is TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        raise self._error(
            f"expected expression, got {tok.type.name} ({tok.value!r})"
        )

    def _parse_arguments(self) -> list[Expr]:
        args = [self._parse_expr()]
        while self._match(TokenType.COMMA):
            args.append(self._parse_expr())
        return args
