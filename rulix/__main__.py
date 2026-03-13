"""CLI entry point: python -m rulix <command> <file.rlx> [--state <file>]

Commands:
  run   <file.rlx> [--state <file>]   Execute the program.
  check <file.rlx>                    Parse-only syntax check; no execution.
  dump  <file.rlx> [--state <file>]   Print current state variables.
  clear <file.rlx> [--state <file>]   Delete the state file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .interpreter import RulixInterpreter
from .lexer import LexError
from .parser import ParseError, parse


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _default_state_path(prog_path: Path) -> Path:
    return prog_path.with_suffix(".state")


def _resolve_state_file(args) -> str | None:
    """Return the effective state file path, or None if --state was omitted."""
    if args.state:
        return args.state
    return None


def _read_program(path: str) -> str:
    p = Path(path)
    if not p.exists():
        print(f"rulix: error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_run(args) -> int:
    source = _read_program(args.file)
    state_file = _resolve_state_file(args)
    try:
        interp = RulixInterpreter(state_file=state_file)
        interp.run(source)
    except (LexError, ParseError) as e:
        print(f"rulix: syntax error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"rulix: error: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_check(args) -> int:
    source = _read_program(args.file)
    try:
        parse(source)
        print("OK")
    except (LexError, ParseError) as e:
        print(f"rulix: syntax error: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_dump(args) -> int:
    state_file = _resolve_state_file(args)
    if state_file is None:
        p = Path(args.file).with_suffix(".state")
        state_file = str(p) if p.exists() else None

    if state_file is None or not Path(state_file).exists():
        print("(no state)")
        return 0

    interp = RulixInterpreter(state_file=state_file)
    data = interp.state.as_dict()
    if not data:
        print("(empty state)")
        return 0
    for key, value in sorted(data.items()):
        if value is None:
            display = "null"
        elif isinstance(value, bool):
            display = "true" if value else "false"
        else:
            display = repr(value)
        print(f"  {key} = {display}")
    return 0


def cmd_clear(args) -> int:
    state_file = _resolve_state_file(args)
    if state_file is None:
        p = Path(args.file).with_suffix(".state")
        state_file = str(p) if p.exists() else None

    if state_file and Path(state_file).exists():
        Path(state_file).unlink()
        print(f"Cleared: {state_file}")
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="rulix",
        description="Rulix rule-based language interpreter",
    )
    sub = root.add_subparsers(dest="command", required=True)

    def add_state_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--state",
            metavar="FILE",
            help="Path to the state file (default: <program>.state)",
        )

    # run
    p_run = sub.add_parser("run", help="Execute a Rulix program")
    p_run.add_argument("file", help="Path to the .rlx source file")
    add_state_arg(p_run)

    # check
    p_check = sub.add_parser("check", help="Syntax-check without executing")
    p_check.add_argument("file", help="Path to the .rlx source file")

    # dump
    p_dump = sub.add_parser("dump", help="Print current state variables")
    p_dump.add_argument("file", help="Path to the .rlx source file")
    add_state_arg(p_dump)

    # clear
    p_clear = sub.add_parser("clear", help="Delete the state file")
    p_clear.add_argument("file", help="Path to the .rlx source file")
    add_state_arg(p_clear)

    return root


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "run":   cmd_run,
        "check": cmd_check,
        "dump":  cmd_dump,
        "clear": cmd_clear,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
