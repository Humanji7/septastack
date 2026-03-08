# SeptaVM Instruction Set Architecture — v0.1

## Machine Model

- **Word size:** 12 septits (base-7 digits), range 0 to 7^12 - 1
- **Memory:** 7^5 = 16,807 words, flat address space
- **Registers:** R0-R6 (general purpose), PC, SP, IR, FR
- **Flags (FR):** Z (Zero), G (Greater), L (Less), C (Carry)
- **Stack:** grows downward (SP starts at top of memory)

## Calling Convention

| Item | Location |
|------|----------|
| Argument 1 | R1 |
| Argument 2 | R2 |
| Argument 3 | R3 |
| Return value | R0 |
| Return address | pushed by CALL, popped by RET |

## v0.1 Limitations

- **No recursion.** Each function's locals are statically allocated at fixed memory addresses. A recursive call would overwrite the caller's locals.
- **Max 3 arguments** per function call (R1-R3).
- **No dynamic stack frames.** Locals are not stack-allocated; they are compiled into per-function static memory slots.
- **addr = word.** The `addr` type is a semantic alias for `word`. No distinct pointer type exists.

## Storage Model (v0.1)

Locals and temporaries for each function are assigned to **static memory slots** at compile time. Each function gets a contiguous block of memory addresses for its variables. Since recursion is not supported, there is no risk of slot collision.

### store[expr] Mapping

The SeptaLang construct `store[expr]` provides raw memory access:

```
// SeptaLang
let v: word = store[addr_expr];   // read
store[addr_expr] = value;          // write
```

These compile to indirect load/store instructions:

```
; addr_expr result in some register Ra
LDR Rn, [Ra]    ; load: Rn <- memory[Ra]
STR Rn, [Ra]    ; store: memory[Ra] <- Rn
```

The index expression is evaluated into a register, then LDR/STR use that register as an indirect memory address.

## Instructions

### Data Movement

| Opcode | Syntax | Description |
|--------|--------|-------------|
| LI | `LI Rn, imm` | Load immediate: Rn <- imm |
| MOV | `MOV Rn, Rm` | Copy register: Rn <- Rm |
| LD | `LD Rn, [addr]` | Load direct: Rn <- memory[addr] |
| ST | `ST Rn, [addr]` | Store direct: memory[addr] <- Rn |
| LDR | `LDR Rn, [Ra]` | Load indirect: Rn <- memory[Ra] |
| STR | `STR Rn, [Ra]` | Store indirect: memory[Ra] <- Rn |

**LD/ST** use a literal address encoded in the instruction (static).
**LDR/STR** use a register value as the address (dynamic). These are required for `store[expr]` where the index is computed at runtime.

### Arithmetic

| Opcode | Syntax | Description |
|--------|--------|-------------|
| ADD | `ADD Rn, Rm, Rk` | Rn <- Rm + Rk (mod word size, sets flags) |
| SUB | `SUB Rn, Rm, Rk` | Rn <- Rm - Rk (mod word size, sets flags) |

Flags set: Z if result is zero, C on overflow/underflow, G/L from comparison.

### Comparison

| Opcode | Syntax | Description |
|--------|--------|-------------|
| CMP | `CMP Rm, Rk` | Set flags based on Rm - Rk (result discarded) |

### Control Flow

| Opcode | Syntax | Description |
|--------|--------|-------------|
| JMP | `JMP label` | Unconditional jump: PC <- label |
| JZ | `JZ label` | Jump if Z flag set |
| JNZ | `JNZ label` | Jump if Z flag not set |
| JG | `JG label` | Jump if G flag set |
| JL | `JL label` | Jump if L flag set |
| JGE | `JGE label` | Jump if G or Z flag set |
| JLE | `JLE label` | Jump if L or Z flag set |
| CALL | `CALL label` | Push PC+1 to stack, jump to label |
| RET | `RET` | Pop return address from stack, jump to it |

### System

| Opcode | Syntax | Description |
|--------|--------|-------------|
| PRINT | `PRINT Rn` | Print Rn as base-7 |
| PRINTD | `PRINTD Rn` | Print Rn as decimal |
| HALT | `HALT` | Stop execution |
| NOP | `NOP` | No operation |

## Assembly Syntax

```
; comment (semicolon for assembly comments)
label:
    LI R0, 10
    CALL my_func
    HALT

my_func:
    ADD R0, R1, R2
    RET
```

Labels are identifiers followed by a colon. Instructions are indented by convention.
