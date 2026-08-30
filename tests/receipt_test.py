#!/usr/bin/env python3
"""Does the receipt answer the question the result hash cannot?

`DISSONANCE(ATP Exhausted)` is an ordinary term. It can sit in a content
environment and evaluate to a normal form, so one `result_hash` means "finished"
or "ran out" depending on how it was reached. Book I 0.6.0 §3.4 says so and
requires an `exit` beside the hash; this checks that the requirement is met and,
more usefully, that the ambiguity it exists for is real.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))

import sigma_glyph as sg  # noqa: E402


def main() -> int:
    problems = []
    store = sg.Store()
    for raw in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
        store.put(raw)
    ik = store.put(sg.ser(sg.APPLY, sg.F_LEFT | sg.F_RIGHT, left=sg.I_H, right=sg.K_H))
    exhausted_term = store.put(sg.ser(sg.DISSONANCE, sg.F_ATOM,
                                      atom=sg.sha(b"ATP Exhausted")))

    settled = sg.eval_receipt(ik, 10, store)
    ran_out = sg.eval_receipt(ik, 1, store)
    stored = sg.eval_receipt(exhausted_term, 10, store)
    missing = sg.eval_receipt(bytes.fromhex("cc" * 32), 10, store)

    # 1. the ambiguity is real, and it is exactly what `exit` resolves
    if stored.result_hash != ran_out.result_hash:
        problems.append("the stored DISSONANCE and the exhaustion no longer share "
                        "a result hash, so this test has stopped testing the "
                        "ambiguity it exists for")
    if stored.exit == ran_out.exit:
        problems.append(f"both reached {stored.exit}; the receipt is not "
                        "distinguishing them")

    # 2. every exit the Book names is reachable and correctly labelled
    for name, receipt, wanted in (("settled", settled, "normal_form"),
                                  ("exhausted", ran_out, "atp_exhausted"),
                                  ("absent", missing, "unresolved_reference")):
        if receipt.exit != wanted:
            problems.append(f"{name}: exit is {receipt.exit}, expected {wanted}")

    # 3. the compatibility profile is the same answer, minus the question
    term, spent = sg.eval_hash(ik, 10, store)
    if (sg.term_hash(term), spent) != (settled.result_hash, settled.atp_spent):
        problems.append("eval_hash and eval_receipt disagree on the same input")
    pair = tuple(sg.eval_receipt(ik, 10, store))
    if len(pair) != 2 or sg.term_hash(pair[0]) != settled.result_hash:
        problems.append("a receipt no longer unpacks as the two-value form, so the "
                        "compatibility profile is not compatible")

    # 4. an exit outside the Book's three is not constructible
    try:
        sg.Receipt(("dis", sg.R_ATP), 0, "gave_up")
        problems.append("a receipt accepted an exit the Book does not name")
    except ValueError:
        pass

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("RECEIPT: all three exits reachable and labelled; a stored "
          "DISSONANCE(ATP Exhausted) and a real exhaustion share one result hash "
          f"({stored.result_hash.hex()[:12]}…) and differ only in exit; the "
          "two-value profile still answers the same, minus the question")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
