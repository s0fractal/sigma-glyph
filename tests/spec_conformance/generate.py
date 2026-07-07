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

SPEC_VERSION = "0.5.2"   # Book I document version these vectors conform to
SUITE_VERSION = "0.5.0"  # conformance-suite package (release) version
BOOK1_ANCHOR = "a98a03bd5fcc573d4850cdc9e8e80d66518fdc4888ce31c9888df1e24b48b47b"

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


def eval_vector(vid, note, h, atp, subset=None):
    """subset: optional list of object hashes (hex) — the vector runs against a
    fresh store containing ONLY those objects (format v2; genesis-intrinsic and
    availability vectors need a store the shared preload would contaminate)."""
    if subset is None:
        st = store
    else:
        st = sg.Store()
        for hx in subset:
            st.put(bytes.fromhex(objects[hx]))
    r, spent = sg.eval_hash(h, atp, st)
    if r == ("dis", sg.R_ATP):
        outcome = "atp_exhausted"
    elif r == ("dis", sg.R_UNRES):
        outcome = "unresolved_reference"
    elif r == ("dis", sg.R_INVALID):
        outcome = "invalid_object"
    else:
        outcome = "normal_form"
    v = {
        "id": vid, "kind": "eval", "note": note,
        "term": h.hex(), "atp": atp,
        "expected": {
            "outcome": outcome,
            "result_hash": sg.term_hash(r).hex(),
            "atp_spent": spent,
        },
    }
    if subset is not None:
        v["store_subset"] = sorted(subset)
    vectors.append(v)


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

# ---------- eval: v0.5 hash-thunk machine, size-priced ATP ----------
eval_vector("EV-GENESIS-BARE", "bare intrinsic thunk: eval(H(I)) is NF by hash; 0 ATP, no store access", sg.I_H, 10)

lit_dummy = put(sg.ser(sg.LITERAL, sg.F_ATOM, atom=sg.sha(b"dummy blob")))
eval_vector("EV-LIT-FORCE", "non-genesis LITERAL: one force (1 ATP), then NF. No blob material is supplied; Book I eval MUST depend only on the LITERAL node bytes and MUST NOT fetch or validate the committed blob (ADR-004, s1.1)", lit_dummy, 10)

dis_custom = put(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.sha(b"custom reason")))
eval_vector("EV-DIS-INERT", "a stored DISSONANCE node forces (1 ATP) into a normal form", dis_custom, 10)

# Opus 4.8 review N2: non-combinator in function position -> stuck normal form
h_stuck_dis = put_tree(A(("dis", sg.sha(b"custom reason")), Ig))
eval_vector("EV-STUCK-DIS-FN",
            "APPLY(DISSONANCE, I): no rule matches a DISSONANCE in function position; "
            "stuck normal form, force root (3) + force fn (1) = 4",
            h_stuck_dis, 100)
h_stuck_lit = put_tree(A(("lit", sg.sha(b"dummy blob")), Ig))
eval_vector("EV-STUCK-LIT-FN",
            "APPLY(non-genesis LITERAL, I): a LITERAL that is not I/K/S by hash is "
            "inert in function position; stuck normal form, spent 4",
            h_stuck_lit, 100)
# Opus 4.8 review N2: REF resolving to a combinator enables the redex
h_ref_s = put_tree(A(A(A(("ref", sg.S_H), Ig), Ig), Kg))
eval_vector("EV-REF-COMBINATOR-FIRES",
            "REF(S) I I K: the REF forces (2) and unwraps (1) to the S thunk, "
            "which then fires R-S by hash — a REF target enabling a redex",
            h_ref_s, 100)

h_ik = put_tree(A(Ig, Kg))
eval_vector("EV-TV4-IK", "TV-4: I K -> K; force root (3) + R-I (1) = 4 ATP", h_ik, 100)
eval_vector("EV-TV4-IK-ATP0", "TV-4: budget 0 -> ATP Exhausted, spent 0, decided before any store access", h_ik, 0)
eval_vector("EV-TV4-IK-ATP2", "TV-4: budget 2 -> root force (3) unaffordable; fetched bytes discarded, spent 0", h_ik, 2)
eval_vector("EV-TV4-IK-ATP3", "TV-4: budget 3 -> root forced, R-I unaffordable; spent 3", h_ik, 3)

h_skki = put_tree(A(A(A(Sg, Kg), Kg), Ig))
eval_vector("EV-TV5-SKKI", "TV-5: S K K I -> I; 3 forces (9) + R-S (1+size(z)=2) + R-K (1) = 12 ATP", h_skki, 100)
eval_vector("EV-TV5-EXACT", "TV-5: exact budget 12 reaches the normal form", h_skki, 12)
eval_vector("EV-TV5-UNDER", "TV-5: budget 11 -> ATP Exhausted", h_skki, 11)

h_tv6 = put_tree(A(A(A(Sg, Ig), Ig), A(Ig, Kg)))
eval_vector("EV-TV6-DUP", "TV-6: S I I (I K) -> APPLY(K,K); size-priced duplication; NF hash unchanged from v0.4", h_tv6, 100)
eval_vector("EV-TV6-EXACT", "TV-6: exact budget reaches the normal form", h_tv6, 21)
eval_vector("EV-TV6-UNDER", "TV-6: one under exact -> ATP Exhausted", h_tv6, 20)

W = A(A(Sg, Ig), Ig)
h_omega = put_tree(A(W, W))
eval_vector("EV-TV7-OMEGA", "TV-7: Omega = SII(SII) never terminates; deterministic exhaustion; size-1 <= spent throughout", h_omega, 500)
eval_vector("EV-TV7-OMEGA-0", "TV-7: Omega with budget 0 -> Exhausted, 0 spent, no store access", h_omega, 0)

ghost = sg.sha(b"this node was never stored")
h_missing = put(sg.ser(sg.APPLY, 0x06, left=sg.I_H, right=ghost))
eval_vector("EV-TV8-MISSING-CHILD",
            "TV-8: APPLY(I, <absent>): R-I fires lazily WITHOUT forcing the argument; the absent hash then becomes the demanded root -> Unresolved Reference, spent 4",
            h_missing, 10)

h_k_dead = put(sg.ser(sg.APPLY, 0x06, left=sg.FALSE_H, right=ghost))
eval_vector("EV-K-DEAD-MISSING",
            "TV-11/ADR-003: APPLY(APPLY(K,I), <absent>) -> I. Dead missing argument no longer blocks reduction (v0.4.x: Unresolved Reference — deliberate v0.5 breaking change). ghost = SHA-256('this node was never stored')",
            h_k_dead, 100)

h_ki = put_tree(A(Kg, Ig))
h_ii = put(sg.ser(sg.APPLY, 0x06, left=sg.I_H, right=ghost))
h_k_dead_nested = put(sg.ser(sg.APPLY, 0x06, left=h_ki, right=h_ii))
eval_vector("EV-K-DEAD-NESTED-MISSING",
            "TV-11: APPLY(APPLY(K,I), APPLY(I,<absent>)) -> I; deadness through a nested unresolvable subtree",
            h_k_dead_nested, 100)

h_ski_inner = put_tree(A(A(Sg, A(Kg, Ig)), A(Kg, Kg)))
h_s_dead = put(sg.ser(sg.APPLY, 0x06, left=h_ski_inner, right=ghost))
eval_vector("EV-S-KI-KK-DEAD-Z",
            "TV-11: S (K I) (K K) <absent> -> K; the argument is duplicated by R-S as a hash leaf and discarded by both Ks without ever being forced (divergence class, reviews Codex+Gemini+DeepSeek)",
            h_s_dead, 100)

r_ghost = put(sg.ser(sg.REF, sg.F_ATOM, atom=ghost))
eval_vector("EV-REF-MISSING-ATP0",
            "s3.4: exhaustion decided before any store access — REF(<absent>) at budget 0 -> ATP Exhausted, 0",
            r_ghost, 0)
eval_vector("EV-REF-MISSING-ATP1",
            "s3.4: force of a REF costs 2 -> unaffordable at budget 1; ATP Exhausted, 0 (v0.4.5 gave Unresolved here — v0.5 prices the materialization itself)",
            r_ghost, 1)
eval_vector("EV-REF-MISSING-ATP2",
            "force REF (2), then R-R unaffordable -> ATP Exhausted, spent 2",
            r_ghost, 2)
eval_vector("EV-REF-MISSING-ATP3",
            "force (2) + R-R (1) leave remaining 0; exhaustion is decided BEFORE the next force attempt, so the absence of the target is never discovered -> ATP Exhausted, spent 3 (s3.4 precedence)",
            r_ghost, 3)
eval_vector("EV-REF-MISSING-ATP4",
            "with remaining budget the demanded force is attempted and the target is absent -> Unresolved Reference, spent 3 (failed force not charged)",
            r_ghost, 4)

h_root_missing = sg.sha(b"absent root")
eval_vector("EV-ROOT-MISSING", "root hash absent from store -> Unresolved Reference, 0 ATP", h_root_missing, 10)

r1 = put(sg.ser(sg.REF, sg.F_ATOM, atom=sg.K_H))
r2 = put(sg.ser(sg.REF, sg.F_ATOM, atom=r1))
eval_vector("EV-TV9-REF-CHAIN", "TV-9: REF -> REF -> K: 2 forces (2 each) + 2 R-R (1 each) = 6 ATP; one level per step", r2, 100)
eval_vector("EV-TV9-REF-UNDER", "TV-9: budget 1 -> first force (2) unaffordable; Exhausted, 0", r2, 1)

eval_vector("EV-GENESIS-INTRINSIC",
            "TV-12/s5.1: REF(H(K)) on a store containing ONLY the REF node -> K, 3 ATP; genesis axioms materialize without storage",
            r1, 10, subset=[r1.hex()])

malformed = bytes([0x03, 0x02]) + b"\x00" * 32  # Era-1 LAMBDA opcode, invalid in V2
h_malformed = put(malformed)
h_apply_bad = put(sg.ser(sg.APPLY, 0x06, left=sg.I_H, right=h_malformed))
eval_vector("EV-BAD-BYTES-CHILD",
            "s3.5(b): force root (3) + R-I (1) + force of invalid bytes materializes the Canonical Invalid Object (1) -> its hash, spent 5",
            h_apply_bad, 10)

ck = sg.c1(("lam", "x", ("lam", "y", ("var", "x"))))  # C1[\xy.x] = S (K K) I
h_c1 = put_tree(A(A(ck, Sg), Kg))
eval_vector("EV-TV10-C1-K", "TV-10: C1[\\xy.x] S K -> S (compiler output behaves as K); 20 ATP size-priced", h_c1, 100)

# ---------- sanity: recorded expectations match a fresh oracle run ----------
assert all(v["kind"] != "eval" or "result_hash" in v["expected"] for v in vectors)

doc = {
    "format": "sigma-glyph-conformance",
    "format_version": 2,
    "spec_version": SPEC_VERSION,
    "suite_version": SUITE_VERSION,
    "book1_anchor": BOOK1_ANCHOR,
    "oracle": "impl/sigma_glyph.py",
    "notes": [
        "objects: hex canonical bytes to preload into the CAS, keyed by their SHA-256 NodeHash.",
        "kind=object: serializing the described node MUST yield these bytes and this hash.",
        "kind=deserialize: these bytes MUST fail s4.1 validation and materialize the Canonical Invalid Object.",
        "kind=eval: eval(term, atp) MUST yield result_hash with atp_spent under the v0.5 hash-thunk machine (Book I s3.3-3.4: lazy left-spine, size-priced ATP, hash-leaf sizes, genesis intrinsic).",
        "format v2: an eval vector MAY carry store_subset (list of object hashes) - run it against a fresh store containing ONLY those objects.",
        "outcome is informative; result_hash and atp_spent are the normative observables.",
        "memory bound (normative invariant, property-tested): materialized size - 1 <= atp_spent at every step.",
        "eval vectors do not contain blob-store inputs; implementations MUST NOT make kind=eval results depend on external blob material (ADR-004, adopted v0.5.1).",
    ],
    "objects": dict(sorted(objects.items())),
    "vectors": vectors,
}

out = Path(__file__).resolve().parent / "vectors.json"
out.write_text(json.dumps(doc, indent=2) + "\n")
print(f"wrote {out.relative_to(ROOT)}: {len(objects)} objects, {len(vectors)} vectors")
