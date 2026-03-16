"""Complex integration tests covering nested multi-run behaviours, cascading
disable/stop interactions, deep expression pipelines, and state-machine patterns."""
from rulix import run


# ---------------------------------------------------------------------------
# 1. Full state-machine advancing through all phases in a single run
#
# Because later rules see earlier writes from the same run, the machine
# advances idle → running → done all within run 1.  The "done" rule then
# disables itself so run 2 leaves state untouched.
# ---------------------------------------------------------------------------

def test_state_machine_all_phases_in_one_run():
    source = (
        "rule start:   is_null(phase)          => phase = \"idle\"\n"
        "rule idle:    phase == \"idle\"          => { work = 0\nphase = \"running\" }\n"
        "rule running: phase == \"running\"       => { work = work + 1\nphase = \"done\" }\n"
        "rule done:    phase == \"done\"          => { finished = true\ndisable }\n"
    )
    state = {}
    run(source, state=state)
    assert state["phase"] == "done"
    assert state["work"] == 1
    assert state["finished"] is True

    # run 2: nothing should change
    state["work"] = 99
    run(source, state=state)
    assert state["phase"] == "done"
    assert state["work"] == 99   # neither idle nor running fired


def test_state_machine_phase_transitions_are_atomic():
    """Each phase rule fires exactly once; skipped on re-runs because phase moved on."""
    source = (
        "rule to_b: phase == \"a\" => phase = \"b\"\n"
        "rule to_c: phase == \"b\" => phase = \"c\"\n"
        "rule to_d: phase == \"c\" => { phase = \"d\"\ndisable }\n"
    )
    state = {"phase": "a"}
    run(source, state=state)
    assert state["phase"] == "d"

    run(source, state=state)
    assert state["phase"] == "d"   # to_d is disabled, others don't match


# ---------------------------------------------------------------------------
# 2. Countdown: fires exactly N times then self-disables
# ---------------------------------------------------------------------------

def test_countdown_fires_exactly_n_times():
    source = (
        "rule init:   is_null(count) => { count = 3\ndisable }\n"
        "rule tick:   count > 0      => count = count - 1\n"
        "rule finish: count == 0     => { done = true\ndisable }\n"
    )
    state = {}

    run(source, state=state)
    # run 1: init sets count=3 (disabled), tick → count=2, finish: 2≠0
    assert state["count"] == 2
    assert "done" not in state

    run(source, state=state)
    assert state["count"] == 1

    run(source, state=state)
    # run 3: tick → count=0, finish fires → done=True, disabled
    assert state["count"] == 0
    assert state["done"] is True

    run(source, state=state)
    # run 4: tick doesn't fire (count=0), finish disabled → nothing changes
    assert state["count"] == 0
    assert state["done"] is True
    assert state.get("_rulix_disabled_finish") is True


# ---------------------------------------------------------------------------
# 3. Cascading self-disable chain: four rules each guard-wait and then disable
#    Rule N fires when rule N-1 has set its own "done" flag.
# ---------------------------------------------------------------------------

def test_cascading_self_disable_chain():
    source = (
        "rule setup: is_null(ready)      => { ready = true\ndisable }\n"
        "rule step1: ready == true,  is_null(s1)  => { s1 = true\ndisable }\n"
        "rule step2: s1 == true,     is_null(s2)  => { s2 = true\ndisable }\n"
        "rule step3: s2 == true,     is_null(s3)  => { s3 = true\ndisable }\n"
    )
    state = {}
    run(source, state=state)

    # All four rules fire in a single run (pipeline order)
    assert state["ready"] is True
    assert state["s1"]    is True
    assert state["s2"]    is True
    assert state["s3"]    is True

    # All disabled
    for label in ("setup", "step1", "step2", "step3"):
        assert state.get(f"_rulix_disabled_{label}") is True

    # run 2: all disabled, nothing changes
    state["ready"] = "OVERWRITE"
    run(source, state=state)
    assert state["ready"] == "OVERWRITE"   # no rule rewrote it


# ---------------------------------------------------------------------------
# 4. Guard stop: a rule stops the cycle whenever a threshold is exceeded;
#    a downstream rule therefore never runs while the threshold is active.
# ---------------------------------------------------------------------------

def test_guard_stop_blocks_downstream_rule():
    source = (
        "rule init: is_null(n) => { n = 0\ndisable }\n"
        "=> n = n + 1\n"
        "rule guard: n >= 3 => { exceeded = n\nstop }\n"
        "=> last_seen = n\n"
    )
    state = {}

    run(source, state=state)   # n=1, guard no, last_seen=1
    assert state["last_seen"] == 1

    run(source, state=state)   # n=2, guard no, last_seen=2
    assert state["last_seen"] == 2

    run(source, state=state)   # n=3, guard fires (exceeded=3, stop), last_seen stays 2
    assert state["exceeded"] == 3
    assert state["last_seen"] == 2   # NOT updated this run

    run(source, state=state)   # n=4, guard fires again (exceeded=4, stop)
    assert state["exceeded"] == 4
    assert state["last_seen"] == 2   # still not updated


# ---------------------------------------------------------------------------
# 5. Disable + stop with downstream effects across runs
#    A "critical" rule fires, disables itself AND stops.
#    After disable, stop no longer triggers → downstream rule can run again.
# ---------------------------------------------------------------------------

def test_disable_then_stop_unblocks_downstream():
    source = (
        "rule init:     is_null(n) => { n = 0\ndisable }\n"
        "rule critical: n >= 5     => { alert = true\ndisable\nstop }\n"
        "=> n = n + 1\n"
        "=> last = n\n"
    )
    state = {}

    for _ in range(5):
        run(source, state=state)
    # After 5 runs: n is incremented 5 times (runs 1-5), last=5
    assert state["n"] == 5
    assert state["last"] == 5
    assert "alert" not in state

    run(source, state=state)
    # run 6: critical fires (n=5 >= 5), alert=True, disable, stop
    # n and last are NOT updated this run (stop fired before those rules)
    assert state["alert"] is True
    assert state["n"] == 5
    assert state["last"] == 5

    run(source, state=state)
    # run 7: critical is disabled, n increments to 6, last=6
    assert state["n"] == 6
    assert state["last"] == 6


# ---------------------------------------------------------------------------
# 6. Stop fires only on one specific run; later runs continue normally
# ---------------------------------------------------------------------------

def test_stop_fires_on_exact_run_only():
    source = (
        "rule init: is_null(n) => { n = 0\ndisable }\n"
        "=> n = n + 1\n"
        "n == 3 => stop\n"
        "=> marker = n\n"
    )
    state = {}

    run(source, state=state)   # n=1, stop? No, marker=1
    assert state["marker"] == 1

    run(source, state=state)   # n=2, stop? No, marker=2
    assert state["marker"] == 2

    run(source, state=state)   # n=3, stop fires, marker stays 2
    assert state["n"] == 3
    assert state["marker"] == 2

    run(source, state=state)   # n=4, stop? No (n≠3), marker=4
    assert state["marker"] == 4

    run(source, state=state)   # n=5, stop? No, marker=5
    assert state["marker"] == 5


# ---------------------------------------------------------------------------
# 7. Multiple stop conditions; only the first one reached triggers stop
# ---------------------------------------------------------------------------

def test_multiple_stop_rules_only_first_triggers():
    source = (
        "rule init: is_null(n) => { n = 0\ndisable }\n"
        "=> n = n + 1\n"
        "n == 2 => stop\n"
        "n == 4 => stop\n"
        "=> after = n\n"
    )
    state = {}

    run(source, state=state)            # n=1, neither stop, after=1
    assert state["after"] == 1

    run(source, state=state)            # n=2, first stop fires, after stays 1
    assert state["n"] == 2
    assert state["after"] == 1

    run(source, state=state)            # n=3, neither stop, after=3
    assert state["after"] == 3

    run(source, state=state)            # n=4, second stop fires, after stays 3
    assert state["n"] == 4
    assert state["after"] == 3

    run(source, state=state)            # n=5, neither stop, after=5
    assert state["after"] == 5


# ---------------------------------------------------------------------------
# 8. Deep expression pipeline across multiple rules with nested state
# ---------------------------------------------------------------------------

def test_deep_expression_pipeline_nested_state():
    source = (
        "=> raw.value = 6\n"
        "=> raw.squared = raw.value * raw.value\n"           # 36
        "=> derived.triple = raw.squared + raw.value\n"      # 42
        "=> derived.big = derived.triple * 2\n"              # 84
        "derived.big > 80 => output.label = \"big\"\n"
        "derived.big > 80 => output.total = derived.big + raw.value\n"  # 90
    )
    state = run(source)

    assert state["raw"]["value"] == 6
    assert state["raw"]["squared"] == 36
    assert state["derived"]["triple"] == 42
    assert state["derived"]["big"] == 84
    assert state["output"]["label"] == "big"
    assert state["output"]["total"] == 90


def test_deep_pipeline_five_levels_of_derivation():
    """Each rule reads the previous rule's write and adds one more layer."""
    source = (
        "=> a = 2\n"
        "=> b = a + 3\n"           # 5
        "=> c = b * b\n"           # 25
        "=> d = c - a\n"           # 23
        "=> e = d + b\n"           # 28
        "=> f = e * a\n"           # 56
        "=> g = f - c\n"           # 31
        "=> result = g + a\n"      # 33
    )
    state = run(source)

    assert state["a"] == 2
    assert state["b"] == 5
    assert state["c"] == 25
    assert state["d"] == 23
    assert state["e"] == 28
    assert state["f"] == 56
    assert state["g"] == 31
    assert state["result"] == 33


# ---------------------------------------------------------------------------
# 9. Block with many cascading arithmetic steps
# ---------------------------------------------------------------------------

def test_block_cascading_arithmetic():
    source = (
        "rule compute: => {\n"
        "    a = 4\n"
        "    b = a + 6\n"          # 10
        "    c = b * 3\n"          # 30
        "    d = c - a\n"          # 26
        "    e = d + b\n"          # 36
        "    f = e * a\n"          # 144
        "    summary = f + c\n"    # 174
        "}\n"
    )
    state = run(source)

    assert state["a"] == 4
    assert state["b"] == 10
    assert state["c"] == 30
    assert state["d"] == 26
    assert state["e"] == 36
    assert state["f"] == 144
    assert state["summary"] == 174


def test_block_reads_outer_state_and_builds_on_it():
    """Block reads seeded state and builds several derived values."""
    source = (
        "rule enrich: => {\n"
        "    bonus = base * 2\n"
        "    total = base + bonus\n"
        "    scaled = total * factor\n"
        "}\n"
    )
    state = run(source, state={"base": 5, "factor": 3})

    assert state["bonus"] == 10
    assert state["total"] == 15
    assert state["scaled"] == 45


# ---------------------------------------------------------------------------
# 10. Multiple conditions all using nested state at different depths
# ---------------------------------------------------------------------------

def test_four_nested_conditions_all_true():
    source = (
        "srv.online == true, srv.cpu < 80, srv.mem < 70, srv.errors == 0"
        " => health = \"ok\"\n"
    )
    state = run(
        source,
        state={"srv": {"online": True, "cpu": 50, "mem": 60, "errors": 0}},
    )
    assert state["health"] == "ok"


def test_four_nested_conditions_one_false_blocks():
    source = (
        "srv.online == true, srv.cpu < 80, srv.mem < 70, srv.errors == 0"
        " => health = \"ok\"\n"
    )
    # errors == 1 → condition fails
    state = run(
        source,
        state={"srv": {"online": True, "cpu": 50, "mem": 60, "errors": 1}},
    )
    assert "health" not in state


def test_three_level_deep_condition():
    source = "a.b.c == 42, a.b.d == \"yes\" => found = true\n"
    state = run(source, state={"a": {"b": {"c": 42, "d": "yes"}}})
    assert state["found"] is True


def test_three_level_deep_condition_partial_miss():
    source = "a.b.c == 42, a.b.d == \"yes\" => found = true\n"
    state = run(source, state={"a": {"b": {"c": 42, "d": "no"}}})
    assert "found" not in state


# ---------------------------------------------------------------------------
# 11. Operator precedence in complex multi-rule expressions
# ---------------------------------------------------------------------------

def test_operator_precedence_multiply_before_add():
    """2 + 3 * 4 must evaluate as 2 + (3*4) = 14, not (2+3)*4 = 20."""
    state = run("=> result = 2 + 3 * 4")
    assert state["result"] == 14


def test_operator_precedence_across_rules():
    source = (
        "=> x = 10\n"
        "=> y = 3\n"
        "=> z = x + y * 2 - 1\n"   # 10 + (3*2) - 1 = 15
    )
    state = run(source)
    assert state["z"] == 15


def test_operator_precedence_complex_expression():
    # (2 + 3) is not explicit here; without parens: 1 + 2 * 3 + 4 * 5 = 1+6+20 = 27
    state = run("=> r = 1 + 2 * 3 + 4 * 5")
    assert state["r"] == 27


# ---------------------------------------------------------------------------
# 12. Parentheses for grouping in math expressions
# ---------------------------------------------------------------------------

def test_parens_override_mul_precedence():
    """(2 + 3) * 4 should be 20, not 14."""
    state = run("=> x = (2 + 3) * 4")
    assert state["x"] == 20


def test_parens_right_operand():
    state = run("=> x = 2 * (3 + 4)")
    assert state["x"] == 14


def test_deeply_nested_parens():
    """((10 + 5) - 3) / 2 = 6.0"""
    state = run("=> x = ((10 + 5) - 3) / 2")
    assert state["x"] == 6.0


def test_triple_nested_parens():
    """(2 + (3 * (4 - 1))) = 2 + 9 = 11"""
    state = run("=> x = (2 + (3 * (4 - 1)))")
    assert state["x"] == 11


def test_unary_minus_on_grouped_expr():
    state = run("=> x = -(2 + 3)")
    assert state["x"] == -5


def test_parens_in_condition():
    """Parentheses in a rule condition."""
    source = (
        "=> a = 2\n"
        "=> b = 8\n"
        "rule check: (a + b) * 2 == 20  => ok = true\n"
    )
    state = run(source)
    assert state["ok"] is True


def test_parens_mixed_across_rules():
    source = (
        "=> base = 3\n"
        "=> result = (base + 2) * (base - 1)\n"   # 5 * 2 = 10
    )
    state = run(source)
    assert state["result"] == 10


# ---------------------------------------------------------------------------
# 13. Many-run accumulator with milestone that fires exactly once
# ---------------------------------------------------------------------------

def test_accumulator_with_once_only_milestone():
    source = (
        "rule init:      is_null(count)  => { count = 0\ndisable }\n"
        "=> count = count + 1\n"
        "rule halfway:   count == 5      => { halfway_reached = true\ndisable }\n"
    )
    state = {}
    for _ in range(10):
        run(source, state=state)

    assert state["count"] == 10
    assert state["halfway_reached"] is True
    assert state.get("_rulix_disabled_halfway") is True


def test_accumulator_milestone_fires_at_correct_run():
    """Verify milestone is not set before run 5 and stays set after."""
    source = (
        "rule init:    is_null(count) => { count = 0\ndisable }\n"
        "=> count = count + 1\n"
        "rule target:  count == 5     => { hit = true\ndisable }\n"
    )
    state = {}

    for i in range(4):
        run(source, state=state)
    assert "hit" not in state     # not fired yet

    run(source, state=state)      # run 5: fires
    assert state["hit"] is True

    run(source, state=state)      # run 6: disabled, hit untouched
    assert state["hit"] is True
    assert state["count"] == 6


# ---------------------------------------------------------------------------
# 13. Alert level transitions with conditional disable
# ---------------------------------------------------------------------------

def test_alert_level_transitions_and_disable():
    """high_alert rule fires once (on first high reading) and disables itself."""
    source = (
        "rule init:       is_null(value) => { value = 0\ndisable }\n"
        "=> value = value + 10\n"
        "rule low_alert:  value <= 20    => alert_level = \"low\"\n"
        "rule high_alert: value > 20     => { alert_level = \"high\"\ndisable }\n"
    )
    state = {}

    run(source, state=state)   # value=10, low_alert fires
    assert state["alert_level"] == "low"

    run(source, state=state)   # value=20, low_alert fires (20 <= 20)
    assert state["alert_level"] == "low"

    run(source, state=state)   # value=30, high_alert fires (disabled), low_alert: 30>20 → false
    assert state["alert_level"] == "high"

    run(source, state=state)   # value=40, high_alert disabled, low_alert: 40<=20? No
    # alert_level stays "high" from previous run; neither rule overwrites it
    assert state["alert_level"] == "high"
    assert state.get("_rulix_disabled_high_alert") is True


# ---------------------------------------------------------------------------
# 14. Cross-rule accumulation with multiple checkpoints and early-exit stop
# ---------------------------------------------------------------------------

def test_checkpoints_and_early_exit_stop():
    source = (
        "rule init:         is_null(total) => { total = 0\ndisable }\n"
        "=> total = total + 5\n"
        "rule chk10: total >= 10, is_null(hit10) => { hit10 = true\ndisable }\n"
        "rule chk20: total >= 20, is_null(hit20) => { hit20 = true\ndisable }\n"
        "rule exit:  total >= 25              => { exit_at = total\nstop }\n"
        "=> processed = total\n"
    )
    state = {}

    run(source, state=state)   # total=5, no checkpoints, processed=5
    assert state["processed"] == 5

    run(source, state=state)   # total=10, chk10 fires, processed=10
    assert state["hit10"] is True
    assert state["processed"] == 10

    run(source, state=state)   # total=15, chk20: 15<20? no, processed=15
    assert "hit20" not in state
    assert state["processed"] == 15

    run(source, state=state)   # total=20, chk20 fires, processed=20
    assert state["hit20"] is True
    assert state["processed"] == 20

    run(source, state=state)   # total=25, exit fires (stop!), processed stays 20
    assert state["exit_at"] == 25
    assert state["processed"] == 20   # NOT updated this run

    run(source, state=state)   # total=30, exit fires again (stop!), processed stays 20
    assert state["exit_at"] == 30
    assert state["processed"] == 20


# ---------------------------------------------------------------------------
# 15. String interpolation in a multi-rule pipeline
# ---------------------------------------------------------------------------

def test_string_interpolation_across_pipeline():
    source = (
        "=> stats.base = 100\n"
        "=> stats.bonus = 50\n"
        "=> stats.total = stats.base + stats.bonus\n"
        "=> report = \"base={stats.base} bonus={stats.bonus} total={stats.total}\"\n"
        "stats.total > 100 => summary = \"Total {stats.total} exceeds 100\"\n"
    )
    state = run(source)

    assert state["stats"]["total"] == 150
    assert state["report"] == "base=100 bonus=50 total=150"
    assert state["summary"] == "Total 150 exceeds 100"


def test_interpolation_with_computed_expression():
    source = (
        "=> a = 7\n"
        "=> b = 3\n"
        "=> msg = \"sum={a + b} product={a * b} diff={a - b}\"\n"
    )
    state = run(source)
    assert state["msg"] == "sum=10 product=21 diff=4"


# ---------------------------------------------------------------------------
# 16. Null-guarded setup chain: rules use is_null to guard one-time setup
#     across multiple nested configuration paths
# ---------------------------------------------------------------------------

def test_null_guarded_nested_config_setup():
    source = (
        "rule set_mode:    is_null(cfg.mode)    => cfg.mode = \"fast\"\n"
        "rule set_workers: is_null(cfg.workers) => cfg.workers = 4\n"
        "rule set_timeout: is_null(cfg.timeout) => cfg.timeout = 30\n"
        "rule all_ready:   cfg.mode == \"fast\", cfg.workers > 0, cfg.timeout > 0"
        " => cfg.ready = true\n"
    )
    state = {}
    run(source, state=state)

    assert state["cfg"]["mode"] == "fast"
    assert state["cfg"]["workers"] == 4
    assert state["cfg"]["timeout"] == 30
    assert state["cfg"]["ready"] is True


def test_null_guarded_setup_idempotent():
    """Re-running with all config already set must not overwrite values."""
    source = (
        "rule set_mode:    is_null(cfg.mode)    => cfg.mode = \"fast\"\n"
        "rule set_workers: is_null(cfg.workers) => cfg.workers = 4\n"
    )
    state = {"cfg": {"mode": "slow", "workers": 8}}
    run(source, state=state)

    # is_null guards prevented any overwrite
    assert state["cfg"]["mode"] == "slow"
    assert state["cfg"]["workers"] == 8


# ---------------------------------------------------------------------------
# 17. Rule sequence where every rule's write flows into the next condition
# ---------------------------------------------------------------------------

def test_sequential_condition_gate_chain():
    """Each rule unlocks the next by writing a flag the next rule needs."""
    source = (
        "is_null(gate1) => gate1 = true\n"
        "gate1 == true, is_null(gate2) => gate2 = true\n"
        "gate2 == true, is_null(gate3) => gate3 = true\n"
        "gate3 == true => final = true\n"
    )
    state = run(source)

    # All fire in one run via pipeline order
    assert state["gate1"] is True
    assert state["gate2"] is True
    assert state["gate3"] is True
    assert state["final"] is True


# ---------------------------------------------------------------------------
# 18. A rule that self-disables based on a computed result in its own body
# ---------------------------------------------------------------------------

def test_self_disable_based_on_body_computation():
    """Rule computes a value; if it exceeds threshold it disables itself."""
    source = (
        "rule init: is_null(n) => { n = 0\ndisable }\n"
        "=> n = n + 1\n"
        "rule auto_off: => {\n"
        "    doubled = n * 2\n"
        "    result = doubled + n\n"
        "    disable\n"
        "}\n"
    )
    state = {}
    run(source, state=state)

    # auto_off fires on run 1 with n=1 (init sets 0, increment makes 1)
    assert state["doubled"] == 2
    assert state["result"] == 3
    assert state.get("_rulix_disabled_auto_off") is True

    run(source, state=state)
    # run 2: auto_off disabled, n increments to 2, doubled/result NOT rewritten
    assert state["n"] == 2
    assert state["doubled"] == 2   # still from run 1
    assert state["result"] == 3


# ---------------------------------------------------------------------------
# 19. Deeply nested state written by multiple rules in one run, then read
#     by a final summary rule
# ---------------------------------------------------------------------------

def test_deep_nested_writes_then_summary():
    source = (
        "=> metrics.cpu.usage = 42\n"
        "=> metrics.cpu.temp = 75\n"
        "=> metrics.mem.used = 8\n"
        "=> metrics.mem.total = 16\n"
        "metrics.cpu.usage < 80, metrics.mem.used < metrics.mem.total"
        " => metrics.healthy = true\n"
        "=> report = \"cpu={metrics.cpu.usage} mem={metrics.mem.used}/{metrics.mem.total}\"\n"
    )
    state = run(source)

    assert state["metrics"]["cpu"]["usage"] == 42
    assert state["metrics"]["cpu"]["temp"] == 75
    assert state["metrics"]["mem"]["used"] == 8
    assert state["metrics"]["mem"]["total"] == 16
    assert state["metrics"]["healthy"] is True
    assert state["report"] == "cpu=42 mem=8/16"


# ---------------------------------------------------------------------------
# 20. Stress: 10 rules all chained; last rule only fires if all prior rules
#     produced correct output (implicit integration of whole pipeline)
# ---------------------------------------------------------------------------

def test_ten_rule_chain_all_or_nothing():
    source = (
        "=> v1 = 1\n"
        "=> v2 = v1 + 1\n"            # 2
        "=> v3 = v2 * 2\n"            # 4
        "=> v4 = v3 + v1\n"           # 5
        "=> v5 = v4 * v2\n"           # 10
        "=> v6 = v5 - v3\n"           # 6
        "=> v7 = v6 + v5\n"           # 16
        "=> v8 = v7 * v1\n"           # 16
        "=> v9 = v8 + v4\n"           # 21
        "v9 == 21 => passed = true\n"
    )
    state = run(source)
    assert state["passed"] is True

    # Spot-check intermediates
    assert state["v5"] == 10
    assert state["v9"] == 21
