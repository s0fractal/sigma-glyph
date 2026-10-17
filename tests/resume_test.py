#!/usr/bin/env python3
"""sigma-resume draft reference (impl/sigma_resume.py) against the redesign's
test matrix, N01-N37 (Documents/Codex/2026-10-17/sigma-warrant-redesign).

Each case names its N-id and checks the reason, not only that something failed.
Cases the reference deliberately does not implement are reported UNRUN with the
reason; an UNRUN is not a pass and the summary says so.
"""
import itertools
import sys
from pathlib import Path

import os  # noqa: E402
# RESUME_IMPL lets tests/resume_mutants.py run this file against a mutated copy.
sys.path.insert(0, os.environ.get("RESUME_IMPL") or str(Path(__file__).resolve().parents[1] / "impl"))
import sigma_glyph as G      # noqa: E402
import sigma_resume as R     # noqa: E402

results = {}


def case(nid, ok, what, detail=""):
    results[nid] = "PASS" if ok else "FAIL"
    print(("ok    " if ok else "FAIL  ") + f"{nid} {what}" + ("" if ok else f" | {detail}"))


def unrun(nid, why):
    results[nid] = "UNRUN"
    print(f"UNRUN {nid} {why}")


class Delivered(dict):
    """A byte store that counts reads, so a test can see whether a fetch happened."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.reads = 0

    def get(self, h, default=None):
        self.reads += 1
        return super().get(h, default)


def app(l, r):
    return G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=l, right=r)


def build(*nodes):
    """Store nodes; returns (Delivered, hashes)."""
    d = Delivered()
    hs = []
    for b in nodes:
        h = G.node_hash(b)
        d[h] = b
        hs.append(h)
    return d, hs


def env_for(d, extra=()):
    return R.Environment(list(d.keys()) + list(extra), d)


def fresh(term_hash, env):
    rt = R.root(term_hash, env)
    doc, cid, sb = R.start(rt[1], term_hash)
    return rt, doc, cid, sb


I, K, S = G.I_H, G.K_H, G.S_H

# A small program with every action kind: S K K (K I S) -> ... -> K I S -> I
SKK = app(G.node_hash(app(S, K)), K)
KI = app(K, I)
KIS = app(G.node_hash(KI), S)
PROG = app(G.node_hash(SKK), G.node_hash(KIS))
D, _ = build(app(S, K), SKK, KI, KIS, PROG)
PROG_H = G.node_hash(PROG)


def run_all(h, env, grants):
    rt, doc, cid, sb = fresh(h, env)
    res = None
    for g in grants:
        res = R.advance(doc, cid, sb, env, g)
        doc, cid, sb = res.checkpoint, res.checkpoint_id, res.state_bytes
    return res


def main():
    env = env_for(D)
    total = run_all(PROG_H, env, [10**6])
    full_spent = total.checkpoint["spent_total"]

    # ---------------------------------------------------------- A. state
    d, (h,) = build(app(I, K))
    e = env_for(d)
    rt, doc, cid, sb = fresh(h, e)
    warm = R.advance(doc, cid, sb, e, 3)
    cold_term, warm_term = R.decode_state(sb)[1], warm.term()
    case("N01", G.term_hash(cold_term) == G.term_hash(warm_term) and R.state_id(sb) != R.state_id(warm.state_bytes),
         "cold thunk and paid APPLY: same term_hash, different state_id")

    rt, doc, cid, sb = fresh(PROG_H, env)
    mid = R.advance(doc, cid, sb, env, 5)
    c2, t2 = R.decode_state(mid.state_bytes)
    case("N02", R.encode_state(c2, t2) == mid.state_bytes and t2 == mid.term()
         and any(n[0] == "thunk" for n in _nodes(t2)) and any(n[0] == "app" for n in _nodes(t2)),
         "state round-trips exactly, thunks and materialized nodes kept apart")

    # N03: a warm state with too little spent, never reached by replay
    forged_state = warm.state_bytes
    fdoc, fid = R.checkpoint(cid_of(d, h), forged_state, 3, 0, 3, None, 1)
    basis, code, _ = R.verify(R.root(h, e), e, R._canon(fdoc), forged_state)
    case("N03", basis == R.UNVERIFIED and code.startswith("UNVERIFIED_PREFIX"),
         "warm state with spent 0 (paid force forgotten): UNVERIFIED_PREFIX", code)

    # N04: the same checkpoint under another environment or runtime
    other = R.Environment(list(d.keys()) + [G.node_hash(b"x" * 10)], d)
    basis, code, _ = R.verify(R.root(h, other), e, R._canon(warm.checkpoint), warm.state_bytes)
    rdoc, rcid = R.root(h, e)
    bad_rt = (dict(rdoc, runtime_semantics_id="other-runtime"), rcid)
    basis2, code2, _ = R.verify(bad_rt, e, R._canon(warm.checkpoint), warm.state_bytes)
    case("N04", code == "CONTEXT_MISMATCH" and code2 == "CONTEXT_MISMATCH",
         "environment or runtime changed under the same checkpoint: CONTEXT_MISMATCH", f"{code} / {code2}")

    unrun("N05", "atomic on-disk publication is a host adapter; the reference holds checkpoints in memory")

    # N06: encodings refused, not normalized
    good = R._canon(warm.checkpoint)
    bads = {
        "unknown field": good[:-1] + b',"x":1}',
        "duplicate name": good.replace(b'"spent_total":3', b'"spent_total":3,"spent_total":3'),
        "float": good.replace(b'"spent_total":3', b'"spent_total":3.0'),
        "bool": good.replace(b'"spent_total":3', b'"spent_total":true'),
        "non-canonical spacing": good.replace(b",", b", ", 1),
    }
    refused = []
    for name, raw in bads.items():
        try:
            R.parse_checkpoint(raw)
        except R.InvalidEncoding:
            refused.append(name)
    state_bads = [warm.state_bytes + b"\x00", warm.state_bytes[:-1], warm.state_bytes[:36] + b"Z" + b"\x00" * 32]
    for sbad in state_bads:
        try:
            R.decode_state(sbad)
        except R.InvalidEncoding:
            refused.append("state")
    case("N06", len(refused) == len(bads) + len(state_bads), "unknown/duplicate/float/bool/non-canonical/trailing/unknown-tag refused",
         f"refused only {refused}")

    shared = ("thunk", I)
    t_shared = ("app", shared, shared)
    t_copies = ("app", ("thunk", bytes(I)), ("thunk", bytes(I)))
    case("N07", R.encode_state(cid, t_shared) == R.encode_state(cid, t_copies),
         "physical sharing does not change canonical bytes")

    # ---------------------------------------------------------- B. credit
    rt, doc, cid, sb = fresh(h, e)          # first action: force APPLY(I,K), cost 3
    a = R.advance(doc, cid, sb, e, 2)
    b = R.advance(a.checkpoint, a.checkpoint_id, a.state_bytes, e, 1)
    case("N08", a.outcome == R.PAUSED and a.checkpoint["spent_total"] == 0 and a.checkpoint["credit_total"] == 2
         and b.checkpoint["spent_total"] >= 3,
         "force costs 3: grant 2 pauses with credit kept, +1 performs it", f"{a.outcome} {a.checkpoint} / {b.checkpoint}")

    ok9, n9 = True, 0
    for budget in range(0, full_spent + 2):
        ref = run_all(PROG_H, env, [budget])
        for parts in _partitions(budget, 4):
            n9 += 1
            got = run_all(PROG_H, env, parts)
            if (got.checkpoint["state_id"], got.checkpoint["spent_total"], got.outcome) != \
                    (ref.checkpoint["state_id"], ref.checkpoint["spent_total"], ref.outcome):
                ok9 = False
    case("N09", ok9, f"segmentation invariance: {n9} partitions (<= 4 parts, zeros included) of budgets 0..{full_spent + 1}")

    rt, doc, cid, sb = fresh(PROG_H, env)
    ok10 = True
    for _ in range(full_spent + 1):
        r = R.advance(doc, cid, sb, env, 1)
        sb = R.encode_state(*R.decode_state(r.state_bytes))       # "restart": bytes only
        doc, cid = R.parse_checkpoint(R._canon(r.checkpoint))
        if r.outcome == R.NORMAL_FORM:
            break
    ok10 = r.outcome == R.NORMAL_FORM and doc["spent_total"] == full_spent and doc["state_id"] == total.checkpoint["state_id"]
    case("N10", ok10, "checkpoint after every action, rebuilt from bytes: same normal form and spent")

    # N11: S expansion unaffordable leaves the state untouched
    d11, (sk, skk, h11) = build(app(S, K), app(G.node_hash(app(S, K)), K), app(G.node_hash(app(G.node_hash(app(S, K)), K)), I))
    e11 = env_for(d11)
    rt, doc, cid, sb = fresh(h11, e11)
    seen_s = None
    for _ in range(40):
        r = R.advance(doc, cid, sb, e11, 1)
        if r.outcome == R.PAUSED and r.checkpoint["state_id"] == doc["state_id"] and _is_s_redex(r.term()):
            seen_s = (doc, r)
            break
        doc, cid, sb = r.checkpoint, r.checkpoint_id, r.state_bytes
    case("N11", seen_s is not None and seen_s[1].checkpoint["spent_total"] == seen_s[0]["spent_total"],
         "unaffordable S expansion: PAUSED, state and spent unchanged")

    d.reads = 0
    rt, doc, cid, sb = fresh(h, e)
    z = R.advance(doc, cid, sb, e, 0)
    case("N12", z.outcome == R.PAUSED and d.reads == 0, "credit 0 before a demanded fetch: PAUSED, store not read",
         f"{z.outcome}, reads {d.reads}")

    rt, doc, cid, sb = fresh(h, e)
    exact = R.advance(doc, cid, sb, e, 4)      # force 3 + I-step 1, then K: a genesis leaf
    case("N13", exact.outcome == R.NORMAL_FORM and exact.checkpoint["spent_total"] == exact.checkpoint["credit_total"] == 4,
         "spent == credit at the end: NORMAL_FORM, decided without budget", f"{exact.outcome} {exact.checkpoint}")

    try:
        big = dict(exact.checkpoint, credit_total=R.MAX_INT)
        R.advance(big, "x", exact.state_bytes, e, 1)
        overflow = False
    except R.IntegerOverflow:
        overflow = True
    try:
        R.advance(doc, cid, sb, e, R.MAX_INT + 1)
        too_big = False
    except R.InvalidEncoding:
        too_big = True
    case("N14", overflow and too_big, "credit past 2^53-1: typed refusal, never wrapped or clamped")

    unrun("N15", "the reference has no memo cache; canonical spent is the only cost it reports")

    rt, doc, cid, sb = fresh(PROG_H, env)
    ok16 = True
    for g in (1, 2, 1, 3, 5, 100):
        r = R.advance(doc, cid, sb, env, g)
        if G.size(r.term()) > 1 + r.checkpoint["spent_total"] or r.checkpoint["peak_semantic_size"] > 1 + r.checkpoint["spent_total"]:
            ok16 = False
        doc, cid, sb = r.checkpoint, r.checkpoint_id, r.state_bytes
    case("N16", ok16, "semantic size <= 1 + spent_total across resumes (inherited spent counts)")

    # ---------------------------------------------------------- C. environment
    ghost = G.node_hash(b"not in the environment")
    d17, (h17,) = build(app(I, ghost))
    e17 = env_for(d17)
    rt, doc, cid, sb = fresh(h17, e17)
    blk = R.advance(doc, cid, sb, e17, 100)
    case("N17", blk.outcome == R.BLOCKED_REFERENCE and blk.missing == ghost.hex() and blk.checkpoint["spent_total"] > 0,
         "demanded hash outside the manifest: BLOCKED_REFERENCE, missing hash named, checkpoint kept",
         f"{blk.outcome} {blk.missing}")

    e18 = R.Environment(list(d17.keys()) + [ghost], d17)
    rt, doc, cid, sb = fresh(h17, e18)
    un = R.advance(doc, cid, sb, e18, 100)
    case("N18", un.outcome == R.EVIDENCE_UNAVAILABLE and not un.kernel,
         "hash in the manifest, bytes not delivered: EVIDENCE_UNAVAILABLE (local), not BLOCKED", un.outcome)

    d19, (h19,) = build(app(I, K))
    d19[h19] = app(K, I)                       # right name, wrong bytes
    e19 = env_for(d19)
    rt, doc, cid, sb = fresh(h19, e19)
    cas = R.advance(doc, cid, sb, e19, 100)
    case("N19", cas.outcome == R.CAS_MISMATCH, "bytes under a hash they do not have: CAS_MISMATCH", cas.outcome)

    r_old = R.root(h17, e17)
    r_new = R.root(h17, e18)
    basis, code, _ = R.verify(r_new, e18, R._canon(blk.checkpoint), blk.state_bytes)
    case("N20", r_old[1] != r_new[1] and code == "ROOT_MISMATCH",
         "environment changed: new computation_id; the old checkpoint does not carry over", code)

    d21, (h21, _) = build(app(G.node_hash(app(K, I)), ghost), app(K, I))
    e21 = env_for(d21)
    rt, doc, cid, sb = fresh(h21, e21)
    lazy = R.advance(doc, cid, sb, e21, 100)
    case("N21", lazy.outcome == R.NORMAL_FORM, "absent hash in a dead K branch is never demanded", lazy.outcome)

    d.reads = 0
    rt, doc, cid, sb = fresh(h, e)
    pre = R.advance(doc, cid, sb, e, 1)       # min-cost 1 passes, fetch happens, force costs 3
    case("N22", pre.outcome == R.PAUSED and d.reads == 1 and pre.state_bytes == sb and pre.checkpoint["spent_total"] == 0,
         "fetched but unaffordable: no semantic change, no spent (the read is host work)", f"reads {d.reads}")

    # ---------------------------------------------------------- D. prefix trust
    rt, doc, cid, sb = fresh(PROG_H, env)
    unreachable = R.encode_state(rt[1], ("thunk", K))      # right root, unreachable state
    fdoc, _ = R.checkpoint(rt[1], unreachable, 2, 2, 1, None, 1)
    basis, code, _ = R.verify(rt, env, R._canon(fdoc), unreachable)
    case("N23", basis == R.UNVERIFIED and code.startswith("UNVERIFIED_PREFIX"),
         "self-made checkpoint of an unreachable state: UNVERIFIED_PREFIX (no signature consulted)", code)

    other_rt = R.root(h, e)
    basis, code, _ = R.verify(other_rt, e, R._canon(total.checkpoint), total.state_bytes)
    case("N24", code == "ROOT_MISMATCH", "a genuine checkpoint of another computation: ROOT_MISMATCH", code)

    rt, doc, cid, sb = fresh(PROG_H, env)
    p1 = R.advance(doc, cid, sb, env, 6)
    p2 = R.advance(p1.checkpoint, p1.checkpoint_id, p1.state_bytes, env, 6)
    cache = R.VerifiedCache()
    R.verify(rt, env, R._canon(p1.checkpoint), p1.state_bytes, cache=cache)
    stale = R.VerifiedCache(verifier_id="older-engine")
    stale.entries = {("older-engine",) + k[1:]: v for k, v in cache.entries.items()}
    _, _, n_stale = R.verify(rt, env, R._canon(p2.checkpoint), p2.state_bytes, cache=stale)
    _, _, n_cold = R.verify(rt, env, R._canon(p2.checkpoint), p2.state_bytes)
    case("N25", n_stale == n_cold, "cache from another verifier identity is not used: full replay",
         f"{n_stale} vs {n_cold}")
    basis, code, n_warm = R.verify(rt, env, R._canon(p2.checkpoint), p2.state_bytes, cache=cache)
    case("N26", basis == R.REPLAYED and n_warm < n_cold, "own verified parent in cache: replay only the suffix",
         f"{basis} {n_warm} vs {n_cold}")

    unrun("N27", "ATTESTED needs signatures and a recipient trust set: that is Warrant's layer, not the kernel's")

    tight = dict(G.VERIFIER_LIMITS, max_atp=3)
    basis, code, _ = R.verify(rt, env, R._canon(p2.checkpoint), p2.state_bytes, limits=tight)
    case("N28", basis == R.UNVERIFIED and code.startswith("NOT_ASSESSED"),
         "replay stopped by a local limit: NOT_ASSESSED, never verified", code)

    # ---------------------------------------------------------- H. host limits (advance level)
    saved = R.MAX_STATE_BYTES
    R.MAX_STATE_BYTES = len(p2.state_bytes) - 1           # a ceiling just below this state
    try:
        adm = R.advance(p2.checkpoint, p2.checkpoint_id, p2.state_bytes, env, 5)
    finally:
        R.MAX_STATE_BYTES = saved
    case("N61", adm.outcome == R.ADMISSION_REFUSED and adm.state_bytes == p2.state_bytes and not adm.kernel,
         "state over the admission ceiling: ADMISSION_REFUSED before decoding, checkpoint unchanged", adm.outcome)
    rt, doc, cid, sb = fresh(PROG_H, env)
    cut = R.advance(doc, cid, sb, env, 10**6, max_actions=2)
    rest = R.advance(cut.checkpoint, cut.checkpoint_id, cut.state_bytes, env, 0)
    case("N62", cut.outcome == R.INCOMPLETE and not cut.kernel and cut.checkpoint["transition_claim"]["actions"] == 2
         and rest.outcome == R.NORMAL_FORM and rest.checkpoint["state_id"] == total.checkpoint["state_id"]
         and rest.checkpoint["spent_total"] == full_spent,
         "an action limit stops the run: INCOMPLETE (local) with the last atomic state, which resumes to the same end",
         (cut.outcome, rest.outcome))

    # ---------------------------------------------------------- PR #62 review (Codex, AMEND)
    review_regressions()

    # ---------------------------------------------------------- E. cycles
    cycles(env)
    rich()

    print()
    counts = {k: sum(v == k for v in results.values()) for k in ("PASS", "FAIL", "UNRUN")}
    print(f"SIGMA-RESUME: {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['UNRUN']} UNRUN"
          + ("" if counts["UNRUN"] == 0 else " (an UNRUN is not a pass)"))
    return 0 if counts["FAIL"] == 0 else 1


def review_regressions():
    """Codex review of PR #62 at b19cd04: R1-R3, each as a regression."""
    # R1: a cycle proof must be about the recipient's environment
    yi = app(R.Y_H, I)
    h = G.node_hash(yi)
    empty, foreign = R.Environment([], {}), R.Environment([h], {h: yi})
    rt = R.root(h, empty, R.RICH_RUNTIME_ID)
    c, i, s = R.start(rt[1], h)
    blocked = R.advance(c, i, s, empty, 3, runtime=R.RICH_RUNTIME_ID)
    entry = R.advance(c, i, s, foreign, 3, runtime=R.RICH_RUNTIME_ID)
    w = R.cycle_witness(rt[1], entry.checkpoint, entry.state_bytes, 2, 3)
    rt_f = R.root(h, foreign, R.RICH_RUNTIME_ID)
    cf, i_f, sf = R.start(rt_f[1], h)
    entry_f = R.advance(cf, i_f, sf, foreign, 3, runtime=R.RICH_RUNTIME_ID)
    w_f = R.cycle_witness(rt_f[1], entry_f.checkpoint, entry_f.state_bytes, 2, 3)
    case("R1", blocked.outcome == R.BLOCKED_REFERENCE and R.verify_cycle(rt, foreign, w) == "CONTEXT_MISMATCH"
         and R.verify_cycle(rt_f, foreign, w_f) == "CYCLE_PROVEN",
         "a cycle witness under a substituted environment: CONTEXT_MISMATCH; the root that commits to "
         "that environment still proves it", (blocked.outcome, R.verify_cycle(rt, foreign, w)))
    # R2: an INCOMPLETE prefix with unused credit is verifiable, from root and via a verified parent
    ik = app(I, K)
    h2 = G.node_hash(ik)
    env2 = R.Environment([h2], {h2: ik})
    rt2 = R.root(h2, env2)
    c2, i2, s2 = R.start(rt2[1], h2)
    mid = R.advance(c2, i2, s2, env2, 100, max_actions=1)
    from_root = R.verify(rt2, env2, R._canon(mid.checkpoint), mid.state_bytes)
    cache = R.VerifiedCache()
    parent = R.advance(c2, i2, s2, env2, 0)
    R.verify(rt2, env2, R._canon(parent.checkpoint), parent.state_bytes, cache=cache)
    child = R.advance(parent.checkpoint, parent.checkpoint_id, parent.state_bytes, env2, 100, max_actions=1)
    via_parent = R.verify(rt2, env2, R._canon(child.checkpoint), child.state_bytes, cache=cache)
    resumed = R.advance(mid.checkpoint, mid.checkpoint_id, mid.state_bytes, env2, 0)
    whole = R.advance(c2, i2, s2, env2, 100)
    final = R.verify(rt2, env2, R._canon(whole.checkpoint), whole.state_bytes)
    case("R2", mid.outcome == R.INCOMPLETE and from_root[:2] == (R.REPLAYED, "PREFIX")
         and via_parent[:2] == (R.REPLAYED, "PREFIX") and resumed.outcome == R.NORMAL_FORM
         and resumed.checkpoint["state_id"] == whole.checkpoint["state_id"]
         and resumed.checkpoint["spent_total"] == whole.checkpoint["spent_total"]
         and final[:2] == (R.REPLAYED, R.NORMAL_FORM),
         "INCOMPLETE checkpoint with unused credit: REPLAYED as PREFIX (not terminal), from root and via a "
         "verified parent; resumed, it ends where the uninterrupted run ends", (from_root, via_parent, final))
    # R3: malformed identifiers are INVALID_ENCODING, with and without a cache
    bad_values = [{"untrusted": "object"}, ["x"], 7, True, "zz" * 32, "AB" * 32, "ab" * 31]
    ok3 = True
    for field_name in ("parent_checkpoint_id", "computation_id", "state_id"):
        for v in bad_values:
            raw = R._canon(dict(whole.checkpoint, **{field_name: v}))
            for cache3 in (None, R.VerifiedCache()):
                try:
                    basis, code, _ = R.verify(rt2, env2, raw, whole.state_bytes, cache=cache3)
                except Exception:      # noqa: BLE001 -- a host exception is exactly the defect
                    ok3 = False
                    continue
                ok3 &= basis == R.UNVERIFIED and code.startswith("INVALID_ENCODING")
    case("R3", ok3, "object/list/number/bool/non-hex/uppercase/short ids in parent, computation_id or state_id: "
         "INVALID_ENCODING with and without a cache, never a host exception")


# ---------------------------------------------------------------- cycles (toy)

def _lit(n):
    return ("lit", bytes([n]) * 32)


# A deterministic toy transition with a period-3 orbit A1 -> A2 -> A3 -> A1
# (costs 2, 1, 2) entered from A0, and a terminal A9. It obeys step5's contract.
TOY = {0: (1, 1), 1: (2, 2), 2: (3, 1), 3: (1, 2)}


def toy_step(t, remaining, env, stats, limits):
    if t[0] == "thunk":
        nxt, cost = _lit(0), 1
    elif t[0] == "lit" and t[1][0] in TOY and t[1] == bytes([t[1][0]]) * 32:
        n, cost = TOY[t[1][0]]
        nxt = _lit(n)
    else:
        return None
    if cost > remaining:
        raise G.BudgetExhausted()
    return nxt, cost


def cycles(env):
    real = R.STEP
    R.STEP = toy_step
    try:
        toy_env = R.Environment([], {})
        th = bytes(range(32))
        rt = R.root(th, toy_env)
        doc, cid, sb = R.start(rt[1], th)
        to_a1 = R.advance(doc, cid, sb, toy_env, 2)          # thunk->A0 (1), A0->A1 (1)
        w = R.cycle_witness(rt[1], to_a1.checkpoint, to_a1.state_bytes, 3, 5)
        case("N29", R.verify_cycle(rt, toy_env, w) == "CYCLE_PROVEN",
             "real periodic orbit (toy transition): CYCLE_PROVEN with positive cost")
        end = R.advance(doc, cid, sb, toy_env, 1)            # A0, then its own "cycle" of 0 actions
        w0 = R.cycle_witness(rt[1], end.checkpoint, end.state_bytes, 0, 0)
        case("N30", R.verify_cycle(rt, toy_env, w0).startswith("INVALID_CYCLE_WITNESS"),
             "a state 'repeated' with no priced transition is not a cycle")
        foreign = R.root(bytes(32), toy_env)
        case("N32", R.verify_cycle(foreign, toy_env, w).startswith("PREFIX_MISMATCH"),
             "the same orbit offered under another root: PREFIX_MISMATCH")
        bad_n = dict(w, cycle_action_count=2)
        bad_c = dict(w, cycle_cost=4)           # too low: the period no longer fits the budget
        bad_c_high = dict(w, cycle_cost=6)      # too high: fits, but the claim is false
        bad_e = dict(w, entry_state_id="00" * 32)
        verdicts = [R.verify_cycle(rt, toy_env, x) for x in (bad_n, bad_c, bad_c_high, bad_e)]
        case("N33", all(v.startswith(("INVALID_CYCLE_WITNESS", "PREFIX_MISMATCH")) for v in verdicts),
             "altered action count, cost or entry state: refused", str(verdicts))
        a_rich = R.advance(doc, cid, sb, toy_env, 2)
        a_rich2 = R.advance(R.start(rt[1], th)[0], R.start(rt[1], th)[1], sb, toy_env, 3)   # +1 unspent credit
        case("N34", a_rich.checkpoint["state_id"] == a_rich2.checkpoint["state_id"],
             "credit differs, state the same: the state (cycle projection) carries no counters")
        many = R.advance(doc, cid, sb, toy_env, 50)
        case("N35", many.outcome == R.PAUSED, "advance never stops 'on a cycle': the kernel has no detector", many.outcome)
        w_later = R.cycle_witness(rt[1], R.advance(doc, cid, sb, toy_env, 4).checkpoint,
                                  R.advance(doc, cid, sb, toy_env, 4).state_bytes, 3, 5)
        w_double = dict(w, cycle_action_count=6, cycle_cost=10)
        case("N37", R.verify_cycle(rt, toy_env, w_later) == "CYCLE_PROVEN" and R.verify_cycle(rt, toy_env, w_double) == "CYCLE_PROVEN",
             "same orbit from another entry, or walked twice: valid witnesses (novelty is Warrant's question)")
    finally:
        R.STEP = real
    # N31 and N36 on the real Sigma transition.
    d, (h,) = build(app(I, K))
    e = env_for(d)
    rt, doc, cid, sb = fresh(h, e)
    w31 = R.cycle_witness(rt[1], doc, sb, 1, 3)      # force: same term_hash, different state
    case("N31", R.verify_cycle(rt, e, w31).startswith("INVALID_CYCLE_WITNESS"),
         "endpoint with the same term_hash but materialized: not a cycle")
    a = G.node_hash(app(G.node_hash(app(S, I)), I))
    d36, _ = build(app(S, I), app(G.node_hash(app(S, I)), I), app(a, a))
    e36 = env_for(d36)
    rt, doc, cid, sb = fresh(G.node_hash(app(a, a)), e36)
    om = R.advance(doc, cid, sb, e36, 2000)
    case("N36", om.outcome == R.PAUSED, "a long non-periodic run (Omega) ends PAUSED, not DIVERGES", om.outcome)


# ---------------------------------------------------------------- rich profile (draft)

def rich():
    """The draft SKI+Y+M+W profile on the real Sigma transition."""
    import random
    RID = R.RICH_RUNTIME_ID
    Yt, Mt, Wt = ("thunk", R.Y_H), ("thunk", R.M_H), ("thunk", R.W_H)

    def stored(*nodes):
        d = Delivered()
        for b in nodes:
            d[G.node_hash(b)] = b
        return d

    def go(h, env, grants, runtime=RID):
        rt = R.root(h, env, runtime)
        doc, cid, sb = R.start(rt[1], h)
        res = None
        for g in grants:
            res = R.advance(doc, cid, sb, env, g, runtime=runtime)
            doc, cid, sb = res.checkpoint, res.checkpoint_id, res.state_bytes
        return rt, res

    # N29 on Sigma itself: Y I (period 2) and M M (period 1) are proved cycles.
    verdicts = []
    for node, entry_spent, n, cost in ((app(R.Y_H, I), 0, 2, 3), (app(R.M_H, R.M_H), 0, 1, 2)):
        d = stored(node)
        e = R.Environment(list(d), d)
        h = G.node_hash(node)
        rt, warm = go(h, e, [3])            # force the stored node first (cost 3), entry after it
        w = R.cycle_witness(rt[1], warm.checkpoint, warm.state_bytes, n, cost)
        verdicts.append(R.verify_cycle(rt, e, w))
    case("R-N29", verdicts == ["CYCLE_PROVEN", "CYCLE_PROVEN"],
         "Sigma rich profile: Y I (period 2, cost 3) and M M (period 1, cost 2) are CYCLE_PROVEN", str(verdicts))

    # The same stored term under the Book I profile: Y and M are inert literals there.
    node = app(R.M_H, R.M_H)
    d = stored(node)
    d[R.M_H] = R.RICH_GENESIS[R.M_H]          # under Book I, M is a stored literal
    e = R.Environment(list(d), d)
    rt_ski, res_ski = go(G.node_hash(node), e, [100], runtime=R.RUNTIME_SEMANTICS_ID)
    rt_rich, res_rich = go(G.node_hash(node), e, [100])
    basis, code, _ = R.verify(rt_ski, e, R._canon(res_rich.checkpoint), res_rich.state_bytes)
    case("R-ISO", rt_ski[1] != rt_rich[1] and res_ski.outcome == R.NORMAL_FORM and res_rich.outcome == R.PAUSED
         and code == "ROOT_MISMATCH",
         "profile is part of the task: M M halts under Book I, loops under rich; checkpoints do not cross",
         f"{res_ski.outcome} {res_rich.outcome} {code}")

    # Segmentation invariance on terminating rich programs: W K I -> K I I -> I ; M (K I) -> I.
    ki = app(K, I)
    progs = [(app(G.node_hash(app(R.W_H, K)), I), [app(R.W_H, K)]),
             (app(R.M_H, G.node_hash(ki)), [ki])]
    ok = True
    n_parts = 0
    for top, extra in progs:
        d = stored(top, *extra)
        e = R.Environment(list(d), d)
        h = G.node_hash(top)
        full = go(h, e, [10**6])[1].checkpoint["spent_total"]
        for budget in range(full + 2):
            ref = go(h, e, [budget])[1]
            for parts in _partitions(budget, 3):
                n_parts += 1
                got = go(h, e, list(parts))[1]
                if (got.checkpoint["state_id"], got.checkpoint["spent_total"], got.outcome) != \
                        (ref.checkpoint["state_id"], ref.checkpoint["spent_total"], ref.outcome):
                    ok = False
    case("R-N09", ok, f"rich profile segmentation invariance: {n_parts} partitions of W K I and M (K I)")

    # Size bound and budget-independent action choice on random rich terms.
    random.seed(11)
    atoms = [("thunk", I), ("thunk", K), ("thunk", S), Yt, Mt, Wt]

    def rnd(depth):
        if depth == 0 or random.random() < 0.3:
            return random.choice(atoms)
        return ("app", rnd(depth - 1), rnd(depth - 1))
    viol_size = viol_choice = pairs = 0
    empty = R.Environment([], {})
    for _ in range(250):
        t, spent = rnd(5), 0
        s0 = G.size(t)
        for _ in range(40):
            full = R.rich_step(t, 10**9, empty, {"fetches": 0}, G.DEFAULT_LIMITS)
            if full is None or G.size(t) > 2000:
                break
            for r in range(full[1] + 1):
                pairs += 1
                try:
                    got = R.rich_step(t, r, empty, {"fetches": 0}, G.DEFAULT_LIMITS)
                except G.BudgetExhausted:
                    viol_choice += r >= full[1]
                    continue
                viol_choice += got != full
            t, spent = full[0], spent + full[1]
            viol_size += G.size(t) > s0 + spent
    case("R-N16", viol_size == 0 and viol_choice == 0,
         f"rich profile: size <= initial + spent and budget-independent action choice ({pairs} pairs)",
         f"size {viol_size}, choice {viol_choice}")


# ---------------------------------------------------------------- helpers

def _nodes(t):
    stack, out = [t], []
    while stack:
        n = stack.pop()
        out.append(n)
        if n[0] == "app":
            stack += [n[1], n[2]]
    return out


def _is_s_redex(t):
    return t[0] == "app" and t[1][0] == "app" and t[1][1][0] == "app" and G.glyph_eq(t[1][1][1], S)


def _partitions(total, max_parts):
    out = set()
    for k in range(1, max_parts + 1):
        for cuts in itertools.combinations_with_replacement(range(total + 1), k - 1):
            bounds = (0,) + cuts + (total,)
            out.add(tuple(bounds[i + 1] - bounds[i] for i in range(k)))
        out.add((0,) * (k - 1) + (total,))
    return sorted(out)


def cid_of(d, h):
    return R.root(h, env_for(d))[1]


if __name__ == "__main__":
    sys.exit(main())
