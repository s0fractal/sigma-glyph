#!/usr/bin/env python3
"""--retry re-delivers a round's recorded prompt to a reviewer that could not be
reached. It must not let a family that returned a named verdict be asked again:
the gate takes each family's LATEST attempt (`standing`), so re-asking a family
that said REJECT until it says ADOPT turns a failed gate into a passing one.

Offline: no API call is made; attempts are written the way review_one() writes them.
Run: python3 tests/candidate_gate_retry_test.py   (nonzero exit on any failure)
"""
import contextlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("candidate_gate", ROOT / "tools" / "candidate_gate.py")
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)
ok = []


def chk(cond, label, detail=""):
    ok.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + label + ("" if cond else f" -> {detail}"))


def attempt(freeze, family, verdict, retry):
    """Write one attempt as review_one() does; return None if --retry is refused."""
    try:
        md, js, number, previous = cg.attempt_paths(freeze, family, retry)
    except SystemExit:
        return None
    record = {"family": family, "attempt": number if retry else 1, "verdict": verdict,
              "model_answered": family + "-model", "follows": previous}
    js.write_text(json.dumps(record)); md.write_text(verdict + "\n")
    return record


def gate(freeze, results):
    with contextlib.redirect_stdout(io.StringIO()):
        return cg.report(results, freeze)


def main():
    cg.ROOT = Path(tempfile.mkdtemp())
    freeze = "gates/probe"
    (cg.ROOT / freeze).mkdir(parents=True)
    first = [attempt(freeze, "google", "REJECT", False), attempt(freeze, "deepseek", "ADOPT", False),
             attempt(freeze, "qwen", "NO VERDICT", False)]
    chk(gate(freeze, first) == 1, "first attempts: one REJECT and one NO VERDICT fail the gate")
    again = attempt(freeze, "google", "ADOPT", True)
    chk(again is None, "--retry of a family that returned REJECT is refused", again)
    chk(cg.standing(freeze)["google"]["verdict"] == "REJECT", "the REJECT still stands",
        cg.standing(freeze)["google"])
    adopt_again = attempt(freeze, "deepseek", "REJECT", True)
    chk(adopt_again is None, "--retry of a family that returned ADOPT is refused too", adopt_again)
    delivered = attempt(freeze, "qwen", "ADOPT", True)
    chk(delivered is not None and delivered["attempt"] == 2 and delivered["follows"] == "review-qwen.md",
        "--retry of a family that returned NO VERDICT is allowed and follows it", delivered)
    chk(gate(freeze, [delivered]) == 1, "with the REJECT standing, the gate still fails")
    print("\nCANDIDATE-GATE-RETRY: " + ("ALL PASS" if all(ok) else "FAILURES PRESENT"))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
