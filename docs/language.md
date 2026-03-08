# SeptaLang Language Reference

## Program Structure

A SeptaLang program is a sequence of top-level declarations: global variables and functions. Execution begins at `fn main() -> void`.

```
// Global variable
let threshold: word = d:10;

// Function
fn add(a: word, b: word) -> word {
    return a + b;
}

// Entry point (required)
fn main() -> void {
    let result: word = add(3, 4);
    print(result);
}
```

## Types

| Type | Description | Values |
|------|-------------|--------|
| `word` | 12-septit unsigned integer | 0 to 7^12 − 1 |
| `bool7` | Septary boolean | `false` (0) or `true` (6) |
| `addr` | Memory address (alias for `word` in v0.1) | same as `word` |
| `void` | No value | — |

No implicit type conversions. All type rules are strict.

## Numeric Literals

All unprefix literals are **base-7**:

```
0       → zero
6       → six (max septit)
10      → seven (decimal)
16      → thirteen (decimal)
100     → forty-nine (decimal)
d:42    → forty-two (decimal, explicit prefix)
d:0     → zero (decimal)
```

## Boolean Literals

```
true    → 6
false   → 0
```

In conditionals, `0` is false, any nonzero is true.

## Variables

```
let x: word = 10;          // base-7 literal (= decimal 7)
let y: word = d:42;        // decimal literal
let flag: bool7 = true;    // boolean
let ptr: addr = d:50;      // address (alias for word)
```

Variables must be initialized at declaration. No uninitialized variables.

## Operators

### Arithmetic (word × word → word)
| Op | Description |
|----|-------------|
| `+` | Addition (modulo 7^12) |
| `-` | Subtraction (modulo 7^12, wraps on underflow) |

### Unary
| Op | Input | Output | Description |
|----|-------|--------|-------------|
| `-` | word | word | Negation (modulo 7^12) |
| `not` | any non-void | bool7 | Logical NOT |

### Comparison (word × word → bool7)
| Op | Description |
|----|-------------|
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater or equal |
| `<=` | Less or equal |

### Equality (T × T → bool7, T ∈ {word, bool7})
| Op | Description |
|----|-------------|
| `==` | Equal |
| `!=` | Not equal |

### Logical (not yet short-circuit)
| Op | Description |
|----|-------------|
| `and` | Logical AND |
| `or` | Logical OR |

## Control Flow

### If / Else
```
if condition {
    // then branch
}

if condition {
    // then branch
} else {
    // else branch
}
```

Condition: any non-void expression. Zero = false, nonzero = true.

### While Loop
```
while condition {
    // body
}
```

## Functions

```
fn name(param1: type, param2: type) -> return_type {
    // body
    return expr;    // for non-void
}

fn side_effect() -> void {
    // no return needed
}
```

- Max 3 parameters (v0.1 limitation)
- No recursion (v0.1 limitation)
- No nested functions
- No first-class functions

## Built-in Functions

| Function | Argument | Description |
|----------|----------|-------------|
| `print(x)` | `word` | Print value in base-7 |
| `printd(x)` | `word` | Print value in decimal |
| `halt()` | — | Stop VM execution immediately |

## Memory Access

`store[expr]` provides raw memory access to addresses 0–99:

```
store[0] = d:42;                    // write 42 to address 0
let val: word = store[0];           // read from address 0
store[d:10] = store[0] + store[1];  // computed index
```

- Index expression must be `word` type
- Result type is `word`
- Addresses 0–99 are user-accessible
- Addresses 100+ are compiler-managed (do not access directly)

## Comments

```
// Single-line comment
let x: word = 10; // inline comment
```

No block comments.

## Assignment

```
x = x + 1;             // variable assignment
store[0] = d:42;       // memory assignment
```

Cannot assign to function parameters (they are copied to local slots).

## Limitations (v0.1)

- No recursion
- Max 3 function arguments
- No signed arithmetic
- No strings
- No arrays
- No imports/modules
- No error recovery (first error stops compilation)
- No operator overloading
- `and`/`or` evaluate both sides (not short-circuit)
