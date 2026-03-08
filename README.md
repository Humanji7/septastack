# SeptaStack

An experimental programming language and execution stack for a **seven-state (septary) computer architecture**.

> **Disclaimer:** This is a research prototype exploring how non-binary computing systems could be programmed. It makes no claims of superiority over binary architectures. The goal is to investigate alternative computational models for educational and research purposes.

## Why This Exists

Modern computing is built entirely on binary logic. But is binary the only viable foundation? Ternary computers (like the Soviet Setun) demonstrated that alternative bases are feasible. SeptaStack pushes this idea further — to **base-7** — and asks: what does a complete programming stack look like when every value is a seven-state symbol (septit) instead of a bit?

SeptaStack is a vertical prototype: a high-level language, compiler, assembler, executable image format, and virtual machine — all designed from scratch for septary arithmetic.

## Architecture

```
  SeptaLang source (.septa)
        │
        ▼
  ┌─────────────┐
  │    Lexer     │  tokenization
  ├─────────────┤
  │   Parser     │  recursive descent → AST
  ├─────────────┤
  │  Semantic    │  two-pass type checking & symbol resolution
  │  Analyzer    │
  ├─────────────┤
  │  IR Lowering │  AST → flat three-address-code IR
  ├─────────────┤
  │   Codegen    │  IR → SeptaASM text
  ├─────────────┤
  │  Assembler   │  SeptaASM → executable image (JSON)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │   SeptaVM    │  12-septit virtual machine emulator
  └─────────────┘
```

See [docs/architecture.md](docs/architecture.md) for details.

## Current Status

**MVP complete.** The full pipeline from SeptaLang source to VM execution works end-to-end. The test suite has 576 passing tests covering all layers.

### What Works

- Base-7 numeric literals (with `d:` prefix for decimal)
- Variables (`word`, `bool7`, `addr` types)
- Arithmetic (`+`, `-`), comparisons (`>`, `<`, `>=`, `<=`, `==`, `!=`)
- Boolean logic (`and`, `or`, `not`)
- Control flow (`if`/`else`, `while`)
- Functions with up to 3 parameters and return values
- Direct memory access (`store[expr]`)
- Built-in `print()` (base-7), `printd()` (decimal), `halt()`
- Global variables
- Full instruction set: 24 opcodes
- JSON executable image format
- VM emulator with registers, flags, stack, and syscalls

### Limitations (v0.1)

- No recursion (locals use static memory slots)
- Max 3 function arguments
- No dynamic stack frames
- No signed arithmetic
- No string type
- `addr` is a semantic alias for `word`

## The Septary / Base-7 Idea

A **septit** is the fundamental unit — a symbol with 7 possible states (0–6), analogous to a bit (2 states) or a trit (3 states).

A **machine word** in SeptaVM is **12 septits** wide, giving a value range of 0 to 7<sup>12</sup> − 1 (13,841,287,200 in decimal).

All unprefix numeric literals in SeptaLang are base-7:

```
10      → seven (decimal 7)
16      → thirteen (decimal 13)
100     → forty-nine (decimal 49)
d:42    → forty-two (decimal, explicit prefix)
```

The truth model: `false` = 0, `true` = 6.

## Quick Start

### Requirements

- Python 3.12+
- No external dependencies (only `pytest` for testing)

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run a Program

```bash
septa run examples/hello.septa
# Output: 60

septa run examples/add.septa
# Output:
# 10
# 7
```

### Compile to Image

```bash
septa compile examples/hello.septa -o hello.json
```

### Run Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Example: Functions

```
// functions.septa — Function calls and return values
fn add(a: word, b: word) -> word {
    return a + b;
}

fn main() -> void {
    let result: word = add(3, 4);
    print(result);     // prints 10 (7 in base-7)
    printd(result);    // prints 7
}
```

```bash
$ septa run examples/functions.septa
10
7
```

## Project Structure

```
septastack/
├── septa/
│   ├── common/       base-7 math, errors, source locations
│   ├── lexer/        tokenizer
│   ├── parser/       recursive descent parser, AST nodes
│   ├── semantic/     type checking, symbol resolution
│   ├── ir/           intermediate representation, AST lowering
│   ├── codegen/      IR → assembly emitter
│   ├── asm/          assembler, image builder
│   ├── vm/           virtual machine emulator
│   └── cli/          command-line interface
├── docs/             architecture docs, ISA reference
├── examples/         sample .septa programs
└── tests/            test suite (576 tests)
```

## Documentation

- [Project overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Language reference](docs/language.md)
- [ISA reference](docs/ISA.md)
- [Demo walkthrough](docs/demo.md)

## Roadmap

- [x] MVP — full pipeline from source to VM execution
- [ ] Better CLI UX (REPL, error formatting)
- [ ] Debugger / trace mode
- [ ] Binary image format
- [ ] Recursion / stack frames
- [ ] Stronger type model
- [ ] Optimization passes

## License

[MIT](LICENSE)
