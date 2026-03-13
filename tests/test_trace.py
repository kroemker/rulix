"""Tests for interpreter trace data (which rules fired, were skipped, etc.)."""
import pytest
from rulix import Interpreter, RuleOutcome, RuleTrace


def trace(source, state=None):
    interp = Interpreter(state=state or {})
    interp.run(source)
    return interp.last_trace


# ---------------------------------------------------------------------------
# Basic outcomes
# ---------------------------------------------------------------------------

def test_single_unconditional_rule_fires():
    t = trace("=> x = 1")
    assert len(t) == 1
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].index == 0
    assert t[0].label is None


def test_labeled_rule_has_label_in_trace():
    t = trace("rule init: => x = 1")
    assert t[0].label == "init"
    assert t[0].outcome == RuleOutcome.FIRED


def test_condition_false_rule():
    t = trace("x == 99 => y = 1")  # x is null, not 99
    assert t[0].outcome == RuleOutcome.CONDITION_FALSE


def test_condition_true_rule_fires():
    t = trace("x == 5 => y = 1", state={"x": 5})
    assert t[0].outcome == RuleOutcome.FIRED


def test_multiple_rules_all_fired():
    t = trace("=> a = 1\n=> b = 2\n=> c = 3")
    assert all(r.outcome == RuleOutcome.FIRED for r in t)
    assert [r.index for r in t] == [0, 1, 2]


def test_mixed_outcomes():
    source = "=> a = 1\nx == 99 => b = 2\n=> c = 3"
    t = trace(source)
    assert t[0].outcome == RuleOutcome.FIRED          # => a = 1
    assert t[1].outcome == RuleOutcome.CONDITION_FALSE # x == 99, false
    assert t[2].outcome == RuleOutcome.FIRED          # => c = 3


# ---------------------------------------------------------------------------
# ALREADY_DISABLED
# ---------------------------------------------------------------------------

def test_already_disabled_rule():
    source = "rule init: => x = 1"
    state = {"_rulix_disabled_init": True}
    t = trace(source, state=state)
    assert t[0].outcome == RuleOutcome.ALREADY_DISABLED
    assert t[0].label == "init"


def test_disabled_anonymous_rule():
    source = "=> x = 1"
    state = {"_rulix_disabled_0": True}
    t = trace(source, state=state)
    assert t[0].outcome == RuleOutcome.ALREADY_DISABLED


def test_only_disabled_rule_skipped_others_fire():
    source = "rule r1: => a = 1\nrule r2: => b = 2"
    state = {"_rulix_disabled_r1": True}
    t = trace(source, state=state)
    assert t[0].outcome == RuleOutcome.ALREADY_DISABLED
    assert t[1].outcome == RuleOutcome.FIRED


# ---------------------------------------------------------------------------
# disabled_self flag
# ---------------------------------------------------------------------------

def test_disabled_self_flag_set():
    t = trace("rule once: => { x = 1\ndisable }")
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].disabled_self is True


def test_disabled_self_false_when_not_called():
    t = trace("=> x = 1")
    assert t[0].disabled_self is False


def test_disabled_self_only_on_the_rule_that_called_it():
    source = "rule r1: => { x = 1\ndisable }\nrule r2: => y = 2"
    t = trace(source)
    assert t[0].disabled_self is True
    assert t[1].disabled_self is False


def test_disable_before_condition_false_rule():
    source = "rule r1: => disable\nrule r2: x == 99 => y = 1"
    t = trace(source)
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].disabled_self is True
    assert t[1].outcome == RuleOutcome.CONDITION_FALSE
    assert t[1].disabled_self is False


# ---------------------------------------------------------------------------
# stopped_cycle flag and NOT_REACHED
# ---------------------------------------------------------------------------

def test_stop_marks_stopped_cycle():
    t = trace("=> stop\n=> x = 1")
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].stopped_cycle is True


def test_stop_marks_remaining_as_not_reached():
    t = trace("=> stop\n=> x = 1\n=> y = 2")
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].stopped_cycle is True
    assert t[1].outcome == RuleOutcome.NOT_REACHED
    assert t[2].outcome == RuleOutcome.NOT_REACHED


def test_not_reached_rules_preserve_labels():
    source = "=> stop\nrule after: => x = 1"
    t = trace(source)
    assert t[1].outcome == RuleOutcome.NOT_REACHED
    assert t[1].label == "after"


def test_stop_not_triggered_no_not_reached():
    t = trace("x == 99 => stop\n=> y = 1")
    assert t[0].outcome == RuleOutcome.CONDITION_FALSE
    assert t[0].stopped_cycle is False
    assert t[1].outcome == RuleOutcome.FIRED


def test_stop_mid_program():
    source = "=> a = 1\n=> stop\n=> b = 2\n=> c = 3"
    t = trace(source)
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[1].outcome == RuleOutcome.FIRED
    assert t[1].stopped_cycle is True
    assert t[2].outcome == RuleOutcome.NOT_REACHED
    assert t[3].outcome == RuleOutcome.NOT_REACHED


def test_stopped_cycle_false_when_no_stop():
    t = trace("=> x = 1")
    assert t[0].stopped_cycle is False


# ---------------------------------------------------------------------------
# disable + stop combined
# ---------------------------------------------------------------------------

def test_disable_and_stop_both_flagged():
    source = "rule guard: => {\n    disable\n    stop\n}\n=> after = 1"
    t = trace(source)
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].disabled_self is True
    assert t[0].stopped_cycle is True
    assert t[1].outcome == RuleOutcome.NOT_REACHED


def test_stop_before_disable_not_disabled():
    source = "rule r: => {\n    stop\n    disable\n}\n=> x = 1"
    t = trace(source)
    assert t[0].outcome == RuleOutcome.FIRED
    assert t[0].stopped_cycle is True
    assert t[0].disabled_self is False   # disable was never reached
    assert t[1].outcome == RuleOutcome.NOT_REACHED


# ---------------------------------------------------------------------------
# trace resets between runs
# ---------------------------------------------------------------------------

def test_trace_resets_on_each_run():
    interp = Interpreter()
    interp.run("=> x = 1\n=> y = 2")
    assert len(interp.last_trace) == 2
    interp.run("=> z = 3")
    assert len(interp.last_trace) == 1   # fresh trace


def test_last_trace_empty_before_first_run():
    interp = Interpreter()
    assert interp.last_trace == []


# ---------------------------------------------------------------------------
# RuleTrace fields
# ---------------------------------------------------------------------------

def test_trace_index_correct_for_multi_rule():
    source = "rule a: => x=1\nrule b: => y=2\nrule c: => z=3"
    t = trace(source)
    assert [r.index for r in t] == [0, 1, 2]
    assert [r.label for r in t] == ["a", "b", "c"]


def test_anonymous_rules_have_none_label():
    t = trace("=> x=1\n=> y=2")
    assert t[0].label is None
    assert t[1].label is None


# ---------------------------------------------------------------------------
# RulixInterpreter exposes last_trace
# ---------------------------------------------------------------------------

def test_rulix_interpreter_exposes_last_trace():
    from rulix import RulixInterpreter
    interp = RulixInterpreter()
    interp.run("rule r: => x = 1")
    t = interp.last_trace
    assert len(t) == 1
    assert t[0].label == "r"
    assert t[0].outcome == RuleOutcome.FIRED


def test_rulix_interpreter_trace_empty_before_run():
    from rulix import RulixInterpreter
    interp = RulixInterpreter()
    assert interp.last_trace == []
