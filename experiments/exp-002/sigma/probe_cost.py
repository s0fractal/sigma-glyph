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

from probe_lib import (A, L, LIMITS, Store, V, church_booleans, compile_store,
                       eval_hash, forced, node, put, sha)



BUDGET = 60_000_000











def encode_bytes(store, data: bytes, true, false):
    """A right-fold list of 8-bit values, most significant bit first.

    list = \\c.\\n. c b0 (c b1 (... n)), each byte a \\s. s d7 d6 ... d0.
    """
    tail = compile_store(store, L("c", L("n", V("n"))))
    for value in reversed(data):
        bits = [true if (value >> (7 - i)) & 1 else false for i in range(8)]
        # a byte as a function that hands its eight bits to a consumer
        selector = compile_store(store, L("s", V("s")))
        byte_term = node(store, selector, *bits)
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
        _, spent = eval_hash(forced[1], BUDGET, store, limits=LIMITS)
        print(f"  {size:4} bytes -> {spent:>10,} ATP  ({spent // max(size,1):>7,} per byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
