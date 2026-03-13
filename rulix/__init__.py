from .config import RulixConfig
from .interpreter import Interpreter, RulixError, RulixInterpreter, StateView


def run(
    source: str,
    state: dict | None = None,
    config: RulixConfig | None = None,
) -> dict:
    """Execute a Rulix program and return the resulting state.

    Args:
        source: Rulix source code as a string.
        state:  Optional initial state dict. Mutated in-place and returned,
                allowing callers to seed values before the run.
        config: Optional RulixConfig controlling which built-in groups are
                available. Defaults to RulixConfig.full() (all groups on).

    Returns:
        The state dict after all rules have been evaluated.
    """
    interp = Interpreter(state=state, config=config)
    interp.run(source)
    return interp.state


__all__ = ["run", "Interpreter", "RulixConfig", "RulixError", "RulixInterpreter", "StateView"]
