"""Tests for JSON-file state persistence in RulixInterpreter."""
import json
import pytest
from pathlib import Path
from rulix import RulixInterpreter


@pytest.fixture
def state_file(tmp_path) -> Path:
    return tmp_path / "test.state"


# ---------------------------------------------------------------------------
# State persists across interpreter instances
# ---------------------------------------------------------------------------

def test_state_written_to_file_after_run(state_file):
    interp = RulixInterpreter(state_file=str(state_file))
    interp.run("=> x = 42")
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["x"] == 42


def test_state_loaded_on_next_instance(state_file):
    interp1 = RulixInterpreter(state_file=str(state_file))
    interp1.run("=> counter = 1")

    interp2 = RulixInterpreter(state_file=str(state_file))
    interp2.run("=> counter = counter + 1")
    assert interp2.state.get("counter") == 2


def test_state_accumulates_over_many_runs(state_file):
    for _ in range(5):
        interp = RulixInterpreter(state_file=str(state_file))
        source = "is_null(n) => n = 0\n=> n = n + 1"
        interp.run(source)

    interp = RulixInterpreter(state_file=str(state_file))
    assert interp.state.get("n") == 5


def test_no_state_file_means_ephemeral_state():
    """Without a state_file the state is lost when the interpreter is discarded."""
    interp1 = RulixInterpreter()   # no file
    interp1.run("=> x = 99")

    interp2 = RulixInterpreter()   # fresh, no file
    assert interp2.state.get("x") is None


def test_missing_state_file_starts_fresh(state_file):
    """A non-existent state file is not an error — state starts empty."""
    assert not state_file.exists()
    interp = RulixInterpreter(state_file=str(state_file))
    interp.run("=> x = 1")
    assert interp.state.get("x") == 1


def test_state_file_preserves_all_types(state_file):
    interp = RulixInterpreter(state_file=str(state_file))
    interp.run('=> s = "hello"\n=> n = 42\n=> f = 3.14\n=> b = true')
    interp2 = RulixInterpreter(state_file=str(state_file))
    assert interp2.state.get("s") == "hello"
    assert interp2.state.get("n") == 42
    assert interp2.state.get("f") == pytest.approx(3.14)
    assert interp2.state.get("b") is True


def test_null_values_not_written_to_state_file(state_file):
    """Null / deleted variables are omitted from the JSON file."""
    interp = RulixInterpreter(state_file=str(state_file))
    interp.run('=> x = 1\n=> delete("x")')
    data = json.loads(state_file.read_text())
    assert "x" not in data


# ---------------------------------------------------------------------------
# StateView — host state access across runs
# ---------------------------------------------------------------------------

def test_host_seed_persists_through_run(state_file):
    interp = RulixInterpreter(state_file=str(state_file))
    interp.state.set("threshold", 10)
    interp.run("threshold > 5 => alert = true")
    assert interp.state.get("alert") is True


def test_state_view_delete_removes_key(state_file):
    interp = RulixInterpreter(state_file=str(state_file))
    interp.state.set("x", 1)
    interp.state.delete("x")
    assert interp.state.get("x") is None


def test_state_view_as_dict(state_file):
    interp = RulixInterpreter(state_file=str(state_file))
    interp.run("=> a = 1\n=> b = 2")
    d = interp.state.as_dict()
    assert d["a"] == 1
    assert d["b"] == 2
