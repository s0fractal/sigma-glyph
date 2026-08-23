#!/usr/bin/env python3
"""A third encoding: a balanced tree instead of a chain.

If the quadratic cost of a list walk comes from re-forcing a deep closure chain,
a balanced tree of depth log2(n) should collapse it. If the tree is quadratic
too, the cost is the evaluator's lack of result sharing rather than my choice of
shape, and no encoding of the input escapes it.
"""
from __future__ import annotations

from probe_lib import (A, L, LIMITS, Store, V, church_booleans, compile_store,
                       eval_hash, forced, node, put, sha)



BUDGET = 80_000_000








def main() -> int:
    print("balanced-tree fold with an associative combiner (AND over one bit):")
    previous = None
    for size in (4, 8, 16, 32, 64, 128, 256):
        store = Store()
        true = compile_store(store, L("a", L("b", V("a"))))
        false = compile_store(store, L("a", L("b", V("b"))))
        conj = compile_store(store, L("a", L("b", A(A(V("a"), V("b")), false))))
        # leaves are the bits themselves; internal nodes combine two subtrees
        level = [true] * size
        while len(level) > 1:
            level = [node(store, conj, level[i], level[i + 1])
                     for i in range(0, len(level) - 1, 2)] + (
                     [level[-1]] if len(level) % 2 else [])
        forced = node(store, level[0], ("lit", sha(b"I")), ("lit", sha(b"I")))
        _, spent = eval_hash(forced[1], BUDGET, store, limits=LIMITS)
        ratio = f"  x{spent/previous:.1f}" if previous else ""
        print(f"  {size:4} leaves -> {spent:>12,} ATP ({spent//size:>7,}/leaf){ratio}")
        previous = spent
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
