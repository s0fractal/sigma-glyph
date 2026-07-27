#!/usr/bin/env python3
"""Resonant Precedent — WARRANT RUNTIME INTEGRATION behind ADR-008 rev 7,
answering the Codex rev-6 gate (2026-07-26). Illustrative, NON-NORMATIVE.

This is a PROTOTYPE WRAPPER around `W.verify_store` — NOT the single-context
public verifier WRT-001 ultimately requires (that is a real Warrant change). It
demonstrates the runtime contract:

  1. NON-RETROACTIVE version. `wave@v1` is permitted only under a NEW body
     version tag; "0.2" bytes are untouched, so a clean Warrant verifier rejects
     a wave record as an unknown version (never re-interprets 0.2).
  2. Dispatched via `verify_store` (wrapper), TOTAL over the byte domain, and
     FAIL-CLOSED: a requested settlement verification whose context cannot be
     built is a global error, never a silent zero.
  3. LIVE-HEAD index (R0, explicitly named). The candidate universe is
     `settlement_active_for(jurisdiction)` MINUS only the current citation
     WarrantID (bound by `citation.subject == check.entry`). A citation is a
     claim as of its verification head; store growth STALES it (shown below). A
     non-manipulable historical checkpoint (immune to growth) is R1 and needs
     key-state — deferred BEFORE budget.
  4. RULESET binds semantics. Exactly one governed anchor-set (real Book II/III
     Specification Anchors + profile); any other ruleset is unverified.

§7 novelty/tunnel is PROPOSED-AND-DEFERRED: the real Warrant `fingerprint()`
still returns None for a wave reason (not yet integrated). Also deferred, in
order: key-state (→ R1 checkpoint), budget, abstention vectors, Go/Rust parity.

    $ python3 examples/resonant_precedent_join_probe.py
"""
import os
import sys
import json
import shutil
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "impl"))
import sigma_wave as sw
import sigma_federation as sf


def _load_warrant():
    cand = Path.home() / "Projects/warrant/impl/warrant.py"
    if not cand.exists():
        return None
    spec = importlib.util.spec_from_file_location("warrant", cand)
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    return W

W = _load_warrant()
jcs, sha_hex = sf.jcs, sf.sha_hex
H = lambda s: sha_hex(s.encode())

PROJ_TAG = "sigma-glyph.precedent-projection@v1"
ENTRY_TAG = "sigma-glyph.precedent-entry@v1"
VIEW_TAG = "sigma-glyph.precedent-index-view@v1"
CHECK_TAG = "sigma-glyph.wave@v1"
PPOLICY_TAG = "sigma-glyph.projection-policy@v1"
ANCHOR_TAG = "sigma-glyph.anchor-set@v1"
VOCAB_TAG = "sigma-glyph.vocabulary-set@v1"
METRIC = "coherence.lut-cos@v1"
WAVE_RUNTIME = "sigma-glyph.wave@v1"
WAVE_VERSION = "0.2+sigma-wave.1"          # NON-RETROACTIVE: distinct body version

# the ONE governed ruleset this runtime implements — REAL governed Specification
# Anchors from sigma-glyph spec/ANCHORS.txt (v0.6.6), not symbolic labels.
# Book I is unreachable; NodeHash identity is the only narrow Book I dependency.
BOOK_II = "7733dfb0876db9a8b243864745acffa671cef7641517a9bb7774af1aef5d01fe"   # spec/book-2-navigation.md
BOOK_III = "e7bdbac8047cc3ae1d811cec11f7caf23b488e8260b83e1bf91a9997e917f1ef"  # spec/book-3-federation.md
# profile anchor is PROVISIONAL until ADR-008 is itself anchored via GOV-anchors
PROFILE_ANCHOR = "a9096dd245ab474cabc8811f1d452bb05489eddc3dc3d348e7ebd3d2497557e3"  # sha256(ADR-008), provisional
RULESET_OBJ = {"anchor_set": ANCHOR_TAG, "books": sorted({BOOK_II, BOOK_III, PROFILE_ANCHOR})}
WAVE_RULESET = sha_hex(jcs(RULESET_OBJ))

# --- WRT-001 §8 re-execution budget (prototype) --------------------------------
# Deterministic integer cost meter: +(1 + len(raw)) per blob resolved (the 1 =
# resolution/digest, len = materialization). A citation commits check["budget"];
# the local re-execution cap below mirrors ski@v1's SKI_REEXEC_MAX_ATP.
WAVE_MAX_COST = 10_000_000
_METER = {"cost": 0}


def effective_active(sctx):
    """CANDIDATE derivation (NOT a closed contract). Warrant `active_records` is
    ELIGIBILITY, not effective lifecycle: a record marked `supersede`d (SPEC §7)
    is still eligible. This subtracts every active-supersede target so a
    superseded assertion cannot win `select()` and a superseded projection is not
    counted.

    ⚠ UNSAFE without authorization (Codex refactor gate P1): Warrant eligibility
    only checks a self-signature, so ANY self-signed actor can supersede ANOTHER
    actor's WarrantID and censor it (demonstrated in main as a KNOWN-OPEN gap).
    An authorized effective supersede needs target-policy / key-state binding —
    so effective-lifecycle and key-state (deferred items 1+2) are NOT separable
    and both precede R1/budget. Supersede-of-supersede is also undefined here."""
    active = sctx["active_records"]
    superseded = set()
    for wid in active:
        b = sctx["recs"].get(wid, {}).get("body", {})
        if isinstance(b, dict) and b.get("decision") == "supersede":
            subj = b.get("subject", {})
            if isinstance(subj, dict) and isinstance(subj.get("hash"), str):
                superseded.add(subj["hash"])
    return active - superseded


def wave_fingerprint(reason, store):
    """§7 outcome fingerprint for wave@v1 — deterministic, recomputable from the
    check blob (belongs in Warrant's fingerprint() dispatcher; see the Warrant
    runtime ADR). Returns None if the check does not resolve."""
    chk, e = load(store, reason.get("check"), v_check)
    if e:
        return None
    entry, e = load(store, chk["entry"], v_entry)
    if e:
        return None
    return (WAVE_RUNTIME, chk["entry"], chk["query_assertion"], chk["threshold"],
            chk["ruleset"], reason.get("verdict"))

SCRATCH = Path(os.environ.get("SIGMA_SCRATCH",
    "/private/tmp/claude-501/-Users-s0fractal/"
    "b787f763-8abf-4237-b1c9-92e5983b9090/scratchpad")) / "rp_fixture"
KEY_SEED = "33" * 32


# ---------- loaders / schemas -------------------------------------------------
def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)
def _is_int16(v):
    return isinstance(v, int) and not isinstance(v, bool) and -32768 <= v <= 32767
def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError("dup")
        d[k] = v
    return d
def _sorted_hex_set(x):
    return isinstance(x, list) and all(_is_hex64(i) for i in x) and list(x) == sorted(set(x))

def load(store, h, validator):
    if not _is_hex64(h):
        return None, "hash not hex64"
    p = store.blobs / h
    if not p.exists():
        return None, "unresolved reference"
    raw = p.read_bytes()
    _METER["cost"] += 1 + len(raw)                      # WRT-001 §8: 1 + bytes read
    if sha_hex(raw) != h:
        return None, "digest mismatch"
    try:
        obj = json.loads(raw.decode(), object_pairs_hook=_no_dupes)
    except (ValueError, UnicodeDecodeError):
        return None, "malformed/dup JSON"
    if jcs(obj) != raw:
        return None, "non-canonical bytes"
    err = validator(obj)
    return (None, err) if err else (obj, None)

def v_projection(d):
    if not isinstance(d, dict) or set(d) != {"projection", "source_warrant",
            "source_subject", "profile", "term", "vocabulary"}:
        return "projection field set"
    if d["projection"] != PROJ_TAG:
        return "projection tag"
    return next((f"{k} hex64" for k in ("source_warrant", "source_subject",
                "profile", "term", "vocabulary") if not _is_hex64(d[k])), None)
def v_ppolicy(d):
    if not isinstance(d, dict) or set(d) != {"projection_policy", "vocabulary"}:
        return "ppolicy field set"
    return None if (d["projection_policy"] == PPOLICY_TAG and _is_hex64(d["vocabulary"])) else "ppolicy contents"
def v_anchorset(d):
    if not isinstance(d, dict) or set(d) != {"anchor_set", "books"}:
        return "anchor-set field set"
    if d["anchor_set"] != ANCHOR_TAG:
        return "anchor-set tag"
    return None if _sorted_hex_set(d["books"]) and d["books"] else "books sorted set"
def v_vocab(d):
    if not isinstance(d, dict) or set(d) != {"vocabulary", "leaves"}:
        return "vocab field set"
    if d["vocabulary"] != VOCAB_TAG:
        return "vocab tag"
    return None if _sorted_hex_set(d["leaves"]) else "leaves sorted set"
def v_view(d):
    if not isinstance(d, dict) or set(d) != {"view", "jurisdiction", "genesis_roots",
            "projection_profile", "metric", "sigma_ruleset", "wave_selection_policy",
            "active_warrant_set_commit", "epoch"}:
        return "view field set"
    if d["view"] != VIEW_TAG or d["metric"] != METRIC:
        return "view tag/metric"
    for k in ("jurisdiction", "projection_profile", "sigma_ruleset",
              "wave_selection_policy", "active_warrant_set_commit"):
        if not _is_hex64(d[k]):
            return f"{k} hex64"
    if not _sorted_hex_set(d["genesis_roots"]):
        return "genesis_roots set"
    if not (isinstance(d["epoch"], int) and not isinstance(d["epoch"], bool) and 0 <= d["epoch"] < (1 << 64)):
        return "epoch"
    return None
def v_entry(d):
    if not isinstance(d, dict) or set(d) != {"entry", "decision_warrant",
            "projection_warrant", "projection", "wave_assertion_warrant",
            "wave_assertion", "index_view"}:
        return "entry field set"
    if d["entry"] != ENTRY_TAG:
        return "entry tag"
    return next((f"{k} hex64" for k in ("decision_warrant", "projection_warrant",
                "projection", "wave_assertion_warrant", "wave_assertion",
                "index_view") if not _is_hex64(d[k])), None)
def v_check(d):
    base = {"check", "entry", "query_assertion", "threshold", "ruleset"}
    if not isinstance(d, dict) or set(d) not in (base, base | {"budget"}):
        return "check field set"
    if d["check"] != CHECK_TAG:
        return "check tag"
    if not (_is_hex64(d["entry"]) and _is_hex64(d["query_assertion"]) and _is_hex64(d["ruleset"])):
        return "check hashes"
    if "budget" in d and not (isinstance(d["budget"], int) and not isinstance(d["budget"], bool)
                              and 0 <= d["budget"] < (1 << 32)):
        return "budget uint32"
    return None if _is_int16(d["threshold"]) else "threshold int16"

def coherence(wq, wc):
    dd = abs(wq["ph"] - wc["ph"])
    return sw.LUT_COS[min(dd, 65536 - dd)]


class _Ctx:
    def __init__(self, store, active):
        self.store, self.active = store, set(active)
    def _b(self, wid):
        rec = self.store.get_record(wid) if _is_hex64(wid) else None
        return rec["body"] if rec else None
    def subject_hash(self, wid):
        b = self._b(wid); return b["subject"]["hash"] if b else None
    def under(self, wid):
        b = self._b(wid); return list(b["under"]) if b else []
    def decision(self, wid):
        b = self._b(wid); return b["decision"] if b else None
    def actor(self, wid):
        b = self._b(wid); return b["actor"]["id"] if b else None
    def ts(self, wid):
        b = self._b(wid); return b["ts"] if b else None


# ---------- the runtime: derives its own snapshot; binds the ruleset ----------
def verify_citation(check_hash, cw_wid, sctx, store, use_effective=True):
    _METER["cost"] = 0                                  # WRT-001 §8: fresh cost meter
    chk, e = load(store, check_hash, v_check)
    if e: return "unverified", f"check: {e}"
    # RULESET binds semantics: this runtime implements exactly one governed set
    if chk["ruleset"] != WAVE_RULESET:
        return "unverified", "unsupported ruleset (runtime binds one anchor-set)"
    # §8 over-cap: a committed budget beyond the local re-execution cap is
    # unaffordable to re-verify -> unverified (mirrors ski@v1 atp-over-cap).
    if "budget" in chk and chk["budget"] > WAVE_MAX_COST:
        return "unverified", "budget exceeds re-execution cap"
    _, e = load(store, chk["ruleset"], v_anchorset)
    if e: return "unverified", f"ruleset anchor: {e}"
    entry, e = load(store, chk["entry"], v_entry)
    if e: return "unverified", f"entry: {e}"
    view, e = load(store, entry["index_view"], v_view)
    if e: return "unverified", f"view: {e}"
    if view["sigma_ruleset"] != chk["ruleset"]:
        return "unverified", "view ruleset != check ruleset"

    # R1 STORED-citation binding: the reason-bearing record's subject MUST be the
    # entry (legitimises the citation and rejects a borrowed reason). Skipped for
    # a genuine R0 direct query (cw_wid is None): a query files no Warrant, so
    # there is no citation WarrantID to bind or to subtract from the universe.
    if cw_wid is not None:
        cw_body = sctx["recs"].get(cw_wid, {}).get("body") if isinstance(sctx["recs"].get(cw_wid), dict) else None
        if not (isinstance(cw_body, dict) and cw_body.get("subject", {}).get("hash") == chk["entry"]):
            return "unverified", "reason-bearing Warrant subject != check.entry"

    # LIVE-HEAD semantics (R0, explicitly named — see WRT-001 §temporal): the
    # candidate universe is settlement_active_for(J) MINUS only THIS citation
    # WarrantID (never "any record carrying a wave reason" — that let a rival
    # assertion erase itself from selection). A citation is a claim as of its
    # verification head; store growth makes it `stale` and requires re-citation.
    # A non-manipulable historical checkpoint (immune to growth) is R1 and needs
    # key-state — deferred BEFORE budget.
    J = view["jurisdiction"]
    record_roots = sctx["record_roots"]
    # R0 (a query, use_effective=False) ranks over RAW settlement eligibility, so a
    # foreign self-signed `supersede` cannot change a query result. The authorized
    # effective set is R1-only (needs key-state); the naïve effective_active is used
    # only by the R1-anticipating path as an explicitly-failing research vector.
    eff = effective_active(sctx) if use_effective else sctx["active_records"]
    index = {w for w in eff if J in record_roots(w) and w != cw_wid}
    if view["active_warrant_set_commit"] != sf.assertion_set_root(sorted(index)):
        return "unverified", "live-head effective set != view commitment (stale or tampered)"
    if J not in view["genesis_roots"]:
        return "unverified", "jurisdiction not in genesis_roots"
    ctx = _Ctx(store, index)

    c0, e = load(store, entry["projection"], v_projection)
    if e: return "unverified", f"C0: {e}"
    if view["projection_profile"] != c0["profile"]:
        return "unverified", "C0 profile != view profile"
    ppol, e = load(store, c0["profile"], v_ppolicy)
    if e: return "unverified", f"projection policy: {e}"
    if c0["vocabulary"] != ppol["vocabulary"]:
        return "unverified", "C0 vocabulary != governed vocabulary"
    _, e = load(store, ppol["vocabulary"], v_vocab)
    if e: return "unverified", f"vocabulary anchor: {e}"
    cited, e = load(store, entry["wave_assertion"], sf.validate_assertion)
    if e: return "unverified", f"cited: {e}"
    query, e = load(store, chk["query_assertion"], sf.validate_assertion)
    if e: return "unverified", f"query: {e}"

    dw, pw, aw = entry["decision_warrant"], entry["projection_warrant"], entry["wave_assertion_warrant"]
    if c0["source_warrant"] != dw:
        return "unverified", "C0 source_warrant != decision_warrant"
    if dw not in ctx.active:
        return "unverified", "decision inactive/out of snapshot"
    if ctx.subject_hash(dw) != c0["source_subject"]:
        return "unverified", "decision subject != C0 source_subject"
    if pw not in ctx.active:
        return "unverified", "projection inactive/out of snapshot"
    if ctx.decision(pw) != "accept":
        return "unverified", f"projection decision {ctx.decision(pw)} != accept"
    if ctx.subject_hash(pw) != entry["projection"]:
        return "unverified", "projection subject != C0 blob"
    if ctx.under(pw) != [c0["profile"]]:
        return "unverified", "projection under != [profile]"
    rivals = []
    for wid in ctx.active:
        h = ctx.subject_hash(wid)
        cand, err = (load(store, h, v_projection) if h else (None, "x"))
        if not err and cand["source_warrant"] == dw and cand["profile"] == c0["profile"]:
            rivals.append(wid)
    if rivals != [pw]:
        return "unverified", f"projection cardinality ({len(rivals)})"
    if c0["term"] != cited["node"]:
        return "unverified", "C0 term != cited node"
    if aw not in ctx.active:
        return "unverified", "cited assertion inactive/out of snapshot"
    if ctx.decision(aw) != "accept":
        return "unverified", f"assertion decision {ctx.decision(aw)} != accept"
    if ctx.subject_hash(aw) != entry["wave_assertion"]:
        return "unverified", "assertion subject != assertion blob"
    if cited["jurisdiction"] != J:
        return "unverified", "cited jurisdiction != view jurisdiction"
    selpol, e = load(store, view["wave_selection_policy"], sf.validate_policy)
    if e: return "unverified", f"selection policy: {e}"
    cands = []
    for wid in ctx.active:
        h = ctx.subject_hash(wid)
        ab, err = (load(store, h, sf.validate_assertion) if h else (None, "x"))
        if err or ctx.decision(wid) != "accept":
            continue
        cands.append({"warrant_id": wid, "actor": ctx.actor(wid), "ts": ctx.ts(wid), "assertion": ab})
    sel = sf.select(cands, selpol, J, cited["node"], view["epoch"])
    if sel["status"] != "selected" or sel["selected"]["warrant_id"] != aw:
        return "unverified", f"cited loses selection ({sel['status']})"

    # §8 exhaustion: enforce the committed budget over the accrued cost. (Spec
    # requires stopping mid-evaluation with bounded reads; this prototype meters
    # the full cost and enforces at the end — same verdict on the exact/one-under
    # boundary; the mid-way stop is the anti-DoS refinement a real runtime adds.)
    if "budget" in chk and _METER["cost"] > chk["budget"]:
        return "unverified", f"budget exhausted (cost={_METER['cost']} > budget={chk['budget']})"
    coh = coherence(query["wave"], cited["wave"])
    return ("pass" if coh >= chk["threshold"] else "fail"), f"coherence={coh}"


def verify_query(check_hash, sctx, store):
    """GENUINE R0 ephemeral query — files no Warrant. Ranks over RAW settlement
    eligibility (use_effective=False), with NO citation to bind or subtract
    (cw_wid=None), so an unauthorized `supersede` cannot alter a query result. A
    non-settlement retrieval answer, never a stored reason. Authorized effective
    lifecycle is R1-only."""
    return verify_citation(check_hash, None, sctx, store, use_effective=False)


# ---------- non-retroactive registration + total dispatcher in verify_store ---
def install_wave_runtime(W):
    if WAVE_VERSION not in W.ACCEPTED:
        W.ACCEPTED = tuple(W.ACCEPTED) + (WAVE_VERSION,)
    W.RUNTIMES[WAVE_VERSION] = ("cmd@v1", "ski@v1", WAVE_RUNTIME)
    orig = W.verify_store
    if getattr(orig, "_wave_wrapped", False):
        return

    def dispatch(store, sctx):
        """TOTAL and FAIL-CLOSED. sctx is None when context construction failed:
        every wave reason is then `unverified` and — since activeness cannot be
        proven — counted as ERR (never silently zero)."""
        de = dw = 0
        recs = sctx["recs"] if sctx else store.all_records()
        active = sctx["active_records"] if sctx else None
        for wid, env in recs.items():
            if not isinstance(env, dict):
                continue
            body = env.get("body")
            if not isinstance(body, dict):
                continue
            because = body.get("because")
            if not isinstance(because, list):
                continue
            for r in because:
                if not isinstance(r, dict) or r.get("kind") != "check" or r.get("runtime") != WAVE_RUNTIME:
                    continue
                if sctx is None:
                    verdict = "unverified"             # FAIL-CLOSED, not a silent pass
                else:
                    try:
                        verdict, _ = verify_citation(r.get("check"), wid, sctx, store)
                    except Exception:
                        verdict = "unverified"
                if verdict == "unverified" or verdict != r.get("verdict"):
                    if active is None or wid in active:
                        de += 1
                    else:
                        dw += 1
        return de, dw

    def wrapped(store, quiet=False, settlement=None):
        # PROTOTYPE WRAPPER (not the single-context public verifier WRT-001
        # requires — that is a real Warrant change). It approximates the contract:
        # if a settlement verification was REQUESTED but its context cannot be
        # built, that is a GLOBAL fail-closed ERR — the requested verification did
        # not happen — independent of whether any wave reason is present.
        ctx_failed = False
        sctx = None
        if settlement is not None:
            try:
                sctx = W._settlement_context(store, settlement.get("trust_config"),
                                             settlement.get("genesis_roots"))
            except Exception:
                ctx_failed = True
        e, w = orig(store, quiet=quiet, settlement=settlement if sctx is not None else None)
        de, dw = dispatch(store, sctx)
        if ctx_failed:
            de += 1                                     # requested settlement never happened
        return e + de, w + dw

    wrapped._wave_wrapped = True
    W.verify_store = wrapped


# ============================ hermetic fixture ================================
def build(**o):
    if W is None:
        raise RuntimeError("warrant impl not found")
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    store = W.Store(str(SCRATCH)); store.init()
    keyp = SCRATCH / "k.hex"; keyp.write_text(KEY_SEED)
    trust = SCRATCH / "trust.json"
    ACTOR = "fixture@sigma"

    def put(obj):
        return store.put_blob(jcs(obj))
    def putb(b):
        return store.put_blob(b)
    def file_w(decision, subject_hash, under, prior, because=None, version="0.2"):
        body = {"warrant": version, "decision": decision,
                "subject": {"hash": subject_hash}, "under": list(under),
                "because": because or ([] if decision in ("propose", "accept") else [{"kind": "prose", "text": "x"}]),
                "evidence": [], "actor": {"id": ACTOR}, "prior": list(prior), "ts": 1_700_000_000}
        errs = W.validate_body(body)
        assert not errs, errs
        env = {"body": body, "sigs": [W.sign_envelope(body, ACTOR, str(keyp))]}
        return store.put_record(env)

    E = o.get("epoch", 5)
    vocab_blob = put({"vocabulary": VOCAB_TAG, "leaves": sorted({H("I"), H("S"), H("K")})})
    ruleset = put(RULESET_OBJ)                          # the governed ruleset resolves
    if o.get("evil_ruleset"):                           # well-shaped but ungoverned (distinct hash)
        evil = put({"anchor_set": ANCHOR_TAG, "books": sorted({H("evil-1"), H("evil-2")})})
        o = {**o, "view_ruleset": evil, "check_ruleset": evil}
    ppolicy = put({"projection_policy": PPOLICY_TAG, "vocabulary": vocab_blob})
    selpolicy = put({"federation_policy": sf.POLICY_TAG, "order": [{"field": "epoch", "dir": "desc"}]})
    base_pol = put({"kind": "generic-policy"})

    genesis_subject = putb(b"genesis-jurisdiction-subject")
    R = file_w("accept", genesis_subject, [base_pol], [])
    JUR = R
    trust.write_text(json.dumps({"genesis_roots": [R]}))

    subject = putb(b"the-decided-subject-bytes")
    D = file_w(o.get("decision_dec", "accept"), subject, [base_pol], [R])
    cited = {"annotation": sf.ASSERTION_TAG, "jurisdiction": o.get("cited_jur", JUR),
             "node": o.get("cited_node", H("term-N")), "epoch": o.get("cited_epoch", E),
             "wave": o.get("cited_wave", {"ph": 16384, "am": 65535, "en": -32768})}
    cited_h = put(cited)
    AW = file_w(o.get("assertion_dec", "accept"), cited_h, [base_pol], [R])
    c0 = {"projection": PROJ_TAG, "source_warrant": D,
          "source_subject": o.get("c0_source_subject", subject),
          "profile": o.get("c0_profile", ppolicy), "term": o.get("c0_term", H("term-N")),
          "vocabulary": o.get("c0_vocab", vocab_blob)}
    c0_h = put(c0)
    PW = file_w(o.get("proj_dec", "accept"), c0_h, o.get("pw_under", [ppolicy]), [R])
    proj_warrant = PW
    if o.get("supersede_projection"):                  # replace the projection
        file_w("supersede", PW, [base_pol], [R])       # old PW no longer effective
        proj_warrant = file_w("accept", c0_h, [ppolicy], [PW])  # distinct WID (prior=[PW])
    if o.get("supersede_cited"):                        # replace the cited assertion
        file_w("supersede", AW, [base_pol], [R])       # AW no longer effective
    if o.get("unauth_supersede"):                       # KNOWN-OPEN: a FOREIGN actor censors AW
        kp2 = SCRATCH / "k2.hex"; kp2.write_text("44" * 32)
        b = {"warrant": "0.2", "decision": "supersede", "subject": {"hash": AW},
             "under": [base_pol], "because": [{"kind": "prose", "text": "censor"}],
             "evidence": [], "actor": {"id": "attacker@evil"}, "prior": [R], "ts": 1_700_000_000}
        assert not W.validate_body(b), W.validate_body(b)
        store.put_record({"body": b, "sigs": [W.sign_envelope(b, "attacker@evil", str(kp2))]})

    # rivals are settlement-active but NOT put in CW.prior — the checkpoint
    # universe is settlement-derived, so the filer cannot hide them.
    if o.get("second_projection"):
        c0b = dict(c0); c0b["term"] = H("other")
        file_w("accept", put(c0b), [ppolicy], [R])
    if o.get("competitor"):
        riv = {"annotation": sf.ASSERTION_TAG, "jurisdiction": JUR, "node": H("term-N"),
               "epoch": o.get("competitor_epoch", E), "wave": {"ph": 16384, "am": 30000, "en": 0}}
        file_w("accept", put(riv), [base_pol], [R])
    if o.get("borrowed_reason"):
        # a LIVE (epoch == view epoch, > the cited epoch) settlement-active rival
        # assertion that ALSO carries a wave reason. It must NOT vanish from
        # selection just for carrying a reason (role-confusion fix): included, it
        # wins Book III select() and the cited assertion loses.
        riv = {"annotation": sf.ASSERTION_TAG, "jurisdiction": JUR, "node": H("term-N"),
               "epoch": E, "wave": {"ph": 16384, "am": 65535, "en": -32768}}
        file_w("accept", put(riv), [base_pol], [R], version=WAVE_VERSION,
               because=[{"kind": "check", "check": H("borrowed"), "runtime": WAVE_RUNTIME, "verdict": "pass"}])
    if o.get("malformed_inactive"):                    # totality: junk record, must not crash
        env = {"body": {"warrant": "0.2", "decision": "accept", "subject": {"hash": H("x")},
                        "under": [], "because": ["not-an-object"], "evidence": [],
                        "actor": {"id": ACTOR}, "prior": [], "ts": 1}, "sigs": []}
        (store.records / f"{H('junk-record')}.json").write_text(json.dumps(env))

    # the checkpoint the VIEW commits to = settlement-active-for(J) MINUS wave
    # citations (there are none yet — CW is filed last).
    ctx0 = W._settlement_context(store, trust_config=str(trust))
    # R0 query fixtures commit the RAW eligibility set (verify_query ranks over it);
    # R1-anticipating fixtures commit the naïve effective set (research vector).
    eligible = ctx0["active_records"] if o.get("no_file_cw") else effective_active(ctx0)
    universe = {w for w in eligible if JUR in ctx0["record_roots"](w)}
    commit_set = set(universe)
    if o.get("omit_root"):                              # attacker drops the active root from the commit
        commit_set.discard(JUR)

    query_h = put({"annotation": sf.ASSERTION_TAG, "jurisdiction": JUR, "node": H("term-N"),
                   "epoch": E, "wave": o.get("query_wave", {"ph": 16384, "am": 65535, "en": -32768})})
    view = {"view": VIEW_TAG, "jurisdiction": JUR, "genesis_roots": sorted({JUR}),
            "projection_profile": o.get("view_profile", ppolicy), "metric": METRIC,
            "sigma_ruleset": o.get("view_ruleset", ruleset), "wave_selection_policy": selpolicy,
            "active_warrant_set_commit": sf.assertion_set_root(sorted(commit_set)), "epoch": E}
    view_h = put(view)
    entry = {"entry": ENTRY_TAG, "decision_warrant": D, "projection_warrant": proj_warrant,
             "projection": c0_h, "wave_assertion_warrant": AW, "wave_assertion": cited_h,
             "index_view": o.get("index_view", view_h)}
    entry_h = put(entry)
    check = {"check": CHECK_TAG, "entry": entry_h, "query_assertion": query_h,
             "threshold": o.get("threshold", 30000), "ruleset": o.get("check_ruleset", ruleset)}
    if o.get("budget") is not None:                     # WRT-001 §8 committed ceiling
        check["budget"] = o["budget"]
    check_h = put(check)

    borrower = None
    if o.get("borrowed_resolvable"):
        # a record with a RESOLVABLE valid check but subject != check.entry:
        # it must fail the subject/entry binding, not "unresolved reference".
        borrower = file_w("accept", H("unrelated-subject"), [base_pol], [R], version=WAVE_VERSION,
                          because=[{"kind": "check", "check": check_h, "runtime": WAVE_RUNTIME, "verdict": "pass"}])

    CW = None
    if not o.get("no_file_cw"):                         # R0 query files NO Warrant
        CW = file_w("accept", entry_h, [base_pol], [R, D, proj_warrant, AW], version=WAVE_VERSION,
                    because=[{"kind": "check", "check": check_h, "runtime": WAVE_RUNTIME,
                              "verdict": o.get("claimed_verdict", "pass")}])
    n_records = len(list(store.records.glob("*.json")))
    return {"store": store, "trust": str(trust), "check_h": check_h, "CW": CW,
            "universe": universe, "JUR": JUR, "borrower": borrower, "n_records": n_records}


def main():
    if W is None:
        print("SKIP: warrant impl not found"); return
    install_wave_runtime(W)
    S = lambda fx: {"trust_config": fx["trust"]}        # the ONE settlement source

    # (1) non-retroactive: a clean 0.2 validator rejects the wave record
    wave_reason = [{"kind": "check", "check": H("c"), "runtime": WAVE_RUNTIME, "verdict": "pass"}]
    body02 = {"warrant": "0.2", "decision": "accept", "subject": {"hash": H("s")}, "under": [H("u")],
              "because": wave_reason, "evidence": [], "actor": {"id": "a"}, "prior": [], "ts": 1}
    saved = W.RUNTIMES["0.2"]; W.RUNTIMES["0.2"] = ("cmd@v1", "ski@v1")
    clean_rejects = bool(W.validate_body(body02))
    W.RUNTIMES["0.2"] = saved
    print("=== (1) NON-RETROACTIVE: clean 0.2 verifier rejects a wave reason under 0.2 ===")
    print(f"  clean 0.2 rejects wave-in-0.2 body: {clean_rejects}   (wave only under {WAVE_VERSION})")

    print("\n=== R0 is a GENUINE non-filing ephemeral query: ===")
    fxq = build(no_file_cw=True)                        # NO citation Warrant filed
    before = fxq["n_records"]
    vq = verify_query(fxq["check_h"], W._settlement_context(fxq["store"], trust_config=fxq["trust"]), fxq["store"])
    after = len(list(fxq["store"].records.glob("*.json")))
    print(f"  CW filed: {fxq['CW'] is not None}   records before/after query: {before}/{after}  (unchanged: {before == after})")
    print(f"  verify_query(...) = {vq}   (no cw_wid, no Warrant reason — a query, not a stored citation)")
    # R0 ranks over RAW eligibility: a foreign self-signed supersede must NOT change it
    fxr = build(no_file_cw=True, unauth_supersede=True)
    vr = verify_query(fxr["check_h"], W._settlement_context(fxr["store"], trust_config=fxr["trust"]), fxr["store"])
    print(f"  R0 under a FOREIGN supersede of the cited assertion = {vr}   (unchanged — censorship formula NOT used)")

    print("\n=== STORED-reason demo via verify_store — ANTICIPATES R1, not permitted R0 ===")
    print("  (a settlement-active wave reason needs the R1 authorized checkpoint;")
    print("   the check/view schema has no R0/R1 mode yet — see WRT-001. Shown for plumbing only.)")
    fx = build()
    errs, warns = W.verify_store(fx["store"], quiet=True, settlement=S(fx))
    warns_loud = W.verify_store(fx["store"], quiet=False, settlement=S(fx))[1]  # honest count
    print(f"  live-head universe: {len(fx['universe'])}   ruleset real anchors: "
          f"{BOOK_II[:8]}…/{BOOK_III[:8]}…")
    print(f"  PUBLIC verify_store (wrapper prototype): {errs} errors; warnings={warns_loud} "
          f"(unbound signatures — key-state deferred; quiet suppresses the count)")
    happy_ok = errs == 0

    print("\n=== LIVE-HEAD staleness (named, not a bug): store growth stales a citation ===")
    fx = build()
    e0, _ = W.verify_store(fx["store"], quiet=True, settlement=S(fx))
    # append one unrelated active record under the same root
    st = fx["store"]
    body = {"warrant": "0.2", "decision": "accept", "subject": {"hash": H("unrelated")},
            "under": [H("p")], "because": [], "evidence": [], "actor": {"id": "fixture@sigma"},
            "prior": [fx["JUR"]], "ts": 1_700_000_000}
    st.put_record({"body": body, "sigs": [W.sign_envelope(body, "fixture@sigma", str(SCRATCH / "k.hex"))]})
    e1, _ = W.verify_store(st, quiet=True, settlement=S(fx))
    print(f"  before append: {e0} err   after unrelated active record: {e1} err "
          f"(R0 is live-head; historical checkpoint = R1, needs key-state)")

    print("\n=== (P1) FAIL-CLOSED: a broken settlement context must NOT verify a lie clean ===")
    fx = build(claimed_verdict="fail")                 # a lie: claims fail, coherence passes
    Path(fx["trust"]).unlink()                          # break the context
    errs_fc, _ = W.verify_store(fx["store"], quiet=True, settlement=S(fx))
    print(f"  lie + deleted trust file -> verify_store errors={errs_fc} (fail-closed: >=1)")

    print("\n=== totality: malformed inactive record must NOT crash ===")
    fx = build(malformed_inactive=True)
    try:
        em, _ = W.verify_store(fx["store"], quiet=True, settlement=S(fx)); crash = False
    except Exception:
        em, crash = None, True
    print(f"  junk record: errors={em} crashed={crash}")
    total_ok = (not crash) and isinstance(errs_fc, int) and errs_fc >= 1

    print("\n=== §7: NOT integrated (obsolete tuple sketch; real fingerprint() is None) ===")
    fx = build()
    rec = fx["store"].get_record(fx["CW"])
    fp = wave_fingerprint(rec["body"]["because"][0], fx["store"])   # sketch: carries CLAIMED verdict
    real = W.fingerprint(rec["body"]["because"][0], rec["body"], fx["store"])
    print(f"  obsolete sketch tuple non-None: {fp is not None} (uses CLAIMED verdict — not §7-valid)")
    print(f"  real Warrant fingerprint(wave reason): {real}   (None => not settlement-novelty-integrated)")

    print("\n=== effective-records (P1-B): supersede lifecycle applied, not raw eligibility ===")
    fxs = build(supersede_cited=True)
    v_sup = verify_citation(fxs["check_h"], fxs["CW"], W._settlement_context(fxs["store"], trust_config=fxs["trust"]), fxs["store"])
    print(f"  superseded cited assertion -> {v_sup[0]} ({v_sup[1]})  (a replaced wave cannot be cited)")
    fxp = build(supersede_projection=True)
    v_prj = verify_citation(fxp["check_h"], fxp["CW"], W._settlement_context(fxp["store"], trust_config=fxp["trust"]), fxp["store"])
    print(f"  superseded projection + replacement -> {v_prj[0]} ({v_prj[1]})  (effective cardinality 1, not 2)")
    fxu = build(unauth_supersede=True)
    v_un = verify_citation(fxu["check_h"], fxu["CW"], W._settlement_context(fxu["store"], trust_config=fxu["trust"]), fxu["store"])
    print(f"  ⚠ KNOWN-OPEN: FOREIGN actor supersede censors AW -> {v_un[0]} ({v_un[1]})")
    print(f"    (any self-signed actor can remove another's record; needs key-state authorization — deferred)")

    print("\n=== WRT-001 §8 re-execution budget (deterministic cost meter) ===")
    sc = lambda fx: W._settlement_context(fx["store"], trust_config=fx["trust"])
    # learn the cost + determinism on ONE store, re-running BEFORE any rebuild
    # (build() wipes the shared scratch, so hold no fixture across a build):
    fx = build(budget=WAVE_MAX_COST)
    ctx = sc(fx)
    v1 = verify_citation(fx["check_h"], fx["CW"], ctx, fx["store"]); C = _METER["cost"]
    verify_citation(fx["check_h"], fx["CW"], ctx, fx["store"]); C2 = _METER["cost"]
    print(f"  happy citation cost = {C}  (verdict {v1[0]}); deterministic re-run: {C == C2}")
    # boundary far from the digit-noise (budget is committed IN the check blob, so
    # its width nudges the cost — exact equality is a fixed point; under/over is clean):
    fu = build(budget=C // 2)
    vu = verify_citation(fu["check_h"], fu["CW"], sc(fu), fu["store"])
    fo = build(budget=C * 2)
    vo = verify_citation(fo["check_h"], fo["CW"], sc(fo), fo["store"])
    fc = build(budget=WAVE_MAX_COST + 1)
    vc = verify_citation(fc["check_h"], fc["CW"], sc(fc), fc["store"])
    print(f"  under-budget (C//2 = {C // 2}) -> {vu}")
    print(f"  over-budget  (C*2  = {C * 2}) -> {vo[0]} ({vo[1]})")
    print(f"  over local re-execution cap  -> {vc}")

    print("\n=== binding edge (P2): a RESOLVABLE borrowed check on a non-citation subject ===")
    fxb = build(borrowed_resolvable=True)
    ctxb = W._settlement_context(fxb["store"], trust_config=fxb["trust"])
    vb, whyb = verify_citation(fxb["check_h"], fxb["borrower"], ctxb, fxb["store"])
    print(f"  borrower (subject != entry, valid check) -> {vb}: {whyb}")

    print("\n=== negatives -> public verify_store MUST report >=1 error (active citation) ===")
    edges = {
        "projection is reject":       dict(proj_dec="reject"),
        "assertion is reject":        dict(assertion_dec="reject"),
        "wrong source_subject":       dict(c0_source_subject=H("other")),
        "under != [profile]":         dict(pw_under=[H("p1"), H("p2")]),
        "assertion wrong node":       dict(cited_node=H("other")),
        "foreign jurisdiction":       dict(cited_jur=H("jur-B")),
        "rival wins (in prior or not)": dict(cited_epoch=4, competitor=True),
        "rival borrows a wave reason": dict(cited_epoch=4, borrowed_reason=True),
        "superseded cited assertion": dict(supersede_cited=True),
        "view omits active root":     dict(omit_root=True),
        "second active projection":   dict(second_projection=True),
        "vocabulary mismatch":        dict(c0_vocab=H("rogue")),
        "wrong index_view":           dict(index_view=H("ghost")),
        "well-shaped evil ruleset":   dict(evil_ruleset=True),
        "claimed verdict lie (fail)": dict(claimed_verdict="fail"),
    }
    ok = happy_ok and total_ok
    for name, o in edges.items():
        try:
            fx = build(**o)
            errs_n, _ = W.verify_store(fx["store"], quiet=True, settlement=S(fx))
        except Exception as ex:
            errs_n, ok = f"CRASH:{ex!r}", False
        caught = isinstance(errs_n, int) and errs_n >= 1
        if not caught:
            ok = False
        print(f"  {name:30} -> verify_store errors={errs_n}  caught={caught}")

    print(f"\nHAPPY 0-err + fail-closed + total + every negative caught: {ok}")


if __name__ == "__main__":
    main()
