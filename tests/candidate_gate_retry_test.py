#!/usr/bin/env python3
"""Attempt records are append-only. --retry re-delivers a round's recorded prompt to a reviewer that could not be
reached. It must not let a family that returned a named verdict be asked again:
the gate takes each family's LATEST attempt (`standing`), so re-asking a family
that said REJECT until it says ADOPT turns a failed gate into a passing one.

A plain re-run is the other re-ask path: it wrote review-{family}.json again, so the
same shopping worked without --retry. Once a first attempt exists a plain run refuses;
after NO VERDICT only --retry may follow; after a named verdict, only a new round.
Refusal happens before any reviewer is called and before any file is written.

Offline: no API call is made; attempts are written the way review_one() writes them.
Run: python3 tests/candidate_gate_retry_test.py   (nonzero exit on any failure)
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
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
              "model_answered": family + "-model", "follows": previous,
              "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
              "system_sha256": hashlib.sha256(cg.SYSTEM.encode()).hexdigest()}
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

    # The plain re-run path (Codex review of #59): no --retry, same round, same family.
    plain = attempt(freeze, "google", "ADOPT", False)
    chk(plain is None, "a plain re-run of a family that returned REJECT is refused", plain)
    chk(cg.standing(freeze)["google"]["verdict"] == "REJECT", "the REJECT still stands after a plain re-run",
        cg.standing(freeze)["google"])
    chk(attempt(freeze, "deepseek", "REJECT", False) is None,
        "a plain re-run of a family that returned ADOPT is refused")
    fresh = "gates/probe-nv"
    (cg.ROOT / fresh).mkdir(parents=True)
    attempt(fresh, "qwen", "NO VERDICT", False)
    chk(attempt(fresh, "qwen", "ADOPT", False) is None,
        "a plain re-run after NO VERDICT is refused too: only --retry files a next attempt")
    chk(json.loads((cg.ROOT / fresh / "review-qwen.json").read_text())["verdict"] == "NO VERDICT",
        "the first attempt record is unchanged")

    # Both re-ask paths through run(). The first family in REVIEWERS order has only a
    # NO VERDICT, so a tool that checks family by family would already have called it
    # and written its record before reaching the named verdicts: the whole run must
    # refuse up front, before any call and before any write.
    calls = []
    cg.ask = lambda *a, **k: calls.append(a) or ("VERDICT: ADOPT", "m", "stop")
    cg.check_freeze = lambda f: ("0" * 40, None)
    cg.build_prompt = lambda: "prompt"
    mixed = "gates/probe-run"
    (cg.ROOT / mixed).mkdir(parents=True)
    (cg.ROOT / mixed / "prompt.txt").write_text("prompt")
    (cg.ROOT / mixed / "prompt.system.txt").write_text(cg.SYSTEM)
    for (family, _), verdict in zip(cg.REVIEWERS, ("NO VERDICT", "REJECT", "ADOPT")):
        attempt(mixed, family, verdict, False)
    before = {p.name: p.read_bytes() for p in (cg.ROOT / mixed).iterdir()}
    for label, retry in (("--retry run", True), ("plain run", False)):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                cg.run(mixed, 1, [], 100, retry)
            refused = False
        except SystemExit:
            refused = True
        chk(refused and calls == [], f"{label} over a round holding named verdicts is refused "
            "before any reviewer is called", (refused, len(calls)))
    after = {p.name: p.read_bytes() for p in (cg.ROOT / mixed).iterdir()}
    chk(after == before, "no file was written or replaced",
        sorted(n for n in set(after) | set(before) if after.get(n) != before.get(n)))
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cg.run(mixed, 1, [cg.REVIEWERS[0][0]], 100, True)
        retried = True
    except SystemExit:
        retried = False
    chk(retried and len(calls) == 1 and (cg.ROOT / mixed / f"review-{cg.REVIEWERS[0][0]}.retry-1.json").exists(),
        "--retry --only the NO VERDICT family still delivers", (retried, len(calls)))

    # Concurrency (Codex review of #59): two processes can both pass the preflight before
    # either writes, both ask the same family, and the last write_text() wins. A round is
    # locked for the whole run, before any prompt, call or write; and an attempt record is
    # created exclusively, so even a writer that got past the lock cannot replace one.
    family = cg.REVIEWERS[0][0]
    locked = "gates/probe-locked"
    (cg.ROOT / locked).mkdir(parents=True)
    holder = subprocess.Popen(
        [sys.executable, "-c", "import fcntl, os, sys; fd = os.open(sys.argv[1], os.O_RDONLY); "
         "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); print('held', flush=True); sys.stdin.read()",
         str(cg.ROOT / locked)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    chk(holder.stdout.readline().strip() == "held", "another process holds the round")
    calls.clear()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cg.run(locked, 1, [family], 100, False)
        refused = False
    except SystemExit:
        refused = True
    holder.stdin.close(); holder.wait(timeout=30)
    chk(refused and calls == [] and list((cg.ROOT / locked).iterdir()) == [],
        "a run over a round another process holds is refused before any call or write",
        (refused, len(calls), sorted(p.name for p in (cg.ROOT / locked).iterdir())))

    raced = "gates/probe-raced"
    (cg.ROOT / raced).mkdir(parents=True)
    other = {"family": family, "attempt": 1, "verdict": "REJECT", "model_answered": "other-process"}

    def racing_ask(*a, **k):
        # While this process waits on the API, another writes its own first attempt.
        (cg.ROOT / raced / f"review-{family}.md").write_text("REJECT\n")
        (cg.ROOT / raced / f"review-{family}.json").write_text(json.dumps(other))
        return "VERDICT: ADOPT", "m", "stop"
    cg.ask = racing_ask
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cg.run(raced, 1, [family], 100, False)
    except SystemExit:
        pass
    kept = json.loads((cg.ROOT / raced / f"review-{family}.json").read_text())
    chk(kept == other and (cg.ROOT / raced / f"review-{family}.md").read_text() == "REJECT\n",
        "an attempt record written by another process during the call is not replaced", kept)
    print("\nCANDIDATE-GATE-RETRY: " + ("ALL PASS" if all(ok) else "FAILURES PRESENT"))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
