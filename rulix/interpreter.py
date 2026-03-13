from __future__ import annotations

import math
import sys
from datetime import datetime

from .parser import (
    Assignment, BinaryOp, FunctionCall, Identifier, Literal, Program,
    Rule, UnaryOp, parse,
)


class RulixError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truthy(value: object) -> bool:
    return value is not None and value is not False


def _to_str(v: object) -> str:
    """Convert a Rulix value to its string representation."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


# ---------------------------------------------------------------------------
# Stateless built-in functions
# Each entry: name -> (handler, arity, group)
# arity=None means variadic.
# ---------------------------------------------------------------------------

# --- group: type ---

def _fn_is_null(args):  return args[0] is None
def _fn_is_int(args):   return isinstance(args[0], int) and not isinstance(args[0], bool)
def _fn_is_float(args): return isinstance(args[0], float)
def _fn_is_string(args):return isinstance(args[0], str)
def _fn_is_bool(args):  return isinstance(args[0], bool)

def _fn_str(args):   return _to_str(args[0])
def _fn_bool(args):  return _truthy(args[0])
def _fn_type(args):
    return {int: "int", float: "float", bool: "bool", str: "string", type(None): "null"}.get(
        type(args[0]), "unknown"
    )

def _fn_int(args):
    try:
        v = args[0]
        if isinstance(v, float):
            return int(v)
        return int(v)
    except (TypeError, ValueError) as e:
        raise RulixError(f"int(): cannot convert {args[0]!r}") from e

def _fn_float(args):
    try:
        return float(args[0])
    except (TypeError, ValueError) as e:
        raise RulixError(f"float(): cannot convert {args[0]!r}") from e

# --- group: math ---

def _fn_abs(args):
    return abs(args[0])

def _fn_min(args):
    return min(args[0], args[1])

def _fn_max(args):
    return max(args[0], args[1])

def _fn_floor(args):
    return int(math.floor(args[0]))

def _fn_ceil(args):
    return int(math.ceil(args[0]))

def _fn_round(args):
    return int(round(args[0]))

def _fn_pow(args):
    return float(args[0] ** args[1])

def _fn_sqrt(args):
    return float(math.sqrt(args[0]))

# --- group: string ---

def _fn_len(args):
    return len(args[0])

def _fn_upper(args):   return args[0].upper()
def _fn_lower(args):   return args[0].lower()
def _fn_trim(args):    return args[0].strip()

def _fn_contains(args):     return args[1] in args[0]
def _fn_starts_with(args):  return args[0].startswith(args[1])
def _fn_ends_with(args):    return args[0].endswith(args[1])
def _fn_replace(args):      return args[0].replace(args[1], args[2], 1)

# --- group: io ---

def _fn_print(args):
    print(" ".join(_to_str(a) for a in args))
    return None

def _fn_log(args):
    level, message = args[0], args[1]
    ts = datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] [{level.upper()}] {message}", file=sys.stderr)
    return None

def _fn_input(args):
    prompt = _to_str(args[0]) if args else ""
    return input(prompt)


# Stateless registry — group: io, type, math, string
# State-aware functions (exists, delete) are bound methods registered in __init__.
_STATELESS_BUILTINS: dict[str, tuple] = {
    # --- type ---
    "is_null":   (_fn_is_null,   1,    "type"),
    "is_int":    (_fn_is_int,    1,    "type"),
    "is_float":  (_fn_is_float,  1,    "type"),
    "is_string": (_fn_is_string, 1,    "type"),
    "is_bool":   (_fn_is_bool,   1,    "type"),
    "str":       (_fn_str,       1,    "type"),
    "int":       (_fn_int,       1,    "type"),
    "float":     (_fn_float,     1,    "type"),
    "bool":      (_fn_bool,      1,    "type"),
    "type":      (_fn_type,      1,    "type"),
    # --- math ---
    "abs":       (_fn_abs,       1,    "math"),
    "min":       (_fn_min,       2,    "math"),
    "max":       (_fn_max,       2,    "math"),
    "floor":     (_fn_floor,     1,    "math"),
    "ceil":      (_fn_ceil,      1,    "math"),
    "round":     (_fn_round,     1,    "math"),
    "pow":       (_fn_pow,       2,    "math"),
    "sqrt":      (_fn_sqrt,      1,    "math"),
    # --- string ---
    "len":         (_fn_len,         1, "string"),
    "upper":       (_fn_upper,       1, "string"),
    "lower":       (_fn_lower,       1, "string"),
    "trim":        (_fn_trim,        1, "string"),
    "contains":    (_fn_contains,    2, "string"),
    "starts_with": (_fn_starts_with, 2, "string"),
    "ends_with":   (_fn_ends_with,   2, "string"),
    "replace":     (_fn_replace,     3, "string"),
    # --- io ---
    "print": (_fn_print, None, "io"),
    "log":   (_fn_log,   2,    "io"),
    "input": (_fn_input, 1,    "io"),
}

# All known built-in names (used by RulixConfig to prevent shadowing)
BUILTIN_NAMES: frozenset[str] = frozenset(_STATELESS_BUILTINS) | {"exists", "delete"}


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    def __init__(self, state: dict | None = None, config=None) -> None:
        self.state: dict = state if state is not None else {}
        self._config = config  # None = no group checking (all allowed)
        # Registry: name -> (handler, arity | None, group)
        self._functions: dict[str, tuple] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        for name, entry in _STATELESS_BUILTINS.items():
            self._functions[name] = entry
        # State-aware built-ins need access to self.state; register as bound methods.
        self._functions["exists"] = (self._fn_exists, 1, "state")
        self._functions["delete"] = (self._fn_delete, 1, "state")
        # Custom functions from config (if any)
        if self._config is not None:
            for name, (handler, arity) in self._config.custom_functions.items():
                self._functions[name] = (handler, arity, "custom")

    def _fn_exists(self, args) -> bool:
        if not isinstance(args[0], str):
            raise RulixError("exists() expects a string (variable name)")
        return args[0] in self.state

    def _fn_delete(self, args) -> None:
        if not isinstance(args[0], str):
            raise RulixError("delete() expects a string (variable name)")
        self.state.pop(args[0], None)
        return None

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
                return  # skip rule on condition error
            if not _truthy(result):
                return
        for stmt in rule.body:
            self._exec(stmt)

    # --- statement execution ---

    def _exec(self, stmt: object) -> None:
        if isinstance(stmt, Assignment):
            self.state[stmt.name] = self._eval(stmt.value)
        else:
            self._eval(stmt)

    # --- expression evaluation ---

    def _eval(self, node: object) -> object:
        if isinstance(node, Literal):
            return node.value

        if isinstance(node, Identifier):
            return self.state.get(node.name)

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

        if op == "and":
            return _truthy(self._eval(node.left)) and _truthy(self._eval(node.right))
        if op == "or":
            return _truthy(self._eval(node.left)) or _truthy(self._eval(node.right))

        left  = self._eval(node.left)
        right = self._eval(node.right)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return _to_str(left) + _to_str(right)
            return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":  return left / right
        if op == "%":  return left % right

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
        handler, arity, group = entry

        # Group permission check (only when a config is present)
        if self._config is not None and group != "custom":
            if not self._config.is_group_enabled(group):
                raise RulixError(
                    f"function '{node.name}' is not available (group '{group}' is disabled)"
                )

        args = [self._eval(a) for a in node.args]
        if arity is not None and len(args) != arity:
            raise RulixError(
                f"'{node.name}' expects {arity} argument(s), got {len(args)}"
            )
        return handler(args)


# ---------------------------------------------------------------------------
# StateView — host-facing read/write interface over the state dict
# ---------------------------------------------------------------------------

class StateView:
    """Read/write proxy over the interpreter's state dictionary.

    Returned by ``RulixInterpreter.state``.  The host uses this to seed
    input values before a run and to read output values afterwards.
    """

    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, name: str, default: object = None) -> object:
        return self._data.get(name, default)

    def set(self, name: str, value: object) -> None:
        self._data[name] = value

    def delete(self, name: str) -> None:
        self._data.pop(name, None)

    def as_dict(self) -> dict:
        return dict(self._data)


# ---------------------------------------------------------------------------
# RulixInterpreter — public high-level interpreter
# ---------------------------------------------------------------------------

class RulixInterpreter:
    """High-level interpreter for embedding Rulix in host applications.

    Maintains state across multiple ``run()`` calls and optionally
    persists that state to a file between sessions (see iteration 5).

    Example::

        config = RulixConfig.sandbox()
        config.register_function("myapp_alert", handler=send_alert, arity=1)

        interp = RulixInterpreter(config=config)
        interp.state.set("cpu_usage", get_cpu())
        interp.run(source)
    """

    def __init__(
        self,
        config: "RulixConfig | None" = None,
        state_file: str | None = None,
    ) -> None:
        from .config import RulixConfig as _RC
        self._config = config if config is not None else _RC.full()
        self._state_file = state_file
        self._state_data: dict = {}

    @property
    def state(self) -> StateView:
        return StateView(self._state_data)

    def run(self, source: str) -> None:
        """Evaluate all rules in *source* against the current state."""
        interp = Interpreter(state=self._state_data, config=self._config)
        interp.run(source)
        # _state_data is mutated in-place by the inner Interpreter
