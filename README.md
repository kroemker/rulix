# Rulix

A lightweight, embeddable rule-based interpreter written in Python.

A Rulix program is a list of **rules**. Every time the interpreter runs, it
evaluates each rule in order. A rule fires when all its conditions are true,
executing its body. State persists across runs.

---

## Quick example

```rulix
# counter.rlx
is_null(runs) => runs = 0
=> runs = runs + 1
=> print("Run #" + str(runs))
```

```
$ python -m rulix run counter.rlx
Run #1
$ python -m rulix run counter.rlx
Run #2
```

---

## Language

### Rules

```
[rule <name>:] [condition, ...] => statement
[rule <name>:] [condition, ...] => {
    statement
    statement
}
```

An **unconditional rule** (no conditions) fires on every run:

```rulix
=> x = 1
```

A **conditional rule** fires only when all conditions are true (comma = AND):

```rulix
x > 0, x < 100 => print("in range")
```

Rules are evaluated top-to-bottom on every run. Multiple rules can fire per
run. Rule labels are optional and documentary only:

```rulix
rule init:  is_null(score) => score = 0
rule level: score >= 100   => print("level up!")
```

### Conditions

Conditions are comma-separated boolean expressions. All must be true for the
rule to fire. Standard operators are supported inside expressions:

| Kind        | Operators                          |
|-------------|------------------------------------|
| Arithmetic  | `+` `-` `*` `/` `%`               |
| Comparison  | `==` `!=` `<` `>` `<=` `>=`       |
| Boolean     | `and` `or` `not`                   |

Operator precedence follows standard mathematical convention.
`or` is lower priority than `and`, which is lower than comparisons.

### Statements

A statement is an **assignment**, a **control-flow keyword**, or a **function call**:

```rulix
x = x + 1          # assignment
print("hello")     # function call
disable            # control-flow keyword
stop               # control-flow keyword
```

Assignment is a statement only — it cannot appear inside a larger expression.

### Control flow

Two keyword statements are valid inside a rule body:

| Keyword | Effect |
|---------|--------|
| `disable` | Marks the current rule as disabled in state. It will not fire in any future run. Execution of the current body continues normally. |
| `stop` | Immediately ends the current evaluation cycle. No further statements or rules run this cycle. The next run starts fresh from rule 1. |

```rulix
# One-shot initialisation
rule init: is_null(n) => {
    n = 0
    disable          # fires exactly once across all runs
}

# Emergency brake
rule overflow: n > 1000 => {
    log("warn", "overflow, resetting")
    n = 0
    stop             # skip remaining rules this cycle
}

# Both at once: disable self and end the cycle
rule critical: error_count > 10 => {
    log("error", "critical threshold hit")
    disable
    stop
}
```

`disable` stores a flag in state as `_rulix_disabled_<label>` (label if present,
otherwise the rule's 0-based index). Delete that key from host code to re-enable.

### String interpolation

Embed expressions directly inside strings using `{expr}`:

```rulix
name = "Alice"
score = 95
rule greet: => msg = "Hello {name}, score: {score}!"
```

Any Rulix expression is valid inside `{...}`, including arithmetic and function calls:

```rulix
=> summary = "next={count + 1}, type={type(x)}"
```

Use `{{` for a literal `{` and `}}` for a literal `}`:

```rulix
=> msg = "{{not a hole}} but {x} is"   # → "{not a hole} but <x>"
```

### Data types

| Type     | Examples                      |
|----------|-------------------------------|
| `int`    | `0`, `42`, `-7`               |
| `float`  | `3.14`, `-0.5`                |
| `bool`   | `true`, `false`               |
| `string` | `"hello"`, `"hi {name}"`      |
| `null`   | `null`                        |

Unset variables evaluate to `null`. `null` and `false` are falsy; everything
else is truthy.

### Comments

```rulix
# full-line comment
x = 1  # inline comment
```

---

## Built-in functions

### `type` group — type checks and conversion

| Function | Returns | Description |
|---|---|---|
| `is_null(v)` | bool | True if `v` is null |
| `is_int(v)` | bool | True if `v` is an integer |
| `is_float(v)` | bool | True if `v` is a float |
| `is_string(v)` | bool | True if `v` is a string |
| `is_bool(v)` | bool | True if `v` is a boolean |
| `str(v)` | string | Convert to string |
| `int(v)` | int | Parse / truncate to integer |
| `float(v)` | float | Parse / widen to float |
| `bool(v)` | bool | Truthiness coercion |
| `type(v)` | string | `"int"`, `"float"`, `"bool"`, `"string"`, or `"null"` |

### `math` group

| Function | Returns | Description |
|---|---|---|
| `abs(n)` | number | Absolute value |
| `min(a, b)` | number | Smaller of two numbers |
| `max(a, b)` | number | Larger of two numbers |
| `floor(n)` | int | Round down |
| `ceil(n)` | int | Round up |
| `round(n)` | int | Round to nearest |
| `pow(base, exp)` | float | Exponentiation |
| `sqrt(n)` | float | Square root |

### `string` group

| Function | Returns | Description |
|---|---|---|
| `len(s)` | int | Character count |
| `upper(s)` | string | Uppercase |
| `lower(s)` | string | Lowercase |
| `trim(s)` | string | Strip whitespace |
| `contains(s, sub)` | bool | Substring test |
| `starts_with(s, pre)` | bool | Prefix test |
| `ends_with(s, suf)` | bool | Suffix test |
| `replace(s, old, new)` | string | Replace first occurrence |

### `io` group

| Function | Description |
|---|---|
| `print(v, ...)` | Print values to stdout, space-separated |
| `log(level, msg)` | Timestamped message to stderr (`"info"`, `"warn"`, `"error"`) |
| `input(prompt)` | Read a line from stdin |

### `state` group

| Function | Returns | Description |
|---|---|---|
| `exists("name")` | bool | True if the variable has been assigned and not deleted |
| `delete("name")` | null | Remove variable from state |

---

## CLI

```
python -m rulix run   <file.rlx> [--state <file>]   # execute
python -m rulix check <file.rlx>                     # syntax check only
python -m rulix dump  <file.rlx> [--state <file>]   # print current state
python -m rulix clear <file.rlx> [--state <file>]   # wipe state file
```

State is saved to `<program>.state` by default. Use `--state` to override.

---

## Embedding

Rulix is designed to be embedded. Use `RulixInterpreter` for full control
and `RulixConfig` to restrict available functions.

### Simple embedding

```python
from rulix import RulixInterpreter, RulixConfig, RulixError

# Sandbox: only type, math, string functions available
config = RulixConfig.sandbox()

# Register a host-provided function
def send_alert(args):
    message = args[0]          # args are plain Python values
    my_notifier.send(message)
    return None

config.register_function("myapp_alert", handler=send_alert, arity=1)

interp = RulixInterpreter(config=config, state_file="monitor.state")
interp.state.set("cpu_usage", get_cpu_usage())
interp.run(open("monitor.rlx").read())

last_alert = interp.state.get("last_alert_time")
```

```rulix
# monitor.rlx
is_null(alerted) => alerted = false

rule high_cpu: cpu_usage > 90, alerted == false => {
    myapp_alert("CPU critical: " + str(cpu_usage))
    alerted = true
}

rule recovered: cpu_usage <= 90, alerted == true => {
    myapp_alert("CPU back to normal")
    alerted = false
}
```

### Group sandboxing

```python
config = RulixConfig()          # all groups on by default
config.disable_group("io")      # no print / log / input
config.disable_group("state")   # no delete / exists
```

**Presets:**

| Preset | Enabled groups |
|---|---|
| `RulixConfig.full()` | `io`, `type`, `math`, `string`, `state` |
| `RulixConfig.sandbox()` | `type`, `math`, `string` |

Calling a function in a disabled group raises `RulixError` at runtime.

### Custom function contract

| Aspect | Rule |
|---|---|
| Argument types | Rulix values arrive as Python natives: `int`, `float`, `str`, `bool`, `None` |
| Return type | Must return `int`, `float`, `str`, `bool`, or `None` |
| Arity | Pass `arity=N` for exact count, `arity=None` for variadic |
| Errors | Raise `RulixError("msg")` to surface a runtime error in the script |
| Name conflicts | Registering a built-in name raises `ValueError` at config time |

### State access from host code

```python
interp.state.set("key", value)   # write before run
interp.state.get("key")          # read after run (None if absent)
interp.state.delete("key")       # remove
interp.state.as_dict()           # snapshot as plain dict
```

### Quick `run()` helper

For one-shot use without persistence:

```python
from rulix import run

state = run("=> x = 1\nx == 1 => y = 2")
print(state)  # {'x': 1, 'y': 2}

# Seed input values
state = run("score > 10 => grade = \"pass\"", state={"score": 15})
```

---

## Project structure

```
rulix/
  __init__.py      Public API: run, RulixInterpreter, RulixConfig, RulixError
  lexer.py         Tokenizer
  parser.py        AST nodes + recursive-descent parser
  interpreter.py   Evaluator, built-in functions, RulixInterpreter, StateView
  config.py        RulixConfig (group sandboxing, custom function registry)
  __main__.py      CLI entry point
examples/
  basic_example.rlx
tests/
  test_basic.py
  test_blocks_labels.py
  test_builtins.py
  test_config.py
  test_custom_functions.py
  test_persistence.py
  test_cli.py
SPEC.md            Full language specification
```

---

## Running the tests

```
pip install pytest
python -m pytest
```
