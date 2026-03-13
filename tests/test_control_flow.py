"""Tests for the disable and stop control-flow statements."""
import pytest
from rulix import run


# ---------------------------------------------------------------------------
# disable — rule disables itself for future runs
# ---------------------------------------------------------------------------

def test_disable_rule_fires_on_first_run():
    """The rule fires normally on the first run."""
    source = "rule once: => { x = 1\ndisable }"
    state = run(source)
    assert state["x"] == 1


def test_disable_labeled_rule_does_not_fire_again():
    """A labeled rule that calls disable does not fire on subsequent runs."""
    source = "rule once: => { x = 1\ndisable }"
    state = {}
    run(source, state=state)
    assert state["x"] == 1
    # Overwrite x to verify second run doesn't set it back
    state["x"] = 99
    run(source, state=state)
    assert state["x"] == 99   # unchanged — rule was disabled


def test_disable_anonymous_rule_does_not_fire_again():
    """An anonymous rule that calls disable does not fire on subsequent runs."""
    # Only rule in the program → index 0
    source = "=> { x = 1\ndisable }"
    state = {}
    run(source, state=state)
    state["x"] = 99
    run(source, state=state)
    assert state["x"] == 99


def test_disable_statements_after_disable_still_execute():
    """disable does not stop execution of the current body."""
    source = "rule once: => { disable\nx = 42 }"
    state = run(source)
    assert state["x"] == 42


def test_disable_only_disables_its_own_rule():
    """disable only affects the rule it is called from, not others."""
    source = (
        "rule r1: => { a = 1\ndisable }\n"
        "rule r2: => b = 1\n"
    )
    state = {}
    run(source, state=state)
    assert state["a"] == 1
    assert state["b"] == 1
    state["a"] = 99
    state["b"] = 99
    run(source, state=state)
    assert state["a"] == 99  # r1 disabled
    assert state["b"] == 1   # r2 still fires


def test_disable_with_condition():
    """disable works in a conditional rule."""
    source = "rule milestone: x == 5 => { hit = true\ndisable }"
    state = {"x": 5}
    run(source, state=state)
    assert state["hit"] is True
    state["hit"] = False
    run(source, state=state)
    assert state["hit"] is False  # rule disabled, not re-triggered


def test_disable_single_statement():
    """disable as the sole statement in a rule body."""
    source = "rule r: => disable"
    state = {}
    run(source, state=state)
    run(source, state=state)
    # No crash; rule simply disabled itself. The test just checks it doesn't error.


def test_disable_persists_state_key():
    """The disabled flag is stored in the state dict under _rulix_disabled_<identity>."""
    source = "rule init: => disable"
    state = {}
    run(source, state=state)
    assert state.get("_rulix_disabled_init") is True


def test_disable_anonymous_persists_state_key_by_index():
    """Anonymous rule stores disabled flag by index."""
    source = "=> disable"
    state = {}
    run(source, state=state)
    assert state.get("_rulix_disabled_0") is True


def test_disable_accumulator_fires_exactly_once():
    """Classic one-shot pattern: initialisation rule fires exactly once."""
    source = (
        "is_null(runs) => runs = 0\n"
        "rule init: is_null(initialized) => { initialized = true\ndisable }\n"
        "=> runs = runs + 1\n"
    )
    state = {}
    for _ in range(5):
        run(source, state=state)
    assert state["initialized"] is True
    assert state["runs"] == 5
    # init rule's disable key must be present
    assert state.get("_rulix_disabled_init") is True


# ---------------------------------------------------------------------------
# stop — end the current evaluation cycle immediately
# ---------------------------------------------------------------------------

def test_stop_prevents_later_rules_from_firing():
    """Rules after the stop-ing rule do not execute in the same cycle."""
    source = "=> x = 1\n=> stop\n=> y = 2"
    state = run(source)
    assert state["x"] == 1
    assert "y" not in state


def test_stop_as_conditional():
    """stop fires only when the condition is met."""
    source = "=> x = 1\nx == 1 => stop\n=> y = 2"
    state = run(source)
    assert state["x"] == 1
    assert "y" not in state


def test_stop_does_not_fire_when_condition_false():
    """When the stop rule's condition is false, later rules still run."""
    source = "=> x = 0\nx == 1 => stop\n=> y = 2"
    state = run(source)
    assert state["y"] == 2


def test_stop_in_block_abandons_remaining_statements():
    """Statements after stop inside a block do not execute."""
    source = "=> {\n    x = 1\n    stop\n    y = 2\n}"
    state = run(source)
    assert state["x"] == 1
    assert "y" not in state


def test_stop_does_not_affect_next_run():
    """stop only ends the current cycle; the next run starts fresh from rule 1."""
    source = (
        "is_null(n) => n = 0\n"
        "=> n = n + 1\n"
        "n == 1 => stop\n"
        "=> marker = true\n"
    )
    state = {}
    run(source, state=state)   # n→1, stop fires, marker not set
    assert state["n"] == 1
    assert "marker" not in state
    run(source, state=state)   # n→2, stop doesn't fire, marker set
    assert state["n"] == 2
    assert state["marker"] is True


def test_stop_on_first_rule():
    """If the first rule stops, nothing else runs."""
    source = "=> stop\n=> x = 1"
    state = run(source)
    assert "x" not in state


# ---------------------------------------------------------------------------
# disable + stop combined
# ---------------------------------------------------------------------------

def test_disable_then_stop():
    """A rule can disable itself and then stop the cycle."""
    source = (
        "rule guard: => {\n"
        "    fired = true\n"
        "    disable\n"
        "    stop\n"
        "}\n"
        "=> after = true\n"
    )
    state = {}
    run(source, state=state)
    assert state["fired"] is True
    assert "after" not in state     # stop prevented it
    state.pop("fired")
    run(source, state=state)
    assert "fired" not in state     # disable prevented it
    assert state["after"] is True   # stop no longer fires


def test_stop_before_disable():
    """If stop comes before disable in the body, disable never executes.

    Because rule r was never disabled it fires again on run 2 and stops
    the cycle again — x = 1 is never reached on either run.
    """
    source = "rule r: => {\n    stop\n    disable\n}\n=> x = 1"
    state = {}
    run(source, state=state)
    assert "x" not in state                  # stop fired, x never set
    assert "_rulix_disabled_r" not in state  # disable was never reached
    run(source, state=state)
    assert "x" not in state                  # rule r fires again, stops again
