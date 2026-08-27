#!/usr/bin/env python3
"""Differential bridge for EvalMachine's store-monotonicity theorems.

`evalHash_mono` is a fact about the Lean model. Every other theorem here is tied
to the live oracle by a bridge, and this one needs the same tie, or it is a
statement about a model nobody runs (SECURITY-ASSUMPTIONS SA-2).

The theorem says: extending a store cannot change the answer, except that an
`Unresolved` answer may become something else. Two directions are checked against
`impl/sigma_glyph.py` on every eval vector in the suite:

  GROW    add unrelated valid nodes. A settled answer -- a normal form or an
          exhaustion -- must come back identical, term hash and ATP spent.

  SHRINK  remove one node the evaluation actually demanded. The answer must
          become `Unresolved`, or stay exactly as it was. What it must never do
          is become a *different* settled answer: that would mean availability
          could change a result rather than only withhold one, and the theorem
          would be false of the implementation whatever Lean says about the model.

Shrink is the direction with teeth. Growing a store is the easy case; the claim
that carries weight is that taking bytes away cannot silently rewrite a verdict.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))

import sigma_glyph as sg  # noqa: E402

SUITE = json.loads((ROOT / "tests/spec_conformance/vectors.json").read_text())
UNRESOLVED = sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM,
                                 atom=sg.sha(b"Unresolved Reference")))


# Nodes that belong to no vector. Most vectors are handed the whole suite store,
# so "add unrelated nodes" would otherwise have nothing to add and the grow
# direction would be a check with an empty subject.
STRANGERS = [sg.ser(sg.LITERAL, sg.F_ATOM, atom=sg.sha(f"stranger {n}".encode()))
             for n in range(8)]


def store_from(hex_keys, strangers: bool = False) -> sg.Store:
    store = sg.Store()
    for key in hex_keys:
        store.put(bytes.fromhex(SUITE["objects"][key]))
    if strangers:
        for raw in STRANGERS:
            store.put(raw)
    return store


def outcome(term_hex: str, atp: int, keys, strangers: bool = False) -> tuple[str, int]:
    term, spent = sg.eval_hash(bytes.fromhex(term_hex), atp,
                               store_from(keys, strangers))
    return sg.term_hash(term).hex(), spent


def eval_vectors():
    for vector in SUITE["vectors"]:
        if vector["kind"] != "eval":
            continue
        keys = vector.get("store_subset", list(SUITE["objects"]))
        yield vector["id"], vector["term"], vector["atp"], list(keys)


def main() -> int:
    problems, grown, shrunk = [], 0, 0
    # Nodes to add: everything in the suite's store. For a vector already given
    # the whole store this is a no-op, which is why the shrink direction is where
    # the property is actually exercised.
    everything = list(SUITE["objects"])

    for vid, term, atp, keys in eval_vectors():
        base = outcome(term, atp, keys)

        for label, bigger_keys, strangers in (
                ("the rest of the suite", everything, False),
                ("eight nodes belonging to no vector", keys, True),
                ("both", everything, True)):
            if bigger_keys == keys and not strangers:
                continue
            bigger = outcome(term, atp, bigger_keys, strangers)
            grown += 1
            if base[0] != UNRESOLVED.hex() and bigger != base:
                problems.append(
                    f"{vid}: settled at {base[0][:12]}… spending {base[1]}, and "
                    f"adding {label} changed it to {bigger[0][:12]}… spending "
                    f"{bigger[1]}. Extending a store rewrote an answer")

        for dropped in keys:
            smaller = outcome(term, atp, [k for k in keys if k != dropped])
            shrunk += 1
            if smaller == base:
                continue
            if smaller[0] == UNRESOLVED.hex():
                continue
            problems.append(
                f"{vid}: removing {dropped[:12]}… turned {base[0][:12]}… "
                f"(spent {base[1]}) into a different settled answer "
                f"{smaller[0][:12]}… (spent {smaller[1]}), not into Unresolved. "
                "Availability changed a verdict instead of withholding one")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"STORE-MONO BRIDGE: ALL AGREE ({grown} grown, {shrunk} shrunk over "
          f"{len(list(eval_vectors()))} eval vectors) — no addition changed a "
          "settled answer, and no removal produced a different one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
