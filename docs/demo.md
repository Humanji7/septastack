# SeptaStack Demo

Step-by-step walkthrough for a 1–2 minute demo of SeptaStack.

## Setup (one-time)

```bash
git clone <repo-url> && cd septastack
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Demo Script

### 1. Hello World (10 sec)

```bash
cat examples/hello.septa
```

```
// hello.septa — Print a base-7 number
fn main() -> void {
    print(d:42);  // prints 60 (42 in base-7)
}
```

```bash
septa run examples/hello.septa
```

Output: `60` — because 42 in decimal is 60 in base-7 (6×7 + 0).

### 2. Arithmetic (15 sec)

```bash
septa run examples/add.septa
```

Output:
```
10
7
```

`3 + 4 = 7`, but in base-7 that's `10`. The program prints both: `print()` shows base-7, `printd()` shows decimal.

### 3. Control Flow (15 sec)

```bash
septa run examples/while_loop.septa
```

Output:
```
6
5
4
3
2
1
```

A while loop counting down from 6 to 1, printed in base-7.

### 4. Functions (15 sec)

```bash
septa run examples/functions.septa
```

Output:
```
10
7
```

Defines an `add` function, calls it with arguments, prints the result in both bases.

### 5. Memory Access (15 sec)

```bash
septa run examples/memory.septa
```

Output: `300`

Writes `d:100` and `d:200` to memory slots 0 and 1, reads them back, adds, prints decimal.

### 6. Compile to Image (10 sec)

```bash
septa compile examples/hello.septa -o hello.json
cat hello.json
```

Shows the JSON executable image with code, data, and symbol table.

```bash
rm hello.json
```

### 7. Tests (10 sec)

```bash
python -m pytest tests/ -q
```

Shows: `576 passed`.

## Key Talking Points

- All numeric literals are **base-7** by default — `10` means seven
- A machine word is **12 septits** wide (7^12 − 1 max value)
- The full stack is built from scratch: lexer, parser, semantic analysis, IR, codegen, assembler, VM
- No external dependencies — pure Python
- The `store[]` construct provides raw memory access (like pointers, but explicit)
- This is a research prototype — exploring alternative computing models
