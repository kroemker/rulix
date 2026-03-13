"""Tests for RulixConfig: group sandboxing and presets."""
import pytest
from rulix import RulixConfig, RulixError, run


# ---------------------------------------------------------------------------
# Config construction
# ---------------------------------------------------------------------------

def test_full_preset_enables_all_groups():
    config = RulixConfig.full()
    for group in ("io", "type", "math", "string", "state"):
        assert config.is_group_enabled(group)


def test_sandbox_preset_disables_io_and_state():
    config = RulixConfig.sandbox()
    assert not config.is_group_enabled("io")
    assert not config.is_group_enabled("state")


def test_sandbox_preset_keeps_type_math_string():
    config = RulixConfig.sandbox()
    for group in ("type", "math", "string"):
        assert config.is_group_enabled(group)


def test_default_config_equals_full():
    config = RulixConfig()
    for group in ("io", "type", "math", "string", "state"):
        assert config.is_group_enabled(group)


# ---------------------------------------------------------------------------
# enable / disable group
# ---------------------------------------------------------------------------

def test_disable_group():
    config = RulixConfig()
    config.disable_group("io")
    assert not config.is_group_enabled("io")


def test_enable_group():
    config = RulixConfig.sandbox()
    config.enable_group("io")
    assert config.is_group_enabled("io")


def test_unknown_group_raises_at_config_time():
    config = RulixConfig()
    with pytest.raises(ValueError, match="Unknown group"):
        config.disable_group("nonexistent")


def test_unknown_group_enable_raises():
    config = RulixConfig()
    with pytest.raises(ValueError, match="Unknown group"):
        config.enable_group("nonexistent")


# ---------------------------------------------------------------------------
# Group enforcement at runtime
# ---------------------------------------------------------------------------

def test_disabled_io_blocks_print():
    config = RulixConfig()
    config.disable_group("io")
    with pytest.raises(RulixError, match="group 'io' is disabled"):
        run('=> print("hi")', config=config)


def test_disabled_io_blocks_log():
    config = RulixConfig()
    config.disable_group("io")
    with pytest.raises(RulixError, match="group 'io' is disabled"):
        run('=> log("info", "msg")', config=config)


def test_disabled_state_blocks_delete():
    config = RulixConfig()
    config.disable_group("state")
    with pytest.raises(RulixError, match="group 'state' is disabled"):
        run('=> delete("x")', config=config)


def test_disabled_state_blocks_exists():
    config = RulixConfig()
    config.disable_group("state")
    with pytest.raises(RulixError, match="group 'state' is disabled"):
        run('=> y = exists("x")', config=config)


def test_disabled_math_blocks_abs():
    config = RulixConfig()
    config.disable_group("math")
    with pytest.raises(RulixError, match="group 'math' is disabled"):
        run("=> x = abs(-1)", config=config)


def test_sandbox_allows_type_functions():
    # is_null is in the type group — must work under sandbox
    config = RulixConfig.sandbox()
    state = run("is_null(x) => x = 1", config=config)
    assert state["x"] == 1


def test_sandbox_allows_math_functions():
    config = RulixConfig.sandbox()
    state = run("=> x = abs(-5)", config=config)
    assert state["x"] == 5


def test_sandbox_allows_string_functions():
    config = RulixConfig.sandbox()
    state = run('=> x = upper("hello")', config=config)
    assert state["x"] == "HELLO"


def test_sandbox_blocks_print():
    config = RulixConfig.sandbox()
    with pytest.raises(RulixError, match="group 'io' is disabled"):
        run('=> print("hi")', config=config)


def test_re_enabled_group_works():
    config = RulixConfig.sandbox()
    config.enable_group("io")
    # Should not raise
    run('=> print("ok")', config=config)


def test_run_without_config_uses_all_groups(capsys):
    """The bare run() with no config must still allow all built-ins."""
    run('=> print("bare")')
    assert capsys.readouterr().out == "bare\n"
