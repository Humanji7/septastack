# SeptaStack Overview

SeptaStack is an experimental programming language and execution stack built for a hypothetical **seven-state (septary) computer architecture**. Instead of binary bits, the fundamental unit is a **septit** — a symbol with 7 possible states (0–6).

## What Is It?

A complete vertical prototype:

| Layer | Component | Role |
|-------|-----------|------|
| 1 | **SeptaLang** | High-level language with functions, variables, control flow |
| 2 | **IR** | Flat three-address-code intermediate representation |
| 3 | **Codegen + Assembler** | IR → assembly text → executable image |
| 4 | **SeptaVM** | 12-septit virtual machine emulator |

## Why Base-7?

Binary dominates modern computing, but it is not the only option. Ternary computers existed (the Soviet Setun, 1958). SeptaStack explores a less studied base — **7** — to investigate:

- How numeric literals and arithmetic change in a non-binary system
- What a type system looks like when "true" is 6 instead of 1
- How compilation and code generation adapt to a different word size
- What assembly and machine code feel like for a septary machine

This is a research prototype. It does not claim septary computing is better than binary.

## Key Design Choices

- **12-septit word:** value range 0 to 7^12 − 1 (≈13.8 billion)
- **Memory:** 7^5 = 16,807 words flat address space
- **Static allocation:** variables compiled to fixed memory slots (no recursion)
- **Truth model:** false = 0, true = 6
- **All literals are base-7** unless prefixed with `d:` for decimal

## Status

MVP complete. The full pipeline works end-to-end with 576 passing tests.

See [architecture.md](architecture.md) for technical details.
