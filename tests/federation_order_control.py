#!/usr/bin/env python3
"""Order control for Book III selection: the input order of candidates must
not decide the outcome.

    python3 tests/federation_order_control.py            # Python oracle, and Go when a toolchain is present
    python3 tests/federation_order_control.py --no-go    # Python oracle only (the tag says so)

`select(candidates, ...)` is specified as a derivation over a SET of accepted
assertions (Book III s4); the reference takes a list. Every pinned `select`
vector and every adversarial case below is replayed under every permutation
of its candidates (all n! for n <= 6, a seeded sample above that), and the
result must be byte-identical to the unpermuted run. The Go implementation
is held to the same property when a toolchain is available.

Why this exists: in a sibling project two defects had one root, "the first
source in iteration order decided the verdict" (a chamber loop that broke on
the first suspended chamber; an aggregate that hid a per-item loss). Nothing
here was found to depend on order -- this file is the control that keeps it
so, and it proves it can fail: two order-dependent stand-ins for `select`
are run through the same check and MUST be caught.
"""
import copy
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_federation as sf  # noqa: E402

VEC_PATH = ROOT / "tests/spec_conformance/federation_vectors.json"
GO_DIR = ROOT / "impl-go"
MAX_FULL = 6          # n! permutations up to here
SAMPLE = 200          # seeded sample beyond it
TAG = "FEDERATION-ORDER-CONTROL"

ok = []


def chk(name, cond, detail=""):
    ok.append(bool(cond))
    print(("OK  " if cond else "FAIL"), name, "" if cond else detail)


def permutations_of(n, seed):
    if n <= MAX_FULL:
        return list(itertools.permutations(range(n)))
    rng = random.Random(seed)
    return [tuple(rng.sample(range(n), n)) for _ in range(SAMPLE)]


def order_independent(fn, case):
    """True iff fn gives the same result under every permutation of the
    candidates. Returns (independent, first_disagreeing_permutation)."""
    cands = case["candidates"]
    base = fn(copy.deepcopy(cands), case["policy"], case["jurisdiction"], case["node"], case["epoch"])
    for p in permutations_of(len(cands), seed=len(cands)):
        got = fn([copy.deepcopy(cands[i]) for i in p], case["policy"],
                 case["jurisdiction"], case["node"], case["epoch"])
        if got != base:
            return False, p
    return True, None


# ---- cases: the pinned select vectors plus adversarial shapes ---------------

def wid(ch):
    return ch * 64


def cand(ch, actor, ts, epoch, am=40000):
    return {"warrant_id": wid(ch), "actor": actor, "ts": ts,
            "assertion": {"annotation": sf.ASSERTION_TAG, "jurisdiction": sf.J,
                          "node": sf.NODE, "epoch": epoch,
                          "wave": {"ph": 8192, "am": am, "en": -100}}}


POLICY_TIE = {"federation_policy": "sigma-glyph.selection@v1",
              "order": [{"field": "epoch", "dir": "desc"}]}
POLICY_QUOTA = {"federation_policy": "sigma-glyph.selection@v1",
                "order": [{"field": "epoch", "dir": "desc"}, {"field": "ts", "dir": "desc"}],
                "quota_per_actor_epoch": 1}


def adversarial_cases():
    base = dict(policy=POLICY_TIE, jurisdiction=sf.J, node=sf.NODE, epoch=9)
    yield "ADV-DUP-ID-DIFFERENT-WAVE", dict(base, candidates=[
        cand("1", "a@x", 100, 5, am=40000), cand("1", "a@x", 100, 5, am=1)])
    yield "ADV-TIE-THREE-WAY", dict(base, candidates=[
        cand("3", "c@z", 1, 7), cand("1", "a@x", 2, 7), cand("2", "b@y", 3, 7)])
    yield "ADV-QUOTA-GROUP-ORDER", dict(base, policy=POLICY_QUOTA, candidates=[
        cand("5", "a@x", 5, 7), cand("2", "a@x", 9, 7), cand("9", "b@y", 1, 7),
        cand("4", "b@y", 2, 6), cand("7", "a@x", 7, 7), cand("1", "c@z", 3, 7)])
    yield "ADV-MIXED-LIVE-AND-DEAD", dict(base, candidates=[
        cand("2", "a@x", 1, 12),          # future: not live
        cand("4", "b@y", 1, 8),
        {"warrant_id": "nothex", "actor": "z@z", "ts": 1,
         "assertion": cand("6", "z@z", 1, 8)["assertion"]},   # malformed: not live
        cand("3", "c@z", 1, 8)])


doc = json.loads(VEC_PATH.read_text())
cases = [(v["id"], v) for v in doc["vectors"] if v["kind"] == "select"]
cases += list(adversarial_cases())

# ---- 1. the Python oracle ---------------------------------------------------

for name, case in cases:
    indep, p = order_independent(sf.select, case)
    chk(f"PY {name} n={len(case['candidates'])}", indep, f"differs under permutation {p}")

# ---- 2. the check can fail: two order-dependent stand-ins -------------------

def select_first_live(candidates, policy, jurisdiction, node, epoch):
    live = sf._live_candidates(candidates, policy, jurisdiction, node, epoch)
    return {"status": "selected" if live else "absent",
            "selected": live[0] if live else None, "conflict_set": []}


def select_tie_by_input_order(candidates, policy, jurisdiction, node, epoch):
    """The real risk: correct sort, but a tie is resolved by whoever came first
    instead of being surfaced as a conflict."""
    import functools
    live = sf._live_candidates(candidates, policy, jurisdiction, node, epoch)
    live = sf._apply_quota(live, policy.get("quota_per_actor_epoch"),
                           policy["order"] + [{"field": "warrant_id", "dir": "asc"}])
    if not live:
        return {"status": "absent", "selected": None, "conflict_set": []}
    live.sort(key=functools.cmp_to_key(lambda x, y: sf._cmp_order(x, y, policy["order"])))
    return {"status": "selected", "selected": live[0], "conflict_set": []}


for mut_name, mut in (("first-live", select_first_live),
                      ("tie-by-input-order", select_tie_by_input_order)):
    caught = [name for name, case in cases if not order_independent(mut, case)[0]]
    chk(f"MUTATION {mut_name} is caught", caught, "the permutation check accepted an order-dependent select")
    print(f"     caught on: {', '.join(caught) or '-'}")

# ---- 3. the Go implementation, when a toolchain is present -------------------

go_ran = False
if "--no-go" not in sys.argv[1:] and shutil.which("go"):
    out = Path(tempfile.gettempdir()) / "sigma-federation-go-order-control"
    env = dict(os.environ, GOCACHE=str(GO_DIR / ".gocache"))
    subprocess.run(["go", "build", "-o", str(out), "."], cwd=GO_DIR, env=env, check=True)

    def go_select(candidates, policy, jurisdiction, node, epoch):
        payload = {"candidates": candidates, "policy": policy, "jurisdiction": jurisdiction,
                   "node": node, "epoch": epoch}
        p = subprocess.run([str(out), "select"], input=json.dumps(payload, ensure_ascii=False).encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return json.loads(p.stdout.decode())

    def py_as_go(candidates, policy, jurisdiction, node, epoch):
        r = sf.select(candidates, policy, jurisdiction, node, epoch)
        return {"status": r["status"],
                "selected_warrant": r["selected"]["warrant_id"] if r["selected"] else None,
                "conflict_set": r["conflict_set"]}

    for name, case in cases:
        indep, p = order_independent(go_select, case)
        chk(f"GO {name}", indep, f"differs under permutation {p}")
        same = go_select(copy.deepcopy(case["candidates"]), case["policy"], case["jurisdiction"],
                         case["node"], case["epoch"]) == py_as_go(
            copy.deepcopy(case["candidates"]), case["policy"], case["jurisdiction"], case["node"], case["epoch"])
        chk(f"GO==PY {name}", same, "Go and Python disagree on the unpermuted case")
    go_ran = True
elif "--no-go" in sys.argv[1:]:
    print("go: skipped by --no-go")
else:
    print("go: skipped, no toolchain on PATH")

scope = "python, go" if go_ran else "python only; go skipped"
verdict = "ALL PASS" if all(ok) else "FAILURES PRESENT"
print(f"\n{TAG}: {verdict} ({sum(ok)}/{len(ok)}; {scope})")
sys.exit(0 if all(ok) else 1)
