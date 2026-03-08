"""Deterministic memory-slot address allocator for SeptaLang v0.1.

Assigns concrete memory addresses to all named slots (globals, params,
locals, temps) so that codegen can emit LD/ST with literal addresses.

Layout (low addresses first):
  0..data_base-1  — reserved for user store[] access
  data_base..     — globals (one word each, declaration order)
  after globals   — per-function blocks (params, locals, temps)

Each function gets a contiguous block: params first, then locals, then temps.
Functions are ordered by their position in IRProgram.functions.

No recursion in v0.1, so static allocation is safe.

Public API:
  data_base() -> int   — first compiler-managed address
  allocate(program) -> AddressMap
"""

from __future__ import annotations

from dataclasses import dataclass, field

from septa.common.config import get_config
from septa.ir.ir import IRProgram

# Legacy constant for backward compatibility (base-7 default).
DATA_BASE = 100


def data_base() -> int:
    """First compiler-managed address, after user store[] region.

    For base-7: 100 (addresses 0-99 for store[]).
    For smaller bases: scaled proportionally, minimum 4.
    """
    mem = get_config().memory_size
    if mem >= 200:
        return 100
    return max(4, mem // 4)


@dataclass(slots=True)
class AddressMap:
    """Result of address allocation.

    global_addrs: slot name -> address
    fn_addrs: fn_name -> {slot_name -> address}
    next_free: first address after all allocations
    """
    global_addrs: dict[str, int] = field(default_factory=dict)
    fn_addrs: dict[str, dict[str, int]] = field(default_factory=dict)
    next_free: int = 0

    def addr(self, slot: str, fn_name: str = "") -> int:
        """Look up the address of a slot."""
        if slot.startswith("global:"):
            return self.global_addrs[slot]
        return self.fn_addrs[fn_name][slot]


def allocate(program: IRProgram) -> AddressMap:
    """Assign memory addresses to all slots in the program."""
    base = data_base()
    result = AddressMap(next_free=base)
    cursor = base

    # Globals
    for g in program.globals:
        result.global_addrs[g.slot] = cursor
        cursor += 1

    # Per-function slots
    for fn in program.functions:
        fn_map: dict[str, int] = {}
        for slot in fn.params:
            fn_map[slot] = cursor
            cursor += 1
        for slot in fn.local_slots:
            fn_map[slot] = cursor
            cursor += 1
        for i in range(fn.temp_count):
            fn_map[f"temp:{i}"] = cursor
            cursor += 1
        result.fn_addrs[fn.name] = fn_map

    result.next_free = cursor
    return result
