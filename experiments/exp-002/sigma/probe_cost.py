#!/usr/bin/env python3
"""Before building a parser in SKI, find out what one pass over the input costs.

The largest fixture the contract allows is 4 KiB. If a single fold over that many
bytes already exceeds K1's 50,000,000 ATP before any parsing logic is attached,
the answer is decided and no amount of construction changes it. So this measures
the floor first: encode bytes, fold over them, and see what a byte costs.

No new primitives: everything is lambda terms through Profile C1, evaluated by
the published Book I evaluator.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "impl"))
from sigma_glyph import Store, c1, eval_hash, term_bytes, term_hash, sha  # noqa: E402

LIMITS = {"max_node_depth": 500_000, "max_materialized_nodes": 200_000_000,
          "max_store_fetches": 500_000_000}
BUDGET = 60_000_000

V = lambda n: ("var", n)                       # noqa: E731
L = lambda n, b: ("lam", n, b)                 # noqa: E731
A = lambda f, a: ("lapp", f, a)                # noqa: E731


def put(store, term):
    if term[0] == "thunk":
        return term[1]
    if term[0] == "app":
        put(store, term[1])
        put(store, term[2])
    return store.put(term_bytes(term))


def compile_store(store, lam):
    return "thunk", put(store, c1(lam))


def node(store, fn, *args):
    term = fn
    for arg in args:
        term = ("app", term, arg)
        put(store, term)
        term = ("thunk", term_hash(term))
    return term


def church_booleans(store):
    true = compile_store(store, L("a", L("b", V("a"))))
    false = compile_store(store, L("a", L("b", V("b"))))
    return true, false


def encode_bytes(store, data: bytes, true, false):
    """A right-fold list of 8-bit values, most significant bit first.

    list = \\c.\\n. c b0 (c b1 (... n)), each byte a \\s. s d7 d6 ... d0.
    """
    tail = compile_store(store, L("c", L("n", V("n"))))
    for value in reversed(data):
        bits = [true if (value >> (7 - i)) & 1 else false for i in range(8)]
        byte = bits[0]
        selector = compile_store(store, L("s", V("s")))
        packed = node(store, selector, *bits) if False else None
        # a byte as a function that hands its eight bits to a consumer
        lam = L("s", V("s"))
        term = compile_store(store, lam)
        byte_term = node(store, term, *bits)
        cons = compile_store(store, L("h", L("t", L("c", L("n",
                    A(A(V("c"), V("h")), A(A(V("t"), V("c")), V("n"))))))))
        tail = node(store, cons, byte_term, tail)
    return tail


def main() -> int:
    for size in (1, 2, 4, 8, 16, 32):
        store = Store()
        true, false = church_booleans(store)
        data = bytes(range(size)) if size <= 256 else bytes(size)
        listed = encode_bytes(store, data, true, false)
        # a bounded accumulator: one boolean, so per-step cost cannot grow with
        # the length already consumed. The step reads the byte's top bit and ANDs
        # it into the accumulator.
        conj = compile_store(store, L("a", L("b", A(A(V("a"), V("b")), false))))
        top_bit = compile_store(store, L("byte", A(V("byte"),
                    L("d7", L("d6", L("d5", L("d4", L("d3", L("d2", L("d1", L("d0",
                        V("d7"))))))))))))
        step = compile_store(store, L("b", L("acc",
                    A(A(conj, V("acc")), A(top_bit, V("b"))))))
        folded = node(store, listed, step, true)
        forced = node(store, folded, ("lit", sha(b"I")), ("lit", sha(b"I")))
        result, spent = eval_hash(forced[1], BUDGET, store, limits=LIMITS)
        print(f"  {size:4} bytes -> {spent:>10,} ATP  ({spent // max(size,1):>7,} per byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
