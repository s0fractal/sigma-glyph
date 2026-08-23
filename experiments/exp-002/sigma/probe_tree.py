#!/usr/bin/env python3
"""A third encoding: a balanced tree instead of a chain.

If the quadratic cost of a list walk comes from re-forcing a deep closure chain,
a balanced tree of depth log2(n) should collapse it. If the tree is quadratic
too, the cost is the evaluator's lack of result sharing rather than my choice of
shape, and no encoding of the input escapes it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "impl"))
from sigma_glyph import Store, c1, eval_hash, term_bytes, term_hash, sha  # noqa: E402

LIMITS = {"max_node_depth": 500_000, "max_materialized_nodes": 200_000_000,
          "max_store_fetches": 500_000_000}
BUDGET = 80_000_000
V = lambda n: ("var", n)                        # noqa: E731
L = lambda n, b: ("lam", n, b)                  # noqa: E731
A = lambda f, a: ("lapp", f, a)                 # noqa: E731


def put(store, term):
    if term[0] == "thunk":
        return term[1]
    if term[0] == "app":
        put(store, term[1]); put(store, term[2])
    return store.put(term_bytes(term))


def cs(store, lam):
    return "thunk", put(store, c1(lam))


def node(store, fn, *args):
    term = fn
    for arg in args:
        term = ("app", term, arg); put(store, term); term = ("thunk", term_hash(term))
    return term


def main() -> int:
    print("balanced-tree fold with an associative combiner (AND over one bit):")
    previous = None
    for size in (4, 8, 16, 32, 64, 128, 256):
        store = Store()
        true = cs(store, L("a", L("b", V("a"))))
        false = cs(store, L("a", L("b", V("b"))))
        conj = cs(store, L("a", L("b", A(A(V("a"), V("b")), false))))
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
