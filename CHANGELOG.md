# Changelog

## v0.1.0 — MVP

Initial release. Full pipeline from SeptaLang source to VM execution.

### Compiler
- Lexer with base-7 numeric literals and `d:` decimal prefix
- Recursive descent parser (16 AST node types)
- Two-pass semantic analyzer with type checking
- IR lowering to flat three-address-code (24 opcodes)
- Codegen with static memory allocation
- Assembler with label resolution and JSON image output

### VM
- 12-septit machine word (7^12 − 1 max value)
- 7 general-purpose registers (R0–R6) + PC, SP, FR
- 16,807-word flat memory, zero-initialized
- Downward-growing stack with CALL/RET
- Flags: Z, G, L, C
- Built-in: PRINT (base-7), PRINTD (decimal), HALT

### Language Features
- Types: `word`, `bool7`, `addr`, `void`
- Arithmetic: `+`, `-`
- Comparisons: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Boolean: `and`, `or`, `not`
- Control flow: `if`/`else`, `while`
- Functions with up to 3 parameters
- Global variables
- Direct memory access: `store[expr]`

### Known Limitations
- No recursion (static memory slots)
- Max 3 function arguments
- No signed arithmetic
- No string type
