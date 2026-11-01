#!/usr/bin/env python3
"""sigma_provider resume: a foreign checkpoint is continued only after it is
replayed from the caller's own root.

    python3 tests/provider_resume_test.py [--python PY]

With --python, runs the INSTALLED module through `PY -m sigma_provider serve`
from outside the checkout; without it, impl/sigma_provider.py serve. The cases
are S01-S07 and S09 of the Warrant handoff acceptance list (the Warrant-side
cases S08 and S10 are tested in Warrant). The mutants copy impl/ and remove one
guard each; a mutant is KILLED only if its named case fails.

The need it records: raw `advance` trusts its checkpoint (its documented
precondition), so it continues a checkpoint of another computation under the
caller's input without noticing (control R0). A consumer continuing someone
else's work needs verify-then-advance on the same bytes; `resume` is that
composition, with no change to Book I, ATP, roots or the state codec.
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK1 = "sigma-book1-0.6.0/hash-thunk/leftmost-outermost"
RICH = "sigma-resume-draft/ski+Y+M+W/hash-thunk/leftmost-outermost"


class Serve:
    def __init__(self, argv):
        self.argv, self.cwd = argv, tempfile.mkdtemp()

    def __call__(self, op, args, blobs=None):
        req = {"sigma_provider": 1, "op": op, "args": args,
               "blobs": {h: base64.b64encode(b).decode() for h, b in (blobs or {}).items()}}
        p = subprocess.run(self.argv, input=json.dumps(req), capture_output=True, text=True, cwd=self.cwd, timeout=120)
        resp = json.loads(p.stdout)
        if "refused" in resp:
            return {"refused": resp["refused"]}
        return resp["ok"]


def b(v):
    return base64.b64decode(v)


def e(v):
    return base64.b64encode(v).decode()


def cases(call):
    out = {}
    term = call("term", {"expr": "S K K (K I)"})
    nodes = {h: b(v) for h, v in term["nodes"].items()}
    hs, inp = sorted(nodes), term["input"]
    base = {"runtime": BOOK1, "input": inp, "hashes": hs}
    s = call("start", base, nodes)
    paused = call("advance", dict(base, checkpoint=s["checkpoint"], state=s["state"], credit=2), nodes)
    ck, st = paused["checkpoint"], paused["state"]

    def resume(credit=100, max_actions=None, blobs=nodes, **over):
        args = dict(base, checkpoint=ck, state=st, credit=credit, **over)
        if max_actions is not None:
            args["max_actions"] = max_actions
        return call("resume", args, blobs)

    # R0 (the need): raw advance continues this checkpoint under another input
    other = call("term", {"expr": "K"})["input"]
    raw = call("advance", dict(base, input=other, checkpoint=ck, state=st, credit=100), nodes)
    out["R0"] = raw.get("outcome") == "NORMAL_FORM"

    # S01: verified, advanced, and the final checkpoint replays from the root
    r = resume()
    final = r.get("segment", {})
    replay = call("verify", dict(base, chain=[[final.get("checkpoint", e(b"")), final.get("state", e(b""))]]), nodes) \
        if final else {"results": [{}]}
    out["S01"] = (paused["outcome"] == "PAUSED" and r.get("status") == "ADVANCED"
                  and r["base_verification"]["basis"] == "REPLAYED" and final.get("outcome") == "NORMAL_FORM"
                  and replay["results"][0].get("basis") == "REPLAYED"
                  and replay["results"][0].get("result") == final.get("result"))
    # S02: the caller names another input: refused, nothing advanced
    r2 = resume(input=other)
    out["S02"] = r2.get("status") == "REFUSED" and "segment" not in r2
    # S03: another environment or runtime: refused
    out["S03"] = all(x.get("status") == "REFUSED" and "segment" not in x
                     for x in (resume(hashes=[]), resume(runtime=RICH)))
    # S04: the base cannot even be replayed without the declared bytes: refused
    # as not assessed here, never an answer (and not IMPOSSIBLE)
    r4 = call("resume", dict(base, checkpoint=final.get("checkpoint", ck), state=final.get("state", st), credit=10), {})
    out["S04"] = r4.get("status") == "REFUSED" and "segment" not in r4 \
        and r4["base_verification"]["code"].startswith("NOT_ASSESSED")
    # S05: the early prefix replays without the nodes, but the next action needs
    # bytes not delivered here: DEFERRED, with the prefix still verified
    r5 = resume(blobs={})
    out["S05"] = r5.get("status") == "DEFERRED" and r5["base_verification"]["basis"] == "REPLAYED" \
        and "segment" not in r5 and r5["diagnostic"] == "EVIDENCE_UNAVAILABLE"
    # S06: a terminal base is not re-credited: normal form and blocked reference
    nf = call("resume", dict(base, checkpoint=final.get("checkpoint", ck), state=final.get("state", st), credit=50), nodes)
    y = call("term", {"expr": "Y I"})
    ynodes = {h: b(v) for h, v in y["nodes"].items()}
    ybase = {"runtime": BOOK1, "input": y["input"], "hashes": sorted(ynodes)}
    ys = call("start", ybase, ynodes)
    yb = call("advance", dict(ybase, checkpoint=ys["checkpoint"], state=ys["state"], credit=50), ynodes)
    yr = call("resume", dict(ybase, checkpoint=yb["checkpoint"], state=yb["state"], credit=50), ynodes)
    out["S06"] = (nf.get("status") == "TERMINAL" and nf.get("code") == "NORMAL_FORM" and "segment" not in nf
                  and yb["outcome"] == "BLOCKED_REFERENCE" and yr.get("status") == "TERMINAL"
                  and yr.get("code") == "BLOCKED_REFERENCE")
    # S07: an action limit returns an atomic checkpoint that itself replays
    r7 = resume(max_actions=1)
    seg = r7.get("segment", {})
    again = call("verify", dict(base, chain=[[seg.get("checkpoint", e(b"")), seg.get("state", e(b""))]]), nodes) \
        if seg else {"results": [{}]}
    out["S07"] = seg.get("outcome") == "INCOMPLETE" and again["results"][0].get("basis") == "REPLAYED"
    # S09: the same parent and credit give the same segment; no hidden job
    out["S09"] = resume() == r
    # malformed resume operands stay a protocol refusal
    out["S00"] = "refused" in call("resume", dict(base, checkpoint=ck, state=st, credit=True), nodes)
    # S20 (sigma-resume §5 on the wire): the witness bytes are canonical JSON or refused before replay. The same
    # well-shaped witness: spaced bytes are INVALID_CYCLE_WITNESS, canonical bytes reach replay (and fail there,
    # as a witness of another computation must).
    wit = {"schema": "sigma-resume.cycle@draft-1", "computation_id": "0" * 64, "entry_spent_total": 1,
           "entry_state_id": "0" * 64, "cycle_action_count": 1, "cycle_cost": 1}
    spaced = call("verify_cycle", dict(base, witness=e(json.dumps(wit, sort_keys=True).encode())), nodes)
    canon = call("verify_cycle", dict(base, witness=e(json.dumps(wit, sort_keys=True, separators=(",", ":")).encode())),
                 nodes)
    out["S20"] = (spaced.get("code", "").startswith("INVALID_CYCLE_WITNESS") and "not canonical" in spaced["code"]
                  and canon.get("code", "").startswith("PREFIX_MISMATCH"))
    # S21: JSON nested past the interpreter's recursion limit raises RecursionError, not ValueError. Every place
    # the provider decodes JSON answers it as malformed instead of ending without an answer: the request itself,
    # a cycle witness, a checkpoint (Codex's finding on #93: a nested witness ended Python 3.11's provider).
    deep = b"[" * 10**6 + b"0" + b"]" * 10**6
    try:
        raw = subprocess.run(call.argv, input=deep, capture_output=True, cwd=call.cwd, timeout=120)
        request = json.loads(raw.stdout)
        witness = call("verify_cycle", dict(base, witness=e(b'{"schema":' + deep + b"}")), nodes)
        chain = call("verify", dict(base, chain=[[e(b'{"schema":' + deep + b"}"), st]]), nodes)
        out["S21"] = ("refused" in request and witness.get("code", "").startswith("INVALID_CYCLE_WITNESS")
                      and "INVALID_ENCODING" in json.dumps(chain))
    except Exception as x:          # no answer at all is the defect: the case fails, it does not crash the suite
        print(f"S21 raised {type(x).__name__}")
        out["S21"] = False
    return out


MUTANTS = [
    ("resume advances without verifying the base", "S02",
     '    if basis != R.REPLAYED:\n        return {"status": "REFUSED", "base_verification": base}\n', ""),
    ("a local diagnostic is treated as resumable", "S05",
     '    if code not in RESUMABLE:\n        return {"status": "DEFERRED", "base_verification": base, "diagnostic": code}\n', ""),
    ("a terminal base is advanced again", "S06",
     '    if code in TERMINAL:\n', '    if False:\n'),
    ("the witness bytes are parsed by plain json.loads", "S20",
     "        doc = R.parse_cycle_witness(witness)\n", "        doc = json.loads(witness)\n"),
    ("a deeply nested request ends the provider without an answer", "S21",
     "    except (ValueError, RecursionError):\n", "    except ValueError:\n"),
]


def main():
    args = sys.argv[1:]
    if args[:1] == ["--python"]:
        call, where = Serve([args[1], "-m", "sigma_provider", "serve"]), "installed"
    else:
        call, where = Serve([sys.executable, str(ROOT / "impl" / "sigma_provider.py"), "serve"]), "impl/"
    got = cases(call)
    for k in sorted(got):
        print(("OK   " if got[k] else "FAIL ") + k)
    killed = 0
    for what, target, old, new in MUTANTS:
        tmp = Path(tempfile.mkdtemp())
        for n in ("sigma_glyph.py", "sigma_resume.py", "sigma_provider.py"):
            shutil.copy(ROOT / "impl" / n, tmp / n)
        src = (tmp / "sigma_provider.py").read_text()
        assert src.count(old) == 1, f"mutant text moved: {what}"
        (tmp / "sigma_provider.py").write_text(src.replace(old, new))
        try:
            m = cases(Serve([sys.executable, str(tmp / "sigma_provider.py"), "serve"]))
            outcome = "KILLED" if not m[target] else "SURVIVED"
        except Exception as x:          # a crash is not a kill
            outcome = f"CRASH ({type(x).__name__})"
        killed += outcome == "KILLED"
        print(f"{outcome:<9} {target}: {what}")
    passed = all(got.values()) and killed == len(MUTANTS)
    print(f"PROVIDER-RESUME ({where}): {'ALL PASS' if passed else 'FAILURES'} "
          f"({sum(got.values())}/{len(got)} cases, {killed}/{len(MUTANTS)} mutants killed on target)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
