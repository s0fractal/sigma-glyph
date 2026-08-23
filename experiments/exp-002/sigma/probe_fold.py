#!/usr/bin/env python3
"""Two ways to walk the input, measured. The question is not which is prettier
but whether either is linear: a superlinear pass over 4 KiB decides K1 before any
parsing logic exists."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "impl"))
from sigma_glyph import Store, c1, eval_hash, term_bytes, term_hash, sha  # noqa: E402

LIMITS = {"max_node_depth": 500_000, "max_materialized_nodes": 200_000_000,
          "max_store_fetches": 500_000_000}
BUDGET = 80_000_000
V = lambda n: ("var", n)                       # noqa: E731
L = lambda n, b: ("lam", n, b)                 # noqa: E731
A = lambda f, a: ("lapp", f, a)                # noqa: E731


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


def build(store, data: bytes, style: str):
    true = cs(store, L("a", L("b", V("a"))))
    false = cs(store, L("a", L("b", V("b"))))
    bit = lambda v: true if v else false           # noqa: E731

    if style == "right":
        # list = \c.\n. c b0 (c b1 (... n)); the step folds from the right
        tail = cs(store, L("c", L("n", V("n"))))
        cons = cs(store, L("h", L("t", L("c", L("n",
                A(A(V("c"), V("h")), A(A(V("t"), V("c")), V("n"))))))))
        for value in reversed(data):
            tail = node(store, cons, bit(value & 1), tail)
        conj = cs(store, L("a", L("b", A(A(V("a"), V("b")), false))))
        step = cs(store, L("b", L("acc", A(A(conj, V("acc")), V("b")))))
        return node(store, tail, step, true)

    # style == "cps": the list is a function of (step, accumulator) applied left
    # to right, so the accumulator is threaded rather than nested.
    chain = cs(store, L("f", L("acc", V("acc"))))
    prepend = cs(store, L("h", L("rest", L("f", L("acc",
                A(A(V("rest"), V("f")), A(A(V("f"), V("acc")), V("h"))))))))
    for value in data:
        chain = node(store, prepend, bit(value & 1), chain)
    conj = cs(store, L("a", L("b", A(A(V("a"), V("b")), false))))
    return node(store, chain, conj, true)


def main() -> int:
    for style in ("right", "cps"):
        print(f"{style} fold:")
        previous = None
        for size in (4, 8, 16, 32, 48, 64):
            store = Store()
            term = build(store, bytes([1] * size), style)
            forced = node(store, term, ("lit", sha(b"I")), ("lit", sha(b"I")))
            try:
                _, spent = eval_hash(forced[1], BUDGET, store, limits=LIMITS)
            except Exception as failure:
                print(f"  {size:4} bytes -> {type(failure).__name__}")
                break
            ratio = f"  x{spent/previous:.1f}" if previous else ""
            print(f"  {size:4} bytes -> {spent:>12,} ATP ({spent//size:>8,}/byte){ratio}")
            previous = spent
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
