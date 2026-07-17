#!/usr/bin/env python3
"""Three-way Book I differential fuzzer (Python oracle vs Rust vs warrant-go).

The pinned vectors.json fixes a curated battery; this generates thousands of
random SKI terms and ATP budgets, has the Python oracle compute the expected
(result_hash, atp_spent), and then makes the two INDEPENDENT Book I evaluators
recompute them: any divergence surfaces as a conformance failure on that
generated vector. This is the net that catches the splits no curated vector
thought to (e.g. the warrant-go R-S uint32 overflow found in the 2026-07 review).

Reuses the existing conformance harnesses so no new impl surface is needed:
each generated case is emitted in tests/spec_conformance/vectors.json format and
replayed by `book1 conformance` (Rust) and `warrant-go sigma-conformance` (Go).

Deterministic: seed the RNG so a divergence is reproducible.

Usage:  python3 tests/book1_fuzz.py [--terms N] [--seed S]
Env:    RUST_BOOK1=path   (default ./impl-rs/target/release/book1)
        WARRANT_GO=path   (default ~/Projects/warrant/impl-go/warrant-go)
Exit nonzero on any divergence; the failing engine prints the vector id.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

RUST = os.environ.get("RUST_BOOK1", str(ROOT / "impl-rs/target/release/book1"))
WGO = os.environ.get("WARRANT_GO", str(Path.home() / "Projects/warrant/impl-go/warrant-go"))

IG = ("lit", sg.sha(b"I"))
KG = ("lit", sg.sha(b"K"))
SG = ("lit", sg.sha(b"S"))
EVAL_CAP = 4000   # generation-time budget ceiling: eval is total, so this bounds
                  # even non-terminating terms (Omega) to a deterministic Exhausted


def build(rng):
    """Return (root_term, objects) — objects maps hash-hex -> node-bytes-hex for
    every materialized node the term references (genesis excluded: intrinsic)."""
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

    def leaf():
        r = rng.random()
        if r < 0.45:
            return rng.choice([IG, KG, SG])
        if r < 0.6:
            return ("lit", sg.sha(bytes(rng.randrange(256) for _ in range(rng.randint(1, 8)))))
        if r < 0.8:
            # REF to a resolvable target: genesis or a fresh literal we store
            tgt = rng.choice([sg.I_H, sg.K_H, sg.S_H])
            if rng.random() < 0.4:
                tgt = put(sg.term_bytes(("lit", sg.sha(b"ref-target-%d" % rng.randint(0, 1 << 20)))))
            return ("ref", tgt)
        # ghost REF: target absent from the store -> Unresolved iff demanded
        return ("ref", sg.sha(b"ghost-%d" % rng.randint(0, 1 << 30)))

    def term(depth):
        if depth <= 0 or rng.random() < 0.3:
            return leaf()
        return ("app", term(depth - 1), term(depth - 1))

    root = term(rng.randint(1, 5))
    put_tree(root)
    return sg.term_hash(root), objects, store


def atp_grid(rng, term_hash, store):
    r, spent = sg.eval_hash(term_hash, EVAL_CAP, store)
    cand = {0, 1, 2, 3, spent, spent + 1, EVAL_CAP, 2**32 - 1}
    if spent > 1:
        cand |= {spent - 1, spent // 2}
    return sorted(a for a in cand if 0 <= a <= 2**32 - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--terms", type=int, default=150)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # A term that reaches normal form within EVAL_CAP has the SAME (result,
    # spent) at any larger budget, so we can hand the engines a genuine uint32
    # BOUNDARY budget (2^32-1) for it — exercising the exact integer-width path
    # the Go/Rust evaluators must get right, which capping every atp at EVAL_CAP
    # would blind the fuzzer to (Gemini 3.1 Pro audit, 2026-07).
    atp_exhausted = sg.term_hash(("dis", sg.R_ATP)).hex()

    objects = {}
    vectors = []
    for i in range(args.terms):
        th, objs, store = build(rng)
        objects.update(objs)
        for atp in atp_grid(rng, th, store):
            eval_atp = min(atp, EVAL_CAP)
            r, spent = sg.eval_hash(th, eval_atp, store)
            rh = sg.term_hash(r).hex()
            terminated = rh != atp_exhausted
            # emit the REAL atp when the term halts within EVAL_CAP (result valid
            # for any atp >= spent); otherwise the capped value the oracle ran.
            emit_atp = atp if (atp <= EVAL_CAP or terminated) else eval_atp
            vectors.append({
                "id": f"FUZZ-{i}-{atp}",
                "kind": "eval",
                "term": th.hex(),
                "atp": emit_atp,
                "expected": {"result_hash": rh, "atp_spent": spent},
            })

    # Reuse the pinned suite's metadata header so both engines' strict parsers
    # accept the generated file (Rust requires format_version et al.).
    ref = json.load(open(ROOT / "tests/spec_conformance/vectors.json"))
    doc = {k: ref[k] for k in ("format", "format_version", "spec_version",
                               "suite_version", "book1_anchor", "oracle") if k in ref}
    doc["notes"] = f"generated by book1_fuzz.py seed={args.seed} terms={args.terms}"
    doc["objects"] = objects
    doc["vectors"] = vectors

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "fuzz_vectors.json")
        with open(path, "w") as f:
            json.dump(doc, f)

        results = {}
        # The Python oracle computed the expected values by construction, so it
        # trivially agrees; the test is whether the two INDEPENDENT engines
        # recompute the same result_hash + atp_spent on every generated vector.
        if os.path.exists(RUST):
            p = subprocess.run([RUST, "conformance", path], capture_output=True, text=True)
            # Rust's summary line is hardwired to the pinned 49-vector suite size,
            # so judge per-vector: every vector must print "OK", none "FAIL".
            oks = sum(1 for ln in p.stdout.splitlines() if ln.startswith("OK "))
            fails = sum(1 for ln in p.stdout.splitlines() if ln.startswith("FAIL"))
            results["rust"] = (fails == 0 and oks == len(vectors), p)
        else:
            print(f"SKIP rust (not built at {RUST})")
        if os.path.exists(WGO):
            p = subprocess.run([WGO, "sigma-conformance", path], capture_output=True, text=True)
            results["warrant-go"] = ("SIGMA CONFORMANCE: ALL PASS" in p.stdout, p)
        else:
            print(f"SKIP warrant-go (not built at {WGO})")

        n = len(vectors)
        bad = [(k, v[1]) for k, v in results.items() if not v[0]]
        if bad or not results:
            print(f"BOOK1-FUZZ: DIVERGENCE over {n} vectors ({args.terms} terms) seed={args.seed}")
            for k, p in bad:
                fails = [ln for ln in p.stdout.splitlines() if ln.startswith("FAIL")]
                print(f"  {k}:")
                for ln in fails[:10]:
                    print("    ", ln)
            if not results:
                print("  no independent engine available to differ against")
            return 1
        engines = "+".join(["python-oracle"] + list(results))
        print(f"BOOK1-FUZZ: ALL AGREE ({n} vectors, {args.terms} terms, {engines}) seed={args.seed}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
