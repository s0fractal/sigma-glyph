#!/usr/bin/env python3
"""Resonant Precedent — the THREE executable bridge contracts behind ADR-008
rev 3, in reply to the Codex re-verification (2026-07-26). Illustrative,
NON-NORMATIVE; touches no anchored artifact. Reuses the repository's own
canonicalizer and schema (sigma_federation.jcs / sha_hex / validate_assertion /
assertion_set_root) so every byte is the project's, not hand-rolled.

    $ python3 examples/resonant_precedent_contracts_probe.py

Codex's re-verification proved ski@v1 cannot bind Book III JCS assertions to a
Book II coherence computation. This probe answers the three P1 blockers with
running code + reproducible hashes:

  C1. wave@v1 — a NEW deterministic check runtime (Codex's "smallest honest
      contract"). It resolves and validates the two cited JCS wave-assertion
      blobs, extracts their waves, and computes coherence = LUT_COS[|Δph|]. It
      truly BINDS the cited blobs: swapping the cited assertion flips the
      verdict — the exact thing ski@v1 (baked-in facts) cannot do. It is NOT
      ski@v1 and requires a Warrant runtime version tag.
  C2. PrecedentIndexViewID = sha_hex(jcs(closed view object)) — following the
      project's own view_id convention (SHA-256(JCS(...)), not NodeHash). A
      settlement event that changes the active set changes the ID.
  C3. Canonical result encoding — coherence buckets in descending order, IDs
      sorted lexicographically for bytes only (no rank/authority), inclusive at
      the int16 threshold. jcs() gives byte-identical rankings across impls.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "impl"))
import sigma_wave as sw
import sigma_federation as sf

jcs, sha_hex = sf.jcs, sf.sha_hex
H = lambda label: sha_hex(label.encode())          # a stand-in hex64 identity

# ---- a trivial content-addressed store (hash -> canonical bytes) ------------
CAS = {}
def put(obj):
    b = jcs(obj)
    CAS[sha_hex(b)] = b
    return sha_hex(b)

def assertion(jur, node, epoch, ph, am=65535, en=-32768):
    return {"annotation": sf.ASSERTION_TAG, "jurisdiction": jur, "node": node,
            "epoch": epoch, "wave": {"ph": ph, "am": am, "en": en}}

def coherence(w_q, w_c):
    d = abs(w_q["ph"] - w_c["ph"])
    return sw.LUT_COS[min(d, 65536 - d)]


# ============================================================================
# C1 — wave@v1 reference verifier (the runtime ski@v1 is NOT)
# ============================================================================
def wave_v1_verify(check_blob, cas):
    """Deterministic. Returns 'pass' | 'fail' | 'invalid'. Binds the cited blobs."""
    if set(check_blob) != {"check", "query", "cited", "metric", "threshold", "index_view"}:
        return "invalid"
    if check_blob["check"] != "sigma-glyph.wave@v1":
        return "invalid"
    if check_blob["metric"] != "coherence.lut-cos@v1":
        return "invalid"
    try:
        q = json_loads(cas[check_blob["query"]])
        c = json_loads(cas[check_blob["cited"]])
    except KeyError:
        return "invalid"                                   # unresolved reference
    if sf.validate_assertion(q) is not None or sf.validate_assertion(c) is not None:
        return "invalid"
    coh = coherence(q["wave"], c["wave"])                  # Book II integer algorithm
    return "pass" if coh >= check_blob["threshold"] else "fail"

import json as _json
def json_loads(b):
    return _json.loads(b.decode())


def contract_1():
    # NOTE: this shows only the coherence KERNEL and the evidence-binding idea.
    # The TOTAL, closed-schema wave@v1 verifier — with the full precedent-entry
    # join (activeness, jurisdiction, Book III selection, C0 term, index_view)
    # and no host exceptions over its byte domain — lives in
    # examples/resonant_precedent_join_probe.py (ADR-008 rev 4).
    print("[C1] wave@v1 kernel — binds cited JCS assertions (ski@v1 cannot)")
    J, NODE = H("jurisdiction-A"), H("node-x")
    q_blob = assertion(J, NODE, 1, ph=16384)               # query: S-bucket @ 16384
    a_same = assertion(J, NODE, 1, ph=16384)               # cited A: same bucket
    a_diff = assertion(J, NODE, 1, ph=32768)               # cited B: K-bucket @ 32768
    qh, ah, bh = put(q_blob), put(a_same), put(a_diff)
    view = H("index-view-1")
    def check(cited): return {"check": "sigma-glyph.wave@v1", "query": qh,
                              "cited": cited, "metric": "coherence.lut-cos@v1",
                              "threshold": 30000, "index_view": view}
    v_same = wave_v1_verify(check(ah), CAS)
    v_diff = wave_v1_verify(check(bh), CAS)
    print(f"     verdict(cited=same-bucket) = {v_same}   coherence=32767")
    print(f"     verdict(cited=other-bucket)= {v_diff}   coherence=0")
    print(f"     swapping the cited blob flips the verdict: {v_same != v_diff} "
          f"-> the reason is BOUND to the evidence, not baked in")
    # invalid input: a non-assertion blob (what Codex forced -> Canonical Invalid Object)
    junk = put({"not": "an assertion"})
    print(f"     verdict(cited=non-assertion) = "
          f"{wave_v1_verify(check(junk), CAS)}  (deterministic invalid, not a crash)")


# ============================================================================
# C2 — PrecedentIndexViewID (sha_hex(jcs(...)), per the project's view_id)
# ============================================================================
def precedent_index_view_id(genesis_roots, projection_profile, metric,
                            sigma_ruleset, active_warrant_ids, epoch):
    # sets are sets: reject duplicates so [A] and [A,A] cannot mint two IDs
    # for one logical set (Codex rev-3 P2). assertion_set_root's precondition
    # is a mathematical set; enforce it here before hashing.
    if len(set(genesis_roots)) != len(genesis_roots):
        raise ValueError("genesis_roots must be duplicate-free")
    if len(set(active_warrant_ids)) != len(active_warrant_ids):
        raise ValueError("active_warrant_ids must be duplicate-free")
    obj = {
        "view": "sigma-glyph.precedent-index-view@v1",
        "genesis_roots": sorted(set(genesis_roots)),
        "projection_profile": projection_profile,
        "metric": metric,
        "sigma_ruleset": sigma_ruleset,   # governed Sigma anchor-SET identity, not one Book
        "active_warrant_set_commit": sf.assertion_set_root(sorted(set(active_warrant_ids))),
        "epoch": epoch,
    }
    return sha_hex(jcs(obj))


def contract_2():
    print("[C2] PrecedentIndexViewID — deterministic bytes; settlement changes it")
    base = dict(genesis_roots=[H("root-A")], projection_profile=H("proj@v1-policy"),
                metric="coherence.lut-cos@v1", sigma_ruleset=H("book1-v0.5"), epoch=7)
    wids = [H("w1"), H("w2"), H("w3")]
    id1 = precedent_index_view_id(active_warrant_ids=wids, **base)
    id1b = precedent_index_view_id(active_warrant_ids=list(reversed(wids)), **base)
    id2 = precedent_index_view_id(active_warrant_ids=wids + [H("w4")], **base)
    print(f"     id (3 active)          = {id1[:16]}…")
    print(f"     id (same set, shuffled)= {id1b[:16]}…  order-independent? {id1 == id1b}")
    print(f"     id (settlement +w4)    = {id2[:16]}…  changed by new active? {id1 != id2}")


# ============================================================================
# C3 — canonical result encoding (byte-identical rankings, anti-grind)
# ============================================================================
def _valid_wave(w):
    return (isinstance(w, dict) and set(w) == {"ph", "am", "en"}
            and all(isinstance(w[k], int) and not isinstance(w[k], bool) for k in w)
            and 0 <= w["ph"] < (1 << 16) and 0 <= w["am"] < (1 << 16)
            and -32768 <= w["en"] <= 32767)

def precedent(wave_q, index, tau):
    """index: set keyed by warrant_id of {'warrant_id','wave'}. Canonical buckets.
    Input-set contract (Codex rev-3 P2): tau int16 (no bool), every warrant_id
    hex64, every wave a WaveVectorQ, and NO duplicate warrant_id."""
    if not (isinstance(tau, int) and not isinstance(tau, bool) and -32768 <= tau <= 32767):
        raise ValueError("tau must be int16")
    seen, buckets = set(), {}
    for e in index:
        wid = e["warrant_id"]
        if not (isinstance(wid, str) and len(wid) == 64
                and all(c in "0123456789abcdef" for c in wid)):
            raise ValueError("warrant_id must be hex64")
        if wid in seen:
            raise ValueError("duplicate warrant_id in index")   # set, not list
        seen.add(wid)
        if not _valid_wave(e["wave"]):
            raise ValueError("effective wave must be a WaveVectorQ")
        coh = coherence(wave_q, e["wave"])
        if coh >= tau:                                     # inclusive threshold
            buckets.setdefault(coh, []).append(wid)
    return [{"coherence": c, "entries": sorted(buckets[c])}  # ids sorted: bytes only
            for c in sorted(buckets, reverse=True)]          # buckets: desc coherence


def contract_3():
    print("[C3] canonical result encoding — anti-grind + byte-identical")
    wq = {"ph": 16384, "am": 65535, "en": -32768}
    index = [
        {"warrant_id": H("wZ"), "wave": {"ph": 16384, "am": 40000, "en": 0}},
        {"warrant_id": H("wA"), "wave": {"ph": 16384, "am": 20000, "en": 0}},  # same coh as wZ
        {"warrant_id": H("wM"), "wave": {"ph": 20480, "am": 65535, "en": 0}},  # lower coh
        {"warrant_id": H("wLow"), "wave": {"ph": 49152, "am": 65535, "en": 0}},# below tau
    ]
    res = precedent(wq, index, tau=20000)
    print(f"     buckets: {[(b['coherence'], len(b['entries'])) for b in res]}")
    top_ids = [i[:6] for i in res[0]['entries']]
    print(f"     top bucket entries sorted for bytes only (no rank): {top_ids}")
    print(f"     canonical bytes = jcs(result); re-run identical: "
          f"{jcs(res) == jcs(precedent(wq, index, 20000))}")


if __name__ == "__main__":
    contract_1(); print()
    contract_2(); print()
    contract_3()
