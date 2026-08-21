#!/usr/bin/env python3
"""Minimized reproducer for DA-SIGMA-0001. Run from the repository root.

It builds one deterministic check — "178530840.00 + 157960871.70 equals
336491711.70" — as a Sigma-Glyph term, twice over, using two encodings of the
same numbers. Nothing here is proposed for adoption; the script exists so the
cost difference and the encoding gap can be observed rather than asserted.
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "impl"))

from sigma_glyph import Store, c1, eval_hash, sha, term_bytes, term_hash  # noqa: E402

FIXTURES = Path(__file__).resolve().parent
LIMITS = {"max_node_depth": 200_000,
          "max_materialized_nodes": 50_000_000,
          "max_store_fetches": 200_000_000}
WIDTH = 36
EXPECTED_BASELINE_HASH = "025e3c7632c633850851dab5d2dfe789217fd640477cc287a3fd8374d87be99b"
EXPECTED_BASELINE_ATP = 61_479

V = lambda name: ("var", name)                       # noqa: E731
L = lambda name, body: ("lam", name, body)           # noqa: E731
A = lambda fn, arg: ("lapp", fn, arg)                # noqa: E731


def put(store, term):
    if term[0] == "thunk":
        return term[1]
    if term[0] == "app":
        put(store, term[1])
        put(store, term[2])
    return store.put(term_bytes(term))


def compile_store(store, lam):
    """Compile a closed lambda term through Profile C1 and store it."""
    return ("thunk", put(store, c1(lam)))


def node(store, fn, *args):
    term = fn
    for arg in args:
        term = ("app", term, arg)
        put(store, term)
        term = ("thunk", term_hash(term))
    return term


def booleans(store):
    true = compile_store(store, L("a", L("b", V("a"))))
    false = compile_store(store, L("a", L("b", V("b"))))
    nand = compile_store(store, L("a", A(A(V("a"), false), true)))
    xor = compile_store(store, L("a", L("b", A(A(V("a"), A(nand, V("b"))), V("b")))))
    conj = compile_store(store, L("a", L("b", A(A(V("a"), V("b")), false))))
    disj = compile_store(store, L("a", L("b", A(A(V("a"), true), V("b")))))
    xnor = compile_store(store, L("a", L("b", A(nand, A(A(xor, V("a")), V("b"))))))
    return {"TRUE": true, "FALSE": false, "NOT": nand, "XOR": xor,
            "AND": conj, "OR": disj, "XNOR": xnor}


def positional_check(store, g, a, b, expected, width=WIDTH):
    """A width-bit ripple-carry adder asserting a + b == expected, no overflow."""
    bit = lambda value: g["TRUE"] if value else g["FALSE"]  # noqa: E731
    carry = g["FALSE"]
    sums = []
    for index in range(width):
        a_i, b_i = bit((a >> index) & 1), bit((b >> index) & 1)
        half = node(store, g["XOR"], a_i, b_i)
        sums.append(node(store, g["XOR"], half, carry))
        carry = node(store, g["OR"],
                     node(store, g["AND"], a_i, b_i),
                     node(store, g["AND"], carry, half))
    acc = node(store, g["NOT"], carry)
    for index in range(width):
        acc = node(store, g["AND"], acc,
                   node(store, g["XNOR"], sums[index], bit((expected >> index) & 1)))
    return acc


def church(n):
    body = V("x")
    for _ in range(n):
        body = A(V("f"), body)
    return L("f", L("x", body))


CHURCH_ADD = L("m", L("n", L("f", L("x", A(A(V("m"), V("f")),
                                           A(A(V("n"), V("f")), V("x")))))))


def church_cost_per_unit(store):
    """Marginal ATP per unit of magnitude for a Church-encoded addition."""
    measured = []
    for a, b in ((100, 100), (200, 200)):
        term = c1(A(A(A(A(CHURCH_ADD, church(a)), church(b)),
                      ("lit", sha(b"I"))), ("lit", sha(b"I"))))
        _, spent = eval_hash(put(store, term), 10_000_000, store)
        measured.append((a + b, spent))
    (n_1, s_1), (n_2, s_2) = measured
    return (s_2 - s_1) / (n_2 - n_1)


def minor_units(value, decimal_places):
    """Parse a decimal amount exactly and reject fractional minor units."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError) as error:
        raise ValueError(f"invalid decimal amount: {value!r}") from error
    scaled = amount * (Decimal(10) ** decimal_places)
    if not scaled.is_finite() or scaled != scaled.to_integral_value():
        raise ValueError(
            f"amount {value!r} is not exact at {decimal_places} decimal places"
        )
    result = int(scaled)
    if result < 0 or result >= 2 ** WIDTH:
        raise ValueError(f"amount {value!r} does not fit unsigned {WIDTH}-bit encoding")
    return result


def main() -> int:
    amounts = json.loads((FIXTURES / "amounts.json").read_text())
    decimal_places = amounts["decimal_places"]
    a = minor_units(amounts["addends"][0]["amount_uah"], decimal_places)
    b = minor_units(amounts["addends"][1]["amount_uah"], decimal_places)
    published = minor_units(amounts["published_sum_uah"], decimal_places)

    store = Store()
    g = booleans(store)
    true_term, _ = eval_hash(g["TRUE"][1], 10_000, store)
    true_hash = term_hash(true_term)

    print(f"addends (minor units): {a:,} + {b:,}")
    print(f"published sum:         {published:,}\n")

    baseline = None
    for label, claimed, expected_true in (
            ("published sum", published, True),
            ("tampered by 1 minor unit", published - 1, False),
            ("tampered by 10 minor units", published + 10, False)):
        term = positional_check(store, g, a, b, claimed)
        result, spent = eval_hash(term[1], 100_000_000, store, limits=LIMITS)
        is_true = term_hash(result) == true_hash
        verdict = "TRUE" if is_true else "not TRUE"
        print(f"positional, {WIDTH}-bit  {label:<26} term={term[1].hex()[:16]}  "
              f"ATP={spent:>8,}  -> {verdict}")
        if is_true != expected_true:
            raise AssertionError(f"{label}: expected {expected_true=}, got {verdict}")
        if label == "published sum":
            if term[1].hex() != EXPECTED_BASELINE_HASH:
                raise AssertionError("published-sum term hash changed")
            if spent != EXPECTED_BASELINE_ATP:
                raise AssertionError(
                    f"published-sum ATP changed: expected {EXPECTED_BASELINE_ATP}, got {spent}"
                )
        baseline = baseline or spent

    per_unit = church_cost_per_unit(Store())
    projected = per_unit * published
    print(f"\nChurch-encoded, same claim: ~{per_unit:.0f} ATP per unit of magnitude "
          f"-> ~{projected:,.0f} ATP")
    print(f"ratio to the positional encoding: {projected / baseline:,.0f}x")
    print("\nBoth encodings are ordinary SKI citizens. Neither is named by the "
          "specification, so two verifiers who encode the same claim independently "
          "get different term hashes.")
    print("DA-SIGMA-0001: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
