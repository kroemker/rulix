# Rulix Language Specification

**Version:** 0.1 (Draft)

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

A **statement** is either an expression (typically a function call with a
side effect) or an **assignment**.

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

### 5.3 Multiple Conditions vs. Multiple Statements

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

### 8.1 I/O

| Signature | Description |
|-----------|-------------|
| `print(value, ...)` | Print values to stdout, space-separated, with a trailing newline |
| `input(prompt)` | Read a line from stdin; returns a `string` |
| `log(level, message)` | Write a timestamped message to stderr. `level` is `"info"`, `"warn"`, or `"error"` |

### 8.2 Type Conversion

| Signature | Returns | Description |
|-----------|---------|-------------|
| `str(value)` | `string` | Convert any value to its string representation |
| `int(value)` | `int` | Parse a string or truncate a float to int; error on failure |
| `float(value)` | `float` | Parse a string or widen an int to float; error on failure |
| `bool(value)` | `bool` | Truthiness coercion |
| `type(value)` | `string` | Returns `"int"`, `"float"`, `"bool"`, `"string"`, or `"null"` |

### 8.3 Type Predicates

| Signature | Returns | Description |
|-----------|---------|-------------|
| `is_null(value)` | `bool` | True if the value is `null` |
| `is_int(value)` | `bool` | True if the type is `int` |
| `is_float(value)` | `bool` | True if the type is `float` |
| `is_string(value)` | `bool` | True if the type is `string` |
| `is_bool(value)` | `bool` | True if the type is `bool` |

### 8.4 Math

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

### 8.5 String

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

### 8.6 State Management

| Signature | Description |
|-----------|-------------|
| `delete(name)` | Remove the variable `name` from state (resets it to `null`) |
| `exists(name)` | Returns `true` if `name` has ever been assigned and not deleted |

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
             | '{' NEWLINE { statement NEWLINE } '}' ;

statement    = assignment | expr ;
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

## 14. Design Decisions and Rationale

| Decision | Rationale |
|----------|-----------|
| Pipeline execution (all rules evaluate per run) | Predictable; easy to reason about order of effects. Reactive restart would risk infinite loops. |
| Persistent state by default | Enables Rulix to act as a simple automation engine across repeated invocations (cron jobs, daemons, CI steps). |
| Comma = AND in condition list | Visually distinct from the expression-level `and` operator; makes multi-condition rules scannable. |
| `null` for unset variables (no error) | Avoids boilerplate; pairs naturally with `is_null()` initialization guards. |
| Assignment is a statement, not an expression | Prevents accidental assignment-as-condition bugs (e.g., `x = 5` in a condition silently always firing). |
| No list type in v0.1 | Keeps the parser and interpreter minimal; lists can be added as a v0.2 extension. |
| No user-defined functions in v0.1 | Rules themselves serve as the primary control structure; UDFs add significant complexity. |

---

## 15. Reserved Words

```
rule  true  false  null  and  or  not
```

---

## 16. Future Considerations (v0.2+)

- **List type** with `push`, `pop`, `get`, `len` built-ins
- **Import / include** for splitting large programs across files
- **User-defined functions** (`fn name(args) { ... }`)
- **Scoped state namespaces** to avoid variable collisions in large programs
- **Rule priorities** or explicit ordering overrides
- **Watch mode** (`rulix watch <file.rlx>`) for continuously re-running on a timer
