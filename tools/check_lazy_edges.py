#!/usr/bin/env python3
"""Re-verify the two v0.5 lazy-evaluation edges from the 2026-07 peer-Claude review:
discarded-unresolvable-branch (TV-11 family) and dangling-result (TV-8).
Asserts the vectors exist in the suite with the expected canonical outcomes,
then runs the full reference oracle."""
import json, subprocess, sys

EDGES = {
    # discarded-unresolvable-branch: dead ghost must not block reduction
    "EV-K-DEAD-MISSING":        ("normal_form", 7),
    "EV-K-DEAD-NESTED-MISSING": ("normal_form", 7),
    "EV-S-KI-KK-DEAD-Z":        ("normal_form", 20),
    # dangling-result: the root result is always demanded; ghost cannot escape
    "EV-TV8-MISSING-CHILD":     ("unresolved_reference", 4),
}

suite = json.load(open("tests/spec_conformance/vectors.json"))
byid = {v["id"]: v for v in suite["vectors"]}
ok = True
for vid, (outcome, spent) in EDGES.items():
    v = byid.get(vid)
    if v is None:
        print(f"MISSING {vid}"); ok = False; continue
    exp = v["expected"]
    if exp["outcome"] == outcome and exp["atp_spent"] == spent:
        print(f"OK  {vid} -> {outcome}, spent {spent}")
    else:
        print(f"FAIL {vid}: suite says {exp['outcome']}, spent {exp['atp_spent']}"); ok = False

r = subprocess.run([sys.executable, "tests/spec_conformance/run_reference.py"],
                   capture_output=True, text=True)
last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
print(last)
ok = ok and r.returncode == 0 and "ALL PASS" in last
print("lazy edges sealed" if ok else "lazy edges NOT sealed")
sys.exit(0 if ok else 1)
