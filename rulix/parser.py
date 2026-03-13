"""AST node definitions and recursive-descent parser."""
from __future__ import annotations

from dataclasses import dataclass, field

from .lexer import TT, Token, tokenize


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

@dataclass
class Literal:
    value: object  # int | float | str | bool | None


@dataclass
class Identifier:
    name: str


@dataclass
class BinaryOp:
    op:    str
    left:  object
    right: object


@dataclass
class UnaryOp:
    op:      str    # 'not' | '-'
    operand: object


@dataclass
class FunctionCall:
    name: str
    args: list = field(default_factory=list)


@dataclass
class Assignment:
    name:  str
    value: object


@dataclass
class Disable:
    """Marks the current rule as disabled for all future runs."""


@dataclass
class Stop:
    """Ends the current evaluation cycle immediately."""


@dataclass
class Rule:
    label:      str | None
    conditions: list        # list of expr nodes; empty = unconditional
    body:       list        # list of statement nodes


@dataclass
class Program:
    rules: list[Rule]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # --- token navigation ---

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        t = self._tokens[self._pos]
        self._pos += 1
        return t

    def _check(self, *types: TT) -> bool:
        return self._peek().type in types

    def _match(self, *types: TT) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, tt: TT, msg: str = "") -> Token:
        t = self._advance()
        if t.type != tt:
            raise ParseError(msg or f"Expected {tt.name}, got {t.type.name!r} at line {t.line}")
        return t

    def _skip_newlines(self) -> None:
        while self._check(TT.NEWLINE):
            self._advance()

    # --- grammar ---

    def parse(self) -> Program:
        rules: list[Rule] = []
        self._skip_newlines()
        while not self._check(TT.EOF):
            rules.append(self._parse_rule())
            self._skip_newlines()
        return Program(rules)

    def _parse_rule(self) -> Rule:
        # Optional label: 'rule' IDENT ':'
        label: str | None = None
        if self._match(TT.RULE):
            label = self._expect(TT.IDENT, "Expected rule name after 'rule'").value
            self._expect(TT.COLON, "Expected ':' after rule name")

        # Conditions (zero or more expressions before '=>')
        conditions: list = []
        if not self._check(TT.ARROW):
            conditions.append(self._parse_expr())
            while self._match(TT.COMMA):
                conditions.append(self._parse_expr())

        self._expect(TT.ARROW, f"Expected '=>' in rule at line {self._peek().line}")
        body = self._parse_body()
        return Rule(label, conditions, body)

    def _parse_body(self) -> list:
        if self._match(TT.LBRACE):
            self._match(TT.NEWLINE)   # newline after '{' is optional
            self._skip_newlines()
            stmts: list = []
            while not self._check(TT.RBRACE, TT.EOF):
                stmts.append(self._parse_statement())
                self._match(TT.NEWLINE)
                self._skip_newlines()
            self._expect(TT.RBRACE, "Expected '}' to close rule body")
            return stmts
        return [self._parse_statement()]

    def _parse_statement(self) -> object:
        # Control-flow keywords — must be checked before the expression path.
        if self._match(TT.DISABLE):
            return Disable()
        if self._match(TT.STOP):
            return Stop()
        # Look one token ahead: 'IDENT =' is an assignment (not 'IDENT ==').
        if (self._check(TT.IDENT)
                and self._pos + 1 < len(self._tokens)
                and self._tokens[self._pos + 1].type == TT.ASSIGN):
            name = self._advance().value
            self._advance()  # consume '='
            return Assignment(name, self._parse_expr())
        return self._parse_expr()

    # Expressions — standard precedence ladder

    def _parse_expr(self) -> object:
        return self._parse_or()

    def _parse_or(self) -> object:
        left = self._parse_and()
        while self._match(TT.OR):
            left = BinaryOp("or", left, self._parse_and())
        return left

    def _parse_and(self) -> object:
        left = self._parse_not()
        while self._match(TT.AND):
            left = BinaryOp("and", left, self._parse_not())
        return left

    def _parse_not(self) -> object:
        if self._match(TT.NOT):
            return UnaryOp("not", self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> object:
        left = self._parse_add()
        op_map = {
            TT.EQ:  "==",
            TT.NEQ: "!=",
            TT.LT:  "<",
            TT.GT:  ">",
            TT.LTE: "<=",
            TT.GTE: ">=",
        }
        for tt, op in op_map.items():
            if self._match(tt):
                return BinaryOp(op, left, self._parse_add())
        return left

    def _parse_add(self) -> object:
        left = self._parse_mul()
        while True:
            if self._match(TT.PLUS):
                left = BinaryOp("+", left, self._parse_mul())
            elif self._match(TT.MINUS):
                left = BinaryOp("-", left, self._parse_mul())
            else:
                break
        return left

    def _parse_mul(self) -> object:
        left = self._parse_unary()
        while True:
            if self._match(TT.STAR):
                left = BinaryOp("*", left, self._parse_unary())
            elif self._match(TT.SLASH):
                left = BinaryOp("/", left, self._parse_unary())
            elif self._match(TT.PERCENT):
                left = BinaryOp("%", left, self._parse_unary())
            else:
                break
        return left

    def _parse_unary(self) -> object:
        if self._match(TT.MINUS):
            return UnaryOp("-", self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> object:
        t = self._peek()

        if t.type == TT.INT:
            self._advance()
            return Literal(t.value)

        if t.type == TT.FLOAT:
            self._advance()
            return Literal(t.value)

        if t.type == TT.STRING:
            self._advance()
            return Literal(t.value)

        if t.type in (TT.TRUE, TT.FALSE):
            self._advance()
            return Literal(t.value)  # value is already a Python bool

        if t.type == TT.NULL:
            self._advance()
            return Literal(None)

        if t.type == TT.IDENT:
            self._advance()
            if self._match(TT.LPAREN):
                args: list = []
                if not self._check(TT.RPAREN):
                    args.append(self._parse_expr())
                    while self._match(TT.COMMA):
                        args.append(self._parse_expr())
                self._expect(TT.RPAREN, f"Expected ')' in call to '{t.value}' at line {t.line}")
                return FunctionCall(t.value, args)
            return Identifier(t.value)

        if t.type == TT.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TT.RPAREN, f"Expected ')' at line {t.line}")
            return expr

        raise ParseError(f"Unexpected token {t.type.name} ({t.value!r}) at line {t.line}")


def parse(source: str) -> Program:
    tokens = tokenize(source)
    return Parser(tokens).parse()
