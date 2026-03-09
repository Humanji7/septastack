# Phase 9: Balanced Representation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--repr=balanced` flag enabling balanced digit representation for odd radices, so benchmarks can compare unsigned vs balanced across the full stack.

**Architecture:** Add `balanced: bool` to `RadixConfig`, implement `wrap_word()` as the single normalization point, add balanced format/parse to `base7.py`, update ALU/registers/memory to use `wrap_word()`, wire through CLI and bench runner.

**Tech Stack:** Pure Python 3.12+, pytest. Zero new dependencies.

---

### Task 1: RadixConfig — add balanced field and properties

**Files:**
- Modify: `septa/common/config.py`
- Test: `tests/test_base7.py` (add tests at end)

**Step 1: Write failing tests**

Add to `tests/test_base7.py`:

```python
# --- Balanced config tests ---

class TestBalancedConfig:
    def test_balanced_default_false(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.balanced is False

    def test_balanced_true_odd_base(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.balanced is True

    def test_balanced_even_base_raises(self):
        with pytest.raises(ValueError, match="odd base"):
            RadixConfig(base=2, word_width=12, balanced=True)

    def test_word_min_unsigned(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.word_min == 0

    def test_word_max_unsigned(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.word_max == 7**12 - 1

    def test_word_min_balanced(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.word_min == -(7**12 - 1) // 2

    def test_word_max_balanced(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.word_max == (7**12 - 1) // 2

    def test_bool_true_unsigned(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.bool_true == 6

    def test_bool_true_balanced(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.bool_true == 3

    def test_bool_true_balanced_base3(self):
        cfg = RadixConfig(base=3, word_width=12, balanced=True)
        assert cfg.bool_true == 1

    def test_wrap_word_unsigned(self):
        cfg = RadixConfig(base=7, word_width=2)  # modulus=49, range [0,48]
        assert cfg.wrap_word(50) == 1
        assert cfg.wrap_word(-1) == 48
        assert cfg.wrap_word(10) == 10

    def test_wrap_word_balanced(self):
        cfg = RadixConfig(base=7, word_width=2, balanced=True)  # modulus=49, half=24, range [-24,24]
        assert cfg.wrap_word(25) == -24
        assert cfg.wrap_word(-25) == 24
        assert cfg.wrap_word(10) == 10
        assert cfg.wrap_word(-10) == -10

    def test_wrap_word_balanced_base3(self):
        cfg = RadixConfig(base=3, word_width=3, balanced=True)  # modulus=27, half=13, range [-13,13]
        assert cfg.wrap_word(14) == -13
        assert cfg.wrap_word(-14) == 13
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_base7.py::TestBalancedConfig -v`
Expected: FAIL (balanced parameter not accepted)

**Step 3: Implement**

In `septa/common/config.py`, modify `RadixConfig`:

```python
@dataclass(frozen=True, slots=True)
class RadixConfig:
    base: int
    word_width: int
    balanced: bool = False

    def __post_init__(self) -> None:
        if self.base < 2:
            raise ValueError(f"base must be >= 2, got {self.base}")
        if self.word_width < 1:
            raise ValueError(f"word_width must be >= 1, got {self.word_width}")
        if self.balanced and self.base % 2 == 0:
            raise ValueError(f"balanced representation requires odd base, got {self.base}")

    @property
    def word_min(self) -> int:
        if self.balanced:
            return -(self.modulus - 1) // 2
        return 0

    @property
    def word_max(self) -> int:
        if self.balanced:
            return (self.modulus - 1) // 2
        return self.modulus - 1

    # max_word kept for backward compat (unsigned only)
    @property
    def max_word(self) -> int:
        return self.base ** self.word_width - 1

    @property
    def modulus(self) -> int:
        return self.base ** self.word_width

    @property
    def memory_size(self) -> int:
        return self.base ** 5

    @property
    def bool_true(self) -> int:
        if self.balanced:
            return (self.base - 1) // 2
        return self.base - 1

    @property
    def bool_false(self) -> int:
        return 0

    @property
    def max_digit(self) -> str:
        return str(self.base - 1)

    def wrap_word(self, value: int) -> int:
        """Normalize value to word range (unsigned or balanced)."""
        if self.balanced:
            half = (self.modulus - 1) // 2
            return ((value + half) % self.modulus) - half
        return value % self.modulus
```

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_base7.py::TestBalancedConfig -v`
Expected: PASS

**Step 5: Verify existing tests still pass**

Run: `python -m pytest tests/test_base7.py -v`
Expected: all pass (38 old + 14 new)

**Step 6: Commit**

```
git add septa/common/config.py tests/test_base7.py
git commit -m "feat: add balanced repr to RadixConfig with wrap_word()"
```

---

### Task 2: Balanced format and parse in base7.py

**Files:**
- Modify: `septa/common/base7.py`
- Test: `tests/test_base7.py` (add tests)

**Step 1: Write failing tests**

Add to `tests/test_base7.py`:

```python
from septa.common.base7 import format_balanced, parse_balanced

class TestBalancedFormat:
    """Test balanced digit formatting."""

    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=12, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_format_zero(self):
        assert format_balanced(0) == "0"

    def test_format_small_positive(self):
        # 3 is a valid balanced digit for base-7
        assert format_balanced(3) == "3"

    def test_format_needs_carry(self):
        # 5 in balanced base-7: 5 = 1*7 + (-2) → "1B"
        assert format_balanced(5) == "1B"

    def test_format_negative(self):
        # -5 in balanced base-7: -5 = (-1)*7 + 2 → "A2"
        assert format_balanced(-5) == "A2"

    def test_format_negative_one(self):
        # -1 in balanced base-7: just digit A
        assert format_balanced(-1) == "A"

    def test_format_seven(self):
        # 7 = 1*7 + 0 → "10"
        assert format_balanced(7) == "10"

    def test_format_base3(self):
        set_config(RadixConfig(base=3, word_width=12, balanced=True))
        # 5 in balanced base-3: 5 = 2*3 + (-1) → but 2 > 1 (half=1)
        # 5 = 2*3 - 1, 2 > 1 so carry: 5 = (3-1)*3 - 1 → wait
        # 5 / 3 = 1 remainder 2. 2 > 1, so digit = 2-3 = -1 (T), carry = 2
        # 2 / 3 = 0 remainder 2. 2 > 1, so digit = 2-3 = -1 (T), carry = 1
        # 1 / 3 = 0 remainder 1. 1 <= 1, digit = 1
        # Result: "1TT" → 1*9 + (-1)*3 + (-1) = 9 - 3 - 1 = 5 ✓
        assert format_balanced(5) == "1TT"


class TestBalancedParse:
    """Test balanced digit parsing."""

    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=12, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_parse_zero(self):
        assert parse_balanced("0") == 0

    def test_parse_positive_digit(self):
        assert parse_balanced("3") == 3

    def test_parse_with_negative_digit(self):
        # "1B" = 1*7 + (-2) = 5
        assert parse_balanced("1B") == 5

    def test_parse_negative(self):
        # "A2" = (-1)*7 + 2 = -5
        assert parse_balanced("A2") == -5

    def test_parse_base3(self):
        set_config(RadixConfig(base=3, word_width=12, balanced=True))
        # "1TT" = 1*9 + (-1)*3 + (-1) = 5
        assert parse_balanced("1TT") == 5

    def test_roundtrip(self):
        for val in [0, 1, -1, 5, -5, 42, -42, 100, -100]:
            assert parse_balanced(format_balanced(val)) == val
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_base7.py::TestBalancedFormat tests/test_base7.py::TestBalancedParse -v`
Expected: FAIL (functions not defined)

**Step 3: Implement**

Add to `septa/common/base7.py`:

```python
# Balanced digit characters.
# Positive digits: '0', '1', '2', '3' (for base-7)
# Negative digits: 'A' = -1, 'B' = -2, 'C' = -3, 'D' = -4
# Special for base-3: 'T' = -1 (Knuth convention)
_NEG_CHARS = "ABCDEFGHIJ"  # A=-1, B=-2, ..., up to base-21

def _balanced_digit_to_char(d: int, base: int) -> str:
    """Convert a balanced digit integer to its character."""
    if d >= 0:
        return str(d)
    if base == 3 and d == -1:
        return "T"
    return _NEG_CHARS[-d - 1]

def _balanced_char_to_digit(ch: str, base: int) -> int:
    """Convert a balanced digit character to its integer value."""
    if ch.isdigit():
        return int(ch)
    if ch == "T" and base == 3:
        return -1
    idx = _NEG_CHARS.find(ch)
    if idx == -1:
        raise ValueError(f"invalid balanced digit: '{ch}'")
    return -(idx + 1)


def format_balanced(n: int) -> str:
    """Format integer in balanced base-N notation."""
    cfg = get_config()
    base = cfg.base
    half = (base - 1) // 2

    if n == 0:
        return "0"

    negative = n < 0
    if negative:
        n = -n
        # Negate the result at the end by flipping all digits

    digits: list[int] = []
    value = n
    while value != 0:
        remainder = value % base
        if remainder > half:
            remainder -= base
            value = (value - remainder) // base
        else:
            value //= base
        digits.append(remainder)

    if negative:
        digits = [-d for d in digits]

    return "".join(
        _balanced_digit_to_char(d, base) for d in reversed(digits)
    )


def parse_balanced(s: str) -> int:
    """Parse a balanced base-N digit string to a Python int."""
    cfg = get_config()
    if not s:
        raise ValueError(f"empty balanced base-{cfg.base} literal")

    result = 0
    for ch in s:
        d = _balanced_char_to_digit(ch, cfg.base)
        result = result * cfg.base + d

    if result < cfg.word_min or result > cfg.word_max:
        raise ValueError(
            f"balanced base-{cfg.base} literal '{s}' out of word range "
            f"[{cfg.word_min}, {cfg.word_max}]"
        )
    return result
```

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_base7.py::TestBalancedFormat tests/test_base7.py::TestBalancedParse -v`
Expected: PASS

**Step 5: Commit**

```
git add septa/common/base7.py tests/test_base7.py
git commit -m "feat: add balanced format/parse for base-N digits"
```

---

### Task 3: ALU — balanced arithmetic

**Files:**
- Modify: `septa/vm/alu.py`
- Test: `tests/test_vm.py` (add tests at end)

**Step 1: Write failing tests**

Add to `tests/test_vm.py`:

```python
class TestBalancedALU:
    """ALU in balanced representation mode."""

    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=2, balanced=True))
        # modulus=49, half=24, range [-24, 24]

    def teardown_method(self):
        reset_config()

    def test_add_positive(self):
        result, z = alu_add(3, 4)
        assert result == 7
        assert z is False

    def test_add_wrap_positive(self):
        # 20 + 20 = 40, but 40 > 24, so wrap: 40 - 49 = -9
        result, _ = alu_add(20, 20)
        assert result == -9

    def test_sub_negative_result(self):
        result, _ = alu_sub(3, 5)
        assert result == -2

    def test_sub_wrap_negative(self):
        # -20 - 20 = -40, but -40 < -24, so wrap: -40 + 49 = 9
        result, _ = alu_sub(-20, 20)
        assert result == 9

    def test_add_zero(self):
        result, z = alu_add(5, -5)
        assert result == 0
        assert z is True

    def test_cmp_signed(self):
        # -2 < 5 in signed comparison
        z, g, l = alu_cmp(-2, 5)
        assert z is False
        assert g is False
        assert l is True
```

**Step 2: Run to verify fail**

Run: `python -m pytest tests/test_vm.py::TestBalancedALU -v`
Expected: FAIL (balanced wrapping not implemented in ALU)

**Step 3: Implement**

In `septa/vm/alu.py`, replace modular arithmetic with `wrap_word()`:

```python
def alu_add(a: int, b: int) -> tuple[int, bool]:
    result = get_config().wrap_word(a + b)
    return result, result == 0

def alu_sub(a: int, b: int) -> tuple[int, bool]:
    result = get_config().wrap_word(a - b)
    return result, result == 0

def alu_cmp(a: int, b: int) -> tuple[bool, bool, bool]:
    return a == b, a > b, a < b
```

Note: `alu_cmp` uses Python int comparison, which is signed — correct for both modes.

**Step 4: Run tests**

Run: `python -m pytest tests/test_vm.py::TestBalancedALU -v`
Expected: PASS

**Step 5: Verify all old tests still pass**

Run: `python -m pytest tests/ -v --tb=short -q`
Expected: all 615 pass

**Step 6: Commit**

```
git add septa/vm/alu.py tests/test_vm.py
git commit -m "feat: ALU uses wrap_word() for balanced arithmetic"
```

---

### Task 4: Registers and Memory — balanced wrapping

**Files:**
- Modify: `septa/vm/registers.py`
- Modify: `septa/vm/memory.py`
- Test: `tests/test_vm.py` (add tests)

**Step 1: Write failing tests**

Add to `tests/test_vm.py`:

```python
class TestBalancedRegistersAndMemory:
    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=2, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_register_stores_negative(self):
        regs = Registers()
        regs.set(0, -5)
        assert regs.get(0) == -5

    def test_register_wraps_balanced(self):
        regs = Registers()
        regs.set(0, 25)  # > 24 (half), should wrap to -24
        assert regs.get(0) == -24

    def test_memory_stores_negative(self):
        mem = Memory()
        mem.store(0, -5)
        assert mem.load(0) == -5

    def test_memory_wraps_balanced(self):
        mem = Memory()
        mem.store(0, 25)
        assert mem.load(0) == -24
```

**Step 2: Run to verify fail**

Run: `python -m pytest tests/test_vm.py::TestBalancedRegistersAndMemory -v`
Expected: FAIL

**Step 3: Implement**

In `septa/vm/registers.py`, change `set()`:

```python
def set(self, idx: int, value: int) -> None:
    self.gp[idx] = get_config().wrap_word(value)
```

In `septa/vm/memory.py`, change `store()`:

```python
def store(self, addr: int, value: int) -> None:
    if addr < 0 or addr >= len(self._data):
        raise VMError(f"memory write out of bounds: {addr}")
    self._data[addr] = get_config().wrap_word(value)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_vm.py::TestBalancedRegistersAndMemory -v`
Expected: PASS

**Step 5: Verify all tests**

Run: `python -m pytest tests/ -q`
Expected: all 615+ pass

**Step 6: Commit**

```
git add septa/vm/registers.py septa/vm/memory.py tests/test_vm.py
git commit -m "feat: registers and memory use wrap_word() for balanced mode"
```

---

### Task 5: Syscalls — balanced print output

**Files:**
- Modify: `septa/vm/syscalls.py`
- Test: `tests/test_vm.py` (add test)

**Step 1: Write failing test**

Add to `tests/test_vm.py`:

```python
class TestBalancedSyscalls:
    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=12, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_print_balanced_format(self):
        sys_ = Syscalls()
        sys_.print_base7(5)
        # 5 in balanced base-7 = "1B" (1*7 + (-2) = 5)
        assert sys_.output == ["1B"]

    def test_printd_unchanged(self):
        sys_ = Syscalls()
        sys_.print_decimal(5)
        assert sys_.output == ["5"]

    def test_print_negative_balanced(self):
        sys_ = Syscalls()
        sys_.print_base7(-5)
        assert sys_.output == ["A2"]
```

**Step 2: Run to verify fail**

Run: `python -m pytest tests/test_vm.py::TestBalancedSyscalls -v`
Expected: FAIL

**Step 3: Implement**

In `septa/vm/syscalls.py`:

```python
from septa.common.base7 import format_base_n, format_balanced
from septa.common.config import get_config

# In print_base7:
def print_base7(self, value: int) -> None:
    if get_config().balanced:
        self._output.append(format_balanced(value))
    else:
        self._output.append(format_base_n(value))
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_vm.py::TestBalancedSyscalls -v`
Expected: PASS

**Step 5: Commit**

```
git add septa/vm/syscalls.py tests/test_vm.py
git commit -m "feat: print syscall uses balanced format in balanced mode"
```

---

### Task 6: validate_word — balanced range

**Files:**
- Modify: `septa/common/base7.py`
- Test: `tests/test_base7.py` (add tests)

**Step 1: Write failing tests**

```python
class TestBalancedValidation:
    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=2, balanced=True))
        # range [-24, 24]

    def teardown_method(self):
        reset_config()

    def test_validate_word_positive(self):
        assert validate_word(24) == 24

    def test_validate_word_negative(self):
        assert validate_word(-24) == -24

    def test_validate_word_zero(self):
        assert validate_word(0) == 0

    def test_validate_word_overflow(self):
        with pytest.raises(ValueError):
            validate_word(25)

    def test_validate_word_underflow(self):
        with pytest.raises(ValueError):
            validate_word(-25)
```

**Step 2: Implement**

In `septa/common/base7.py`, update `validate_word()`:

```python
def validate_word(n: int) -> int:
    cfg = get_config()
    if n < cfg.word_min or n > cfg.word_max:
        raise ValueError(
            f"value {n} out of word range [{cfg.word_min}, {cfg.word_max}]"
        )
    return n
```

**Step 3: Run tests, commit**

```
git add septa/common/base7.py tests/test_base7.py
git commit -m "feat: validate_word uses balanced range when balanced=True"
```

---

### Task 7: CLI — --repr flag

**Files:**
- Modify: `septa/cli/main.py`
- Test: manual CLI test (no pytest needed — CLI tested via integration)

**Step 1: Implement**

In `septa/cli/main.py`, update `_parse_global_opts()`:

```python
def _parse_global_opts(argv: list[str]) -> tuple[list[str], int, bool]:
    """Extract --base=N and --repr=balanced from argv."""
    base = 7
    balanced = False
    remaining = []
    for arg in argv:
        if arg.startswith("--base="):
            # ... existing ...
        elif arg.startswith("--repr="):
            repr_val = arg.split("=", 1)[1]
            if repr_val == "balanced":
                balanced = True
            elif repr_val == "unsigned":
                balanced = False
            else:
                print(f"Error: invalid repr: {repr_val} (use unsigned or balanced)", file=sys.stderr)
                sys.exit(1)
        else:
            remaining.append(arg)
    return remaining, base, balanced
```

Update `_apply_config()`:

```python
def _apply_config(base: int, balanced: bool = False) -> None:
    from septa.common.config import RadixConfig, set_config
    set_config(RadixConfig(base=base, word_width=12, balanced=balanced))
```

Update `main()` to pass balanced through.

Update USAGE string to document `--repr=`.

**Step 2: Test manually**

```bash
septa --base=7 --repr=balanced run examples/add.septa
septa --base=3 --repr=balanced run examples/add.septa
septa --base=2 --repr=balanced run examples/add.septa  # should error
```

**Step 3: Commit**

```
git add septa/cli/main.py
git commit -m "feat: add --repr=unsigned|balanced CLI flag"
```

---

### Task 8: Bench runner — repr dimension

**Files:**
- Modify: `septa/bench/runner.py`
- Modify: `tests/test_bench.py`

**Step 1: Write failing tests**

Add to `tests/test_bench.py`:

```python
def test_runner_with_repr():
    """Runner handles repr parameter."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[7],
        reprs=["unsigned", "balanced"],
    )
    assert len(results) == 2
    reprs_seen = {r["repr"] for r in results}
    assert reprs_seen == {"unsigned", "balanced"}
    # printd output should be identical
    outputs = {r["repr"]: r["output"] for r in results}
    assert outputs["unsigned"] == outputs["balanced"]


def test_runner_balanced_only_odd():
    """Runner skips balanced for even bases."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[2, 3],
        reprs=["unsigned", "balanced"],
    )
    # base=2 unsigned + base=3 unsigned + base=3 balanced = 3
    assert len(results) == 3


def test_bench_cross_repr_printd_identical():
    """Same program produces identical printd output in unsigned vs balanced."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "accumulator.septa"],
        bases=[7],
        reprs=["unsigned", "balanced"],
    )
    outputs = {r["repr"]: r["output"] for r in results}
    assert outputs["unsigned"] == outputs["balanced"]
```

**Step 2: Implement**

In `septa/bench/runner.py`:
- Add `reprs` parameter to `run_benchmarks()` (default `["unsigned"]`)
- For each (program, base, repr): set config with balanced flag, compile, run
- Skip balanced for even bases
- Add `repr` key to result dicts
- Update `format_table()` to show repr column

**Step 3: Run tests, commit**

```
git add septa/bench/runner.py tests/test_bench.py
git commit -m "feat: bench runner supports repr dimension for balanced comparison"
```

---

### Task 9: Integration — run full benchmark suite

**Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all 615 + ~30 new = ~645+ pass

**Step 2: Run bench with balanced**

```bash
septa bench --bases=3,7 --repr=unsigned,balanced
```

Verify: printd output identical, instruction_count identical, memory_used identical.

**Step 3: Commit if any fixes needed, then final commit**

```
git add -A
git commit -m "feat: Phase 9 complete — balanced representation for odd radices"
git push origin main
```

---

### Task 10: Update memory and roadmap

**Files:**
- Modify: `memory/MEMORY.md` — update test count, add bench repr info
- Modify: `memory/roadmap.md` — mark Phase 9 done
- Modify: `memory/decisions.md` — add balanced repr decision

**Step 1: Update all memory files**

**Step 2: Commit**

```
git add memory/
git commit -m "docs: update memory files for Phase 9"
```
