"""Tests for dot-notation access to nested state values."""
import pytest
from rulix import run
from rulix.parser import ParseError


# ---------------------------------------------------------------------------
# Reading nested values
# ---------------------------------------------------------------------------

def test_read_one_level():
    state = run("=> x = cfg.debug", state={"cfg": {"debug": True}})
    assert state["x"] is True


def test_read_two_levels():
    state = run("=> x = a.b.c", state={"a": {"b": {"c": 42}}})
    assert state["x"] == 42


def test_read_string_value():
    state = run('=> x = user.name', state={"user": {"name": "Alice"}})
    assert state["x"] == "Alice"


def test_read_int_value():
    state = run("=> x = server.port", state={"server": {"port": 8080}})
    assert state["x"] == 8080


def test_read_missing_key_returns_null():
    state = run("=> x = a.b", state={})
    assert state["x"] is None


def test_read_missing_intermediate_returns_null():
    # a exists but is not a dict
    state = run("=> x = a.b.c", state={"a": 5})
    assert state["x"] is None


def test_read_missing_nested_key_returns_null():
    state = run("=> x = a.b", state={"a": {}})
    assert state["x"] is None


def test_read_three_levels():
    state = run("=> x = a.b.c", state={"a": {"b": {"c": "deep"}}})
    assert state["x"] == "deep"


# ---------------------------------------------------------------------------
# Writing nested values
# ---------------------------------------------------------------------------

def test_write_one_level():
    state = {}
    run("=> cfg.debug = true", state=state)
    assert state["cfg"]["debug"] is True


def test_write_creates_intermediate_dicts():
    state = {}
    run("=> a.b.c = 99", state=state)
    assert state["a"]["b"]["c"] == 99


def test_write_preserves_sibling_keys():
    state = {"cfg": {"debug": False, "verbose": True}}
    run("=> cfg.debug = true", state=state)
    assert state["cfg"]["debug"] is True
    assert state["cfg"]["verbose"] is True  # unchanged


def test_write_overwrites_existing():
    state = {"a": {"b": 1}}
    run("=> a.b = 99", state=state)
    assert state["a"]["b"] == 99


def test_write_two_rules_same_object():
    state = {}
    run("=> server.host = \"localhost\"\n=> server.port = 8080", state=state)
    assert state["server"]["host"] == "localhost"
    assert state["server"]["port"] == 8080


def test_write_string_value():
    state = {}
    run('=> user.name = "Bob"', state=state)
    assert state["user"]["name"] == "Bob"


# ---------------------------------------------------------------------------
# Dot access in conditions
# ---------------------------------------------------------------------------

def test_dot_in_condition_true():
    state = run(
        "server.online == true => status = 1",
        state={"server": {"online": True}},
    )
    assert state["status"] == 1


def test_dot_in_condition_false():
    state = run(
        "server.online == true => status = 1",
        state={"server": {"online": False}},
    )
    assert "status" not in state


def test_dot_condition_with_missing_path():
    # Missing path evaluates to null, which is falsy
    state = run("a.b == true => x = 1", state={})
    assert "x" not in state


def test_dot_in_multiple_conditions():
    state = run(
        "cfg.enabled == true, cfg.level > 2 => x = 1",
        state={"cfg": {"enabled": True, "level": 5}},
    )
    assert state["x"] == 1


def test_is_null_on_dot_path():
    state = run("is_null(a.b) => x = 1", state={})
    assert state["x"] == 1


def test_is_null_on_existing_dot_path():
    state = run("is_null(a.b) => x = 1", state={"a": {"b": 42}})
    assert "x" not in state


# ---------------------------------------------------------------------------
# Dot access in expressions
# ---------------------------------------------------------------------------

def test_dot_in_arithmetic():
    state = run("=> total = stats.base + stats.bonus",
                state={"stats": {"base": 10, "bonus": 5}})
    assert state["total"] == 15


def test_dot_in_comparison_expression():
    state = run("=> over = cfg.limit > 10", state={"cfg": {"limit": 15}})
    assert state["over"] is True


def test_dot_in_string_interpolation():
    state = run('=> msg = "hello {user.name}!"',
                state={"user": {"name": "Alice"}})
    assert state["msg"] == "hello Alice!"


def test_dot_in_interpolation_with_arithmetic():
    state = run('=> msg = "next: {server.port + 1}"',
                state={"server": {"port": 8080}})
    assert state["msg"] == "next: 8081"


def test_dot_in_function_call_arg():
    state = run("=> x = int(data.value)", state={"data": {"value": 3.9}})
    assert state["x"] == 3


# ---------------------------------------------------------------------------
# Mixed: flat and nested vars in same program
# ---------------------------------------------------------------------------

def test_flat_and_nested_coexist():
    state = run(
        "=> flat = 1\n=> nested.val = 2\n=> total = flat + nested.val",
        state={},
    )
    assert state["flat"] == 1
    assert state["nested"]["val"] == 2
    assert state["total"] == 3


def test_read_nested_into_flat():
    state = run("=> x = cfg.value", state={"cfg": {"value": 7}})
    assert state["x"] == 7


# ---------------------------------------------------------------------------
# Persistence across runs (nested state survives JSON round-trip naturally)
# ---------------------------------------------------------------------------

def test_nested_write_then_read():
    state = {}
    run("=> cfg.count = 0", state=state)
    assert state["cfg"]["count"] == 0
    run("=> cfg.count = cfg.count + 1", state=state)
    assert state["cfg"]["count"] == 1


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_dot_without_following_ident_raises():
    with pytest.raises((ParseError, Exception)):
        run("=> x = a.")


def test_assign_to_dot_path_expression():
    # Dotted assignment works as a statement
    state = {}
    run("=> a.b = 1", state=state)
    assert state["a"]["b"] == 1
