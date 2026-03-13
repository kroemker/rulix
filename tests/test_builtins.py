"""Tests for all built-in functions across the five groups."""
import math
import pytest
from rulix import run


# ---------------------------------------------------------------------------
# group: type — additional predicates
# ---------------------------------------------------------------------------

def test_is_int_true():
    assert run("=> x = is_int(42)")["x"] is True

def test_is_int_false():
    assert run("=> x = is_int(3.14)")["x"] is False

def test_is_float_true():
    assert run("=> x = is_float(3.14)")["x"] is True

def test_is_float_false():
    assert run("=> x = is_float(1)")["x"] is False

def test_is_string_true():
    assert run('=> x = is_string("hi")')["x"] is True

def test_is_string_false():
    assert run("=> x = is_string(1)")["x"] is False

def test_is_bool_true():
    assert run("=> x = is_bool(true)")["x"] is True

def test_is_bool_false():
    assert run("=> x = is_bool(0)")["x"] is False


# ---------------------------------------------------------------------------
# group: math
# ---------------------------------------------------------------------------

def test_abs_negative():
    assert run("=> x = abs(-7)")["x"] == 7

def test_abs_positive():
    assert run("=> x = abs(3)")["x"] == 3

def test_abs_preserves_int():
    assert isinstance(run("=> x = abs(-4)")["x"], int)

def test_abs_preserves_float():
    assert isinstance(run("=> x = abs(-4.0)")["x"], float)

def test_min():
    assert run("=> x = min(3, 7)")["x"] == 3

def test_max():
    assert run("=> x = max(3, 7)")["x"] == 7

def test_floor():
    assert run("=> x = floor(3.9)")["x"] == 3
    assert isinstance(run("=> x = floor(3.9)")["x"], int)

def test_ceil():
    assert run("=> x = ceil(3.1)")["x"] == 4
    assert isinstance(run("=> x = ceil(3.1)")["x"], int)

def test_round_down():
    assert run("=> x = round(3.3)")["x"] == 3

def test_round_up():
    assert run("=> x = round(3.7)")["x"] == 4

def test_pow():
    assert run("=> x = pow(2, 10)")["x"] == 1024.0
    assert isinstance(run("=> x = pow(2, 10)")["x"], float)

def test_sqrt():
    assert run("=> x = sqrt(9)")["x"] == pytest.approx(3.0)
    assert isinstance(run("=> x = sqrt(9)")["x"], float)


# ---------------------------------------------------------------------------
# group: string
# ---------------------------------------------------------------------------

def test_len():
    assert run('=> x = len("hello")')["x"] == 5

def test_len_empty():
    assert run('=> x = len("")')["x"] == 0

def test_upper():
    assert run('=> x = upper("hello")')["x"] == "HELLO"

def test_lower():
    assert run('=> x = lower("WORLD")')["x"] == "world"

def test_trim():
    assert run('=> x = trim("  hi  ")')["x"] == "hi"

def test_contains_true():
    assert run('=> x = contains("hello world", "world")')["x"] is True

def test_contains_false():
    assert run('=> x = contains("hello world", "xyz")')["x"] is False

def test_starts_with_true():
    assert run('=> x = starts_with("hello", "hel")')["x"] is True

def test_starts_with_false():
    assert run('=> x = starts_with("hello", "ell")')["x"] is False

def test_ends_with_true():
    assert run('=> x = ends_with("hello", "llo")')["x"] is True

def test_ends_with_false():
    assert run('=> x = ends_with("hello", "hel")')["x"] is False

def test_replace():
    assert run('=> x = replace("hello world", "world", "rulix")')["x"] == "hello rulix"

def test_replace_no_match():
    assert run('=> x = replace("hello", "xyz", "abc")')["x"] == "hello"


# ---------------------------------------------------------------------------
# group: io — print and log (input requires interactive stdin, not tested here)
# ---------------------------------------------------------------------------

def test_print_single(capsys):
    run('=> print("hello")')
    assert capsys.readouterr().out == "hello\n"

def test_print_multiple_args(capsys):
    run('=> print("a", "b", "c")')
    assert capsys.readouterr().out == "a b c\n"

def test_print_numbers(capsys):
    run("=> print(1, 2, 3)")
    assert capsys.readouterr().out == "1 2 3\n"

def test_print_returns_null():
    assert run('=> x = print("hi")')["x"] is None

def test_log_writes_to_stderr(capsys):
    run('=> log("info", "something happened")')
    assert "something happened" in capsys.readouterr().err

def test_log_includes_level(capsys):
    run('=> log("warn", "watch out")')
    err = capsys.readouterr().err
    assert "WARN" in err or "warn" in err.lower()


# ---------------------------------------------------------------------------
# group: state — exists and delete
# ---------------------------------------------------------------------------

def test_exists_true():
    assert run('=> x = 1\n=> y = exists("x")')["y"] is True

def test_exists_false_never_set():
    assert run('=> y = exists("ghost")')["y"] is False

def test_exists_false_after_delete():
    assert run('=> x = 1\n=> delete("x")\n=> y = exists("x")')["y"] is False

def test_delete_removes_var_from_state():
    # After deletion the key is gone; accessing it in Rulix yields null.
    state = run('=> x = 1\n=> delete("x")')
    assert state.get("x") is None  # key absent → None, same as Rulix null

def test_delete_nonexistent_is_noop():
    # Should not raise an error
    run('=> delete("ghost")')
