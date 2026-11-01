#!/usr/bin/env python3
"""Differential bridge for proofs/ResumeMachine.lean, ResumeCycle.lean and ResumeLink.lean (sigma-resume).

The Lean theorems say what a run of segments is (`adv`: adv_split, adv_spent_det)
and what `checkCycle`'s CYCLE_PROVEN establishes (checkCycle_sound,
cycle_proven_no_normal_form), and ResumeLink ties `adv` to Book I's mechanized
`EvalMachine.step` (run_eq_adv). This bridge is the seam that `checkCycle` IS
`impl/sigma_resume.py` `verify_cycle`:

  1. Soundness guard (proof_guard.py, front "resume") over Sha256/MachineBytes/
     EvalMachine/ResumeMachine/ResumeCycle/ResumeLink and the ResumeCycleRun.lean
     runner: the source layer plus the environment query (standard axioms only,
     statements and the definitions they rest on match their pins).
  2. Differential: `checkCycle`, compiled (ResumeCycleRun.lean), against
     `verify_cycle` on generated finite transition tables — true witnesses read
     off a simulated orbit, each with its neighbours (one field off by one,
     another entry, a doubled period, the ceiling below the period or the
     prefix) — and random ones. No Book I term with a state cycle is known, so
     the transition is substituted through `sigma_resume.STEP`, whose contract
     the module states for exactly this purpose. Every verdict (P, N, R) must
     occur, so a run that only ever refuses cannot pass.

Moved from s0fractal/minds (I12 of test_vars1_props.py, without the VARS gate)
on 2026-11-01. Needs a `lean` binary (elan). Exit 2 if unavailable — never a
silent pass.
"""
import hashlib, os, random, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "impl"))
import proof_guard  # noqa: E402
import sigma_glyph as SG  # noqa: E402
import sigma_resume as SR  # noqa: E402

FRONT = proof_guard.load_front("resume")
THEOREMS = FRONT["guarded"]
SEED, TABLES = 20261101, 400
CEIL = SG.VERIFIER_LIMITS["max_atp"]
_TOY_TAG = b"sigma-resume-toy-state"


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def toy_term(i):
    """State `i` of a toy table as a Sigma state: a thunk whose hash names it."""
    return ("thunk", hashlib.sha256(_TOY_TAG + i.to_bytes(4, "big")).digest())


def toy_step(table):
    """`sigma_resume.STEP`'s contract over a table: ("nf",), ("blocked",) or ("fire", j, c)."""
    index = {toy_term(i): i for i in range(len(table))}

    def step(term, remaining, env, stats, limits):
        i = index.get(term)
        if i is None or table[i][0] == "nf":
            return None
        if table[i][0] == "blocked":
            raise SG.Unresolved()
        _, j, c = table[i]
        if c > remaining:
            raise SG.BudgetExhausted()
        return toy_term(j), c
    return step


def _truths(table, start):
    """(entry, entry_spent, actions, cost) for the cycle the orbit from `start` enters, if it enters one."""
    n = len(table)
    orbit, spent, s = [], [0], start
    for _ in range(3 * n + 2):
        orbit.append(s)
        if table[s][0] != "fire":
            break
        s, c = table[s][1], table[s][2]
        spent.append(spent[-1] + c)
    seen = {}
    for p, st in enumerate(orbit):
        if st in seen:
            a = seen[st]
            period = p - a
            return [(orbit[q], spent[q], period, spent[q + period] - spent[q])
                    for q in range(a, len(orbit) - period)]
        seen[st] = p
    return []


def _neighbours(table, start, entry, k, acts, cost):
    n = len(table)
    out = [(table, start, entry, k, acts, cost, CEIL), (table, start, entry, k, 2 * acts, 2 * cost, CEIL)]
    for dk, da, dc in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        if k + dk >= 0 and acts + da >= 0 and cost + dc >= 0:
            out.append((table, start, entry, k + dk, acts + da, cost + dc, CEIL))
    out += [(table, start, (entry + 1) % n, k, acts, cost, CEIL),
            (table, start, entry, k, acts, cost, cost - 1),
            (table, start, entry, k, acts, cost, max(cost, k - 1)),
            (table, start, entry, k, acts, cost, max(cost, k)),
            (table, start, entry, CEIL + 1 + k, acts, cost, CEIL),
            (table, start, entry, k, acts, CEIL + 1, CEIL),
            (table, start, entry, CEIL + 1, acts, cost, CEIL)]
    return out


def gen_cases(rng, n_tables):
    """(table, start, entry, entry_spent, actions, cost, max_atp)."""
    cases = []
    for _ in range(n_tables):
        n = rng.randint(1, 6)
        table = []
        for _ in range(n):
            x = rng.random()
            table.append(("nf",) if x < 0.12 else ("blocked",) if x < 0.2 else
                         ("fire", rng.randrange(n), rng.randint(1, 3)))
        start = rng.randrange(n)
        for truth in _truths(table, start)[:3]:
            cases += _neighbours(table, start, *truth)
        for _ in range(3):
            cases.append((table, start, rng.randrange(n + 1), rng.randint(0, 8), rng.randint(0, 4),
                          rng.randint(0, 9), rng.choice([CEIL, rng.randint(0, 9)])))
    # the ceiling's boundary: one action costing the ceiling, entered at and one above it, period at and above it
    edge = [("fire", 0, CEIL)]
    cases += [(edge, 0, 0, CEIL + d, 1, CEIL + p, CEIL) for d in (0, 1) for p in (0, 1)]
    return cases


def runner_input(cases):
    lines = []
    for table, start, entry, k, acts, cost, ceil in cases:
        enc = []
        for t in table:
            enc += [0] if t[0] == "nf" else [1] if t[0] == "blocked" else [2, t[1], t[2]]
        lines.append(" ".join(map(str, [len(table), *enc, start, entry, k, acts, cost, ceil])))
    return "\n".join(lines) + "\n"


def run_lean(lean, stdin):
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, LEAN_PATH=td)
        err = proof_guard.build_front(lean, FRONT, td, runners=True)
        if err:
            fail(err)
        print("OK    Sha256 + MachineBytes + EvalMachine + ResumeMachine + ResumeCycle + ResumeLink compile")
        err = proof_guard.guard_semantics(lean, FRONT, td)
        if err:
            fail(err)
        print(f"OK    axiom cones clean, statements match their pins AND every definition they are stated in "
              f"terms of matches its pin, for {len(THEOREMS)} resume theorems (std axioms only)")
        r = subprocess.run([lean, "--run", os.path.join(HERE, "ResumeCycleRun.lean")],
                           input=stdin, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        fail("ResumeCycleRun.lean failed: " + (r.stderr or r.stdout).strip()[:600])
    return r.stdout.split()


def python_verdict(case):
    """`verify_cycle` on the case as P (CYCLE_PROVEN), N (NOT_ASSESSED) or R (any refusal)."""
    table, start, entry, k, acts, cost, ceil = case
    env = SR.Environment([], {})
    root_doc, cid = SR.root(toy_term(start)[1], env)
    witness = {"schema": SR.SCHEMA_CYCLE, "computation_id": cid, "entry_spent_total": k,
               "entry_state_id": SR.state_id(SR.encode_state(cid, toy_term(entry))),
               "cycle_action_count": acts, "cycle_cost": cost}
    saved = SR.STEP
    SR.STEP = toy_step(table)
    try:
        v = SR.verify_cycle((root_doc, cid), env, witness, dict(SG.VERIFIER_LIMITS, max_atp=ceil))
    finally:
        SR.STEP = saved
    return "P" if v == "CYCLE_PROVEN" else "N" if v.startswith("NOT_ASSESSED") else "R"


def main():
    lean = proof_guard.find_lean()
    if lean is None:
        print("resume bridge needs a `lean` binary (elan) — set LEAN=... ; exit 2")
        return 2
    problems = proof_guard.guard_sources(FRONT)
    if problems:
        fail("source guard: " + "; ".join(problems))
    print("OK    the resume front and ResumeCycleRun pass the source guard (no sorry/admit/axiom, no "
          "metaprogramming, imports in-set, every theorem accounted for)")
    cases = gen_cases(random.Random(SEED), TABLES)
    got = run_lean(lean, runner_input(cases))
    if len(got) != len(cases) or set(got) - {"P", "N", "R"}:
        fail(f"ResumeCycleRun answered {got[:5]}… for {len(cases)} cases")
    bad, counts = 0, {}
    for case, m in zip(cases, got):
        counts[m] = counts.get(m, 0) + 1
        sr = python_verdict(case)
        if sr != m:
            bad += 1
            if bad <= 8:
                print(f"DISAGREE  checkCycle {m}, verify_cycle {sr} on {case}")
    if bad:
        fail(f"{bad}/{len(cases)} cases disagree between checkCycle and verify_cycle")
    if set(counts) != {"P", "N", "R"}:
        fail(f"the generated cases never reach every verdict: {counts}")
    print(f"OK    checkCycle == verify_cycle on {len(cases)} cases "
          f"(CYCLE_PROVEN {counts['P']}, NOT_ASSESSED {counts['N']}, refused {counts['R']})")
    print(f"\nRESUME-BRIDGE: ALL AGREE ({len(cases)}/{len(cases)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
