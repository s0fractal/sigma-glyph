#!/usr/bin/env python3
"""Generate vectors.json from the reference implementation.

Two kinds of expected value live in vectors.json, and the difference matters:

  * SPEC-DERIVED (constraining). Declared BY HAND below in SPEC_EXPECT, read off
    spec/book-1-truth.md (Section 7 test vectors, Section 4.2, Section 5) or
    hand-computed from its rules. If the oracle disagrees with any declaration
    this script REFUSES to write vectors.json. These vectors constrain the
    oracle: an oracle that was wrong from the start cannot launder its own
    answer into the suite. Since Book I 0.6.0 the suite is a normative part of
    the edition and no implementation outranks it: a disagreement between the
    prose and a record makes the edition non-conformant rather than being settled
    in the oracle's favour. Same discipline as the governance suite
    (tools/anchor_governance.py cmd_gen, which has refused since v0.6.x).

  * ORACLE-GENERATED (regression-only). Everything without a declaration is
    still whatever impl/sigma_glyph.py says. Replaying those against the same
    oracle can only detect a CHANGE, never an original error. They are honest
    regression vectors and nothing more.

Note on authority: since Book I 0.6.0 the suite is a normative part of the
edition and no implementation outranks it — a disagreement between the prose and
a record makes the edition non-conformant rather than being settled in the
oracle's favour. This script already worked that way in miniature: it refuses to
let the oracle quietly win on a value the spec states outright, so a divergence
has to be resolved by a human as an implementation bug or a spec erratum. Books
II and III still carry their own oracle-precedence clauses; harmonising them is
separate work.

tests/spec_conformance/README.md carries the per-vector ledger of which is
which. Regenerate after any oracle change:

    python3 tests/spec_conformance/generate.py

Output is deterministic: same oracle -> byte-identical JSON (diffable, anchorable).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

SPEC_VERSION = "0.6.0"   # Book I document version these vectors conform to
SUITE_VERSION = "0.5.0"  # conformance-suite package (release) version
BOOK1_ANCHOR = "629e86f0951e67346915a36328864d0ac9b091b06aad1af55af26700ac547d70"

# ============================================================================
# Spec-declared expectations — hand-written from spec/book-1-truth.md v0.5.2
# ============================================================================
# NOTHING in this block calls the oracle. The only computation is
# hashlib.sha256 over byte strings the SPEC dictates, plus the four-line
# serializer below transcribed directly from Section 1.1 + Section 2:
#
#     Layout: [Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]
#     LITERAL=0x00/F_ATOM=0x01, REF=0x01/F_ATOM, APPLY=0x02/F_LEFT|F_RIGHT=0x06,
#     DISSONANCE=0xFF/F_ATOM;  NodeHash = SHA-256(CanonicalBytes)
#
# That is a second, independent serializer. SPEC_SELFCHECK below proves it
# reproduces every node hash the spec quotes verbatim, so the values it derives
# are as spec-anchored as the quoted ones.
#
#   basis "quoted"  — the value appears verbatim in spec/book-1-truth.md.
#   basis "derived" — hand-computed here from spec rules; the cite names the
#                     rule and the arithmetic.

_h = lambda b: hashlib.sha256(b).hexdigest()
_node = lambda hex_bytes: _h(bytes.fromhex(hex_bytes))
_lit = lambda atom: _node("0001" + atom)
_ref = lambda target: _node("0101" + target)
_dis = lambda reason: _node("ff01" + reason)
_app = lambda left, right: _node("0206" + left + right)

# --- constants quoted verbatim from the spec ---
SP_H_I = "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162"  # s5.1
SP_H_K = "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c"  # s5.1
SP_H_S = "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6"  # s5.1
SP_H_FALSE = "65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098"  # s5.2
SP_TV1_BYTES = ("0001a83dd0ccbffe39d071cc317ddf6e97f5c6b1c87af91919271f9fa1"
                "40b0508c6c")                                                # s7 TV-1
SP_INVALID_BYTES = ("ff017cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078"
                    "df7f696efe8")                                           # s4.2
SP_H_INVALID = "af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507"  # s4.2
SP_TV3_BYTES = ("ff01dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd"
                "7032e090")                                                  # s7 TV-3
SP_H_DIS_ATP = "8bb0006f4c0a51a645877c10db80b7360b0d34f6f826e5737d0847f8b1493176"  # s7 TV-3
SP_R_INVALID = "7cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8"  # s5.3
SP_R_ATP = "dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090"      # s5.3
SP_R_UNRES = "75daae55453d9a98bfadb847d70b73fdd0be91d3b6ef8511d22fc42aa2c7c8e2"    # s5.3
SP_TERM_TV4 = "51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e"   # s7 TV-4
SP_TERM_TV5 = "c9f57b3f594d7b72b0855b0d6fabba89e6ccdf6840c8f84aeb5fd4707300bbfc"   # s7 TV-5
SP_TERM_TV6 = "0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198"   # s7 TV-6
SP_TERM_TV7 = "0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211"   # s7 TV-7
SP_C1_KXY = "bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d"     # s7 TV-10

# --- values derived here, with the spec rule that yields them ---
SP_H_DIS_UNRES = _dis(SP_R_UNRES)          # s1.1 layout + s5.3 reason hash
SP_H_APPLY_KK = _app(SP_H_K, SP_H_K)       # s2 layout; TV-6 normal form APPLY(K,K)
SP_GHOST = _h(b"this node was never stored")   # s7 TV-11 defines ghost by ASCII
SP_H_LIT_DUMMY = _lit(_h(b"dummy blob"))
SP_H_DIS_CUSTOM = _dis(_h(b"custom reason"))
SP_MALFORMED = "0302" + "00" * 32          # s1.2: opcode 0x03 is invalid in V2
SP_H_MALFORMED = _node(SP_MALFORMED)
SP_H_R1 = _ref(SP_H_K)                     # s7 TV-9 store: r1 = REF(H(K))
SP_H_R2 = _ref(SP_H_R1)                    # s7 TV-9 store: r2 = REF(r1)
SP_H_R_GHOST = _ref(SP_GHOST)
SP_H_KI = _app(SP_H_K, SP_H_I)             # == FALSE (s5.2)
SP_H_SKI_INNER = _app(_app(SP_H_S, SP_H_KI), SP_H_APPLY_KK)   # S (K I) (K K)

# Consistency of the hand serializer against every node hash the spec quotes.
# If one of these fails the declarations below are untrustworthy and the
# generator must refuse before it can bless anything.
SPEC_SELFCHECK = [
    ("s7 TV-1 bytes hash to the s5.1 NodeHash of I", _node(SP_TV1_BYTES), SP_H_I),
    ("s5.2 FALSE = APPLY(K,I)", _app(SP_H_K, SP_H_I), SP_H_FALSE),
    ("s4.2 Canonical Invalid Object bytes", _dis(SP_R_INVALID), SP_H_INVALID),
    ("s4.2 Canonical Invalid Object bytes are ff01||SHA-256('Invalid Object')",
     SP_INVALID_BYTES, "ff01" + SP_R_INVALID),
    ("s7 TV-3 DISSONANCE(ATP Exhausted)", _node(SP_TV3_BYTES), SP_H_DIS_ATP),
    ("s7 TV-3 bytes are ff01||SHA-256('ATP Exhausted')", SP_TV3_BYTES, "ff01" + SP_R_ATP),
    ("s5.3 SHA-256('Invalid Object')", _h(b"Invalid Object"), SP_R_INVALID),
    ("s5.3 SHA-256('ATP Exhausted')", _h(b"ATP Exhausted"), SP_R_ATP),
    ("s5.3 SHA-256('Unresolved Reference')", _h(b"Unresolved Reference"), SP_R_UNRES),
    ("s7 TV-4 APPLY(I,K)", _app(SP_H_I, SP_H_K), SP_TERM_TV4),
    ("s7 TV-5 S K K I", _app(_app(_app(SP_H_S, SP_H_K), SP_H_K), SP_H_I), SP_TERM_TV5),
    ("s7 TV-6 S I I (I K)",
     _app(_app(_app(SP_H_S, SP_H_I), SP_H_I), _app(SP_H_I, SP_H_K)), SP_TERM_TV6),
    ("s7 TV-7 Omega = (S I I)(S I I)",
     _app(_app(_app(SP_H_S, SP_H_I), SP_H_I), _app(_app(SP_H_S, SP_H_I), SP_H_I)),
     SP_TERM_TV7),
    ("s7 TV-10 C1[\\xy.x] = APPLY(APPLY(S,APPLY(K,K)),I)",
     _app(_app(SP_H_S, SP_H_APPLY_KK), SP_H_I), SP_C1_KXY),
]


def _q(cite, **fields):
    return dict(basis="quoted", cite=cite, **fields)


def _d(cite, **fields):
    return dict(basis="derived", cite=cite, **fields)


# Observables per kind: object -> {bytes, hash}; deserialize -> {valid};
# eval -> {term, result_hash, atp_spent}. A declaration MAY constrain a subset.
SPEC_EXPECT = {
    # ---- objects (s5.1, s5.2, s4.2, s5.3, s7 TV-1/TV-3) ----
    "OBJ-I": _q("s7 TV-1 + s5.1", bytes=SP_TV1_BYTES, hash=SP_H_I),
    "OBJ-K": _q("s5.1 (bytes 0001||SHA-256('K') not spelled out in the spec)", hash=SP_H_K),
    "OBJ-S": _q("s5.1 (bytes 0001||SHA-256('S') not spelled out in the spec)", hash=SP_H_S),
    "OBJ-FALSE": _q("s5.2 + s7 TV-2", bytes="0206" + SP_H_K + SP_H_I, hash=SP_H_FALSE),
    "OBJ-INVALID": _q("s4.2", bytes=SP_INVALID_BYTES, hash=SP_H_INVALID),
    "OBJ-DIS-ATP-EXHAUSTED": _q("s7 TV-3", bytes=SP_TV3_BYTES, hash=SP_H_DIS_ATP),
    "OBJ-DIS-UNRESOLVED-REFERENCE": _d(
        "s1.1 layout + s5.3 reason hash", bytes="ff01" + SP_R_UNRES, hash=SP_H_DIS_UNRES),
    "OBJ-DIS-INVALID-OBJECT": _q("s4.2", bytes=SP_INVALID_BYTES, hash=SP_H_INVALID),

    # ---- deserialize: s4.1 clauses, restated in s7 "Negative" ----
    "INV-EMPTY": _q("s4.1(1) len >= 2", valid=False),
    "INV-SHORT": _q("s4.1(1) len >= 2", valid=False),
    "INV-FLAGS-HIGH": _q("s1.1 + s4.1(2): Flags bits outside 0x07 MUST be zero", valid=False),
    "INV-OP-RESERVED": _q("s1.2 + s7 Negative: opcode 0x03 is invalid in V2", valid=False),
    "INV-OP-UNKNOWN": _q("s1.2: any opcode outside the s1.1 table", valid=False),
    "INV-FLAGS-MISMATCH": _q("s4.1(2): Flags MUST equal the opcode's normative value",
                             valid=False),
    "INV-LEN-LONG": _q("s4.1(3): len == 2 + 32*popcount(Flags & 0x07)", valid=False),
    "INV-LEN-SHORT": _q("s4.1(3): len == 2 + 32*popcount(Flags & 0x07)", valid=False),

    # ---- eval: every s7 test vector, plus s3.4/s3.5 arithmetic ----
    "EV-GENESIS-BARE": _q("s7 TV-12: eval(H(I), n) = <I>, 0 ATP, store not needed",
                          term=SP_H_I, result_hash=SP_H_I, atp_spent=0),
    "EV-LIT-FORCE": _d("s3.4 cost(force LITERAL) = 1, then normal form (s3.3)",
                       term=SP_H_LIT_DUMMY, result_hash=SP_H_LIT_DUMMY, atp_spent=1),
    "EV-DIS-INERT": _d("s3.4 cost(force DISSONANCE) = 1, then normal form (s3.3)",
                       term=SP_H_DIS_CUSTOM, result_hash=SP_H_DIS_CUSTOM, atp_spent=1),
    "EV-STUCK-DIS-FN": _d(
        "s3.3: no rule matches DISSONANCE in function position; force root APPLY (3) "
        "+ force fn DISSONANCE (1) = 4; the term is hash-transparent so the stuck "
        "normal form has the root's own hash",
        term=_app(SP_H_DIS_CUSTOM, SP_H_I), result_hash=_app(SP_H_DIS_CUSTOM, SP_H_I),
        atp_spent=4),
    "EV-STUCK-LIT-FN": _d(
        "s3.2 Identity by Hash: a LITERAL that is not I/K/S is inert in function "
        "position; 3 + 1 = 4",
        term=_app(SP_H_LIT_DUMMY, SP_H_I), result_hash=_app(SP_H_LIT_DUMMY, SP_H_I),
        atp_spent=4),
    "EV-TV4-IK": _q("s7 TV-4: eval(.,4) = <K>, 4 ATP (force root 3 + R-I 1)",
                    term=SP_TERM_TV4, result_hash=SP_H_K, atp_spent=4),
    "EV-TV4-IK-ATP0": _q("s7 TV-4: eval(.,0) = ATP Exhausted, spent 0, no store access",
                         term=SP_TERM_TV4, result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-TV4-IK-ATP2": _q("s7 TV-4: eval(.,2) = ATP Exhausted, spent 0 (force costs 3 > 2)",
                         term=SP_TERM_TV4, result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-TV4-IK-ATP3": _q("s7 TV-4: eval(.,3) = ATP Exhausted, spent 3",
                         term=SP_TERM_TV4, result_hash=SP_H_DIS_ATP, atp_spent=3),
    "EV-TV5-SKKI": _q("s7 TV-5: eval(.,12) = <I>, 12 ATP (3 forces of 3 + R-S 2 + R-K 1)",
                      term=SP_TERM_TV5, result_hash=SP_H_I, atp_spent=12),
    "EV-TV5-EXACT": _q("s7 TV-5: the exact budget 12 reaches the normal form",
                       term=SP_TERM_TV5, result_hash=SP_H_I, atp_spent=12),
    "EV-TV5-UNDER": _d(
        "s7 TV-5 cost breakdown + s3.4 exhaustion-precedes-action: at budget 11 the "
        "three forces (9) and R-S (2) are affordable, R-K (1) is not -> Exhausted, spent 11",
        term=SP_TERM_TV5, result_hash=SP_H_DIS_ATP, atp_spent=11),
    "EV-TV6-DUP": _q("s7 TV-6: normal form APPLY(<K>,<K>), exactly 21 ATP",
                     term=SP_TERM_TV6, result_hash=SP_H_APPLY_KK, atp_spent=21),
    "EV-TV6-EXACT": _q("s7 TV-6: the exact budget 21 reaches the normal form",
                       term=SP_TERM_TV6, result_hash=SP_H_APPLY_KK, atp_spent=21),
    "EV-TV6-UNDER": _d("s7 TV-6 says 'exactly 21 ATP', so 20 cannot reach the normal "
                       "form -> ATP Exhausted (s3.4). The spec does not state the "
                       "spent value here; it stays oracle-generated",
                       term=SP_TERM_TV6, result_hash=SP_H_DIS_ATP),
    "EV-TV7-OMEGA": _q("s7 TV-7: for all n, eval(Omega,n) = DISSONANCE(ATP Exhausted). "
                       "The spec states no spent value; it stays oracle-generated",
                       term=SP_TERM_TV7, result_hash=SP_H_DIS_ATP),
    "EV-TV7-OMEGA-0": _d("s7 TV-7 + s3.4: minimum action cost is 1, so at budget 0 "
                         "exhaustion is decided before any store access -> spent 0",
                         term=SP_TERM_TV7, result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-TV8-MISSING-CHILD": _q("s7 TV-8: Unresolved Reference, spent 4",
                               term=_app(SP_H_I, SP_GHOST),
                               result_hash=SP_H_DIS_UNRES, atp_spent=4),
    "EV-K-DEAD-MISSING": _q("s7 TV-11: APPLY(<FALSE>, ghost) -> <I>, 7 ATP",
                            term=_app(SP_H_FALSE, SP_GHOST),
                            result_hash=SP_H_I, atp_spent=7),
    "EV-S-KI-KK-DEAD-Z": _q("s7 TV-11: APPLY(S (K I) (K K), ghost) -> <K>, 20 ATP",
                            term=_app(SP_H_SKI_INNER, SP_GHOST),
                            result_hash=SP_H_K, atp_spent=20),
    "EV-REF-MISSING-ATP0": _q("s3.4: eval(REF(missing), 0) = ATP Exhausted before any "
                              "store access", term=SP_H_R_GHOST,
                              result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-REF-MISSING-ATP1": _d("s3.4 cost(force REF) = 2 > 1 -> Exhausted, nothing spent",
                              term=SP_H_R_GHOST, result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-REF-MISSING-ATP2": _d("s3.4: force REF (2) affordable, R-R (1) is not -> spent 2",
                              term=SP_H_R_GHOST, result_hash=SP_H_DIS_ATP, atp_spent=2),
    "EV-REF-MISSING-ATP3": _d("s3.4: force (2) + R-R (1) = 3, then the next force is "
                              "unaffordable and the target's absence is never "
                              "discovered -> Exhausted, spent 3",
                              term=SP_H_R_GHOST, result_hash=SP_H_DIS_ATP, atp_spent=3),
    "EV-REF-MISSING-ATP4": _d("s3.4 + s3.5(a): force (2) + R-R (1), then the demanded "
                              "force finds nothing; a failed action is not charged -> "
                              "Unresolved Reference, spent 3",
                              term=SP_H_R_GHOST, result_hash=SP_H_DIS_UNRES, atp_spent=3),
    "EV-ROOT-MISSING": _d("s3.5(a) + s3.4: the root force fails and is not charged -> "
                          "Unresolved Reference, spent 0",
                          term=_h(b"absent root"), result_hash=SP_H_DIS_UNRES, atp_spent=0),
    "EV-TV9-REF-CHAIN": _q("s7 TV-9: eval(r2, 6) = <K>, exactly 6 ATP",
                           term=SP_H_R2, result_hash=SP_H_K, atp_spent=6),
    "EV-TV9-REF-UNDER": _q("s7 TV-9: eval(r2, 1) = ATP Exhausted, spent 0",
                           term=SP_H_R2, result_hash=SP_H_DIS_ATP, atp_spent=0),
    "EV-GENESIS-INTRINSIC": _q("s7 TV-12 + s5.1: REF(H(K)) on an empty store -> <K>, 3 ATP",
                               term=SP_H_R1, result_hash=SP_H_K, atp_spent=3),
    "EV-BAD-BYTES-CHILD": _d("s3.5(b) + s3.4: force root (3) + R-I (1) + force of "
                             "invalid bytes materializing the Canonical Invalid Object, "
                             "priced as a DISSONANCE force (1) = 5",
                             term=_app(SP_H_I, SP_H_MALFORMED),
                             result_hash=SP_H_INVALID, atp_spent=5),
    "EV-TV10-C1-K": _q("s7 TV-10: eval(APPLY(APPLY(C1[\\xy.x],<S>),<K>), 20) = <S>, 20 ATP",
                       term=_app(_app(SP_C1_KXY, SP_H_S), SP_H_K),
                       result_hash=SP_H_S, atp_spent=20),
}

# Vectors deliberately left oracle-generated (regression-only). Listed so the
# ledger in README.md can be checked mechanically instead of by eye.
ORACLE_ONLY = {
    "EV-REF-COMBINATOR-FIRES",     # s3.1 R-R + R-S compose; the spec states no cost
    "EV-K-DEAD-NESTED-MISSING",    # s7 TV-11 class, but this nesting is not a TV
}

FAILURES = []
DECLARED = set()


def check_declared(vid, observed):
    """Compare the oracle's observables against the hand-declared expectation."""
    decl = SPEC_EXPECT.get(vid)
    if decl is None:
        if vid not in ORACLE_ONLY:
            FAILURES.append(f"{vid}: neither declared in SPEC_EXPECT nor listed in "
                            f"ORACLE_ONLY — classify it before it ships")
        return
    DECLARED.add(vid)
    for key, want in decl.items():
        if key in ("basis", "cite"):
            continue
        got = observed.get(key)
        if got != want:
            FAILURES.append(f"{vid}: {key} = {got!r}, spec ({decl['cite']}) declares "
                            f"{want!r}")

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
    check_declared(vid, {"bytes": b.hex(), "hash": sg.node_hash(b).hex()})
    vectors.append({
        "id": vid, "kind": "object", "note": note,
        "bytes": b.hex(),
        "expected": {"hash": sg.node_hash(b).hex()},
    })


def deser_vector(vid, note, buf):
    check_declared(vid, {"valid": sg.deser(buf) is not None})
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
    check_declared(vid, {"term": h.hex(), "result_hash": sg.term_hash(r).hex(),
                         "atp_spent": spent})
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
eval_vector("EV-GENESIS-BARE", "TV-12: bare intrinsic thunk: eval(H(I)) is NF by hash; 0 ATP, no store access", sg.I_H, 10)

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

# ---------- refuse to generate when the oracle contradicts the spec ----------
# The governance suite has done exactly this since v0.6.x
# (tools/anchor_governance.py cmd_gen). Before that fix, and before this one,
# a vector file could only ever say what its own oracle already believed.
for label, got, want in SPEC_SELFCHECK:
    if got != want:
        FAILURES.append(f"SPEC-SELFCHECK {label}: hand serializer gives {got}, "
                        f"the spec quotes {want}")
missing = sorted(set(SPEC_EXPECT) - DECLARED)
if missing:
    FAILURES.append("declared expectations never exercised (vector renamed or "
                    "deleted?): " + ", ".join(missing))

if FAILURES:
    print("REFUSING TO GENERATE — the oracle disagrees with spec/book-1-truth.md:")
    for f in FAILURES:
        print("  " + f)
    print("\nEither impl/sigma_glyph.py is wrong, or the spec is wrong and needs an "
          "erratum. Do not 'fix' this by editing SPEC_EXPECT to match the oracle: "
          "that is the circularity this block exists to prevent.")
    sys.exit(1)

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
n_spec = len(DECLARED)
print(f"wrote {out.relative_to(ROOT)}: {len(objects)} objects, {len(vectors)} vectors "
      f"({n_spec} spec-derived/constraining, {len(vectors) - n_spec} oracle-generated/"
      f"regression-only)")
