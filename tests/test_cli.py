"""Tests for the CLI (python -m rulix ...)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

RULIX = [sys.executable, "-m", "rulix"]
EXAMPLES = Path(__file__).parent.parent / "examples"


def run_cli(*args, input_text=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        RULIX + list(args),
        capture_output=True,
        text=True,
        input=input_text,
    )


# ---------------------------------------------------------------------------
# rulix run
# ---------------------------------------------------------------------------

def test_run_basic_example():
    result = run_cli("run", str(EXAMPLES / "basic_example.rlx"))
    assert result.returncode == 0


def test_run_prints_output(tmp_path):
    prog = tmp_path / "hello.rlx"
    prog.write_text('=> print("hello world")\n')
    result = run_cli("run", str(prog))
    assert result.returncode == 0
    assert "hello world" in result.stdout


def test_run_creates_state_file(tmp_path):
    prog = tmp_path / "prog.rlx"
    state = tmp_path / "prog.state"
    prog.write_text("=> x = 99\n")
    result = run_cli("run", str(prog), "--state", str(state))
    assert result.returncode == 0
    assert state.exists()
    assert json.loads(state.read_text())["x"] == 99


def test_run_state_persists_across_invocations(tmp_path):
    prog = tmp_path / "counter.rlx"
    state = tmp_path / "counter.state"
    prog.write_text("is_null(n) => n = 0\n=> n = n + 1\n")
    for _ in range(3):
        run_cli("run", str(prog), "--state", str(state))
    data = json.loads(state.read_text())
    assert data["n"] == 3


def test_run_missing_file_exits_nonzero():
    result = run_cli("run", "no_such_file.rlx")
    assert result.returncode != 0
    assert result.stderr  # some error message


def test_run_syntax_error_exits_nonzero(tmp_path):
    prog = tmp_path / "bad.rlx"
    prog.write_text("this is not valid rulix @@\n")
    result = run_cli("run", str(prog))
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# rulix check
# ---------------------------------------------------------------------------

def test_check_valid_program(tmp_path):
    prog = tmp_path / "ok.rlx"
    prog.write_text("=> x = 1\n")
    result = run_cli("check", str(prog))
    assert result.returncode == 0


def test_check_invalid_program_exits_nonzero(tmp_path):
    prog = tmp_path / "bad.rlx"
    prog.write_text("@@@ not valid\n")
    result = run_cli("check", str(prog))
    assert result.returncode != 0


def test_check_does_not_execute_program(tmp_path):
    """check must parse-only; it must not run rules or write a state file."""
    prog = tmp_path / "side_effect.rlx"
    state = tmp_path / "side_effect.state"
    prog.write_text('=> print("SHOULD NOT APPEAR")\n')
    result = run_cli("check", str(prog))
    assert result.returncode == 0
    assert "SHOULD NOT APPEAR" not in result.stdout
    assert not state.exists()


# ---------------------------------------------------------------------------
# rulix dump
# ---------------------------------------------------------------------------

def test_dump_shows_state(tmp_path):
    prog = tmp_path / "prog.rlx"
    state = tmp_path / "prog.state"
    prog.write_text("=> x = 7\n")
    run_cli("run", str(prog), "--state", str(state))
    result = run_cli("dump", str(prog), "--state", str(state))
    assert result.returncode == 0
    assert "x" in result.stdout
    assert "7" in result.stdout


def test_dump_no_state_file_shows_empty(tmp_path):
    prog = tmp_path / "prog.rlx"
    prog.write_text("=> x = 1\n")
    result = run_cli("dump", str(prog))
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# rulix clear
# ---------------------------------------------------------------------------

def test_clear_removes_state_file(tmp_path):
    prog = tmp_path / "prog.rlx"
    state = tmp_path / "prog.state"
    prog.write_text("=> x = 1\n")
    run_cli("run", str(prog), "--state", str(state))
    assert state.exists()
    result = run_cli("clear", str(prog), "--state", str(state))
    assert result.returncode == 0
    assert not state.exists()


def test_clear_no_state_file_is_noop(tmp_path):
    prog = tmp_path / "prog.rlx"
    prog.write_text("=> x = 1\n")
    result = run_cli("clear", str(prog))
    assert result.returncode == 0


def test_clear_missing_state_file_is_noop(tmp_path):
    prog = tmp_path / "prog.rlx"
    state = tmp_path / "prog.state"
    prog.write_text("=> x = 1\n")
    # state file was never created
    result = run_cli("clear", str(prog), "--state", str(state))
    assert result.returncode == 0
