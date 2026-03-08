# SeptaStack Architecture

## Pipeline

A SeptaLang program goes through six stages from source to execution:

```
Source (.septa)
  → Lexer        → token stream
  → Parser       → AST (16 node types)
  → Analyzer     → validated AST (types, symbols)
  → IR Lowering  → flat three-address-code IR (24 opcodes)
  → Codegen      → SeptaASM text
  → Assembler    → executable image (JSON)
  → SeptaVM      → execution
```

## Stage Details

### 1. Lexer (`septa/lexer/`)

Converts source text into a stream of tokens. Handles:
- Keywords (`fn`, `let`, `if`, `else`, `while`, `return`, `true`, `false`)
- Types (`word`, `bool7`, `addr`, `void`)
- Numeric literals (base-7 default, `d:` prefix for decimal)
- Operators, delimiters, identifiers
- Single-line comments (`//`)

Every token carries source location (file, line, column) for error reporting.

### 2. Parser (`septa/parser/`)

Recursive descent parser producing an AST with 16 node types:
- Program, Function, Parameter
- Let, Assignment, Return, If, While, ExprStatement
- Binary, Unary, Call, Identifier, Number, Bool
- StoreRead, StoreWrite

### 3. Semantic Analyzer (`septa/semantic/`)

Two-pass analysis:
1. **First pass:** register all function signatures and global variables
2. **Second pass:** type-check expressions, resolve symbols, validate control flow

Type system: `word` (12-septit unsigned), `bool7` (0 or 6), `addr` (alias for `word`), `void`.

### 4. IR Lowering (`septa/ir/`)

Converts AST to flat three-address-code IR. Each IR instruction has an opcode, a destination, and up to two sources. Temporaries are generated for intermediate expression values.

24 IR opcodes cover data movement, arithmetic, comparison, control flow, and system calls.

### 5. Codegen (`septa/codegen/`)

Translates IR to SeptaASM text. Key responsibilities:
- Static memory allocation for all variables and temporaries
- Function prologue (store arguments from R1–R3 to memory slots)
- Comparison materialization (CMP + conditional jump + LI 0/6 pattern)
- Synthetic labels (`_cg0`, `_cg1`, ...) for internal control flow
- `_init` block: initialize globals → CALL main → HALT

Address allocation: `DATA_BASE = 100`, addresses 0–99 reserved for `store[]`.

### 6. Assembler (`septa/asm/`)

Parses SeptaASM text and resolves labels to numeric addresses. Produces an executable image as a JSON dict:

```json
{
  "version": "0.1",
  "entrypoint": 0,
  "code": [["LI", 4, 7], ["CALL", 5], ["HALT"], ...],
  "data": [[100, 42]],
  "symbols": {"_init": 0, "main": 3, ...}
}
```

### 7. SeptaVM (`septa/vm/`)

Stack-based virtual machine emulator:

- **Registers:** R0–R6 (general), PC, SP, IR, FR (flags)
- **Flags:** Z (Zero), G (Greater), L (Less), C (Carry)
- **Memory:** 7^5 = 16,807 words, zero-initialized
- **Stack:** grows downward from top of memory
- **Calling convention:** args in R1–R3, return in R0, CALL pushes PC+1

Execution starts at the image entrypoint (always address 0, the `_init` block).

## Register Usage

| Register | Purpose |
|----------|---------|
| R0 | Return value |
| R1–R3 | Function arguments |
| R4–R6 | Scratch / temporaries |
| PC | Program counter |
| SP | Stack pointer |
| FR | Flags register |

## Memory Layout

```
Address 0–99:       store[] (user-accessible memory)
Address 100+:       compiler-allocated variables and temporaries
Top of memory:      stack (grows downward)
```

## ISA

Full instruction set reference: [ISA.md](ISA.md)

Summary: LI, MOV, LD, ST, LDR, STR, ADD, SUB, CMP, JMP, JZ, JNZ, JG, JL, JGE, JLE, CALL, RET, PRINT, PRINTD, HALT, NOP.
