from __future__ import annotations

from .parser import (
    Assignment, BinaryOp, FunctionCall, Identifier, Literal, Program,
    Rule, UnaryOp, parse,
)


class RulixError(Exception):
    pass


# ---------------------------------------------------------------------------
# Built-in functions (minimal set for the basic implementation)
# ---------------------------------------------------------------------------

def _builtin_is_null(args: list) -> bool:
    return args[0] is None

def _builtin_str(args: list) -> str:
    v = args[0]
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

def _builtin_int(args: list) -> int:
    try:
        return int(args[0])
    except (TypeError, ValueError) as e:
        raise RulixError(f"int(): cannot convert {args[0]!r}") from e

def _builtin_float(args: list) -> float:
    try:
        return float(args[0])
    except (TypeError, ValueError) as e:
        raise RulixError(f"float(): cannot convert {args[0]!r}") from e

def _builtin_bool(args: list) -> bool:
    return _truthy(args[0])

def _builtin_type(args: list) -> str:
    return {int: "int", float: "float", bool: "bool", str: "string", type(None): "null"}.get(
        type(args[0]), "unknown"
    )


_BUILTINS: dict[str, tuple[callable, int | None]] = {
    # name: (handler, arity)  arity=None means variadic
    "is_null": (_builtin_is_null, 1),
    "str":     (_builtin_str,     1),
    "int":     (_builtin_int,     1),
    "float":   (_builtin_float,   1),
    "bool":    (_builtin_bool,    1),
    "type":    (_builtin_type,    1),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truthy(value: object) -> bool:
    return value is not None and value is not False


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    def __init__(self, state: dict | None = None) -> None:
        self.state: dict = state if state is not None else {}
        # function registry: name -> (handler, arity | None)
        self._functions: dict[str, tuple[callable, int | None]] = dict(_BUILTINS)

    # --- public API ---

    def run(self, source: str) -> None:
        program = parse(source)
        for rule in program.rules:
            self._execute_rule(rule)

    # --- rule execution ---

    def _execute_rule(self, rule: Rule) -> None:
        for cond in rule.conditions:
            try:
                result = self._eval(cond)
            except RulixError:
                return  # skip this rule on condition error
            if not _truthy(result):
                return
        for stmt in rule.body:
            self._exec(stmt)

    # --- statement execution ---

    def _exec(self, stmt: object) -> None:
        if isinstance(stmt, Assignment):
            self.state[stmt.name] = self._eval(stmt.value)
        else:
            self._eval(stmt)  # expression statement; discard return value

    # --- expression evaluation ---

    def _eval(self, node: object) -> object:
        if isinstance(node, Literal):
            return node.value

        if isinstance(node, Identifier):
            return self.state.get(node.name)  # undefined → null

        if isinstance(node, UnaryOp):
            operand = self._eval(node.operand)
            if node.op == "-":
                return -operand
            if node.op == "not":
                return not _truthy(operand)
            raise RulixError(f"Unknown unary operator: {node.op!r}")

        if isinstance(node, BinaryOp):
            return self._eval_binop(node)

        if isinstance(node, FunctionCall):
            return self._call(node)

        raise RulixError(f"Cannot evaluate node of type {type(node).__name__}")

    def _eval_binop(self, node: BinaryOp) -> object:
        op = node.op

        # Short-circuit operators
        if op == "and":
            return _truthy(self._eval(node.left)) and _truthy(self._eval(node.right))
        if op == "or":
            return _truthy(self._eval(node.left)) or _truthy(self._eval(node.right))

        left  = self._eval(node.left)
        right = self._eval(node.right)

        # Arithmetic
        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return _builtin_str([left]) + _builtin_str([right])
            return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":  return left / right
        if op == "%":  return left % right

        # Comparison
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == "<":  return left < right
        if op == ">":  return left > right
        if op == "<=": return left <= right
        if op == ">=": return left >= right

        raise RulixError(f"Unknown binary operator: {op!r}")

    def _call(self, node: FunctionCall) -> object:
        entry = self._functions.get(node.name)
        if entry is None:
            raise RulixError(f"Unknown function: '{node.name}'")
        handler, arity = entry
        args = [self._eval(a) for a in node.args]
        if arity is not None and len(args) != arity:
            raise RulixError(
                f"'{node.name}' expects {arity} argument(s), got {len(args)}"
            )
        return handler(args)
