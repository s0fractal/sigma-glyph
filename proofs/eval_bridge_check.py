#!/usr/bin/env python3
"""Differential bridge for proofs/EvalMachine.lean (Book I evaluator).

The Lean theorems say the in-Lean evaluator is total (fuel-indexed) and
budget-respecting (spent ≤ atp). This bridge is the honest seam that it is
THE oracle: the executed Lean evaluator (EvalRun.lean) reproduces both the
result NodeHash and the exact atp_spent of impl/sigma_glyph.py on every eval
conformance vector — including the divergent Omega (500 ATP → exhausted) and
the store-isolation vectors.

  1. No-sorry guard over EvalMachine.lean.
  2. Compile EvalMachine (its theorems check on compile).
  3. Differential: for every kind="eval" vector in vectors.json, Lean's
     (result_hash, atp_spent) == the vector's expected pair (which the
     oracle produced). Store visibility honors store_subset.

Needs a `lean` binary (elan). Exit 2 if unavailable — never a silent pass.
"""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def main():
    lean = os.environ.get("LEAN", "lean")
    if shutil.which(lean) is None:
        print("eval bridge needs a `lean` binary (elan) — set LEAN=... ; exit 2")
        sys.exit(2)

    body = open(os.path.join(HERE, "EvalMachine.lean")).read()
    if re.search(r"\b(sorry|admit)\b", body) or re.search(r"^\s*axiom\b", body, re.M):
        fail("EvalMachine.lean contains sorry/admit/axiom")
    print("OK    EvalMachine.lean carries no sorry/admit/axiom")

    doc = json.load(open(os.path.join(
        REPO, "tests", "spec_conformance", "vectors.json")))
    objects = doc["objects"]                       # hash_hex -> bytes_hex
    pool_hexes = list(objects.values())            # store pool (byte-values)
    # object KEYS (hashes) align with values by insertion order; index by key
    idx_of = {k: i for i, k in enumerate(objects.keys())}
    evs = [v for v in doc["vectors"] if v["kind"] == "eval"]

    # runner input
    lines = [str(len(pool_hexes))] + pool_hexes + [str(len(evs))]
    for v in evs:
        # store_subset entries are object hashes present in `objects`
        vis = ([idx_of[hx] for hx in v["store_subset"]] if "store_subset" in v
               else list(range(len(pool_hexes))))
        lines.append(f"{v['term']} {v['atp']} {len(vis)} " + " ".join(map(str, vis)))
    stdin = "\n".join(lines) + "\n"

    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, LEAN_PATH=td)
        for mod in ("Sha256", "MachineBytes", "EvalMachine", "EvalRun"):
            r = subprocess.run([lean, os.path.join(HERE, mod + ".lean"),
                                "-o", os.path.join(td, mod + ".olean")],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                fail(f"{mod}.lean does not compile: "
                     + (r.stderr or r.stdout).strip()[:600])
        print("OK    Sha256 + MachineBytes + EvalMachine compile "
              "(step_cost_pos, eval_spent_le check on compile)")
        r = subprocess.run([lean, "--run", os.path.join(HERE, "EvalRun.lean")],
                           input=stdin, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        fail("EvalRun.lean failed: " + (r.stderr or r.stdout).strip()[:600])
    got = r.stdout.strip().splitlines()
    if len(got) != len(evs):
        fail(f"EvalRun emitted {len(got)} lines for {len(evs)} vectors")

    bad = 0
    for v, line in zip(evs, got):
        parts = line.split()
        want = f"{v['expected']['result_hash']} {v['expected']['atp_spent']}"
        if len(parts) != 2 or line.strip() != want:
            bad += 1
            if bad <= 8:
                print(f"DISAGREE  {v['id']}: lean={line.strip()!r} want={want!r}")
    if bad:
        fail(f"{bad}/{len(evs)} eval vectors disagree between Lean and the oracle")
    print(f"OK    Lean evalHash == oracle on {len(evs)} eval vectors "
          f"(result NodeHash AND atp_spent)")
    print(f"\nEVAL-BRIDGE: ALL AGREE ({len(evs)}/{len(evs)})")


if __name__ == "__main__":
    main()
