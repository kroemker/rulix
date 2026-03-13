from rulix import run


def test_block_sets_multiple_vars():
    source = "=> {\n    x = 1\n    y = 2\n}"
    state = run(source)
    assert state["x"] == 1
    assert state["y"] == 2


def test_block_later_statement_sees_earlier_write():
    """Within one block, statements execute in order and share state."""
    source = "=> {\n    x = 5\n    y = x + 1\n}"
    state = run(source)
    assert state["y"] == 6


def test_block_only_fires_when_condition_true():
    source = "=> x = 0\nx == 99 => {\n    y = 1\n    z = 2\n}"
    state = run(source)
    assert "y" not in state
    assert "z" not in state


def test_block_fires_when_condition_true():
    source = "=> x = 1\nx == 1 => {\n    y = 10\n    z = 20\n}"
    state = run(source)
    assert state["y"] == 10
    assert state["z"] == 20


def test_rule_label_fires_normally():
    state = run("rule init: => x = 42")
    assert state["x"] == 42


def test_rule_label_with_condition():
    source = "=> x = 1\nrule check: x == 1 => y = 99"
    state = run(source)
    assert state["y"] == 99


def test_rule_label_does_not_fire_when_condition_false():
    source = "=> x = 0\nrule nope: x == 1 => y = 99"
    state = run(source)
    assert "y" not in state


def test_labeled_block_rule():
    source = "rule setup: => {\n    a = 1\n    b = 2\n}"
    state = run(source)
    assert state["a"] == 1
    assert state["b"] == 2
