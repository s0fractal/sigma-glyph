#!/usr/bin/env python3
"""Sigma-glyph's SINGLE machine verification boundary: a fail-closed CONSUMER of
Warrant's ``verify --store-mode --json`` (warrant.verify-report@v0).

Dogfood, not a re-implementation. sigma-glyph does NOT re-derive Warrant
verification here (that would be a divergent third verifier — see the separate,
deliberately independent offline auditor tool ``warrant_verify.py``). This tool
INVOKES the real verifier and consumes ONLY the documented normative fields of the
report — ``report, grade, ok, records, errors, warnings`` and each finding's
``level``/``subject``. It never branches on a finding's ``message`` (documented as
non-portable human prose).

Everything else is FAIL-CLOSED — "not verified" — so a broken or hostile producer
can never be read as a pass:
  * anything on stderr (human-text contamination);
  * stdout that is not exactly one physical line / one JSON value (truncated or
    multiple objects);
  * a JSON value that is not an object, or whose ``report`` tag is not the exact
    version this consumer understands;
  * a top-level or finding field set that is not the documented schema;
  * a self-inconsistent report (``ok != (errors == 0)``, or the finding levels do
    not match the error/warning counts);
  * an exit code that disagrees with ``ok``;
  * ``ok:false`` (verification failed, including a missing/uninitialised store
    under --store-mode).

Usage:
    warrant_gate.py [store] [--settlement --trust-config FILE]
Exit 0 iff verified. The verifier command is taken from $WARRANT (e.g.
``python3 /tmp/warrant.py`` or ``/path/to/warrant-go``); the store-argument style
is auto-detected (Go takes a positional store, Python a global --store) and can be
forced with $WARRANT_POSITIONAL=1/0.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPORT_TAG = "warrant.verify-report@v0"
TOP_KEYS = {"report", "grade", "ok", "records", "errors", "warnings", "findings"}
FINDING_KEYS = {"level", "subject", "message"}


def default_warrant_cmd():
    """Resolve the verifier command: $WARRANT, else a local warrant checkout
    (prefer the Go binary, else the Python CLI)."""
    env = os.environ.get("WARRANT")
    if env:
        return shlex.split(env)
    go = Path.home() / "Projects/warrant/impl-go/warrant-go"
    if go.exists():
        return [str(go)]
    return [sys.executable, str(Path.home() / "Projects/warrant/impl/warrant.py")]


def _positional_store(cmd):
    forced = os.environ.get("WARRANT_POSITIONAL")
    if forced in ("1", "true"):
        return True
    if forced in ("0", "false"):
        return False
    return any(("warrant-go" in c) or c.endswith("-go") for c in cmd)


def build_argv(cmd, store, settlement=False, trust_config=None):
    verb = ["verify", "--store-mode", "--json"]
    if settlement:
        verb.append("--settlement")
        if trust_config:
            verb += ["--trust-config", trust_config]
    if _positional_store(cmd):
        return cmd + verb + [store]                 # Go: store is positional
    return cmd + ["--store", store] + verb          # Python: --store is global


def check_report(stdout, stderr, returncode):
    """Pure fail-closed validation of the machine boundary. No subprocess, no I/O —
    so the exact contract can be tested against hostile synthetic output.
    Returns (verified: bool, reason: str)."""
    if stderr.strip() != "":
        return False, "stderr contamination (verifier emitted human text)"
    body = stdout.rstrip("\n")
    if body == "" or "\n" in body:
        return False, "stdout is not exactly one physical JSON line"
    try:
        rep = json.loads(stdout)
    except ValueError:
        return False, "stdout is not a single valid JSON value (truncated/garbage)"
    if not isinstance(rep, dict):
        return False, "report is not a JSON object"
    if rep.get("report") != REPORT_TAG:
        return False, f"unknown report tag {rep.get('report')!r} (want {REPORT_TAG})"
    if set(rep) != TOP_KEYS:
        return False, "report top-level field set is not the documented v0 schema"
    if rep["grade"] not in ("base", "settlement"):
        return False, f"unknown grade {rep['grade']!r}"
    if type(rep["ok"]) is not bool:
        return False, "ok is not a bool"
    for k in ("records", "errors", "warnings"):
        if type(rep[k]) is not int or isinstance(rep[k], bool) or rep[k] < 0:
            return False, f"{k} is not a non-negative int"
    if not isinstance(rep["findings"], list):
        return False, "findings is not a list"
    err_c = warn_c = 0
    for f in rep["findings"]:
        if not isinstance(f, dict) or set(f) != FINDING_KEYS:
            return False, "a finding is not the documented {level, subject, message}"
        if f["level"] not in ("ERR", "WARN"):
            return False, f"finding level {f['level']!r} is not ERR/WARN"
        if type(f["subject"]) is not str or type(f["message"]) is not str:
            return False, "finding subject/message is not a string"
        err_c += f["level"] == "ERR"
        warn_c += f["level"] == "WARN"
    # The report must not contradict itself, and the exit code must agree.
    if rep["ok"] != (rep["errors"] == 0):
        return False, "self-inconsistent report: ok != (errors == 0)"
    if err_c != rep["errors"] or warn_c != rep["warnings"]:
        return False, "finding levels do not match the error/warning counts"
    if returncode != (0 if rep["ok"] else 1):
        return False, f"exit code {returncode} disagrees with ok={rep['ok']}"
    if not rep["ok"]:
        return False, f"verification failed: {rep['errors']} error(s)"
    return True, f"verified: {rep['records']} record(s), {rep['warnings']} warning(s)"


def verify(store, settlement=False, trust_config=None, cmd=None, env=None):
    cmd = cmd or default_warrant_cmd()
    argv = build_argv(cmd, store, settlement, trust_config)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
    except OSError as e:
        return False, f"could not run verifier {argv[0]!r}: {e}"
    return check_report(proc.stdout, proc.stderr, proc.returncode)


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Fail-closed consumer of warrant verify --store-mode --json")
    ap.add_argument("store", nargs="?", default=".warrants")
    ap.add_argument("--settlement", action="store_true")
    ap.add_argument("--trust-config")
    a = ap.parse_args()
    verified, reason = verify(a.store, a.settlement, a.trust_config)
    print(("VERIFIED  " if verified else "REJECTED  ") + reason)
    sys.exit(0 if verified else 1)


if __name__ == "__main__":
    main()
