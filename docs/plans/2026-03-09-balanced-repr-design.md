# Phase 9: Balanced Representation — Design

## Decision

`--repr=balanced` as a config parameter alongside `--base=N`.
Balanced only for odd bases (3, 5, 7, 9). Even bases → error.

## Value Domain

- Unsigned: `[0, base^w - 1]`
- Balanced: `[-(base^w - 1)/2, +(base^w - 1)/2]`
- Modulus same (`base^w`), difference is range centering

## Arithmetic (balanced mode)

```
half = (modulus - 1) // 2
result = ((raw + half) % modulus) - half
```

CMP: signed comparison (Python int comparison works directly).

## Truth Model

- Unsigned: `true = base - 1`
- Balanced: `true = (base - 1) // 2`

## Balanced Digit Notation

- Base-3: {T, 0, 1} where T = -1 (Knuth convention)
- Base-5: {B, A, 0, 1, 2} where A=-1, B=-2
- Base-7: {C, B, A, 0, 1, 2, 3} where A=-1, B=-2, C=-3
- General odd base: reverse alphabet for negative digits

## Pipeline Impact

| Layer | Changes |
|-------|---------|
| RadixConfig | + `balanced: bool`, new `word_min`/`word_max`, adjusted `bool_true` |
| base7.py | + `format_balanced()`, `parse_balanced()` |
| alu.py | Signed modular arithmetic in balanced mode |
| vm/syscalls.py | `print` uses balanced format |
| vm/memory.py | Accepts negative values in balanced mode |
| cli/main.py | `--repr=unsigned\|balanced` flag |
| bench/runner.py | repr as comparison axis |

Unchanged: Lexer, Parser, Semantic analyzer, IR, Codegen (structure), Assembler.

## Literals

Phase 9: require `d:` prefix for all literals (benchmarks already do this).
Balanced literal syntax is a future extension.

## Expected Paper Results

- instruction_count: IDENTICAL across repr
- steps_executed: IDENTICAL
- memory_used: IDENTICAL
- `printd` output: IDENTICAL (same mathematical value)
- `print` output: DIFFERS (different digit representation)
- `bool_true`: DIFFERS (e.g., 6 vs 3 for base-7)

Conclusion: representation is orthogonal to compilation pipeline.
