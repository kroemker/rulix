from .interpreter import Interpreter, RulixError


def run(source: str, state: dict | None = None) -> dict:
    """Execute a Rulix program and return the resulting state.

    Args:
        source: Rulix source code as a string.
        state:  Optional initial state dict. If provided it is mutated
                in-place and returned, allowing callers to seed values
                before the run and read them back after.

    Returns:
        The state dict after all rules have been evaluated.
    """
    interp = Interpreter(state)
    interp.run(source)
    return interp.state


__all__ = ["run", "Interpreter", "RulixError"]
