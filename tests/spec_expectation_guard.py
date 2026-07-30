#!/usr/bin/env python3
"""Negative control for the spec-derived conformance gate.

A gate that has never been seen to fail is not a gate. The Book I and Book II
generators now carry hand-written, spec-cited expectations and REFUSE to write
their vector files when the oracle disagrees (tests/spec_conformance/generate.py
SPEC_EXPECT; impl/sigma_wave.py SPEC_EXPECT) — the discipline the governance
suite has had since v0.6.x (tools/anchor_governance.py cmd_gen).

This test proves the refusal fires. For each mutation it copies the oracle and
its generator into a scratch tree, breaks exactly one normative behaviour, and
requires that the generator (a) exits nonzero, (b) says REFUSING TO GENERATE,
(c) names the vector the spec pins, and (d) leaves no vector file behind.

The positive control runs the same harness UNMUTATED and requires the generated
files to be byte-identical to the committed ones — so a mutation that refuses
for some unrelated reason cannot be mistaken for a working gate.

    python3 tests/spec_expectation_guard.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOOK1 = {
    "oracle": "impl/sigma_glyph.py",
    "generator": "tests/spec_conformance/generate.py",
    "output": "tests/spec_conformance/vectors.json",
    "spec": "spec/book-1-truth.md",
}
BOOK2 = {
    "oracle": "impl/sigma_wave.py",
    "generator": "impl/sigma_wave.py",
    "argv": ["gen"],
    "output": "tests/spec_conformance/wave_vectors.json",
    "spec": "spec/book-2-navigation.md",
}

# (label, book, old, new, vector id the refusal must name)
MUTATIONS = [
    ("Book I s3.4: R-I priced at 2 ATP instead of 1", BOOK1,
     "            return a, 1\n", "            return a, 2\n", "EV-TV4-IK"),
    ("Book I s3.4: R-S priced flat instead of 1 + size(z)", BOOK1,
     "c = 1 + size(z)", "c = 1 + 0 * size(z)", "EV-TV5-SKKI"),
    ("Book I s5.1: genesis K forged from a different preimage", BOOK1,
     'K_BYTES = ser(LITERAL, F_ATOM, atom=sha(b"K"))',
     'K_BYTES = ser(LITERAL, F_ATOM, atom=sha(b"k"))', "OBJ-K"),
    ("Book I s4.1(3): the length check is dropped", BOOK1,
     "    if len(buf) != exp: return None", "    if False: return None",
     "INV-LEN-LONG"),
    ("Book II s3: div_round_half_up degraded to floor division", BOOK2,
     "    if 2 * r >= d:\n        q += 1\n", "    if False:\n        q += 1\n",
     "WV-NEG-TIE"),
    ("Book II s5: amp_factor normalised by 65536 instead of 65534", BOOK2,
     "div_round_half_up((r + 32767) * 65535, 65534)",
     "div_round_half_up((r + 32767) * 65535, 65536)", None),
    ("Book II s6.2: the FALSE phase pin drifts by one", BOOK2,
     '"FALSE": (["APPLY", "K", "I"], {"ph": 49152}),',
     '"FALSE": (["APPLY", "K", "I"], {"ph": 49153}),', "WV-COORD-FALSE"),
]

NEEDED = ["impl/sigma_glyph.py", "impl/sigma_wave.py",
          "tests/spec_conformance/generate.py"]

ok = []


def chk(name, cond, detail=""):
    ok.append(cond)
    print(("OK  " if cond else "FAIL"), name, "" if cond else detail)


def stage(tmp):
    """Copy just enough of the tree that the generators run unchanged."""
    for rel in NEEDED:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return tmp


def run(tmp, book):
    cmd = [sys.executable, str(tmp / book["generator"])] + book.get("argv", [])
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp))


def main():
    with tempfile.TemporaryDirectory() as td:
        tmp = stage(Path(td) / "clean")
        for book in (BOOK1, BOOK2):
            p = run(tmp, book)
            out = tmp / book["output"]
            same = out.exists() and out.read_bytes() == (ROOT / book["output"]).read_bytes()
            chk(f"positive control: {book['generator']} generates and matches the "
                f"committed {Path(book['output']).name}",
                p.returncode == 0 and same,
                f"rc={p.returncode} identical={same} {p.stdout.strip()[-200:]}")

    for label, book, old, new, want_id in MUTATIONS:
        with tempfile.TemporaryDirectory() as td:
            tmp = stage(Path(td) / "mutated")
            target = tmp / book["oracle"]
            text = target.read_text()
            if text.count(old) != 1:
                chk(label, False,
                    f"mutation anchor appears {text.count(old)}x in {book['oracle']} "
                    f"— the guard is stale, fix it before trusting the gate")
                continue
            target.write_text(text.replace(old, new))
            p = run(tmp, book)
            blob = p.stdout + p.stderr
            refused = p.returncode != 0 and "REFUSING TO GENERATE" in blob
            named = want_id is None or want_id in blob
            unwritten = not (tmp / book["output"]).exists()
            chk(label, refused and named and unwritten,
                f"rc={p.returncode} refused={refused} named={named} "
                f"unwritten={unwritten}\n---\n{blob.strip()[:900]}\n---")

    print(("\nSPEC-EXPECTATION-GUARD: ALL PASS" if all(ok)
           else "\nSPEC-EXPECTATION-GUARD: FAILURES PRESENT")
          + f" ({sum(ok)}/{len(ok)})")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
