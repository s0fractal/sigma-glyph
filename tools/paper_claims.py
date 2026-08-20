#!/usr/bin/env python3
"""Recount the numbers the papers in `papers/` state about this repository.

    python3 tools/paper_claims.py

The papers describe this repository. Until they lived in it they were outside
every gate: 17 446 words of quantitative claims about `proof_guard.py`, the pin
registry and the Lean sources, checked by nobody. Every number happened to be
correct on the day they moved in — which is the point. Correct-by-luck and
correct-by-construction look identical right up until the file changes, and this
repository's whole argument is that the difference is the only thing that matters.

So the numbers are recounted here. A claim this script cannot check is listed in
UNCHECKED with the reason, rather than omitted: a checker that silently covers
half its subject reports a green that means less than it looks like.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "papers"

checks, failures, unchecked = [], [], []


def chk(name, got, want):
    ok = got == want
    (checks if ok else failures).append(name)
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:<52} paper={want} actual={got}")


def paper_text(slug):
    return (PAPERS / slug / "paper.md").read_text(encoding="utf-8")


def claimed_int(text, pattern, label):
    """Pull the number the paper states, so the paper is the source of the
    expectation rather than a constant duplicated into this file. A checker
    carrying its own copy of the answer only proves the two copies agree."""
    m = re.search(pattern, text)
    if not m:
        unchecked.append(f"{label}: the paper no longer states it in the expected form")
        return None
    return int(m.group(1).replace(",", "").replace(" ", ""))


guard = paper_text("twenty-one-ways-past-a-proof-guard")

# --- file sizes the guard paper states -------------------------------------
n = claimed_int(guard, r"(\d[\d,]*) lines of Python", "proof_guard.py line count")
if n is not None:
    chk("proof_guard.py line count",
        len((ROOT / "proofs" / "proof_guard.py").read_text().splitlines()), n)

non_lean_line_claim = next(
    (m for sentence in guard.split(".") if "Lean" not in sentence
     if (m := re.search(r"(\d[\d,]*)-line\b", sentence))),
    None)
n = (int(non_lean_line_claim.group(1).replace(",", ""))
     if non_lean_line_claim else None)
if n is None:
    unchecked.append("proof_guard_test.py line count: claim not found")
if n is not None:
    chk("proof_guard_test.py line count",
        len((ROOT / "tests" / "proof_guard_test.py").read_text().splitlines()), n)

n = claimed_int(guard, r"(\d+) KB pin registry", "theorem_pins.json size")
if n is not None:
    chk("theorem_pins.json size (KB, truncated)",
        (ROOT / "proofs" / "theorem_pins.json").stat().st_size // 1024, n)

n = claimed_int(guard, r"(\d[\d,]*) lines of Lean", "Lean line total")
if n is not None:
    chk("Lean line total across proofs/*.lean",
        sum(len(p.read_text().splitlines()) for p in sorted((ROOT / "proofs").glob("*.lean"))), n)

# --- pin counts ------------------------------------------------------------
pins = json.loads((ROOT / "proofs" / "theorem_pins.json").read_text())
m = re.search(r"(\d+) statement pins, (\d+) definition pins", guard)
if m:
    chk("statement pins", len(pins.get("statements", {})), int(m.group(1)))
    chk("definition pins", len(pins.get("definitions", {})), int(m.group(2)))
else:
    unchecked.append("pin counts: the paper no longer states them in the expected form")

# --- the title's own count, against the body -------------------------------
# The title says twenty-one. If the body enumerates a different number, one of
# them is wrong and a reader has no way to tell which.
enumerated = len(set(re.findall(r"\*\*(V\d+) —", guard)))
chk("bypasses enumerated in the body vs the title", enumerated, 21)

# --- what this script deliberately does not check --------------------------
unchecked += [
    "Every prose claim about WHY a bypass worked. Mechanically uncheckable; "
    "the code it describes is in proofs/proof_guard.py and the fixes are in the "
    "commits the paper cites by hash.",
    "The engine paper's complexity and benchmark figures — they are measured "
    "against pinned refs and re-measuring them is tools/test-all.sh's job, not "
    "this script's.",
    "That the papers' arguments are correct. This checks arithmetic, not reasoning.",
]

print()
for u in unchecked:
    print(f"  UNCHECKED  {u}")
print()
if failures:
    print(f"PAPER-CLAIMS: FAILURES ({len(failures)}/{len(checks) + len(failures)}): "
          + ", ".join(failures))
    sys.exit(1)
print(f"PAPER-CLAIMS: ALL PASS ({len(checks)}/{len(checks)} checked, "
      f"{len(unchecked)} deliberately unchecked)")
