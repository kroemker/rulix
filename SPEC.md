# Rulix Language Specification

**Version:** 0.2 (Draft)

---

## 1. Overview

Rulix is a rule-based interpreted language. A Rulix program is a sequence of
**rules**. Each time the interpreter runs, it evaluates every rule in
declaration order. A rule fires when all of its conditions are true, executing
its body statements. Multiple rules can fire in a single run (**pipeline
model**).

State is **persistent**: variables written in one run are available in the
next run. This makes Rulix naturally suited for tasks like monitoring,
automation pipelines, and incremental computation.

Rulix is designed to be **embedded**. Host applications can restrict which
built-in function groups are available (sandboxing) and can register their own
functions that Rulix scripts call like any built-in.

---

## 2. Program Structure

```
program ::= item*
item    ::= rule | comment | blank_line
```

A Rulix source file (`.rlx`) contains zero or more rules and comments.
Rules are evaluated strictly top-to-bottom on every interpreter invocation.

---

## 3. Rules

### 3.1 Syntax

```
rule         ::= rule_header? conditions '=>' body
rule_header  ::= 'rule' IDENTIFIER ':'
conditions   ::= condition (',' condition)*
             |   (empty — always fires)
body         ::= statement
             |   '{' statement+ '}'
```

### 3.2 Anatomy

```
rule greet: name != null => print("Hello, " + name)
```

| Part | Description |
|------|-------------|
| `rule greet:` | Optional label. Purely documentary; has no runtime effect. |
| `name != null` | Condition list. All conditions must be true for the rule to fire. |
| `=>` | Separates conditions from the body. |
| `print(...)` | Body — one or more statements. |

### 3.3 Always-Firing Rules

A rule with no conditions fires on every run:

```
=> print("This always runs")
```

### 3.4 Multi-Statement Body

Wrap multiple statements in `{ }`. Each statement occupies its own line.

```
rule reset: counter >= 10 => {
    counter = 0
    print("Counter reset")
}
```

### 3.5 Execution Model

1. The interpreter reads all rules from the source file.
2. Rules are evaluated in declaration order.
3. For each rule: evaluate the condition list.
   - If **all** conditions are truthy → execute the body, then move to the
     next rule.
   - If **any** condition is falsy → skip the body, move to the next rule.
4. After all rules have been evaluated, the run ends and state is persisted.

Rules do **not** restart the evaluation cycle when they fire (that is the
reactive/Rete model). Each rule fires at most once per run.

---

## 4. Expressions

Both conditions and statement values are expressions. Expressions are
evaluated to produce a typed value.

### 4.1 Operator Precedence (high → low)

| Level | Operators | Associativity |
|-------|-----------|---------------|
| 1 | function call `f(...)`, grouping `( )` | — |
| 2 | unary `-`, `not` | right |
| 3 | `*`, `/`, `%` | left |
| 4 | `+`, `-` | left |
| 5 | `==`, `!=`, `<`, `>`, `<=`, `>=` | left (non-chaining) |
| 6 | `and` | left |
| 7 | `or` | left |

### 4.2 Arithmetic Operators

| Operator | Description |
|----------|-------------|
| `+` | Addition (numbers) or concatenation (strings) |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Division (always produces a float) |
| `%` | Modulo (integers only) |

### 4.3 Comparison Operators

Comparisons always return a `bool`. Comparing values of incompatible types
is a runtime error (e.g., `"a" < 3`).

| Operator | Description |
|----------|-------------|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### 4.4 Boolean Operators

| Operator | Description |
|----------|-------------|
| `and` | Logical AND (short-circuit) |
| `or` | Logical OR (short-circuit) |
| `not` | Logical NOT |

---

## 5. Statements

A **statement** is one of: an **assignment**, a **control-flow keyword**
(`disable`, `stop`), or an **expression** (typically a function call with a
side effect).

### 5.1 Assignment

```
assignment ::= IDENTIFIER '=' expression
```

Assignment creates or updates a variable in the persistent state store.
Assignment is a statement; it cannot appear inside a larger expression.

```
counter = counter + 1
name = "Alice"
```

### 5.2 Expression Statements

Any expression can appear as a statement. The return value is discarded.
This is primarily useful for function calls with side effects.

```
print("hello")
log("info", "run complete")
```

### 5.3 Control-flow Statements

Two keyword statements control execution flow from inside a rule body:

#### `disable`

Marks the **current rule** as disabled in the persistent state. The rule
will not fire again in any future run. Execution of the current body
continues normally after `disable`.

```rulix
rule init: is_null(ready) => {
    ready = true
    disable          # will never fire again
}
```

The disabled flag is stored in state as `_rulix_disabled_<identity>`, where
identity is the rule's label (if it has one) or its 0-based position index.
A rule can be re-enabled from host code by deleting that state key.

#### `stop`

Immediately ends the **current evaluation cycle**. No further statements in
the current body execute, and no subsequent rules are evaluated this run.
The next run starts normally from rule 1.

```rulix
rule guard: error_count > 10 => {
    log("error", "too many errors")
    stop             # nothing after this runs this cycle
}
```

Both keywords can be combined. Order matters: `disable` before `stop` disables
the rule *and* stops the cycle; `stop` before `disable` stops immediately
without ever reaching `disable`.

```rulix
rule once_and_stop: => {
    setup = true
    disable          # won't fire again
    stop             # nothing after this rule runs this cycle
}
```

### 5.4 Multiple Conditions vs. Multiple Statements

- **Conditions** are separated by commas (`,`) and implicitly ANDed.
- **Statements** are separated by newlines inside `{ }`.

```
# Two conditions (both must be true)
x > 0, y > 0 => print("both positive")

# One condition, two statements
x > 0 => {
    print("x is positive")
    last_positive = x
}
```

---

## 6. Data Types

| Type | Literals | Notes |
|------|----------|-------|
| `int` | `0`, `42`, `-7` | Arbitrary precision integers |
| `float` | `3.14`, `-0.5`, `1.0` | 64-bit IEEE 754 |
| `bool` | `true`, `false` | |
| `string` | `"hello"`, `"line\none"` | UTF-8, double-quoted; supports `\n`, `\t`, `\\`, `\"` |
| `null` | `null` | Represents absence of a value |

### 6.1 Type Coercion Rules

Rulix is **dynamically typed** with minimal implicit coercion:

- In a boolean context (condition, `not`, `and`, `or`): `null` and `false`
  are falsy; everything else is truthy.
- `int + float` → `float` (int is widened).
- All other mixed-type operations are runtime errors.

---

## 7. Variables and State

### 7.1 Scope

All variables are **global**. There is no local scope, no closures, and no
block scope.

### 7.2 Initialization

A variable that has never been assigned evaluates to `null`. Use the built-in
`is_null(x)` to test for this before using a variable for the first time.

```
# Typical initialization pattern
is_null(counter) => counter = 0
```

### 7.3 Persistence

After each run, all variables are written to a **state file**. On the next
run, the state file is loaded before any rules are evaluated.

- Default state file: `<program-name>.state` (JSON) in the working directory.
- Override with the `--state` CLI flag.
- Use `rulix clear <file.rlx>` to wipe the state file.

Variable names are case-sensitive identifiers: `[a-zA-Z_][a-zA-Z0-9_]*`.

---

## 8. Built-in Functions

Every built-in function belongs to exactly one **group**. When Rulix is
embedded, the host can enable or disable groups individually (see
[Section 17](#17-embedding-and-extension)). If a script calls a function
whose group is disabled, a runtime error is raised:

```
RuntimeError: function 'print' is not available (group 'io' is disabled)
```

The five built-in groups are:

| Group | Description |
|-------|-------------|
| `io` | Standard input/output and logging |
| `type` | Type conversion and type predicates |
| `math` | Numeric operations |
| `string` | String manipulation |
| `state` | Variable inspection and deletion |

All groups are **enabled by default** in the standalone CLI. Embedding hosts
choose which groups to permit.

### 8.1 Group: `io`

| Signature | Description |
|-----------|-------------|
| `print(value, ...)` | Print values to stdout, space-separated, with a trailing newline |
| `input(prompt)` | Read a line from stdin; returns a `string` |
| `log(level, message)` | Write a timestamped message to stderr. `level` is `"info"`, `"warn"`, or `"error"` |

### 8.2 Group: `type`

**Conversion:**

| Signature | Returns | Description |
|-----------|---------|-------------|
| `str(value)` | `string` | Convert any value to its string representation |
| `int(value)` | `int` | Parse a string or truncate a float to int; error on failure |
| `float(value)` | `float` | Parse a string or widen an int to float; error on failure |
| `bool(value)` | `bool` | Truthiness coercion |
| `type(value)` | `string` | Returns `"int"`, `"float"`, `"bool"`, `"string"`, or `"null"` |

**Predicates:**

| Signature | Returns | Description |
|-----------|---------|-------------|
| `is_null(value)` | `bool` | True if the value is `null` |
| `is_int(value)` | `bool` | True if the type is `int` |
| `is_float(value)` | `bool` | True if the type is `float` |
| `is_string(value)` | `bool` | True if the type is `string` |
| `is_bool(value)` | `bool` | True if the type is `bool` |

### 8.3 Group: `math`

| Signature | Returns | Description |
|-----------|---------|-------------|
| `abs(n)` | same as input | Absolute value |
| `min(a, b)` | same as input | Minimum of two numbers |
| `max(a, b)` | same as input | Maximum of two numbers |
| `floor(n)` | `int` | Round down |
| `ceil(n)` | `int` | Round up |
| `round(n)` | `int` | Round to nearest integer |
| `pow(base, exp)` | `float` | Exponentiation |
| `sqrt(n)` | `float` | Square root |

### 8.4 Group: `string`

| Signature | Returns | Description |
|-----------|---------|-------------|
| `len(s)` | `int` | Length of string in characters |
| `upper(s)` | `string` | Uppercase |
| `lower(s)` | `string` | Lowercase |
| `trim(s)` | `string` | Strip leading/trailing whitespace |
| `contains(s, sub)` | `bool` | Substring test |
| `starts_with(s, prefix)` | `bool` | Prefix test |
| `ends_with(s, suffix)` | `bool` | Suffix test |
| `replace(s, old, new)` | `string` | Replace first occurrence |
| `split(s, sep)` | `string` | Not in v0.1 — deferred until lists are added |

### 8.5 Group: `state`

| Signature | Returns | Description |
|-----------|---------|-------------|
| `delete(name)` | `null` | Remove the variable `name` from state (resets it to `null`) |
| `exists(name)` | `bool` | Returns `true` if `name` has ever been assigned and not deleted |

---

## 9. Comments

Lines beginning with `#` (after optional whitespace) are comments and are
ignored by the interpreter. Inline comments (end-of-line `#`) are also
supported.

```
# This is a full-line comment
x = 1  # This is an inline comment
```

---

## 10. Formal Grammar (EBNF)

```ebnf
program      = { item } ;
item         = rule | comment | NEWLINE ;

comment      = '#' { any_char_except_newline } NEWLINE ;

rule         = [ rule_label ] condition_list '=>' body NEWLINE ;
rule_label   = 'rule' IDENTIFIER ':' ;

condition_list = [ condition { ',' condition } ] ;
condition    = expr ;

body         = statement
             | '{' [ NEWLINE ] { statement NEWLINE } '}' ;

statement    = assignment | 'disable' | 'stop' | expr ;
assignment   = IDENTIFIER '=' expr ;

expr         = or_expr ;
or_expr      = and_expr { 'or' and_expr } ;
and_expr     = not_expr { 'and' not_expr } ;
not_expr     = 'not' not_expr | compare_expr ;
compare_expr = add_expr [ ( '==' | '!=' | '<' | '>' | '<=' | '>=' ) add_expr ] ;
add_expr     = mul_expr { ( '+' | '-' ) mul_expr } ;
mul_expr     = unary_expr { ( '*' | '/' | '%' ) unary_expr } ;
unary_expr   = '-' unary_expr | primary ;

primary      = IDENTIFIER '(' [ arg_list ] ')'   (* function call *)
             | IDENTIFIER                          (* variable read *)
             | literal
             | '(' expr ')' ;

arg_list     = expr { ',' expr } ;

literal      = INTEGER | FLOAT | STRING | 'true' | 'false' | 'null' ;

IDENTIFIER   = ( LETTER | '_' ) { LETTER | DIGIT | '_' } ;
INTEGER      = [ '-' ] DIGIT { DIGIT } ;
FLOAT        = [ '-' ] DIGIT { DIGIT } '.' DIGIT { DIGIT } ;
STRING       = '"' { string_char } '"' ;
```

---

## 11. Error Handling

| Error Class | Behavior |
|-------------|----------|
| **Syntax error** | The interpreter reports the line number and halts before executing any rules. |
| **Type error** | The interpreter halts with a message (e.g., `cannot add int and string`). |
| **Runtime error in condition** | The entire rule is skipped and a warning is emitted to stderr. |
| **Runtime error in body** | The interpreter halts with a message and line number. |
| **Undefined variable** | Not an error — evaluates to `null`. |
| **Unknown function** | Runtime error; interpreter halts. |

---

## 12. CLI Interface

```
rulix run <file.rlx> [--state <state-file>]   # Execute the program
rulix clear <file.rlx>                         # Wipe the state file
rulix check <file.rlx>                         # Syntax-check without running
rulix dump <file.rlx>                          # Print current state variables
```

---

## 13. Example Programs

### 13.1 Run Counter

```rulix
# Initialize on first run
is_null(runs) => runs = 0

# Increment every run
=> runs = runs + 1

# Report
=> print("This program has run " + str(runs) + " time(s).")
```

### 13.2 Threshold Alert

```rulix
# Seed value from outside (e.g., set by another tool writing to state)
is_null(temperature) => temperature = 0

rule too_hot:  temperature > 80 => print("WARNING: temperature is " + str(temperature))
rule too_cold: temperature < 10 => print("WARNING: temperature is " + str(temperature))
rule normal:   temperature >= 10, temperature <= 80 => print("Temperature OK: " + str(temperature))
```

### 13.3 Simple Accumulator with Reset

```rulix
is_null(total) => total = 0
is_null(runs)  => runs  = 0

=> {
    total = total + 1
    runs  = runs + 1
}

rule report: runs % 5 == 0 => {
    print("Every 5th run. Total so far: " + str(total))
}

rule milestone: total == 100 => {
    print("Reached 100! Resetting.")
    total = 0
}
```

---

## 14. Embedding and Extension

This section defines how a host application written in Python embeds Rulix,
configures sandbox restrictions, and registers custom functions.

### 14.1 Configuration Object

All embedding is done through a `RulixConfig` object that is passed to the
interpreter at construction time.

```python
from rulix import RulixInterpreter, RulixConfig

config = RulixConfig()
interpreter = RulixInterpreter(config)
interpreter.run("program.rlx")
```

`RulixConfig` with no arguments produces the same behavior as the standalone
CLI: all built-in groups enabled, no custom functions.

### 14.2 Group-Based Sandboxing

The host enables or disables built-in function groups individually. Calling a
function in a disabled group is a **runtime error** in the Rulix script.

```python
config = RulixConfig()
config.disable_group("io")     # no print / input / log
config.disable_group("state")  # no delete / exists
```

Or start from a **preset** and selectively re-enable:

```python
# Sandbox preset: only type, math, string are on; io and state are off
config = RulixConfig.sandbox()
config.enable_group("io")      # add back I/O if needed
```

**Named presets:**

| Preset | Enabled groups |
|--------|----------------|
| `RulixConfig.full()` | `io`, `type`, `math`, `string`, `state` (default) |
| `RulixConfig.sandbox()` | `type`, `math`, `string` |

Individual `enable_group` / `disable_group` calls work on top of any preset.
Calling either method with an unknown group name raises a `ValueError` at
configuration time (not at runtime), so misconfiguration is caught early.

### 14.3 Custom Functions

Host applications register Python callables as Rulix functions. Once
registered, they are called from Rulix scripts exactly like built-ins.

#### Registration

```python
def fetch_temperature(args):
    # args: list of Python-native values (int, float, str, bool, None)
    sensor_id = args[0]          # already a Python str/int/etc.
    return get_sensor_reading(sensor_id)   # return a Python-native value

config.register_function(
    name     = "fetch_temperature",
    handler  = fetch_temperature,
    arity    = 1,               # exact argument count; None = variadic
)
```

Usage in a Rulix script:

```rulix
is_null(temp) => temp = 0
=> temp = fetch_temperature("sensor_a")
temp > 80 => log("warn", "High temperature: " + str(temp))
```

#### Contract

| Aspect | Specification |
|--------|---------------|
| **Argument types** | The interpreter converts Rulix values to Python-native types before calling the handler: `int` → `int`, `float` → `float`, `string` → `str`, `bool` → `bool`, `null` → `None`. |
| **Return type** | The handler must return a Python `int`, `float`, `str`, `bool`, or `None`. These are mapped back to the corresponding Rulix types. Returning any other Python type is an error. |
| **Arity** | If `arity` is an integer and the script passes a different number of arguments, the interpreter raises a runtime error before calling the handler. Pass `arity=None` to accept any number of arguments. |
| **Errors** | The handler may raise `RulixError(message)` to produce a Rulix runtime error. Any other exception propagates as an unhandled Python exception and terminates the interpreter. |
| **Side effects** | Handlers may have arbitrary side effects in the host application. Rulix makes no attempt to sandbox or roll back their effects. |
| **Name conflicts** | Registering a name that matches a built-in function raises a `ValueError` at registration time. Built-in names cannot be overridden. |
| **Naming** | Custom function names must be valid Rulix identifiers (`[a-zA-Z_][a-zA-Z0-9_]*`) and must not be reserved words. |

#### Recommended Naming Convention

To avoid future conflicts as the built-in library grows, custom functions
should use a project-specific prefix separated by an underscore:

```
myapp_send_alert(message)
myapp_get_sensor(id)
```

### 14.4 State Access from the Host

The host can read and write the Rulix state store directly, outside of a
running script. This is useful for seeding input values before a run or
reading output values after one.

```python
interpreter.state.set("temperature", 72)
interpreter.run("monitor.rlx")
result = interpreter.state.get("last_alert")   # None if unset
```

The state store uses the same persistence mechanism as normal runs: after
`run()` completes, the state is written to the configured state file.

### 14.5 Full Embedding Example

```python
from rulix import RulixInterpreter, RulixConfig, RulixError

def send_alert(args):
    message = args[0]
    my_notification_service.send(message)
    return None   # void return

config = RulixConfig.sandbox()             # no I/O or state-mutation builtins
config.enable_group("io")                  # allow print for debugging
config.register_function(
    name    = "myapp_alert",
    handler = send_alert,
    arity   = 1,
)

interpreter = RulixInterpreter(config, state_file="monitor.state")
interpreter.state.set("cpu_usage", get_cpu_usage())
interpreter.run("monitor.rlx")
```

```rulix
# monitor.rlx
is_null(alert_sent) => alert_sent = false

rule high_cpu: cpu_usage > 90, alert_sent == false => {
    myapp_alert("CPU usage critical: " + str(cpu_usage))
    alert_sent = true
}

rule recovered: cpu_usage <= 90, alert_sent == true => {
    myapp_alert("CPU usage back to normal")
    alert_sent = false
}
```

---

## 15. Design Decisions and Rationale

| Decision | Rationale |
|----------|-----------|
| Pipeline execution (all rules evaluate per run) | Predictable; easy to reason about order of effects. Reactive restart would risk infinite loops. |
| Persistent state by default | Enables Rulix to act as a simple automation engine across repeated invocations (cron jobs, daemons, CI steps). |
| Comma = AND in condition list | Visually distinct from the expression-level `and` operator; makes multi-condition rules scannable. |
| `null` for unset variables (no error) | Avoids boilerplate; pairs naturally with `is_null()` initialization guards. |
| Assignment is a statement, not an expression | Prevents accidental assignment-as-condition bugs (e.g., `x = 5` in a condition silently always firing). |
| No list type in v0.1 | Keeps the parser and interpreter minimal; lists can be added as a v0.2 extension. |
| No user-defined functions in v0.1 | Rules themselves serve as the primary control structure; UDFs add significant complexity. |
| Built-ins organized into groups, not individually toggled | Group-level control is simple to configure and reason about; individual function toggling adds overhead with little practical benefit. |
| Custom functions use plain identifiers, not `namespace.fn()` | Avoids a grammar change; a naming convention (prefix) is sufficient for the common embedded use case. Dot notation can be added later. |
| Built-in names cannot be overridden by custom functions | Prevents scripts from being surprised by host-injected behavior shadowing known functions. |
| Configuration errors (bad group names, name conflicts) fail at setup time | Early detection keeps runtime behavior predictable; the host knows its mistakes before any script runs. |

---

## 16. Reserved Words

```
rule  true  false  null  and  or  not  disable  stop
```

---

## 17. Future Considerations (v0.2+)

- **List type** with `push`, `pop`, `get`, `len` built-ins
- **Import / include** for splitting large programs across files
- **User-defined functions** (`fn name(args) { ... }`)
- **Scoped state namespaces** to avoid variable collisions in large programs
- **Rule priorities** or explicit ordering overrides
- **Watch mode** (`rulix watch <file.rlx>`) for continuously re-running on a timer
- **Dot-notation namespaces** for custom functions (`myapp.alert(msg)`) to remove the need for prefix conventions
- **Custom groups** so host applications can group their own registered functions and expose them as a toggleable unit
- **Async handlers** for custom functions that perform I/O without blocking the interpreter
