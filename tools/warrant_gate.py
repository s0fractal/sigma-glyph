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
  * any bytes on stderr (contamination — including whitespace);
  * stdout that is not exactly one physical line / one JSON value (truncated,
    multiple objects, or an extra blank line);
  * output that is not valid UTF-8 (bounded rejection, not a decode traceback);
  * duplicate JSON members at any level (``"ok":false,"ok":true`` is ambiguous);
  * a JSON value that is not an object, or whose ``report`` tag is not the exact
    version this consumer understands;
  * a top-level or finding field set that is not the documented schema;
  * a grade that does not match the one requested (a settlement request answered
    with a base report is a silent downgrade);
  * a self-inconsistent report (``ok != (errors == 0)``, or the finding levels do
    not match the error/warning counts);
  * an exit code that disagrees with ``ok``;
  * ``ok:false`` (verification failed, including a missing/uninitialised store
    under --store-mode).

Invalid option combinations are rejected at the boundary before running the
verifier: settlement without a trust config, or a trust config without settlement.

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


def validated_command(cmd):
    """Return a closed argv sequence; command text is never interpreted by a shell."""
    if not isinstance(cmd, (list, tuple)) or not cmd:
        raise ValueError("verifier command must be a non-empty argv sequence")
    if not all(isinstance(arg, str) and arg and "\x00" not in arg for arg in cmd):
        raise ValueError("verifier argv entries must be non-empty NUL-free strings")
    return list(cmd)


def _reject_dups(pairs):
    """object_pairs_hook that rejects duplicate members at EVERY nesting level.
    Stock json.loads collapses `"ok":false,"ok":true` last-wins, so an ambiguous
    report would pass the exact-field-set check — reject it as malformed instead
    (Codex gate P1)."""
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON member {k!r}")
        seen.add(k)
    return dict(pairs)


def _parse_report(stdout, stderr):
    """Return ``(report, error)`` after the byte/JSON framing checks."""
    if stderr != "":
        return None, "stderr is not empty (verifier emitted extra output)"
    line = stdout[:-1] if stdout.endswith("\n") else stdout
    if line == "" or "\n" in line:
        return None, "stdout is not exactly one physical JSON line"
    try:
        rep = json.loads(stdout, object_pairs_hook=_reject_dups)
    except ValueError as e:
        return None, f"stdout is not a single unambiguous JSON value ({e})"
    if not isinstance(rep, dict):
        return None, "report is not a JSON object"
    return rep, None


def _validate_report_fields(rep, expected_grade):
    """Return the first closed-schema/scalar error, or ``None``."""
    if rep.get("report") != REPORT_TAG:
        return f"unknown report tag {rep.get('report')!r} (want {REPORT_TAG})"
    if set(rep) != TOP_KEYS:
        return "report top-level field set is not the documented v0 schema"
    if rep["grade"] not in ("base", "settlement"):
        return f"unknown grade {rep['grade']!r}"
    if expected_grade is not None and rep["grade"] != expected_grade:
        return f"grade {rep['grade']!r} != requested {expected_grade!r} (downgrade?)"
    if type(rep["ok"]) is not bool:
        return "ok is not a bool"
    for k in ("records", "errors", "warnings"):
        if type(rep[k]) is not int or isinstance(rep[k], bool) or rep[k] < 0:
            return f"{k} is not a non-negative int"
    if not isinstance(rep["findings"], list):
        return "findings is not a list"
    return None


def _finding_counts(findings):
    """Return ``((errors, warnings), error)`` for a closed findings list."""
    err_c = warn_c = 0
    for f in findings:
        if not isinstance(f, dict) or set(f) != FINDING_KEYS:
            return None, "a finding is not the documented {level, subject, message}"
        if f["level"] not in ("ERR", "WARN"):
            return None, f"finding level {f['level']!r} is not ERR/WARN"
        if type(f["subject"]) is not str or type(f["message"]) is not str:
            return None, "finding subject/message is not a string"
        err_c += f["level"] == "ERR"
        warn_c += f["level"] == "WARN"
    return (err_c, warn_c), None


def _consistency_error(rep, counts, returncode):
    """Return a cross-field/exit-status contradiction, or ``None``."""
    err_c, warn_c = counts
    if rep["ok"] != (rep["errors"] == 0):
        return "self-inconsistent report: ok != (errors == 0)"
    if err_c != rep["errors"] or warn_c != rep["warnings"]:
        return "finding levels do not match the error/warning counts"
    if returncode != (0 if rep["ok"] else 1):
        return f"exit code {returncode} disagrees with ok={rep['ok']}"
    return None


def check_report(stdout, stderr, returncode, expected_grade=None):
    """Pure fail-closed validation of the machine boundary. No subprocess, no I/O —
    so the exact contract can be tested against hostile synthetic output.
    `expected_grade` (base|settlement), when given, MUST equal the report grade —
    a producer that ignores --settlement and returns a base report is a downgrade.
    Returns (verified: bool, reason: str)."""
    rep, error = _parse_report(stdout, stderr)
    if error is not None:
        return False, error
    error = _validate_report_fields(rep, expected_grade)
    if error is not None:
        return False, error
    counts, error = _finding_counts(rep["findings"])
    if error is not None:
        return False, error
    error = _consistency_error(rep, counts, returncode)
    if error is not None:
        return False, error
    if not rep["ok"]:
        return False, f"verification failed: {rep['errors']} error(s)"
    return True, f"verified: {rep['records']} record(s), {rep['warnings']} warning(s)"


def verify(store, settlement=False, trust_config=None, cmd=None, env=None):
    # Reject ambiguous/unsafe option combinations at the boundary BEFORE running, so
    # a requested control can never be silently dropped (Codex gate P1):
    #  * settlement without a trust source is not a real settlement verification;
    #  * a trust config without --settlement would be silently ignored by argv.
    if settlement and not trust_config:
        return False, "settlement requested without a trust config (not a real settlement verification)"
    if trust_config and not settlement:
        return False, "trust config given without --settlement (the option would be silently ignored)"
    try:
        command = validated_command(cmd or default_warrant_cmd())
    except ValueError as error:
        return False, str(error)
    argv = build_argv(command, store, settlement, trust_config)
    try:
        # capture BYTES: invalid UTF-8 must be a bounded rejection, not a decode
        # traceback (Codex gate P2). `argv` is a validated sequence and the
        # verifier is explicitly operator-selected; no shell parses any value.
        proc = subprocess.run(argv, capture_output=True, env=env, shell=False)  # NOSONAR pythonsecurity:S8701,pythonsecurity:S8705
    except OSError as e:
        return False, f"could not run verifier {argv[0]!r}: {e}"
    try:
        stdout = proc.stdout.decode("utf-8")
        stderr = proc.stderr.decode("utf-8")
    except UnicodeDecodeError:
        return False, "verifier output is not valid UTF-8"
    expected = "settlement" if settlement else "base"
    return check_report(stdout, stderr, proc.returncode, expected_grade=expected)


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
