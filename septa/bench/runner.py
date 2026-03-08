"""Benchmark runner for cross-radix comparison.

Compiles and runs SeptaLang programs across multiple bases,
collecting metrics for comparative analysis.

Public API:
  run_benchmarks(programs, bases) -> list[dict]
  format_table(results, bases) -> str
"""

from __future__ import annotations

from pathlib import Path

from septa.common.config import RadixConfig, reset_config, set_config


def _compile_and_measure(source: str, filename: str) -> dict:
    """Compile and run a program, returning metrics."""
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
        "instruction_count": len(image["code"]),
        "steps_executed": vm.steps,
        "memory_used": addrs.next_free,
        "output": output,
    }


def run_benchmarks(
    programs: list[Path],
    bases: list[int] | None = None,
) -> list[dict]:
    """Run benchmark programs across specified bases.

    Returns a list of result dicts, one per (program, base) pair:
      {program, base, instruction_count, steps_executed, memory_used, output}
    """
    if bases is None:
        bases = [2, 3, 7, 10]

    results: list[dict] = []
    for prog_path in programs:
        source = prog_path.read_text(encoding="utf-8")
        name = prog_path.stem
        for base in bases:
            set_config(RadixConfig(base=base, word_width=12))
            metrics = _compile_and_measure(source, prog_path.name)
            results.append({
                "program": name,
                "base": base,
                **metrics,
            })
    reset_config()
    return results


METRICS = ["instructions", "steps_executed", "memory_used"]

# Map display name -> result dict key
_METRIC_KEY = {
    "instructions": "instruction_count",
    "steps_executed": "steps_executed",
    "memory_used": "memory_used",
}


def format_table(results: list[dict], bases: list[int]) -> str:
    """Format benchmark results as a comparative table."""
    # Group by (program, metric)
    by_prog: dict[str, dict[int, dict]] = {}
    for r in results:
        by_prog.setdefault(r["program"], {})[r["base"]] = r

    # Column widths
    prog_w = max(len("Program"), max(len(p) for p in by_prog))
    metric_w = max(len("Metric"), max(len(m) for m in METRICS))
    base_cols = {b: max(len(f"base={b}"), 7) for b in bases}

    # Header
    header = f"{'Program':<{prog_w}} | {'Metric':<{metric_w}}"
    for b in bases:
        header += f" | {'base=' + str(b):>{base_cols[b]}}"
    sep = "-" * prog_w + "-+-" + "-" * metric_w
    for b in bases:
        sep += "-+-" + "-" * base_cols[b]

    lines = [header, sep]

    for prog_name in sorted(by_prog):
        base_data = by_prog[prog_name]
        for metric in METRICS:
            key = _METRIC_KEY[metric]
            row = f"{prog_name:<{prog_w}} | {metric:<{metric_w}}"
            for b in bases:
                val = base_data.get(b, {}).get(key, "")
                row += f" | {val:>{base_cols[b]}}"
            lines.append(row)

    return "\n".join(lines)
