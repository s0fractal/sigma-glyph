#!/usr/bin/env python3
"""The three Book self-tests must put their verdict in the EXIT STATUS.

WHY THIS EXISTS
---------------
`impl/sigma_glyph.py` ended in

    if __name__ == "__main__":
        run_tests()

for the whole life of the project. `run_tests()` returns a boolean and prints
`ALL PASS` or `FAILURES PRESENT`, and the return value was thrown away: the
process exited 0 either way. Observed on master (fbefd4a), with one check forced
false:

    $ python3 impl/sigma_glyph.py ; echo $?
    ...
    FAILURES PRESENT
    0

`sigma_wave` and `sigma_federation` always did `sys.exit(0 if selftest() else 1)`.
So Book I was the odd one out, and nothing noticed, because every gate that
consumes these suites greps stdout for the tag. Greping is a legitimate extra
check; it is not a substitute. `python -m sigma_glyph && ./publish` — the shape
CI uses by default — reported success on a failing oracle.

WHAT THIS PINS
--------------
Not the oracle's correctness (that is the suite's own job) but the WIRING: the
boolean the suite computes reaches `$?`. It is checked by substituting the
entry function in a copy of each module — a stub that returns False must produce
a non-zero exit, and a stub that returns True must produce 0 — so the test is
about the `__main__` block and nothing else, and it cannot be satisfied by a
suite that happens to pass today.

The substitution is structural: the source is split at its `if __name__ ==
"__main__":` line and an override of the entry function is inserted just above
it. If that line ever stops existing, this guard fails rather than silently
testing nothing.

    python3 tests/exit_status_guard.py     # -> EXIT-STATUS-GUARD: ALL PASS

WHERE IT STOPS
--------------
It says nothing about WHICH checks a suite runs, only that the verdict it
reaches is the verdict the operating system is told. Verb-level behaviour of an
installed copy is tools/check_release_surface.py's job.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = 'if __name__ == "__main__":'

# (module file, the function whose boolean must become the exit status)
ENTRIES = (
    ("sigma_glyph.py", "run_tests"),
    ("sigma_wave.py", "selftest"),
    ("sigma_federation.py", "selftest"),
)

ok = []


def chk(name, cond, detail=""):
    ok.append(cond)
    print(("OK  " if cond else "FAIL"), name, "" if cond else detail)


def stubbed(source, entry, verdict):
    """`source` with `entry` redefined to return `verdict`, just above the
    __main__ guard so the redefinition is the one the guard calls."""
    head, sep, tail = source.rpartition("\n" + GUARD)
    if not sep:
        return None
    stub = (f"\n\ndef {entry}():\n"
            f"    print('exit-status guard stub: verdict {verdict}')\n"
            f"    return {verdict}\n")
    return head + stub + sep + tail


def run_stubbed(tmp, name, entry, verdict):
    src = (ROOT / "impl" / name).read_text()
    mutated = stubbed(src, entry, verdict)
    if mutated is None:
        return None, None
    d = Path(tmp) / f"{name}-{verdict}"
    d.mkdir()
    for other, _ in ENTRIES:                 # siblings: sigma_federation imports
        (d / other).write_text((ROOT / "impl" / other).read_text())
    (d / name).write_text(mutated)
    p = subprocess.run([sys.executable, str(d / name)], capture_output=True,
                       text=True, cwd=str(d), timeout=300)
    return p.returncode, p.stdout + p.stderr


with tempfile.TemporaryDirectory(prefix="sigma-exit-status-") as tmp:
    for name, entry in ENTRIES:
        src = (ROOT / "impl" / name).read_text()
        chk(f"{name}: has the `{GUARD}` entry point this guard substitutes into",
            ("\n" + GUARD) in src)

        rc, out = run_stubbed(tmp, name, entry, False)
        chk(f"{name}: a failing {entry}() exits NON-ZERO "
            f"(was exit 0 for sigma_glyph.py through v0.6.6)",
            rc is not None and rc != 0, f"exit {rc}; output {out!r}")
        chk(f"{name}: the stub really replaced {entry}()",
            out is not None and "exit-status guard stub: verdict False" in out,
            f"output {out!r}")

        rc, out = run_stubbed(tmp, name, entry, True)
        chk(f"{name}: a passing {entry}() exits 0 "
            f"(the guard must not pass by exiting non-zero always)",
            rc == 0, f"exit {rc}; output {out!r}")

    # The unmodified modules, as a stranger runs them: pass and say so.
    for name, _ in ENTRIES:
        p = subprocess.run([sys.executable, str(ROOT / "impl" / name)],
                           capture_output=True, text=True, cwd=str(ROOT),
                           timeout=300)
        chk(f"{name}: the real suite passes AND exits 0 in this checkout",
            p.returncode == 0 and "FAILURES PRESENT" not in p.stdout,
            f"exit {p.returncode}")

print(f"\n{'EXIT-STATUS-GUARD: ALL PASS' if all(ok) else 'EXIT-STATUS-GUARD: FAILURES PRESENT'}"
      f" ({sum(ok)}/{len(ok)})")
sys.exit(0 if all(ok) else 1)
