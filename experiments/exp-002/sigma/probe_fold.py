#!/usr/bin/env python3
"""Two ways to walk the input, measured. The question is not which is prettier
but whether either is linear: a superlinear pass over 4 KiB decides K1 before any
parsing logic exists."""
from __future__ import annotations

from probe_lib import (A, L, LIMITS, Store, V, church_booleans, compile_store,
                       eval_hash, forced, node, put, sha)



BUDGET = 80_000_000








def build(store, data: bytes, style: str):
    true = compile_store(store, L("a", L("b", V("a"))))
    false = compile_store(store, L("a", L("b", V("b"))))
    bit = lambda v: true if v else false           # noqa: E731

    if style == "right":
        # list = \c.\n. c b0 (c b1 (... n)); the step folds from the right
        tail = compile_store(store, L("c", L("n", V("n"))))
        cons = compile_store(store, L("h", L("t", L("c", L("n",
                A(A(V("c"), V("h")), A(A(V("t"), V("c")), V("n"))))))))
        for value in reversed(data):
            tail = node(store, cons, bit(value & 1), tail)
        conj = compile_store(store, L("a", L("b", A(A(V("a"), V("b")), false))))
        step = compile_store(store, L("b", L("acc", A(A(conj, V("acc")), V("b")))))
        return node(store, tail, step, true)

    # style == "cps": the list is a function of (step, accumulator) applied left
    # to right, so the accumulator is threaded rather than nested.
    chain = compile_store(store, L("f", L("acc", V("acc"))))
    prepend = compile_store(store, L("h", L("rest", L("f", L("acc",
                A(A(V("rest"), V("f")), A(A(V("f"), V("acc")), V("h"))))))))
    for value in data:
        chain = node(store, prepend, bit(value & 1), chain)
    conj = compile_store(store, L("a", L("b", A(A(V("a"), V("b")), false))))
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
