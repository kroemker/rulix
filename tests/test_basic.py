from pathlib import Path

from rulix import run

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_unconditional_rule():
    """An unconditional rule (no conditions) fires on every run."""
    state = run("=> x = 1")
    assert state["x"] == 1


def test_conditional_rule_fires():
    """A conditional rule fires when its condition is true."""
    state = run("=> x = 1\nx == 1 => y = 2")
    assert state["y"] == 2


def test_conditional_rule_does_not_fire():
    """A conditional rule is skipped when its condition is false."""
    state = run("=> x = 1\nx == 99 => y = 2")
    assert "y" not in state


def test_pipeline_order():
    """Rules execute in declaration order; later rules see earlier writes."""
    state = run("=> x = 1\n=> x = 2")
    assert state["x"] == 2


def test_multiple_conditions():
    """All conditions in a rule must be true for it to fire (implicit AND)."""
    state = run("=> x = 5\n=> y = 3\nx > 4, y < 10 => z = 1")
    assert state["z"] == 1


def test_multiple_conditions_one_false():
    """If any condition is false the rule does not fire."""
    state = run("=> x = 5\n=> y = 3\nx > 4, y > 10 => z = 1")
    assert "z" not in state


def test_arithmetic_in_body():
    """Arithmetic expressions evaluate correctly in assignment bodies."""
    state = run("=> x = 3 + 4")
    assert state["x"] == 7


def test_initial_state_is_passed_in():
    """Callers can seed state before running (embedding use case)."""
    state = run("x > 10 => y = 1", state={"x": 20})
    assert state["y"] == 1


def test_example_program():
    """The basic_example.rlx program produces the expected state."""
    source = (EXAMPLES / "basic_example.rlx").read_text()
    state = run(source)
    assert state["x"] == 1
    assert state["y"] == 2
