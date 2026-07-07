"""Sigma-GLYPH Book III reference implementation (federation; current release bundle v0.6.1).

Pure functions only: assertion/policy validation, selection derivation,
effective-wave computation, AnnotationViewID and assertion_set_root. No
warrant-store I/O here — the caller supplies the accepted, settlement-active
assertion set (that part is Warrant v0.3's job); this oracle answers what a
jurisdiction derives from it. Selection-only by construction (ADR-006,
gate 3/3, F1-strict): interfere() is used exclusively for structural APPLY
derivation and never to merge assertions.

    python3 impl/sigma_federation.py         # selftest + replay federation_vectors.json
    python3 impl/sigma_federation.py gen     # regenerate tests/spec_conformance/federation_vectors.json
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sigma_wave import W, interfere, FULL_PINS, ALIASES, complete  # noqa: E402

ASSERTION_TAG = "sigma-glyph.wave-assertion@v1"
POLICY_TAG = "sigma-glyph.selection@v1"
VIEW_TAG = "sigma-glyph.annotation-view@v1"
ORDER_FIELDS = ("epoch", "ts", "warrant_id", "actor")


def jcs(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha_hex(b):
    return hashlib.sha256(b).hexdigest()


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _is_uint(v, bits):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v < (1 << bits)


def validate_assertion(doc):
    """Book III §2. Returns None or an error string."""
    if not isinstance(doc, dict) or set(doc) != {"annotation", "jurisdiction",
                                                 "node", "epoch", "wave"}:
        return "assertion blob must have exactly {annotation, jurisdiction, node, epoch, wave}"
    if doc["annotation"] != ASSERTION_TAG:
        return f"annotation must be {ASSERTION_TAG!r}"
    if not (_is_hex64(doc["jurisdiction"]) and _is_hex64(doc["node"])):
        return "jurisdiction and node must be hex64"
    if not _is_uint(doc["epoch"], 64):
        return "epoch must be a uint64"
    w = doc["wave"]
    if not isinstance(w, dict) or set(w) != {"ph", "am", "en"}:
        return "wave must be a complete WaveVectorQ {ph, am, en}"
    if not (_is_uint(w["ph"], 16) and _is_uint(w["am"], 16)):
        return "ph and am must be uint16"
    en = w["en"]
    if not isinstance(en, int) or isinstance(en, bool) or not (-32768 <= en <= 32767):
        return "en must be int16"
    return None


def validate_policy(doc):
    """Book III §4. Returns None or an error string."""
    allowed = {"federation_policy", "order", "max_age_epochs", "quota_per_actor_epoch"}
    if not isinstance(doc, dict) or not set(doc) <= allowed:
        return "policy has unknown fields"
    if doc.get("federation_policy") != POLICY_TAG:
        return f"federation_policy must be {POLICY_TAG!r}"
    order = doc.get("order")
    if not isinstance(order, list) or not order:
        return "order must be a nonempty list"
    for k in order:
        if not isinstance(k, dict) or set(k) != {"field", "dir"}:
            return "order keys must be {field, dir}"
        if k["field"] not in ORDER_FIELDS:
            return f"order field must be one of {ORDER_FIELDS}"
        if k["dir"] not in ("asc", "desc"):
            return "order dir must be asc|desc"
    for opt in ("max_age_epochs", "quota_per_actor_epoch"):
        if opt in doc and not _is_uint(doc[opt], 64):
            return f"{opt} must be a uint64"
    return None


def _valid_metadata(c):
    """Book III §4: fields a policy can sort on must be well-typed, or the
    candidate is not live (imported Warrant field domains)."""
    return (_is_hex64(c.get("warrant_id"))
            and isinstance(c.get("actor"), str) and c["actor"].strip()
            and _is_uint(c.get("ts"), 64))


def _field(c, name):
    return c["assertion"]["epoch"] if name == "epoch" else c[name]


def _cmp_order(a, b, order):
    """Strict lexicographic comparison over the policy's order keys.
    Strings compare by Unicode scalar values DIRECTLY; desc inverts the
    comparison result — never a character-complement transform (Codex
    implementation-gate P1: prefix pairs break under complements and
    non-ASCII overflows chr)."""
    for k in order:
        av, bv = _field(a, k["field"]), _field(b, k["field"])
        c = (av > bv) - (av < bv)
        if c:
            return -c if k["dir"] == "desc" else c
    return 0


def select(candidates, policy, jurisdiction, node, epoch):
    """Book III §4 derivation over caller-supplied accepted assertions.

    candidates: list of {"warrant_id", "actor", "ts", "assertion": <blob dict>}
    Returns {"status": "selected"|"conflict"|"absent", "selected": cand|None,
             "conflict_set": [warrant_id...]} — deterministic, total.
    """
    import functools
    live = []
    for c in candidates:
        if not _valid_metadata(c):                     # malformed order fields: not live
            continue
        a = c["assertion"]
        if validate_assertion(a) is not None:
            continue
        if a["node"] != node:                          # node-bound selection, §4
            continue
        if a["jurisdiction"] != jurisdiction:          # replay resistance, §2 (v0.6: no peer roots)
            continue
        if a["epoch"] > epoch:                         # future assertions are not live (MUST)
            continue
        max_age = policy.get("max_age_epochs")
        if max_age is not None and epoch - a["epoch"] > max_age:
            continue                                   # stale, criterion 9
        live.append(c)
    order = policy["order"]
    tie_order = order + [{"field": "warrant_id", "dir": "asc"}]
    quota = policy.get("quota_per_actor_epoch")
    if quota is not None:
        # anti-spam pre-filter: survivors chosen by the SAME policy order with
        # warrant_id asc appended as deterministic tiebreak (Book III §4)
        groups = {}
        for c in live:
            groups.setdefault((c["actor"], c["assertion"]["epoch"]), []).append(c)
        live = []
        for g in groups.values():
            g.sort(key=functools.cmp_to_key(lambda x, y: _cmp_order(x, y, tie_order)))
            live.extend(g[:quota])
    if not live:
        return {"status": "absent", "selected": None, "conflict_set": []}
    live.sort(key=functools.cmp_to_key(lambda x, y: _cmp_order(x, y, tie_order)))
    top = [c for c in live if _cmp_order(c, live[0], order) == 0]
    if len(top) == 1:
        return {"status": "selected", "selected": top[0], "conflict_set": []}
    return {"status": "conflict", "selected": None,      # §4: clients MUST NOT merge
            "conflict_set": sorted(c["warrant_id"] for c in top)}


def wave_fed(term, resolve_selection):
    """Book III §5: effective wave over symbolic terms (sigma_wave term syntax).

    resolve_selection(term) -> selection result dict for a DIRECT assertion on
    that term's node, or None if the jurisdiction has no candidates for it.
    Priority per leaf: assertion > pin (null-jurisdiction default) > absent.
    APPLY: direct assertion wins; otherwise structural interfere (absent-poisoning).
    """
    sel = resolve_selection(term)
    if sel is not None:
        if sel["status"] == "selected":
            return dict(sel["selected"]["assertion"]["wave"])
        if sel["status"] == "conflict":
            return None                                # treated as unannotated, §4
    if isinstance(term, str):
        if term in FULL_PINS:
            return dict(FULL_PINS[term])
        if term in ALIASES:
            sub, pin = ALIASES[term]
            return complete(wave_fed(sub, resolve_selection), pin)
        return None
    if isinstance(term, dict):
        return None
    if isinstance(term, list) and term[0] == "APPLY":
        wl = wave_fed(term[1], resolve_selection)
        wr = wave_fed(term[2], resolve_selection)
        if wl is None or wr is None:
            return None
        return interfere(wl, wr)
    raise ValueError(f"bad term: {term!r}")


def view_id(jurisdiction, node, policy_hash, epoch):
    """Book III §6."""
    return sha_hex(jcs({"view": VIEW_TAG, "jurisdiction": jurisdiction,
                        "node": node, "policy": policy_hash, "epoch": epoch}))


def assertion_set_root(warrant_ids):
    """Book III §6: deterministic SET COMMITMENT (not a Merkle tree, not
    zero-knowledge: small candidate universes are enumerable offline —
    Codex implementation-gate P2)."""
    return sha_hex(jcs(sorted(warrant_ids)))


# ---------------------------------------------------------------------------
VEC_PATH = Path(__file__).resolve().parents[1] / "tests/spec_conformance/federation_vectors.json"

J = "aa" * 32
J2 = "bb" * 32
NODE = "cc" * 32
POLICY = {"federation_policy": POLICY_TAG,
          "order": [{"field": "epoch", "dir": "desc"},
                    {"field": "warrant_id", "dir": "asc"}],
          "max_age_epochs": 10}
POLICY_TIE = {"federation_policy": POLICY_TAG,
              "order": [{"field": "epoch", "dir": "desc"}]}   # no id tiebreak: ties surface
POLICY_ACTOR_DESC = {"federation_policy": POLICY_TAG,
                     "order": [{"field": "actor", "dir": "desc"}]}
POLICY_TS = {"federation_policy": POLICY_TAG,
             "order": [{"field": "ts", "dir": "desc"}],
             "quota_per_actor_epoch": 1}


def _cand(wid_byte, actor, ts, epoch, wave, jur=J, node=NODE):
    return {"warrant_id": wid_byte * 64, "actor": actor, "ts": ts,
            "assertion": {"annotation": ASSERTION_TAG, "jurisdiction": jur,
                          "node": node, "epoch": epoch, "wave": wave}}


CANDS = [
    _cand("1", "a@x", 100, 5, W(8192, 40000, -100)),
    _cand("2", "b@y", 110, 7, W(16384, 30000, 50)),
    _cand("3", "c@z", 120, 7, W(0, 20000, 0)),
    _cand("4", "m@ev", 130, 7, W(0, 65535, -32768), jur=J2),   # foreign: replayed
    _cand("5", "d@w", 140, 1, W(0, 1000, 0)),                  # stale at epoch 20
]


def _sel_expected(res):
    return {"status": res["status"],
            "selected_warrant": res["selected"]["warrant_id"] if res["selected"] else None,
            "conflict_set": res["conflict_set"]}


def _book1_fixture():
    """Book I unreachable (criterion 1): eval a fixture from vectors.json;
    the result MUST be byte-identical no matter what annotation state exists
    (federation is pure functions over a separate domain by construction —
    this vector makes the boundary executable)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sigma_glyph", Path(__file__).resolve().parent / "sigma_glyph.py")
    sg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sg)
    suite = json.loads((Path(__file__).resolve().parents[1] /
                        "tests/spec_conformance/vectors.json").read_text())
    vec = next(v for v in suite["vectors"] if v["id"] == "EV-TV4-IK")
    store = sg.Store()
    for h, bts in suite["objects"].items():
        store.put(bytes.fromhex(bts))
    r, spent = sg.eval_hash(bytes.fromhex(vec["term"]), vec["atp"], store)
    return {"book1_vector": "EV-TV4-IK",
            "result_hash": sg.term_hash(r).hex(), "atp_spent": spent,
            "matches_book1_suite": sg.term_hash(r).hex() == vec["expected"]["result_hash"]
                                    and spent == vec["expected"]["atp_spent"]}


def gen_vectors():
    vectors = []
    bad = dict(CANDS[0]["assertion"]); bad["extra"] = 1
    part = dict(CANDS[0]["assertion"]); part["wave"] = {"ph": 1, "am": 2}
    vectors.append({"id": "FV-ASSERT-VALID", "kind": "validate_assertion",
                    "doc": CANDS[0]["assertion"], "expected": None,
                    "note": "well-formed complete assertion validates"})
    vectors.append({"id": "FV-ASSERT-UNKNOWN-FIELD", "kind": "validate_assertion",
                    "doc": bad, "expected": validate_assertion(bad),
                    "note": "closed schema: unknown fields invalid"})
    vectors.append({"id": "FV-ASSERT-PARTIAL-WAVE", "kind": "validate_assertion",
                    "doc": part, "expected": validate_assertion(part),
                    "note": "partial waves are Book II pin data, not federation assertions"})
    badpol = dict(POLICY); badpol["order"] = [{"field": "vibes", "dir": "desc"}]
    vectors.append({"id": "FV-POLICY-VALID", "kind": "validate_policy",
                    "doc": POLICY, "expected": None,
                    "note": "machine-readable policy blob validates"})
    vectors.append({"id": "FV-POLICY-BAD-FIELD", "kind": "validate_policy",
                    "doc": badpol, "expected": validate_policy(badpol),
                    "note": "only mechanically verifiable order fields are legal"})

    def sel_vec(vid, cands, pol, epoch, note, node=NODE):
        res = select(cands, pol, J, node, epoch)
        vectors.append({"id": vid, "kind": "select", "policy": pol, "epoch": epoch,
                        "jurisdiction": J, "node": node, "candidates": cands,
                        "expected": _sel_expected(res), "note": note})

    sel_vec("FV-SELECT-LATEST", CANDS, POLICY, 8,
            "epoch desc + warrant_id asc: epoch-7 pair resolved by id -> '2'*64; "
            "the foreign-jurisdiction candidate is never selectable (replay resistance)")
    sel_vec("FV-CONFLICT-TIE", CANDS, POLICY_TIE, 8,
            "no id tiebreak: the epoch-7 pair is a genuine tie -> ConflictSet, clients MUST NOT merge")
    sel_vec("FV-STALE-EXCLUDED", CANDS, POLICY, 20,
            "epoch-1 assertion exceeds max_age_epochs=10 at epoch 20; latest live wins")
    sel_vec("FV-SELECT-FUTURE-EXCLUDED",
            [_cand("1", "a@x", 100, 8, W(0, 1, 0)), _cand("2", "b@y", 110, 9, W(0, 2, 0))],
            POLICY_TIE, 8,
            "an assertion with epoch > view epoch is not live (MUST); epoch-8 wins at view epoch 8")
    sel_vec("FV-SELECT-ACTOR-DESC-PREFIX",
            [_cand("1", "a", 100, 1, W(0, 1, 0)), _cand("2", "aa", 100, 1, W(0, 2, 0))],
            POLICY_ACTOR_DESC, 1,
            "actor desc is DIRECT Unicode-scalar lexicographic order inverted: "
            "'aa' > 'a', so 'aa' wins (complement transforms are nonconforming)")
    sel_vec("FV-SELECT-ACTOR-NONASCII",
            [_cand("1", "\u0100gent", 100, 1, W(0, 1, 0)), _cand("2", "agent", 100, 1, W(0, 2, 0))],
            POLICY_ACTOR_DESC, 1,
            "actor strings are arbitrary I-JSON: U+0100 sorts above 'a' by scalar value; "
            "implementations MUST be total over all Unicode scalars")
    sel_vec("FV-SELECT-NODE-FILTER",
            [_cand("1", "a@x", 100, 1, W(0, 1, 0)),
             _cand("2", "b@y", 110, 9, W(0, 2, 0), node="dd" * 32)],
            POLICY_TIE, 9,
            "selection is node-bound: the higher-epoch assertion for another node never competes")
    sel_vec("FV-QUOTA-ACTOR-EPOCH",
            [_cand("1", "same@actor", 100, 5, W(0, 100, 0)),
             _cand("2", "same@actor", 200, 5, W(0, 200, 0))],
            POLICY_TS, 5,
            "quota survivors are chosen by the SAME policy order (+warrant_id asc tiebreak): "
            "ts desc keeps the ts=200 assertion, not the lowest warrant_id")
    sel_vec("FV-SELECT-BAD-METADATA",
            [{"warrant_id": "not-hex", "actor": "a@x", "ts": 1,
              "assertion": CANDS[0]["assertion"]},
             {"warrant_id": "9" * 64, "actor": "", "ts": 1,
              "assertion": CANDS[0]["assertion"]}],
            POLICY_TIE, 8,
            "candidates with malformed order-field metadata are not live -> absent")

    # effective wave
    r = select(CANDS, POLICY, J, NODE, 8)
    vectors.append({"id": "FV-WAVE-ASSERTION-OVER-PIN", "kind": "wave_fed",
                    "term": "K", "selection": _sel_expected(r),
                    "selected_wave": r["selected"]["assertion"]["wave"],
                    "expected": wave_fed("K", lambda t: r if t == "K" else None),
                    "note": "a selected assertion on K overrides the Trinity pin"})
    vectors.append({"id": "FV-WAVE-STRUCTURAL", "kind": "wave_fed",
                    "term": ["APPLY", "K", "I"], "selection": None, "selected_wave": None,
                    "expected": wave_fed(["APPLY", "K", "I"], lambda t: None),
                    "note": "no assertions anywhere: structural derivation = Book II wave (FALSE derivation)"})
    apply_sel = {"status": "selected", "conflict_set": [],
                 "selected": {"warrant_id": "7" * 64, "actor": "a@x", "ts": 1,
                              "assertion": {"annotation": ASSERTION_TAG, "jurisdiction": J,
                                            "node": "ee" * 32, "epoch": 1,
                                            "wave": W(1, 2, 3)}}}
    vectors.append({"id": "FV-WAVE-APPLY-ASSERTION-OVERRIDES", "kind": "wave_fed",
                    "term": ["APPLY", "K", "I"],
                    "selection": _sel_expected(apply_sel),
                    "selected_wave": W(1, 2, 3),
                    "expected": wave_fed(["APPLY", "K", "I"],
                                         lambda t: apply_sel if t == ["APPLY", "K", "I"] else None),
                    "note": "a direct assertion on an APPLY node overrides structural derivation"})

    ph = sha_hex(jcs(POLICY))
    vectors.append({"id": "FV-VIEW-ID", "kind": "view_id",
                    "jurisdiction": J, "node": NODE, "policy_hash": ph, "epoch": 8,
                    "expected": view_id(J, NODE, ph, 8),
                    "note": "jurisdiction-bound per-node view COORDINATE (not a content hash: "
                            "the verifiable projection is (ViewID, assertion_set_root))"})
    vectors.append({"id": "FV-SET-ROOT", "kind": "assertion_set_root",
                    "warrant_ids": ["2" * 64, "1" * 64, "3" * 64],
                    "expected": assertion_set_root(["2" * 64, "1" * 64, "3" * 64]),
                    "note": "order-insensitive set commitment (NOT zero-knowledge: small "
                            "universes are enumerable; see Book III s6)"})
    w1, w2, w3 = W(0, 65535, 0), W(16384, 65535, 0), W(16384, 65535, 0)
    vectors.append({"id": "FV-FOLD-UNSOUND", "kind": "fold_probe",
                    "w1": w1, "w2": w2, "w3": w3,
                    "expected": {"left": interfere(interfere(w1, w2), w3),
                                 "right": interfere(w1, interfere(w2, w3))},
                    "note": "grouping alone changes the result (16384 vs 32768): "
                            "interfere() is not a merge; normative MUST NOT in s1"})
    fx = _book1_fixture()
    vectors.append({"id": "FV-BOOK-I-UNREACHABLE", "kind": "book1_unreachable",
                    "expected": fx,
                    "note": "criterion 1 executable: the Book I eval of EV-TV4-IK is "
                            "byte-identical regardless of any annotation state - federation "
                            "is a pure-function domain that eval() cannot observe"})
    doc = {"format": "sigma-glyph-federation-conformance", "format_version": 1,
           "spec_version": "0.6.0",
           "notes": ["Book III (DRAFT) oracle: impl/sigma_federation.py; selection-only "
                     "federation per ADR-006 gate 3/3 (F1-strict).",
                     "string order fields compare by Unicode scalar values directly; desc "
                     "inverts the comparison (complement transforms are nonconforming).",
                     "expected values computed by the oracle; regenerate: "
                     "python3 impl/sigma_federation.py gen"],
           "vectors": vectors}
    VEC_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {VEC_PATH.name}: {len(vectors)} vectors")


def selftest():
    ok = []

    def chk(name, cond, detail=""):
        ok.append(cond)
        print(("OK  " if cond else "FAIL"), name, "" if cond else detail)

    chk("assertion schema closed", validate_assertion(
        {**CANDS[0]["assertion"], "x": 1}) is not None)
    chk("policy rejects unverifiable fields", validate_policy(
        {"federation_policy": POLICY_TAG,
         "order": [{"field": "truth", "dir": "desc"}]}) is not None)
    r = select(CANDS, POLICY, J, NODE, 8)
    chk("latest-live wins with id tiebreak", r["status"] == "selected"
        and r["selected"]["warrant_id"] == "2" * 64)
    r2 = select(CANDS, POLICY_TIE, J, NODE, 8)
    chk("genuine tie -> ConflictSet", r2["status"] == "conflict"
        and r2["conflict_set"] == ["2" * 64, "3" * 64])
    chk("conflict poisons wave to absent",
        wave_fed("K", lambda t: r2 if t == "K" else None) is None)
    chk("assertion overrides pin",
        wave_fed("K", lambda t: r if t == "K" else None) == W(16384, 30000, 50))
    chk("no assertions -> Book II wave",
        wave_fed(["APPLY", "K", "I"], lambda t: None) == W(32768, 0, -32512))
    da = select([_cand("1", "a", 1, 1, W(0, 1, 0)), _cand("2", "aa", 1, 1, W(0, 2, 0))],
                POLICY_ACTOR_DESC, J, NODE, 1)
    chk("actor desc: 'aa' beats 'a' (prefix pair)",
        da["selected"]["actor"] == "aa")
    na = select([_cand("1", "\u0100gent", 1, 1, W(0, 1, 0)), _cand("2", "agent", 1, 1, W(0, 2, 0))],
                POLICY_ACTOR_DESC, J, NODE, 1)
    chk("actor desc total over non-ASCII", na["selected"]["actor"] == "\u0100gent")
    nf = select([_cand("1", "a@x", 1, 1, W(0, 1, 0)),
                 _cand("2", "b@y", 1, 9, W(0, 2, 0), node="dd" * 32)],
                POLICY_TIE, J, NODE, 9)
    chk("selection is node-bound", nf["selected"]["warrant_id"] == "1" * 64)
    fu = select([_cand("1", "a@x", 1, 8, W(0, 1, 0)), _cand("2", "b@y", 1, 9, W(0, 2, 0))],
                POLICY_TIE, J, NODE, 8)
    chk("future assertions not live", fu["selected"]["warrant_id"] == "1" * 64)
    q = select([_cand("1", "s@a", 100, 5, W(0, 100, 0)), _cand("2", "s@a", 200, 5, W(0, 200, 0))],
               POLICY_TS, J, NODE, 5)
    chk("quota survivors follow policy order", q["selected"]["warrant_id"] == "2" * 64)
    bm = select([{"warrant_id": "nope", "actor": "a@x", "ts": 1,
                  "assertion": CANDS[0]["assertion"]}], POLICY_TIE, J, NODE, 8)
    chk("malformed metadata not live", bm["status"] == "absent")
    chk("set root order-insensitive",
        assertion_set_root(["1" * 64, "2" * 64]) == assertion_set_root(["2" * 64, "1" * 64]))
    chk("view id closed and deterministic",
        view_id(J, NODE, "dd" * 32, 8) == view_id(J, NODE, "dd" * 32, 8))
    fx = _book1_fixture()
    chk("Book I unreachable (eval matches suite regardless of annotations)",
        fx["matches_book1_suite"])

    if VEC_PATH.exists():
        doc = json.loads(VEC_PATH.read_text())
        for v in doc["vectors"]:
            k = v["kind"]
            if k == "validate_assertion":
                got = validate_assertion(v["doc"])
            elif k == "validate_policy":
                got = validate_policy(v["doc"])
            elif k == "select":
                got = _sel_expected(select(v["candidates"], v["policy"],
                                           v["jurisdiction"], v["node"], v["epoch"]))
            elif k == "wave_fed":
                if v["selected_wave"] is not None:
                    sel = {"status": "selected", "conflict_set": [],
                           "selected": {"assertion": {"wave": v["selected_wave"]}}}
                    got = wave_fed(v["term"], lambda t: sel if t == v["term"] else None)
                else:
                    got = wave_fed(v["term"], lambda t: None)
            elif k == "view_id":
                got = view_id(v["jurisdiction"], v["node"], v["policy_hash"], v["epoch"])
            elif k == "assertion_set_root":
                got = assertion_set_root(v["warrant_ids"])
            elif k == "fold_probe":
                got = {"left": interfere(interfere(v["w1"], v["w2"]), v["w3"]),
                       "right": interfere(v["w1"], interfere(v["w2"], v["w3"]))}
            elif k == "book1_unreachable":
                got = _book1_fixture()
            else:
                got = f"unknown kind {k}"
            chk(f"vector {v['id']}", got == v["expected"], f"got {got}")
    else:
        chk("federation_vectors.json present", False,
            "run: python3 impl/sigma_federation.py gen")

    print(("\nFEDERATION: ALL PASS" if all(ok) else "\nFEDERATION: FAILURES PRESENT")
          + f" ({sum(ok)}/{len(ok)})")
    return all(ok)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gen":
        gen_vectors()
    else:
        sys.exit(0 if selftest() else 1)
