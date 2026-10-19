#!/usr/bin/env python3
"""Negative controls for local command and content-address filesystem edges."""

import importlib.util
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cosign = load("cosign_boundary", "tools/cosign.py")
hermes = load("hermes_review_boundary", "tools/hermes_review.py")
failures = []


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    if not condition:
        failures.append(name)


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    marker = root / "shell-expanded"
    shell_text = f"; touch {marker}"
    transcript, verdict = hermes.run_check([
        sys.executable, "-c", "import sys; print(sys.argv[1])", shell_text])
    check("Hermes check succeeds through structured argv", verdict == "pass")
    check("Hermes check preserves shell metacharacters as data",
          shell_text in transcript and not marker.exists())

try:
    cosign.record_path("../../outside")
except ValueError:
    invalid_wid_rejected = True
else:
    invalid_wid_rejected = False
check("co-signing rejects a path-shaped warrant id", invalid_wid_rejected)

if failures:
    print(f"\nSECURITY-BOUNDARY: FAILURES PRESENT ({len(failures)})")
    raise SystemExit(1)
print("\nSECURITY-BOUNDARY: ALL PASS")
