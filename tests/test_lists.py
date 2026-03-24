"""Tests for list type support."""
import pytest
from rulix import run
from rulix.interpreter import RulixError
from rulix.parser import ParseError


# ---------------------------------------------------------------------------
# List literals
# ---------------------------------------------------------------------------

def test_empty_list_literal():
    state = run("=> items = []")
    assert state["items"] == []


def test_list_literal_ints():
    state = run("=> nums = [1, 2, 3]")
    assert state["nums"] == [1, 2, 3]


def test_list_literal_mixed_types():
    state = run('=> items = [1, "hello", true, null]')
    assert state["items"] == [1, "hello", True, None]


def test_list_literal_nested():
    state = run("=> nested = [[1, 2], [3, 4]]")
    assert state["nested"] == [[1, 2], [3, 4]]


def test_list_literal_with_expressions():
    state = run("=> nums = [1 + 1, 2 * 3, 10 - 4]")
    assert state["nums"] == [2, 6, 6]


def test_list_assigned_from_state():
    """A list in initial state is accessible."""
    state = run("=> x = 1", state={"items": [10, 20, 30]})
    assert state["items"] == [10, 20, 30]


# ---------------------------------------------------------------------------
# Index access (read)
# ---------------------------------------------------------------------------

def test_index_access_first_element():
    state = run("=> nums = [10, 20, 30]\n=> x = nums[0]")
    assert state["x"] == 10


def test_index_access_last_element():
    state = run("=> nums = [10, 20, 30]\n=> x = nums[2]")
    assert state["x"] == 30


def test_index_access_negative():
    """Negative indices work Python-style."""
    state = run("=> nums = [10, 20, 30]\n=> x = nums[-1]")
    assert state["x"] == 30


def test_index_access_out_of_bounds_returns_null():
    state = run("=> nums = [1, 2]\n=> x = nums[99]")
    assert state["x"] is None


def test_index_access_in_condition():
    state = run("=> nums = [0, 5, 0]\nnums[1] > 3 => x = 1")
    assert state["x"] == 1


def test_index_access_seeded_state():
    state = run("=> x = items[0]", state={"items": [42, 43]})
    assert state["x"] == 42


# ---------------------------------------------------------------------------
# Index assignment (write)
# ---------------------------------------------------------------------------

def test_index_assignment_basic():
    state = run("=> nums = [1, 2, 3]\n=> nums[1] = 99")
    assert state["nums"] == [1, 99, 3]


def test_index_assignment_first():
    state = run("=> nums = [1, 2, 3]\n=> nums[0] = 0")
    assert state["nums"] == [0, 2, 3]


def test_index_assignment_negative():
    state = run("=> nums = [1, 2, 3]\n=> nums[-1] = 100")
    assert state["nums"] == [1, 2, 100]


def test_index_assignment_with_expression_value():
    state = run("=> nums = [1, 2, 3]\n=> x = 10\n=> nums[0] = x * 2")
    assert state["nums"] == [20, 2, 3]


# ---------------------------------------------------------------------------
# push() — list group
# ---------------------------------------------------------------------------

def test_push_to_empty_list():
    state = run("=> items = []\n=> push(items, 42)")
    assert state["items"] == [42]


def test_push_multiple():
    state = run("=> items = []\n=> push(items, 1)\n=> push(items, 2)\n=> push(items, 3)")
    assert state["items"] == [1, 2, 3]


def test_push_to_existing_list():
    state = run("=> items = [1, 2]\n=> push(items, 3)")
    assert state["items"] == [1, 2, 3]


def test_push_returns_null():
    state = run("=> items = []\n=> result = push(items, 1)")
    assert state["result"] is None


def test_push_non_list_raises():
    with pytest.raises(RulixError, match="push\\(\\) expects a list"):
        run('=> x = "hello"\n=> push(x, 1)')


# ---------------------------------------------------------------------------
# pop() — list group
# ---------------------------------------------------------------------------

def test_pop_returns_last_element():
    state = run("=> items = [1, 2, 3]\n=> x = pop(items)")
    assert state["x"] == 3
    assert state["items"] == [1, 2]


def test_pop_empty_list_returns_null():
    state = run("=> items = []\n=> x = pop(items)")
    assert state["x"] is None
    assert state["items"] == []


def test_pop_single_element():
    state = run("=> items = [99]\n=> x = pop(items)")
    assert state["x"] == 99
    assert state["items"] == []


def test_pop_non_list_raises():
    with pytest.raises(RulixError, match="pop\\(\\) expects a list"):
        run("=> x = pop(42)")


# ---------------------------------------------------------------------------
# get() — list group
# ---------------------------------------------------------------------------

def test_get_valid_index():
    state = run("=> nums = [10, 20, 30]\n=> x = get(nums, 1)")
    assert state["x"] == 20


def test_get_negative_index():
    state = run("=> nums = [10, 20, 30]\n=> x = get(nums, -1)")
    assert state["x"] == 30


def test_get_out_of_bounds_returns_null():
    state = run("=> nums = [1, 2]\n=> x = get(nums, 5)")
    assert state["x"] is None


def test_get_non_list_raises():
    with pytest.raises(RulixError, match="get\\(\\) expects a list"):
        run('=> x = get("hello", 0)')


def test_get_non_int_index_raises():
    with pytest.raises(RulixError, match="index must be an int"):
        run('=> nums = [1, 2]\n=> x = get(nums, "a")')


# ---------------------------------------------------------------------------
# len() with lists
# ---------------------------------------------------------------------------

def test_len_empty_list():
    state = run("=> items = []\n=> n = len(items)")
    assert state["n"] == 0


def test_len_non_empty_list():
    state = run("=> items = [1, 2, 3, 4]\n=> n = len(items)")
    assert state["n"] == 4


def test_len_still_works_on_strings():
    state = run('=> n = len("hello")')
    assert state["n"] == 5


# ---------------------------------------------------------------------------
# is_list() — type group
# ---------------------------------------------------------------------------

def test_is_list_true():
    state = run("=> items = [1, 2]\n=> r = is_list(items)")
    assert state["r"] is True


def test_is_list_false_for_string():
    state = run('=> r = is_list("hello")')
    assert state["r"] is False


def test_is_list_false_for_null():
    state = run("=> r = is_list(null)")
    assert state["r"] is False


def test_is_list_false_for_int():
    state = run("=> r = is_list(42)")
    assert state["r"] is False


# ---------------------------------------------------------------------------
# type() with lists
# ---------------------------------------------------------------------------

def test_type_returns_list():
    state = run("=> items = [1, 2]\n=> t = type(items)")
    assert state["t"] == "list"


# ---------------------------------------------------------------------------
# str() with lists
# ---------------------------------------------------------------------------

def test_str_on_list():
    state = run('=> items = [1, 2, 3]\n=> s = str(items)')
    assert state["s"] == "[1, 2, 3]"


def test_str_on_empty_list():
    state = run('=> items = []\n=> s = str(items)')
    assert state["s"] == "[]"


# ---------------------------------------------------------------------------
# split() — string group (now that lists exist)
# ---------------------------------------------------------------------------

def test_split_basic():
    state = run('=> parts = split("a,b,c", ",")')
    assert state["parts"] == ["a", "b", "c"]


def test_split_by_space():
    state = run('=> parts = split("hello world foo", " ")')
    assert state["parts"] == ["hello", "world", "foo"]


def test_split_no_separator_found():
    state = run('=> parts = split("hello", ",")')
    assert state["parts"] == ["hello"]


def test_split_result_len():
    state = run('=> parts = split("a,b,c", ",")\n=> n = len(parts)')
    assert state["n"] == 3


def test_split_result_index_access():
    state = run('=> parts = split("x:y:z", ":")\n=> first = parts[0]\n=> last = parts[2]')
    assert state["first"] == "x"
    assert state["last"] == "z"


# ---------------------------------------------------------------------------
# List in string interpolation
# ---------------------------------------------------------------------------

def test_list_interpolation():
    state = run('=> items = [1, 2, 3]\n=> msg = "list: {items}"')
    assert state["msg"] == "list: [1, 2, 3]"


# ---------------------------------------------------------------------------
# List persistence (round-trip through JSON)
# ---------------------------------------------------------------------------

def test_list_persists_across_runs(tmp_path):
    from rulix import RulixInterpreter
    state_file = str(tmp_path / "test.state")
    interp = RulixInterpreter(state_file=state_file)
    interp.run("=> items = [1, 2, 3]")
    assert interp.state.get("items") == [1, 2, 3]

    # Second run: list is still there from persisted state
    interp2 = RulixInterpreter(state_file=state_file)
    interp2.run("=> push(items, 4)")
    assert interp2.state.get("items") == [1, 2, 3, 4]


def test_list_state_seeded_by_host():
    state = run("=> n = len(items)", state={"items": [10, 20, 30]})
    assert state["n"] == 3


# ---------------------------------------------------------------------------
# List equality
# ---------------------------------------------------------------------------

def test_list_equality_true():
    state = run("=> a = [1, 2, 3]\n=> b = [1, 2, 3]\na == b => x = 1")
    assert state["x"] == 1


def test_list_equality_false():
    state = run("=> a = [1, 2]\n=> b = [1, 3]\na != b => x = 1")
    assert state["x"] == 1


# ---------------------------------------------------------------------------
# Sandbox / group control
# ---------------------------------------------------------------------------

def test_list_group_can_be_disabled():
    from rulix import RulixInterpreter, RulixConfig
    config = RulixConfig.full()
    config.disable_group("list")
    interp = RulixInterpreter(config=config)
    with pytest.raises(RulixError, match="group 'list' is disabled"):
        interp.run("=> items = []\n=> push(items, 1)")


def test_list_group_disabled_affects_pop():
    from rulix import RulixInterpreter, RulixConfig
    config = RulixConfig.full()
    config.disable_group("list")
    interp = RulixInterpreter(config=config)
    with pytest.raises(RulixError, match="group 'list' is disabled"):
        interp.run("=> items = [1]\n=> x = pop(items)")


def test_sandbox_includes_list_by_default():
    """sandbox() should still allow list operations."""
    from rulix import RulixInterpreter, RulixConfig
    config = RulixConfig.sandbox()
    interp = RulixInterpreter(config=config)
    interp.run("=> items = [1, 2, 3]\n=> push(items, 4)")
    assert interp.state.get("items") == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_index_non_list_raises():
    with pytest.raises(RulixError, match="not a list"):
        run("=> x = 42\n=> y = x[0]")


def test_index_assignment_non_list_raises():
    with pytest.raises(RulixError, match="not a list"):
        run("=> x = 42\n=> x[0] = 1")


def test_index_assignment_out_of_bounds_raises():
    with pytest.raises(RulixError, match="out of range"):
        run("=> nums = [1, 2]\n=> nums[5] = 99")


def test_len_non_list_non_string_raises():
    with pytest.raises(RulixError, match="len\\(\\) expects a string or list"):
        run("=> x = len(42)")
