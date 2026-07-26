#!/usr/bin/env python3
"""Resonant Precedent — the executable probe behind ADR-008. Illustrative,
NON-NORMATIVE. Touches no anchored artifact; lives in examples/ like
mem_diverge.py. Reproduce every number in the ADR before reading the prose
(reviews/README: "run first, read second").

    $ python3 examples/resonant_precedent_probe.py

Findings (all recomputed here; corrected after the Codex 2026-07-26 gate):
  1. A term's wave is a deterministic, computed coordinate. Retrieval is a
     PAIRWISE score, so ADR-006's non-associativity P0 does not apply. The
     metric LUT_COS[|Δph|] is SYMMETRIC — swapping query/item does not change
     it (the earlier "directional" framing was wrong; interfere's output phase
     is never read by ranking).
  2. Ranking by raw post-interference AMPLITUDE is unsound: it conflates phase
     alignment with the item's own loudness ("Gravity").
  3. Ranking by phase COHERENCE (LUT_COS[|Δph|]) is sound and amplitude-
     independent, BUT relevance is the left-head PHASE BUCKET, not head
     identity: distinct pinned heads that share a phase (S and V @ 16384;
     SATOSHI/TESLA @ 8192) fall in one bucket and co-retrieve — the settled
     phase-not-identity behavior, not a bug. The boundary tie-set spans heads.
  4. Retrieval resolution is the count of distinct PHASE buckets (3 -> 9 here),
     since ranking reads ph only. The count of full (ph,am,en) triples (10 ->
     67) is a different quantity the metric does not use.

Injects RUNTIME-ONLY full pins for ph-only leaves (ADR-005), purely to explore
the design direction. Proposes NO spec change by itself.
"""
import os
import sys
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "impl"))
import sigma_wave as sw

A = lambda l, r: ["APPLY", l, r]
CRYST = {"am": 65535, "en": -32768}          # the {am=65535, en=-32768} fixed point


def make_wave(vocab):
    pins = dict(sw.FULL_PINS)                 # I/S/K already full-pinned
    for n in vocab:
        ph = sw.coordinate(n)
        if ph is not None and n not in pins:
            pins[n] = {"ph": ph, **CRYST}

    def wave(term):
        if isinstance(term, str):
            return dict(pins[term]) if term in pins else None
        if isinstance(term, list) and term[0] == "APPLY":
            l, r = wave(term[1]), wave(term[2])
            return None if l is None or r is None else sw.interfere(l, r)
        return None

    return wave


def corpus(vocab):
    terms = {f"{a}·{b}": A(a, b) for a, b in itertools.product(vocab, repeat=2)}
    for a, b, c in [("S", "I", "I"), ("K", "I", "I"),
                    ("TURING", "I", "K"), ("GODEL", "S", "I")]:
        if all(x in vocab for x in (a, b, c)):
            terms[f"({a}·{b})·{c}"] = A(A(a, b), c)
    return terms


def head(name):
    return name.split("·")[0].lstrip("(")


def amplitude(wave, q, t):
    a, b = wave(q), wave(t)
    return None if a is None or b is None else sw.interfere(a, b)["am"]


def coherence(wave, q, t):
    a, b = wave(q), wave(t)
    if a is None or b is None:
        return None
    x = abs(a["ph"] - b["ph"])
    return sw.LUT_COS[min(x, 65536 - x)]       # +32767 aligned .. -32767 opposed


def finding_1():
    wave = make_wave(["I", "S", "K"])
    ts = corpus(["I", "S", "K"])
    q = A("I", "K")
    r1 = [coherence(wave, q, t) for t in ts.values()]
    r2 = [coherence(wave, q, t) for t in ts.values()]
    a, b = A("S", "I"), A("K", "I")
    print("[1] determinism + pairwise + symmetric metric")
    print(f"    re-run byte-identical: {r1 == r2}")
    print(f"    metric symmetric: coh(SI,KI)={coherence(wave,a,b)} "
          f"coh(KI,SI)={coherence(wave,b,a)} -> equal? "
          f"{coherence(wave,a,b) == coherence(wave,b,a)} (no directional claim)")


def finding_2():
    wave = make_wave(["I", "S", "K", "TURING", "GODEL"])
    ts = corpus(["I", "S", "K", "TURING", "GODEL"])
    q = A("TURING", "I")
    ranked = sorted(((n, amplitude(wave, q, t)) for n, t in ts.items()),
                    key=lambda kv: -kv[1])[:5]
    print("[2] naive AMPLITUDE ranking (query TURING·I) — unsound")
    for n, s in ranked:
        print(f"    {n:14} amp={s:5} head={head(n)}")
    heads = {head(n) for n, _ in ranked}
    print(f"    top-5 heads = {sorted(heads)} -> single head? {heads == {'TURING'}}")


def finding_3():
    # Include V (phase 16384 == S) to show buckets span heads.
    vocab = ["I", "S", "K", "V", "TURING", "GODEL"]
    wave = make_wave(vocab)
    ts = corpus(vocab)
    q = A("S", "I")                            # head S @ 16384
    scored = [(n, coherence(wave, q, t)) for n, t in ts.items()]
    top = max(s for _, s in scored)
    tie = sorted(n for n, s in scored if s == top)
    print("[3] phase COHERENCE ranking (query S·I) — sound, bucket-not-head")
    print(f"    max coherence = {top}; boundary tie-set size = {len(tie)}")
    print(f"    heads in the tie-set = {sorted({head(n) for n in tie})} "
          f"(S and V share phase 16384 -> one bucket, correctly co-retrieved)")
    print(f"    -> relevance is the left-head PHASE BUCKET, not head identity")


def finding_4():
    print("[4] retrieval resolution = distinct PHASE buckets")
    EXT = ["I", "S", "K", "TURING", "GODEL", "HEGEL",
           "LEIBNIZ", "BACH", "V", "SATOSHI", "TESLA"]
    for label, vocab in [("baseline I/S/K", ["I", "S", "K"]), ("extended +named", EXT)]:
        wave = make_wave(vocab)
        phs, trips = set(), set()
        for t in corpus(vocab).values():
            w = wave(t)
            if w is None:
                continue
            phs.add(w["ph"])
            trips.add((w["ph"], w["am"], w["en"]))
        print(f"    {label:16} vocab={len(vocab):2} "
              f"phase_buckets={len(phs):2} (metric)  "
              f"full_triples={len(trips):3} (not used by metric)")


if __name__ == "__main__":
    finding_1()
    print()
    finding_2()
    print()
    finding_3()
    print()
    finding_4()
