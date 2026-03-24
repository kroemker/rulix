from __future__ import annotations

import re

_VALID_GROUPS: frozenset[str] = frozenset({"io", "type", "math", "string", "state", "list"})
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Reserved words that cannot be used as function names
_RESERVED_WORDS: frozenset[str] = frozenset(
    {"rule", "true", "false", "null", "and", "or", "not", "disable", "stop"}
)


class RulixConfig:
    """Configuration for a Rulix interpreter instance.

    Controls which built-in function groups are available and allows
    host applications to register custom functions.
    """

    def __init__(self) -> None:
        self._enabled: set[str] = set(_VALID_GROUPS)   # all groups on by default
        self._custom: dict[str, tuple] = {}             # name -> (handler, arity)

    # --- presets ---

    @classmethod
    def full(cls) -> "RulixConfig":
        """All built-in groups enabled (default)."""
        return cls()

    @classmethod
    def sandbox(cls) -> "RulixConfig":
        """Safe preset: only type, math, string enabled; io and state off."""
        c = cls()
        c.disable_group("io")
        c.disable_group("state")
        return c

    # --- group control ---

    def enable_group(self, name: str) -> None:
        _require_valid_group(name)
        self._enabled.add(name)

    def disable_group(self, name: str) -> None:
        _require_valid_group(name)
        self._enabled.discard(name)

    def is_group_enabled(self, name: str) -> bool:
        return name in self._enabled

    # --- custom function registration ---

    def register_function(
        self,
        name: str,
        handler: callable,
        arity: int | None = None,
    ) -> None:
        """Register a host-provided function callable from Rulix scripts.

        Args:
            name:    Valid Rulix identifier; must not clash with a built-in.
            handler: Python callable receiving a list of native Python values
                     and returning a native Python value (or None).
            arity:   Exact argument count, or None for variadic.

        Raises:
            ValueError: if the name is invalid, reserved, or shadows a built-in.
        """
        # Import here to avoid circular dependency at module load time.
        from .interpreter import BUILTIN_NAMES

        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid function name: {name!r}")
        if name in _RESERVED_WORDS:
            raise ValueError(f"Function name {name!r} is a reserved word")
        if name in BUILTIN_NAMES:
            raise ValueError(f"Cannot override built-in function: {name!r}")
        if name in self._custom:
            raise ValueError(f"Function {name!r} is already registered")
        self._custom[name] = (handler, arity)

    @property
    def custom_functions(self) -> dict[str, tuple]:
        return dict(self._custom)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _require_valid_group(name: str) -> None:
    if name not in _VALID_GROUPS:
        raise ValueError(f"Unknown group: {name!r}. Valid groups: {sorted(_VALID_GROUPS)}")
