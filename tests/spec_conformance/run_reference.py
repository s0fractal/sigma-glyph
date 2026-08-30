#!/usr/bin/env python3
"""Run vectors.json against the reference implementation.

This is both (a) the self-check that vectors.json matches the oracle, and
(b) executable documentation of runner semantics for other-language
implementations: preload `objects` into your CAS, then replay `vectors`.

    python3 tests/spec_conformance/run_reference.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

# An optional path so a control can hand this runner a deliberately broken
# suite without copying the runner somewhere its imports no longer resolve.
suite_path = (Path(sys.argv[1]) if len(sys.argv) > 1
              else Path(__file__).resolve().parent / "vectors.json")
doc = json.loads(suite_path.read_text())

store = sg.Store()
for h_hex, b_hex in doc["objects"].items():
    b = bytes.fromhex(b_hex)
    assert sg.node_hash(b).hex() == h_hex, f"CAS key mismatch for {h_hex}"
    store.put(b)

ok = []


INVALID_OBJECT_HASH = sg.term_hash(("dis", sg.R_INVALID)).hex()


def classify(receipt):
    """The suite's classification, derived from the receipt and the result.

    `invalid_object` is not a fourth exit: it names a `normal_form` exit whose
    result is the Canonical Invalid Object (Book I s4.2). Deriving it from the
    exit AND the result hash keeps the two levels apart -- classifying by the
    result term alone is what conflated them, since DISSONANCE(ATP Exhausted) is
    an ordinary term that can be a normal form.
    """
    if receipt.exit == "normal_form" and receipt.result_hash.hex() == INVALID_OBJECT_HASH:
        return "invalid_object"
    return receipt.exit


def chk(vid, cond, detail=""):
    ok.append(cond)
    print(("OK  " if cond else "FAIL"), vid, detail if not cond else "")


for v in doc["vectors"]:
    kind, exp = v["kind"], v["expected"]
    if kind == "object":
        got = sg.node_hash(bytes.fromhex(v["bytes"])).hex()
        chk(v["id"], got == exp["hash"], f"got {got}")
    elif kind == "deserialize":
        got = sg.deser(bytes.fromhex(v["bytes"]))
        chk(v["id"], (got is None) == (not exp["valid"]), f"got {got}")
    elif kind == "eval":
        st = store
        if "store_subset" in v:                      # format v2: isolated store
            st = sg.Store()
            for hx in v["store_subset"]:
                st.put(bytes.fromhex(doc["objects"][hx]))
        # eval_receipt, not eval_hash. The two-value form cannot answer `exit`,
        # so a runner built on it checked the hash and the spend and left the
        # exit unexamined -- which is how a suite came to record a classification
        # no engine had ever been asked to agree with.
        receipt = sg.eval_receipt(bytes.fromhex(v["term"]), v["atp"], st)
        got_hash = receipt.result_hash.hex()
        chk(f"{v['id']} exit", receipt.exit == exp["exit"],
            f"got {receipt.exit}, want {exp['exit']}")
        chk(f"{v['id']} result_hash", got_hash == exp["result_hash"],
            f"got {got_hash}, want {exp['result_hash']}")
        chk(f"{v['id']} atp_spent", receipt.atp_spent == exp["atp_spent"],
            f"got {receipt.atp_spent}, want {exp['atp_spent']}")
        # The classification is checked as its own claim, against its own rule,
        # so that `exit` and `outcome` cannot be satisfied by one another.
        got_class = classify(receipt)
        chk(f"{v['id']} outcome", exp["outcome"] == got_class,
            f"got {got_class}, want {exp['outcome']}")
    else:
        chk(v["id"], False, f"unknown kind {kind}")

n = len(ok)
print(f"\n{'CONFORMANCE: ALL PASS' if all(ok) else 'CONFORMANCE: FAILURES PRESENT'} ({sum(ok)}/{n})")
sys.exit(0 if all(ok) else 1)
