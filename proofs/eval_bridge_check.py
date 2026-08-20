#!/usr/bin/env python3
"""Differential bridge for proofs/EvalMachine.lean (Book I evaluator).

The Lean theorems say the in-Lean evaluator is total (fuel-indexed) and
budget-respecting (spent ≤ atp). This bridge is the honest seam that it is
THE oracle: the executed Lean evaluator (EvalRun.lean) reproduces both the
result NodeHash and the exact atp_spent of impl/sigma_glyph.py on every eval
conformance vector — including the divergent Omega (500 ATP → exhausted) and
the store-isolation vectors.

  1. Soundness guard (proof_guard.py, front "eval") over Sha256/MachineBytes/
     EvalMachine and the EvalRun.lean runner: the source layer (literal-aware
     comment stripping, sorry/admit/axiom, import allowlist, metaprogramming
     denylist, coverage registry) plus a data-only environment query asserting
     that every load-bearing theorem depends only on the standard axioms (no
     native_decide, no sorryAx, no smuggled axiom however prefixed) AND still
     states exactly what proofs/theorem_pins.json pins it to state.
  2. Compile EvalMachine (its theorems check on compile).
  3. Differential: for every kind="eval" vector in vectors.json, Lean's
     (result_hash, atp_spent) == the vector's expected pair (which the
     oracle produced). Store visibility honors store_subset.

Needs a `lean` binary (elan). Exit 2 if unavailable — never a silent pass.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import proof_guard  # noqa: E402

#: Load-bearing theorems (proofs/README.md, evaluator section) — all
#: symbolic: the standard axioms only, no native_decide in their cones. The
#: list, the allowed axioms and the pinned statements: theorem_pins.json.
FRONT = proof_guard.load_front("eval")
THEOREMS = FRONT["guarded"]


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def load_eval_vectors():
    path = os.path.join(REPO, "tests", "spec_conformance", "vectors.json")
    with open(path, encoding="utf-8") as source:
        doc = json.load(source)
    objects = doc["objects"]                       # hash_hex -> bytes_hex
    pool_hexes = list(objects.values())            # store pool (byte-values)
    # object KEYS (hashes) align with values by insertion order; index by key
    idx_of = {k: i for i, k in enumerate(objects.keys())}
    evs = [v for v in doc["vectors"] if v["kind"] == "eval"]
    return pool_hexes, idx_of, evs


def runner_input(pool_hexes, idx_of, evs):
    lines = [str(len(pool_hexes))] + pool_hexes + [str(len(evs))]
    for v in evs:
        # store_subset entries are object hashes present in `objects`
        vis = ([idx_of[hx] for hx in v["store_subset"]] if "store_subset" in v
               else list(range(len(pool_hexes))))
        lines.append(f"{v['term']} {v['atp']} {len(vis)} " + " ".join(map(str, vis)))
    return "\n".join(lines) + "\n"


def run_lean_eval(lean, stdin):
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, LEAN_PATH=td)
        # FRONT["build"] + FRONT["runner_sources"] is the single place this
        # front's compiled module set is spelled — the guard reads the same
        # field, so the two cannot drift apart (round-4 F17).
        err = proof_guard.build_front(lean, FRONT, td, runners=True)
        if err:
            fail(err)
        print("OK    Sha256 + MachineBytes + EvalMachine compile "
              "(step_cost_pos, eval_spent_le check on compile)")
        err = proof_guard.guard_semantics(lean, FRONT, td)
        if err:
            fail(err)
        print(f"OK    axiom cones clean, statements match their pins AND every "
              f"definition they are stated in terms of matches its pin, for "
              f"{len(THEOREMS)} evaluator theorems (std axioms only)")
        r = subprocess.run([lean, "--run", os.path.join(HERE, "EvalRun.lean")],
                           input=stdin, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        fail("EvalRun.lean failed: " + (r.stderr or r.stdout).strip()[:600])
    return r.stdout.strip().splitlines()


def compare_eval_vectors(evs, got):
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


def main():
    lean = proof_guard.find_lean()
    if lean is None:
        print("eval bridge needs a `lean` binary (elan) — set LEAN=... ; exit 2")
        return 2
    problems = proof_guard.guard_sources(FRONT)
    if problems:
        fail("source guard: " + "; ".join(problems))
    print("OK    Sha256 + MachineBytes + EvalMachine + EvalRun pass the source "
          "guard (no sorry/admit/axiom, no metaprogramming, imports in-set, "
          "every theorem accounted for)")
    pool_hexes, idx_of, evs = load_eval_vectors()
    got = run_lean_eval(lean, runner_input(pool_hexes, idx_of, evs))
    compare_eval_vectors(evs, got)
    print(f"OK    Lean evalHash == oracle on {len(evs)} eval vectors "
          f"(result NodeHash AND atp_spent)")
    print(f"\nEVAL-BRIDGE: ALL AGREE ({len(evs)}/{len(evs)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
