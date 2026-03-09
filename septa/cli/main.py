"""CLI entry point for SeptaStack toolchain.

Commands:
  run      <file.septa>                 — compile and execute
  compile  <file.septa> -o <file.json>  — compile to image (JSON)
  bench    [--bases=2,3,7,10] [--repr=unsigned,balanced] [files]
                                        — run benchmarks across bases/reprs
  version                               — show version

Options:
  --base=N           Set radix (default: 7). Supported: 2-10.
  --repr=MODE        Set representation (default: unsigned). Modes: unsigned, balanced.
"""

import json
import sys
from pathlib import Path


def _parse_global_opts(argv: list[str]) -> tuple[list[str], int, bool]:
    """Extract --base=N and --repr=balanced from argv. Returns (remaining_args, base, balanced)."""
    base = 7
    balanced = False
    remaining = []
    for arg in argv:
        if arg.startswith("--base="):
            try:
                base = int(arg.split("=", 1)[1])
            except ValueError:
                print(f"Error: invalid base: {arg}", file=sys.stderr)
                sys.exit(1)
            if base < 2 or base > 10:
                print(f"Error: base must be 2-10, got {base}", file=sys.stderr)
                sys.exit(1)
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


def _apply_config(base: int, balanced: bool = False) -> None:
    """Set active radix configuration."""
    from septa.common.config import RadixConfig, set_config
    set_config(RadixConfig(base=base, word_width=12, balanced=balanced))


def _read_source(path: str) -> str:
    """Read source file, fail fast on errors."""
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    if p.suffix != ".septa":
        print(f"Error: expected .septa file, got: {path}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def _compile(source: str, filename: str) -> dict:
    """Full pipeline: source -> tokens -> AST -> IR -> asm -> image."""
    from septa.asm.assembler import assemble
    from septa.asm.image import build_image
    from septa.asm.parser import parse_asm
    from septa.codegen.addresses import allocate
    from septa.codegen.codegen import generate
    from septa.ir.lowering import lower
    from septa.lexer.lexer import Lexer
    from septa.parser.parser import Parser
    from septa.semantic.analyzer import analyze

    tokens = Lexer(source, filename).tokenize()
    program = Parser(tokens).parse()
    analyze(program)
    ir = lower(program)
    asm_text = generate(ir)
    asm_lines = parse_asm(asm_text, filename.replace(".septa", ".sasm"))
    asm_image = assemble(asm_lines)
    addrs = allocate(ir)
    return build_image(asm_image, ir, addrs)


def _cmd_run(args: list[str]) -> None:
    if not args:
        print("Usage: septa run <file.septa>", file=sys.stderr)
        sys.exit(1)
    source = _read_source(args[0])
    image = _compile(source, args[0])

    from septa.vm.machine import Machine

    vm = Machine(image)
    output = vm.run()
    for line in output:
        print(line)


def _cmd_compile(args: list[str]) -> None:
    if not args:
        print("Usage: septa compile <file.septa> [-o <file.json>]", file=sys.stderr)
        sys.exit(1)
    source = _read_source(args[0])
    image = _compile(source, args[0])

    out_path = None
    if "-o" in args:
        idx = args.index("-o")
        if idx + 1 < len(args):
            out_path = args[idx + 1]

    if out_path:
        Path(out_path).write_text(
            json.dumps(image, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Image written to {out_path}")
    else:
        print(json.dumps(image, indent=2))


def _cmd_bench(args: list[str]) -> None:
    """Run benchmarks across multiple bases/reprs and print comparison table."""
    from septa.bench.runner import format_table, run_benchmarks

    # Parse --bases=2,3,7,10 and --repr=unsigned,balanced
    bases = [2, 3, 7, 10]
    reprs = ["unsigned"]
    programs = []
    for arg in args:
        if arg.startswith("--bases="):
            bases = [int(b) for b in arg.split("=", 1)[1].split(",")]
        elif arg.startswith("--repr="):
            reprs = arg.split("=", 1)[1].split(",")
            for r in reprs:
                if r not in ("unsigned", "balanced"):
                    print(f"Error: invalid repr: {r} (use unsigned or balanced)", file=sys.stderr)
                    sys.exit(1)
        else:
            programs.append(Path(arg))

    # Default: all .septa files in benchmarks/
    if not programs:
        bench_dir = Path(__file__).parent.parent.parent / "benchmarks"
        programs = sorted(bench_dir.glob("*.septa"))
        if not programs:
            print("Error: no benchmark files found", file=sys.stderr)
            sys.exit(1)

    results = run_benchmarks(programs, bases, reprs=reprs)

    # Verify output consistency across bases
    by_prog: dict[str, dict[int, list[str]]] = {}
    for r in results:
        by_prog.setdefault(r["program"], {})[r["base"]] = r["output"]
    for prog, outputs in by_prog.items():
        vals = list(outputs.values())
        if any(v != vals[0] for v in vals[1:]):
            print(
                f"Warning: {prog} output differs across bases: {outputs}",
                file=sys.stderr,
            )

    print(format_table(results, bases))


COMMANDS = {
    "run": _cmd_run,
    "compile": _cmd_compile,
    "bench": _cmd_bench,
}

USAGE = """\
SeptaStack v0.1 — multi-radix programming toolkit

Usage: septa <command> [options] [args]

Commands:
  run      <file.septa>                 Compile and execute
  compile  <file.septa> [-o <file.json>] Compile to image (JSON)
  bench    [--bases=2,3,7,10] [--repr=unsigned,balanced] [files]
                                        Run benchmarks across bases/reprs
  version                               Show version

Options:
  --base=N           Set radix (default: 7). Supported: 2-10.
  --repr=MODE        Set representation (default: unsigned). Modes: unsigned, balanced.

Examples:
  septa run examples/add.septa                        Base-7 unsigned (default)
  septa --base=3 run examples/add.septa               Base-3 (ternary)
  septa --base=7 --repr=balanced run examples/add.septa  Base-7 balanced
"""


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    args, base, balanced = _parse_global_opts(sys.argv[1:])
    _apply_config(base, balanced)

    if not args:
        print(USAGE)
        sys.exit(0)

    command = args[0]

    if command in ("version", "--version", "-v"):
        print("SeptaStack v0.1.0")
        sys.exit(0)

    if command in ("help", "--help", "-h"):
        print(USAGE)
        sys.exit(0)

    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Error: unknown command '{command}'", file=sys.stderr)
        print("Run 'septa --help' for usage.", file=sys.stderr)
        sys.exit(1)

    handler(args[1:])


if __name__ == "__main__":
    main()
