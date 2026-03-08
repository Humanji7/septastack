"""SeptaVM executable image format (JSON-based, v0.1).

Image structure:
  {
    "version": "0.1",
    "entrypoint": 0,
    "code": [[opcode, arg1, ...], ...],
    "data": [[addr, value], ...],
    "symbols": {label: instr_index, ...}
  }

'data' contains initial memory state (globals with their values).
'symbols' maps label names to instruction indices for debugging.

Public API:
  build_image(asm_image, ir_program, address_map) -> dict
  save_image(image, path) -> None
  load_image(path) -> dict
"""

from __future__ import annotations

import json
from pathlib import Path

from septa.codegen.addresses import AddressMap
from septa.ir.ir import IRProgram


def build_image(
    asm_image: dict,
    program: IRProgram,
    addrs: AddressMap,
) -> dict:
    """Combine assembled code with data section from globals."""
    data: list[list[int]] = []
    for g in program.globals:
        addr = addrs.global_addrs[g.slot]
        data.append([addr, g.init_value])

    return {
        "version": asm_image["version"],
        "entrypoint": asm_image["entrypoint"],
        "code": asm_image["code"],
        "data": data,
        "symbols": asm_image["symbols"],
    }


def save_image(image: dict, path: str | Path) -> None:
    """Write image to a JSON file."""
    with open(path, "w") as f:
        json.dump(image, f, indent=2)
        f.write("\n")


def load_image(path: str | Path) -> dict:
    """Read image from a JSON file."""
    with open(path) as f:
        return json.load(f)
