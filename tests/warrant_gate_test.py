#!/usr/bin/env python3
"""Countervectors for the fail-closed warrant machine-boundary consumer
(tools/warrant_gate.py). Proves the consumer treats the documented
warrant.verify-report@v0 contract as the ONLY thing it trusts, and fails closed on
everything else.

Two layers:
  * REAL integration — build a store with the warrant library, verify it through
    the actual `warrant verify --store-mode --json` CLI: a clean store passes; a
    malformed record and a missing store are rejected.
  * HOSTILE synthetic — feed check_report() crafted (stdout, stderr, rc) a
    well-behaved verifier would never emit: stderr contamination, truncated JSON,
    multiple objects, an unknown report tag, a self-inconsistent report, a
    counts/findings mismatch, an exit code disagreeing with ok, and finding-schema
    violations. Every one must be rejected; a valid ok:true report must pass.

Set $WARRANT to the verifier command (default: a local warrant checkout). The
real-integration layer skips (not fails) if no verifier with --store-mode/--json
is reachable, so the hostile-contract layer always runs.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
import warrant_gate as G  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else "  <<< " + detail))
    if not cond:
        FAILS.append(name)


def load_warrant():
    """Load the warrant library to BUILD fixtures (not to verify — verification
    goes through the CLI boundary under test)."""
    env = os.environ.get("WARRANT_PY")
    cand = Path(env) if env else Path.home() / "Projects/warrant/impl/warrant.py"
    if not cand.exists():
        return None
    spec = importlib.util.spec_from_file_location("warrant_lib", cand)
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    return W


def make_store(W, malformed=False):
    d = tempfile.mkdtemp()
    st = W.Store(d)
    st.init()
    kp = os.path.join(d, "k")
    open(kp, "w").write((bytes([1]) * 32).hex() + "\n")
    pol = st.put_blob(b"p")
    subj = st.put_blob(b"s")
    body = {"warrant": "0.2", "decision": "accept", "subject": {"hash": subj},
            "under": [pol], "because": [], "evidence": [],
            "actor": {"id": "a@t"}, "prior": [], "ts": 1}
    st.put_record({"body": body, "sigs": [W.sign_envelope(body, "a@t", kp)]})
    if malformed:
        (st.records / ("f" * 64 + ".json")).write_text("{ bad")
    return d


def real_integration():
    W = load_warrant()
    if W is None:
        print("SKIP real integration: no warrant library to build fixtures")
        return
    # Probe once that the configured verifier supports the machine boundary; if not
    # (e.g. an old pin without --store-mode), skip the real layer, keep the contract
    # layer. A clean store that VERIFIES is the probe.
    clean = make_store(W)
    ok, reason = G.verify(clean)
    if not ok and "unknown report tag" not in reason and "one physical JSON line" not in reason \
            and "single valid JSON" not in reason:
        # verifier ran and produced a real verdict
        pass
    if not ok and ("could not run" in reason or "JSON" in reason or "unknown report tag" in reason):
        print(f"SKIP real integration: verifier lacks the boundary ({reason})")
        return
    check("[real] clean store VERIFIES through the CLI boundary", ok, reason)

    bad = make_store(W, malformed=True)
    ok, reason = G.verify(bad)
    check("[real] malformed record is REJECTED (ok:false)", not ok, reason)

    missing = os.path.join(tempfile.mkdtemp(), "no-such-store")
    ok, reason = G.verify(missing)
    check("[real] missing store is REJECTED (--store-mode fail-closed)", not ok, reason)


# --- HOSTILE contract vectors: pure check_report(stdout, stderr, returncode) ---
GOOD = ('{"report":"warrant.verify-report@v0","grade":"base","ok":true,'
        '"records":2,"errors":0,"warnings":1,'
        '"findings":[{"level":"WARN","subject":"' + "a" * 64 + '","message":"x"}]}\n')


def hostile_contract():
    # positive control: a valid ok:true report verifies
    ok, reason = G.check_report(GOOD, "", 0)
    check("[contract] valid ok:true report VERIFIES", ok, reason)

    cases = [
        ("stderr contamination", GOOD, "warning: something\n", 0),
        ("empty stdout", "", "", 1),
        ("truncated JSON", '{"report":"warrant.verify-report@v0","grade":"bas', "", 0),
        ("multiple JSON objects (two lines)", GOOD.strip() + "\n" + GOOD, "", 0),
        ("two objects one line", GOOD.strip() + GOOD.strip() + "\n", "", 0),
        ("not a JSON object", '["warrant.verify-report@v0"]\n', "", 0),
        ("unknown report tag",
         GOOD.replace("warrant.verify-report@v0", "warrant.verify-report@v9"), "", 0),
        ("unknown top-level key",
         GOOD[:-2] + ',"extra":1}\n', "", 0),
        ("ok:true but errors:1 (self-inconsistent)",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":true,"records":1,'
         '"errors":1,"warnings":0,"findings":[]}\n', "", 0),
        ("findings do not match counts",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":true,"records":1,'
         '"errors":0,"warnings":2,"findings":[]}\n', "", 0),
        ("exit code disagrees with ok",
         GOOD, "", 1),
        ("finding has an unknown level",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"records":1,'
         '"errors":1,"warnings":0,"findings":[{"level":"INFO","subject":"x","message":"y"}]}\n',
         "", 1),
        ("finding subject not a string",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"records":1,'
         '"errors":1,"warnings":0,"findings":[{"level":"ERR","subject":7,"message":"y"}]}\n',
         "", 1),
        ("finding has an extra key",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"records":1,'
         '"errors":1,"warnings":0,"findings":[{"level":"ERR","subject":"x","message":"y",'
         '"code":9}]}\n', "", 1),
        ("ok:false is not a pass",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"records":1,'
         '"errors":1,"warnings":0,"findings":[{"level":"ERR","subject":"store","message":"no store"}]}\n',
         "", 1),
        ("records is a bool (JSON true)",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":true,"records":true,'
         '"errors":0,"warnings":0,"findings":[]}\n', "", 0),
        # Codex re-gate additions:
        ("duplicate ok member (last-wins ambiguity)",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"ok":true,'
         '"records":0,"errors":0,"warnings":0,"findings":[]}\n', "", 0),
        ("duplicate member inside a finding",
         '{"report":"warrant.verify-report@v0","grade":"base","ok":false,"records":1,'
         '"errors":1,"warnings":0,"findings":[{"level":"ERR","level":"WARN",'
         '"subject":"x","message":"y"}]}\n', "", 1),
        ("extra blank line after the object", GOOD + "\n", "", 0),
        ("whitespace-only stderr", GOOD, "  \n", 0),
    ]
    for name, out, err, rc in cases:
        ok, reason = G.check_report(out, err, rc)
        check(f"[contract] {name} -> REJECTED", not ok, f"unexpectedly verified: {reason}")

    # grade binding (Codex re-gate P1): a settlement REQUEST answered with a base
    # report is a downgrade and must be rejected; a matching grade verifies.
    ok, reason = G.check_report(GOOD, "", 0, expected_grade="settlement")
    check("[contract] base report for a settlement request -> REJECTED (downgrade)",
          not ok, f"unexpectedly verified: {reason}")
    ok, reason = G.check_report(GOOD, "", 0, expected_grade="base")
    check("[contract] matching grade verifies", ok, reason)


def option_and_process():
    """verify()-level boundary: invalid option combinations rejected before running,
    and non-UTF-8 verifier output is a bounded rejection, not a traceback."""
    ok, r = G.verify("/tmp/whatever", settlement=True, trust_config=None)
    check("[combo] settlement without trust config -> REJECTED", not ok, r)
    ok, r = G.verify("/tmp/whatever", settlement=False, trust_config="/tmp/t.json")
    check("[combo] trust config without --settlement -> REJECTED", not ok, r)
    # a fake verifier that emits invalid UTF-8 on stdout
    fake = [sys.executable, "-c",
            "import sys; sys.stdout.buffer.write(b'\\xff\\xfe not-utf8'); sys.exit(0)"]
    ok, r = G.verify("store", cmd=fake)
    check("[proc] invalid UTF-8 output -> bounded REJECTED", not ok, r)


def main():
    real_integration()
    hostile_contract()
    option_and_process()
    print()
    if FAILS:
        print(f"WARRANT-GATE: {len(FAILS)} FAIL(S): " + ", ".join(FAILS))
        sys.exit(1)
    print("WARRANT-GATE: ALL PASS")


if __name__ == "__main__":
    main()
