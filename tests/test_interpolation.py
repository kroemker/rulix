"""Tests for string interpolation: "hello {name}"."""
import pytest
from rulix import run
from rulix.parser import ParseError
from rulix.lexer import LexError


# ---------------------------------------------------------------------------
# Basic usage
# ---------------------------------------------------------------------------

def test_basic_variable():
    state = run('=> msg = "hello {name}"', state={"name": "Alice"})
    assert state["msg"] == "hello Alice"


def test_variable_only():
    state = run('=> msg = "{x}"', state={"x": 42})
    assert state["msg"] == "42"


def test_multiple_holes():
    state = run('=> msg = "{a} plus {b} is {a + b}"', state={"a": 1, "b": 2})
    assert state["msg"] == "1 plus 2 is 3"


def test_text_before_hole():
    state = run('=> msg = "count: {n}"', state={"n": 7})
    assert state["msg"] == "count: 7"


def test_text_after_hole():
    state = run('=> msg = "{n} items"', state={"n": 7})
    assert state["msg"] == "7 items"


def test_hole_in_middle():
    state = run('=> msg = "hi {name}!"', state={"name": "Bob"})
    assert state["msg"] == "hi Bob!"


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

def test_null_value():
    # Unset variable evaluates to null → "null"
    state = run('=> msg = "value is {missing}"')
    assert state["msg"] == "value is null"


def test_bool_true():
    state = run('=> msg = "flag is {flag}"', state={"flag": True})
    assert state["msg"] == "flag is true"


def test_bool_false():
    state = run('=> msg = "flag is {flag}"', state={"flag": False})
    assert state["msg"] == "flag is false"


def test_float_value():
    state = run('=> msg = "pi is {x}"', state={"x": 3.14})
    assert state["msg"] == "pi is 3.14"


def test_int_value():
    state = run('=> msg = "n={n}"', state={"n": 100})
    assert state["msg"] == "n=100"


def test_negative_int():
    state = run('=> msg = "{x}"', state={"x": -5})
    assert state["msg"] == "-5"


# ---------------------------------------------------------------------------
# Expressions inside holes
# ---------------------------------------------------------------------------

def test_arithmetic_addition():
    state = run('=> msg = "{x + y}"', state={"x": 3, "y": 4})
    assert state["msg"] == "7"


def test_arithmetic_multiplication():
    state = run('=> msg = "{x * 7}"', state={"x": 6})
    assert state["msg"] == "42"


def test_arithmetic_subtraction():
    state = run('=> msg = "{x - 3}"', state={"x": 10})
    assert state["msg"] == "7"


def test_arithmetic_modulo():
    state = run('=> msg = "{x % 5}"', state={"x": 17})
    assert state["msg"] == "2"


def test_function_call_in_hole():
    state = run('=> msg = "truncated: {int(x)}"', state={"x": 3.9})
    assert state["msg"] == "truncated: 3"


def test_complex_expression():
    state = run('=> msg = "{a * b + 1} is the answer"', state={"a": 2, "b": 3})
    assert state["msg"] == "7 is the answer"


def test_literal_int_in_hole():
    state = run('=> msg = "{42}"')
    assert state["msg"] == "42"


def test_literal_bool_in_hole():
    state = run('=> msg = "{true}"')
    assert state["msg"] == "true"


# ---------------------------------------------------------------------------
# Brace escaping  ({{ → literal {,  }} → literal })
# ---------------------------------------------------------------------------

def test_escaped_open_brace():
    state = run('=> msg = "{{literal brace"')
    assert state["msg"] == "{literal brace"


def test_escaped_close_brace():
    # }} outside a hole → literal }
    # "prefix {x} suffix }}" → "prefix a suffix }"
    state = run('=> msg = "prefix {x} suffix }}"', state={"x": "a"})
    assert state["msg"] == "prefix a suffix }"


def test_escaped_both_braces():
    state = run('=> msg = "{{not interpolated}}"')
    assert state["msg"] == "{not interpolated}"


def test_escaped_around_hole():
    # {{{ → literal { + start interpolation;  x}}} → x value + literal }
    state = run('=> msg = "{{{x}}}"', state={"x": 42})
    assert state["msg"] == "{42}"


# ---------------------------------------------------------------------------
# Plain strings are unchanged
# ---------------------------------------------------------------------------

def test_no_hole_plain_string():
    state = run('=> msg = "hello world"')
    assert state["msg"] == "hello world"


def test_string_concatenation_still_works():
    state = run('=> msg = a + b', state={"a": "hello", "b": " world"})
    assert state["msg"] == "hello world"


def test_regular_string_in_condition():
    state = run('x == "ok" => result = "yes"', state={"x": "ok"})
    assert state["result"] == "yes"


# ---------------------------------------------------------------------------
# Interpolation in various positions
# ---------------------------------------------------------------------------

def test_interp_in_condition_rhs():
    state = run(
        'name == "Alice" => greeting = "hi {name}!"',
        state={"name": "Alice"},
    )
    assert state["greeting"] == "hi Alice!"


def test_interp_in_rule_body():
    state = run(
        'runs > 3 => msg = "ran {runs} times"',
        state={"runs": 5},
    )
    assert state["msg"] == "ran 5 times"


def test_interp_as_condition():
    state = run(
        '=> msg = "val={x}"\nmsg == "val=1" => hit = true',
        state={"x": 1},
    )
    assert state["hit"] is True


def test_interp_chained_across_rules():
    state = run(
        '=> first = "step {n}"\n=> second = "done: {first}"',
        state={"n": 3},
    )
    assert state["first"] == "step 3"
    assert state["second"] == "done: step 3"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_empty_hole_raises():
    with pytest.raises(ParseError):
        run('=> msg = "{}"')


def test_unclosed_brace_raises():
    with pytest.raises((ParseError, LexError)):
        run('=> msg = "hello {name"')


def test_invalid_expr_in_hole_raises():
    with pytest.raises((ParseError, LexError)):
        run('=> msg = "{@invalid}"')


def test_extra_tokens_in_hole_raises():
    with pytest.raises(ParseError):
        run('=> msg = "{x y}"', state={"x": 1})
