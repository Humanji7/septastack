"""Tests for the benchmark suite and runner.

Verifies:
  - Each benchmark compiles and runs in base-7 (default)
  - Each benchmark produces identical printd output across bases 2, 3, 7
  - The runner collects all expected metrics
  - Correctness: known expected values for each benchmark
"""

from pathlib import Path

import pytest

from septa.common.config import RadixConfig, reset_config, set_config

BENCHMARKS_DIR = Path(__file__).parent.parent / "benchmarks"

# Expected printd output for each benchmark
EXPECTED_OUTPUT = {
    "arith_chain": ["130"],
    "countdown": ["0"],
    "nested_if": ["3"],
    "fn_calls": ["12"],
    "gcd": ["6"],
    "memory_walk": ["100"],
    "accumulator": ["1275"],
    "bool_logic": ["4"],
}

BENCHMARK_FILES = sorted(BENCHMARKS_DIR.glob("*.septa"))
BENCHMARK_NAMES = [f.stem for f in BENCHMARK_FILES]


def _compile_and_run(source: str, filename: str = "bench.septa") -> dict:
    """Compile and run, returning (image, machine) for metric extraction."""
    from septa.asm.assembler import assemble
    from septa.asm.image import build_image
    from septa.asm.parser import parse_asm
    from septa.codegen.addresses import allocate
    from septa.codegen.codegen import generate
    from septa.ir.lowering import lower
    from septa.lexer.lexer import Lexer
    from septa.parser.parser import Parser
    from septa.semantic.analyzer import analyze
    from septa.vm.machine import Machine

    tokens = Lexer(source, filename).tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    ir = lower(program)
    asm_text = generate(ir)
    asm_lines = parse_asm(asm_text, filename.replace(".septa", ".sasm"))
    asm_image = assemble(asm_lines)
    addrs = allocate(ir)
    image = build_image(asm_image, ir, addrs)
    vm = Machine(image)
    output = vm.run()
    return {
        "output": output,
        "instruction_count": len(image["code"]),
        "steps_executed": vm.steps,
        "memory_used": addrs.next_free,
    }


# --- Test: all benchmark files exist ---


def test_all_benchmark_files_exist():
    for name in EXPECTED_OUTPUT:
        path = BENCHMARKS_DIR / f"{name}.septa"
        assert path.exists(), f"Missing benchmark file: {path}"


def test_benchmark_count():
    assert len(BENCHMARK_FILES) == 8


# --- Test: each benchmark compiles and runs in base-7 ---


@pytest.fixture(autouse=True)
def _reset_radix():
    """Reset config to base-7 after each test."""
    yield
    reset_config()


@pytest.mark.parametrize("septa_file", BENCHMARK_FILES, ids=BENCHMARK_NAMES)
def test_benchmark_runs_base7(septa_file):
    """Each benchmark compiles and runs without error in base-7."""
    reset_config()  # base-7 default
    source = septa_file.read_text(encoding="utf-8")
    result = _compile_and_run(source, septa_file.name)
    assert isinstance(result["output"], list)


# --- Test: correctness of each benchmark ---


@pytest.mark.parametrize("septa_file", BENCHMARK_FILES, ids=BENCHMARK_NAMES)
def test_benchmark_correctness(septa_file):
    """Each benchmark produces the expected printd output."""
    reset_config()
    source = septa_file.read_text(encoding="utf-8")
    result = _compile_and_run(source, septa_file.name)
    expected = EXPECTED_OUTPUT[septa_file.stem]
    assert result["output"] == expected, (
        f"{septa_file.stem}: expected {expected}, got {result['output']}"
    )


# --- Test: cross-base output consistency ---


CROSS_BASES = [2, 3, 7]


@pytest.mark.parametrize("septa_file", BENCHMARK_FILES, ids=BENCHMARK_NAMES)
def test_benchmark_cross_base_output(septa_file):
    """Same printd output regardless of base."""
    source = septa_file.read_text(encoding="utf-8")
    outputs = {}
    for base in CROSS_BASES:
        set_config(RadixConfig(base=base, word_width=12))
        result = _compile_and_run(source, septa_file.name)
        outputs[base] = result["output"]
    # All bases should produce same output
    first = outputs[CROSS_BASES[0]]
    for base in CROSS_BASES[1:]:
        assert outputs[base] == first, (
            f"{septa_file.stem}: base-{base} output {outputs[base]} "
            f"!= base-{CROSS_BASES[0]} output {first}"
        )


# --- Test: runner collects all metrics ---


@pytest.mark.parametrize("septa_file", BENCHMARK_FILES, ids=BENCHMARK_NAMES)
def test_metrics_collected(septa_file):
    """Runner returns all expected metric keys with positive values."""
    reset_config()
    source = septa_file.read_text(encoding="utf-8")
    result = _compile_and_run(source, septa_file.name)
    for key in ("instruction_count", "steps_executed", "memory_used"):
        assert key in result, f"Missing metric: {key}"
        assert result[key] > 0, f"Metric {key} should be > 0"


# --- Test: runner module API ---


def test_runner_run_benchmarks():
    """Runner.run_benchmarks() returns structured results."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[7],
    )
    assert len(results) == 1
    r = results[0]
    assert r["program"] == "arith_chain"
    assert r["base"] == 7
    assert r["output"] == ["130"]
    assert r["instruction_count"] > 0
    assert r["steps_executed"] > 0
    assert r["memory_used"] > 0


def test_runner_multiple_bases():
    """Runner handles multiple bases correctly."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[2, 3, 7],
    )
    assert len(results) == 3
    bases_seen = {r["base"] for r in results}
    assert bases_seen == {2, 3, 7}
    # printd output should be same across bases
    outputs = {r["base"]: r["output"] for r in results}
    assert outputs[2] == outputs[3] == outputs[7]


def test_runner_multiple_programs():
    """Runner handles multiple programs correctly."""
    from septa.bench.runner import run_benchmarks

    programs = [
        BENCHMARKS_DIR / "arith_chain.septa",
        BENCHMARKS_DIR / "countdown.septa",
    ]
    results = run_benchmarks(programs=programs, bases=[7])
    assert len(results) == 2
    names = {r["program"] for r in results}
    assert names == {"arith_chain", "countdown"}


def test_runner_output_verification():
    """Runner detects output mismatch across bases (sanity check)."""
    from septa.bench.runner import run_benchmarks

    # All benchmarks should have consistent output across bases
    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "accumulator.septa"],
        bases=[2, 7],
    )
    outputs = [r["output"] for r in results]
    assert outputs[0] == outputs[1]


# --- Test: format_table ---


def test_format_table():
    """format_table produces readable output."""
    from septa.bench.runner import format_table, run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[2, 7],
    )
    table = format_table(results, bases=[2, 7])
    assert "arith_chain" in table
    assert "base=2" in table
    assert "base=7" in table
    assert "instruction" in table.lower() or "instructions" in table.lower()


# --- Test: repr dimension ---


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


def test_bench_instruction_count_identical_across_repr():
    """Instruction count identical between unsigned and balanced (same codegen)."""
    from septa.bench.runner import run_benchmarks

    results = run_benchmarks(
        programs=[BENCHMARKS_DIR / "arith_chain.septa"],
        bases=[7],
        reprs=["unsigned", "balanced"],
    )
    by_repr = {r["repr"]: r for r in results}
    assert by_repr["unsigned"]["instruction_count"] == by_repr["balanced"]["instruction_count"]
    assert by_repr["unsigned"]["steps_executed"] == by_repr["balanced"]["steps_executed"]
    assert by_repr["unsigned"]["memory_used"] == by_repr["balanced"]["memory_used"]
