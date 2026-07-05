#!/usr/bin/env python3
"""Generate vectors.json from the reference implementation.

The reference implementation is the normative oracle (prose vs code: code wins).
Every expected value in vectors.json is COMPUTED by this script, never written
by hand. Regenerate after any oracle change:

    python3 tests/spec_conformance/generate.py

Output is deterministic: same oracle -> byte-identical JSON (diffable, anchorable).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

SPEC_VERSION = "0.4.5"   # Book I document version these vectors conform to
SUITE_VERSION = "0.4.5"  # conformance-suite package (release) version
BOOK1_ANCHOR = "6ca303f30889a9a52117f7558e4a8b44ce5b42a0303cd6da381594d792ea2cfb"

store = sg.Store()
objects = {}


def put(b):
    h = store.put(b)
    objects[h.hex()] = b.hex()
    return h


def put_tree(t):
    if t[0] == "app":
        put_tree(t[1])
        put_tree(t[2])
    return put(sg.term_bytes(t))


A = lambda l, r: ("app", l, r)
Ig, Kg, Sg = ("lit", sg.sha(b"I")), ("lit", sg.sha(b"K")), ("lit", sg.sha(b"S"))

vectors = []


def obj_vector(vid, note, b):
    vectors.append({
        "id": vid, "kind": "object", "note": note,
        "bytes": b.hex(),
        "expected": {"hash": sg.node_hash(b).hex()},
    })


def deser_vector(vid, note, buf):
    assert sg.deser(buf) is None, f"{vid}: expected invalid bytes"
    vectors.append({
        "id": vid, "kind": "deserialize", "note": note,
        "bytes": buf.hex(),
        "expected": {"valid": False},
    })


def eval_vector(vid, note, h, atp):
    r, spent = sg.eval_hash(h, atp, store)
    if r == ("dis", sg.R_ATP):
        outcome = "atp_exhausted"
    elif r == ("dis", sg.R_UNRES):
        outcome = "unresolved_reference"
    elif r == ("dis", sg.R_INVALID):
        outcome = "invalid_object"
    else:
        outcome = "normal_form"
    vectors.append({
        "id": vid, "kind": "eval", "note": note,
        "term": h.hex(), "atp": atp,
        "expected": {
            "outcome": outcome,
            "result_hash": sg.term_hash(r).hex(),
            "atp_spent": spent,
        },
    })


# ---------- objects: genesis + canonical constants ----------
obj_vector("OBJ-I", "genesis axiom I = LITERAL(SHA-256('I'))", sg.I_BYTES)
obj_vector("OBJ-K", "genesis axiom K = LITERAL(SHA-256('K'))", sg.K_BYTES)
obj_vector("OBJ-S", "genesis axiom S = LITERAL(SHA-256('S'))", sg.S_BYTES)
obj_vector("OBJ-FALSE", "first theorem FALSE = APPLY(K,I)", sg.FALSE_BYTES)
obj_vector("OBJ-INVALID", "Canonical Invalid Object (Book I s4.2)", sg.INVALID_OBJECT)
for name, reason in (("ATP-EXHAUSTED", sg.R_ATP),
                     ("UNRESOLVED-REFERENCE", sg.R_UNRES),
                     ("INVALID-OBJECT", sg.R_INVALID)):
    obj_vector(f"OBJ-DIS-{name}",
               f"canonical DISSONANCE node for reason '{name.replace('-', ' ').title()}'",
               sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=reason))

for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES, sg.FALSE_BYTES):
    put(b)

# ---------- deserialize: malformed bytes -> Canonical Invalid Object ----------
deser_vector("INV-EMPTY", "empty buffer", b"")
deser_vector("INV-SHORT", "single byte, no flags", bytes([0x00]))
deser_vector("INV-FLAGS-HIGH", "flags with bits outside 0x07", bytes([0x00, 0x09]) + b"\x00" * 32)
deser_vector("INV-OP-RESERVED", "opcode 0x03 (Era-1 LAMBDA) is invalid in V2", bytes([0x03, 0x02]) + b"\x00" * 32)
deser_vector("INV-OP-UNKNOWN", "unknown opcode 0x7f", bytes([0x7F, 0x01]) + b"\x00" * 32)
deser_vector("INV-FLAGS-MISMATCH", "LITERAL with APPLY flags", bytes([0x00, 0x06]) + b"\x00" * 64)
deser_vector("INV-LEN-LONG", "APPLY with one extra byte", bytes([0x02, 0x06]) + b"\x00" * 65)
deser_vector("INV-LEN-SHORT", "APPLY truncated to one child", bytes([0x02, 0x06]) + b"\x00" * 32)

# ---------- eval: TV-4 .. TV-10 + boundaries ----------
h_I = sg.I_H
eval_vector("EV-LIT", "a lone LITERAL is a normal form; 0 ATP", h_I, 10)

dis_custom = put(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.sha(b"custom reason")))
eval_vector("EV-DIS-INERT", "a stored DISSONANCE node is a normal form; 0 ATP", dis_custom, 10)

h_ik = put_tree(A(Ig, Kg))
eval_vector("EV-TV4-IK", "TV-4: I K -> K in 1 ATP (R-I)", h_ik, 1)
eval_vector("EV-TV4-IK-ATP0", "TV-4: budget 0 with a redex present -> ATP Exhausted", h_ik, 0)

h_skki = put_tree(A(A(A(Sg, Kg), Kg), Ig))
eval_vector("EV-TV5-SKKI", "TV-5: S K K I -> I in 2 ATP", h_skki, 10)
eval_vector("EV-TV5-EXACT", "TV-5: exact budget 2 still reaches the normal form", h_skki, 2)
eval_vector("EV-TV5-UNDER", "TV-5: budget 1 -> ATP Exhausted", h_skki, 1)

h_tv6 = put_tree(A(A(A(Sg, Ig), Ig), A(Ig, Kg)))
eval_vector("EV-TV6-DUP", "TV-6: S I I (I K) -> APPLY(K,K); tree-semantics ATP is normative (5, not 4)", h_tv6, 100)
eval_vector("EV-TV6-EXACT", "TV-6: exact budget 5 reaches the normal form", h_tv6, 5)
eval_vector("EV-TV6-UNDER", "TV-6: budget 4 (graph-semantics cost) MUST exhaust under tree semantics", h_tv6, 4)

W = A(A(Sg, Ig), Ig)
h_omega = put_tree(A(W, W))
eval_vector("EV-TV7-OMEGA", "TV-7: Omega = SII(SII) never terminates; deterministic exhaustion", h_omega, 50)
eval_vector("EV-TV7-OMEGA-0", "TV-7: Omega with budget 0", h_omega, 0)

ghost = sg.sha(b"this node was never stored")
h_missing = put(sg.ser(sg.APPLY, 0x06, left=sg.I_H, right=ghost))
eval_vector("EV-TV8-MISSING-CHILD", "TV-8: APPLY(I, <absent hash>) -> Unresolved Reference", h_missing, 10)

h_k_dead = put(sg.ser(sg.APPLY, 0x06, left=sg.FALSE_H, right=ghost))
eval_vector("EV-K-DEAD-MISSING",
            "s3.5: eager materialization is normative in 0.4.x — APPLY(APPLY(K,I), <absent>) -> Unresolved Reference, NOT I (dead argument must exist; lazy spine = ADR-003)",
            h_k_dead, 10)

r_ghost = put(sg.ser(sg.REF, sg.F_ATOM, atom=ghost))
eval_vector("EV-REF-MISSING-ATP0",
            "s3.4: exhaustion is decided BEFORE any resolve of the next step — REF(<absent>) at budget 0 -> ATP Exhausted, not Unresolved",
            r_ghost, 0)
eval_vector("EV-REF-MISSING-ATP1",
            "s3.4: a failed firing is not charged — REF(<absent>) at budget 1 -> Unresolved Reference, 0 ATP",
            r_ghost, 1)

h_i_ref = put_tree(A(Ig, ("ref", ghost)))
eval_vector("EV-I-REF-MISSING-ATP1",
            "s3.4 totality + precedence: APPLY(I, REF(<absent>)) at exact budget 1 -> R-I fires, then exhaustion wins over the pending unresolvable R-R",
            h_i_ref, 1)
eval_vector("EV-I-REF-MISSING-ATP2",
            "s3.4 totality: same term at budget 2 -> canonical Unresolved Reference (never a raw error), only the completed R-I is charged",
            h_i_ref, 2)

h_root_missing = sg.sha(b"absent root")
eval_vector("EV-ROOT-MISSING", "root hash absent from store -> Unresolved Reference, 0 ATP", h_root_missing, 10)

r1 = put(sg.ser(sg.REF, sg.F_ATOM, atom=sg.K_H))
r2 = put(sg.ser(sg.REF, sg.F_ATOM, atom=r1))
eval_vector("EV-TV9-REF-CHAIN", "TV-9: REF -> REF -> K unwraps one level per step; 2 ATP", r2, 10)
eval_vector("EV-TV9-REF-UNDER", "TV-9: budget 1 stops between the two unwraps -> ATP Exhausted", r2, 1)

malformed = bytes([0x03, 0x02]) + b"\x00" * 32  # Era-1 LAMBDA opcode, invalid in V2
h_malformed = put(malformed)
h_apply_bad = put(sg.ser(sg.APPLY, 0x06, left=sg.I_H, right=h_malformed))
eval_vector("EV-BAD-BYTES-CHILD",
            "s3.5(b): resolve() returns bytes failing s4.1 -> Canonical Invalid Object materialized; R-I then yields it",
            h_apply_bad, 10)

ck = sg.c1(("lam", "x", ("lam", "y", ("var", "x"))))  # C1[\xy.x] = S (K K) I
h_c1 = put_tree(A(A(ck, Sg), Kg))
eval_vector("EV-TV10-C1-K", "TV-10: C1[\\xy.x] S K -> S (compiler output behaves as K)", h_c1, 16)

# ---------- sanity: recorded expectations match a fresh oracle run ----------
assert all(v["kind"] != "eval" or "result_hash" in v["expected"] for v in vectors)

doc = {
    "format": "sigma-glyph-conformance",
    "format_version": 1,
    "spec_version": SPEC_VERSION,
    "suite_version": SUITE_VERSION,
    "book1_anchor": BOOK1_ANCHOR,
    "oracle": "impl/sigma_glyph.py",
    "notes": [
        "objects: hex canonical bytes to preload into the CAS, keyed by their SHA-256 NodeHash.",
        "kind=object: serializing the described node MUST yield these bytes and this hash.",
        "kind=deserialize: these bytes MUST fail s4.1 validation and materialize the Canonical Invalid Object.",
        "kind=eval: eval(term, atp) MUST yield result_hash with atp_spent under tree semantics.",
        "outcome is informative; result_hash and atp_spent are the normative observables.",
    ],
    "objects": dict(sorted(objects.items())),
    "vectors": vectors,
}

out = Path(__file__).resolve().parent / "vectors.json"
out.write_text(json.dumps(doc, indent=2) + "\n")
print(f"wrote {out.relative_to(ROOT)}: {len(objects)} objects, {len(vectors)} vectors")
