# SeptaStack — Agent Instructions

## Project Identity
SeptaStack is an experimental programming language and execution stack for a **seven-state (septary) computer architecture**. Research prototype, not production software.

## Research Direction
The strategic goal is to turn SeptaStack into a **parameterized radix research platform** (base-2, base-3, base-7). The research question: "What changes across the full software stack when the target radix changes?" See `memory/research.md` for expert assessment, key references, and experiment design.

## Quick Commands
```bash
source .venv/bin/activate
python -m pytest tests/ -v          # run all 576 tests
septa run examples/hello.septa      # compile and execute
septa compile examples/add.septa    # compile to JSON image
```

## Architecture (DO NOT break this pipeline)
```
Source → Lexer → Parser → Analyzer → IR Lowering → Codegen → Assembler → Image → VM
```
Each stage is in `septa/{stage}/`. Tests in `tests/test_{stage}.py`.

Full pipeline code: see `septa/cli/main.py:_compile()` or `tests/test_vm.py:compile_and_run()`.

## Critical Invariants
1. **_init at address 0** — always: init globals → CALL main → HALT
2. **Static allocation** — all variables in fixed memory slots, no recursion
3. **DATA_BASE = 100** — addresses 0–99 for user store[], 100+ for compiler
4. **R0=return, R1-R3=args, R4-R6=scratch** — register convention
5. **base-7 default** — unprefix literals are base-7, `d:` for decimal
6. **true=6, false=0** — septary truth model
7. **576 tests must pass** — before any commit
8. **No circular imports** — layered architecture, see memory/architecture.md

## Development Rules

### Before Any Code Change
1. Read the relevant module file(s) first
2. Check memory/ for design decisions
3. Write test FIRST (TDD)
4. Run full suite after change

### Adding a New Language Feature
1. Add token(s) to `lexer/tokens.py` + `lexer/lexer.py`
2. Add AST node(s) to `parser/ast.py` + parsing in `parser/parser.py`
3. Add type rules in `semantic/analyzer.py`
4. Add IR op(s) to `ir/ir.py` + lowering in `ir/lowering.py`
5. Add codegen handler in `codegen/codegen.py`
6. Verify assembler handles new opcodes in `asm/`
7. Add VM instruction handler in `vm/instructions.py`
8. Add tests at EACH stage
9. Add example in `examples/`

### Adding a New VM Instruction
1. Add to `VALID_OPCODES` in `asm/parser.py`
2. Add encoding in `asm/assembler.py`
3. Add handler function in `vm/instructions.py` + register in `_DISPATCH`
4. Update `docs/ISA.md`
5. Add unit test in `test_vm.py` and integration test in `test_pipeline.py`

### Adding a CLI Command
1. Add handler function `_cmd_name()` in `cli/main.py`
2. Register in `COMMANDS` dict
3. Update USAGE string
4. Update README.md

## File Size Limits
- Max 500 lines per file
- Current largest: `test_vm.py` (1109 lines — tests OK to be longer)
- If implementation file grows past 500, split by responsibility

## Error Types
Each stage has its own: `LexerError`, `ParserError`, `SemanticError`, `CodegenError`, `AssemblerError`, `VMError`. All inherit `SeptaError`. Always include location when available.

## Dependencies
- **Zero** runtime dependencies (pure Python 3.12+)
- **pytest** for tests only
- Never add external packages to core

## What NOT To Do
- Don't add recursion support without stack frame rework
- Don't change register convention without updating codegen + VM
- Don't modify DATA_BASE without cascading to all tests
- Don't auto-load image "data" into VM memory (it's debug metadata)
- Don't add global state or singletons
- Don't break deterministic compilation (same source = same image)
- Don't claim base-7 is superior to binary — this is a research comparison tool
- Don't call it PL theory without formal semantics

## Radix Parameterization (upcoming)
When implementing Phase 7, all radix-dependent values must come from a single config:
- `BASE`, `WORD_WIDTH`, `MAX_WORD`, `MEMORY_SIZE`, `BOOL_TRUE`
- Currently hardcoded in: `common/base7.py`, `vm/alu.py`, `ir/lowering.py`, `codegen/codegen.py`
- Target: `septa run --base=3 examples/add.septa`
