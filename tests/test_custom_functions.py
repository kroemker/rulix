"""Tests for custom function registration and the RulixInterpreter class."""
import pytest
from rulix import RulixConfig, RulixError, RulixInterpreter, run


# ---------------------------------------------------------------------------
# register_function — validation
# ---------------------------------------------------------------------------

def test_invalid_name_raises():
    config = RulixConfig()
    with pytest.raises(ValueError, match="Invalid function name"):
        config.register_function("123bad", handler=lambda a: None, arity=0)


def test_reserved_word_raises():
    config = RulixConfig()
    with pytest.raises(ValueError, match="reserved word"):
        config.register_function("and", handler=lambda a: None, arity=0)


def test_builtin_name_raises():
    config = RulixConfig()
    with pytest.raises(ValueError, match="Cannot override built-in"):
        config.register_function("print", handler=lambda a: None)


def test_same_name_twice_raises():
    config = RulixConfig()
    config.register_function("myapp_greet", handler=lambda a: "hi", arity=0)
    with pytest.raises(ValueError):
        config.register_function("myapp_greet", handler=lambda a: "hi", arity=0)


# ---------------------------------------------------------------------------
# calling custom functions from Rulix
# ---------------------------------------------------------------------------

def test_custom_function_called_with_correct_args():
    received = []

    def capture(args):
        received.extend(args)
        return None

    config = RulixConfig()
    config.register_function("myapp_capture", handler=capture, arity=2)
    run('=> myapp_capture(42, "hello")', config=config)
    assert received == [42, "hello"]


def test_custom_function_return_value_stored():
    config = RulixConfig()
    config.register_function("myapp_double", handler=lambda args: args[0] * 2, arity=1)
    state = run("=> x = myapp_double(5)", config=config)
    assert state["x"] == 10


def test_custom_function_returning_none():
    config = RulixConfig()
    config.register_function("myapp_noop", handler=lambda args: None, arity=0)
    state = run("=> x = myapp_noop()", config=config)
    assert state["x"] is None


def test_custom_function_variadic():
    config = RulixConfig()
    config.register_function("myapp_sum", handler=lambda args: sum(args), arity=None)
    state = run("=> x = myapp_sum(1, 2, 3, 4)", config=config)
    assert state["x"] == 10


def test_custom_function_arity_mismatch_raises():
    config = RulixConfig()
    config.register_function("myapp_one", handler=lambda args: args[0], arity=1)
    with pytest.raises(RulixError, match="expects 1 argument"):
        run("=> x = myapp_one(1, 2)", config=config)


def test_custom_function_can_raise_rulix_error():
    def explode(args):
        raise RulixError("custom error triggered")

    config = RulixConfig()
    config.register_function("myapp_explode", handler=explode, arity=0)
    with pytest.raises(RulixError, match="custom error triggered"):
        run("=> myapp_explode()", config=config)


def test_custom_function_works_with_sandbox():
    """Custom functions are always reachable regardless of group settings."""
    config = RulixConfig.sandbox()
    config.register_function("myapp_flag", handler=lambda args: True, arity=0)
    state = run("=> x = myapp_flag()", config=config)
    assert state["x"] is True


def test_custom_function_receives_null_as_none():
    received = []
    config = RulixConfig()
    config.register_function("myapp_recv", handler=lambda args: received.append(args[0]) or None, arity=1)
    run("=> myapp_recv(null)", config=config)
    assert received == [None]


def test_custom_function_receives_bool():
    received = []
    config = RulixConfig()
    config.register_function("myapp_recv", handler=lambda args: received.append(args[0]) or None, arity=1)
    run("=> myapp_recv(true)", config=config)
    assert received == [True]


# ---------------------------------------------------------------------------
# RulixInterpreter
# ---------------------------------------------------------------------------

def test_rulix_interpreter_runs_source():
    interp = RulixInterpreter()
    interp.run("=> x = 1")
    assert interp.state.get("x") == 1


def test_rulix_interpreter_state_set_seeds_value():
    interp = RulixInterpreter()
    interp.state.set("threshold", 100)
    interp.run("threshold > 50 => triggered = true")
    assert interp.state.get("triggered") is True


def test_rulix_interpreter_state_get_returns_none_for_missing():
    interp = RulixInterpreter()
    assert interp.state.get("missing") is None


def test_rulix_interpreter_with_config():
    config = RulixConfig.sandbox()
    interp = RulixInterpreter(config=config)
    with pytest.raises(RulixError, match="group 'io' is disabled"):
        interp.run('=> print("hi")')


def test_rulix_interpreter_state_persists_across_run_calls():
    interp = RulixInterpreter()
    interp.run("=> x = 1")
    interp.run("=> y = x + 1")
    assert interp.state.get("y") == 2


def test_rulix_interpreter_with_custom_function():
    config = RulixConfig()
    config.register_function("myapp_val", handler=lambda args: 42, arity=0)
    interp = RulixInterpreter(config=config)
    interp.run("=> x = myapp_val()")
    assert interp.state.get("x") == 42
