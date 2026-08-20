#!/usr/bin/env python3
"""Negative controls for local command and content-address filesystem edges."""

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


anchor = load("anchor_governance_boundary", "tools/anchor_governance.py")
cosign = load("cosign_boundary", "tools/cosign.py")
hermes = load("hermes_review_boundary", "tools/hermes_review.py")
warrant_gate = load("warrant_gate_boundary", "tools/warrant_gate.py")
failures = []


def check(name, condition):
    print(("OK   " if condition else "FAIL ") + name)
    if not condition:
        failures.append(name)


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    blobs = root / "blobs"
    blobs.mkdir()
    payload = b"inside"
    digest = hashlib.sha256(payload).hexdigest()
    (blobs / digest).write_bytes(payload)
    check("valid content-addressed blob remains readable",
          anchor.read_blob(str(blobs), digest) == payload)

    check("absolute blob path is rejected before I/O",
          anchor.read_blob(str(blobs), "/etc/hosts") is None)
    check("traversal-shaped blob path is rejected before I/O",
          anchor.read_blob(str(blobs), "../outside") is None)

    outside = root / "outside"
    outside.write_bytes(b"outside secret")
    outside_hash = hashlib.sha256(outside.read_bytes()).hexdigest()
    (blobs / outside_hash).symlink_to(outside)
    check("content-address-shaped symlink cannot escape blob root",
          anchor.read_blob(str(blobs), outside_hash) is None)

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

for label, command in (("shell command string", "warrant verify"),
                       ("NUL-bearing argv", ["warrant", "bad\x00arg"])):
    try:
        warrant_gate.validated_command(command)
    except ValueError:
        rejected = True
    else:
        rejected = False
    check(f"warrant gate rejects {label}", rejected)

if failures:
    print(f"\nSECURITY-BOUNDARY: FAILURES PRESENT ({len(failures)})")
    raise SystemExit(1)
print("\nSECURITY-BOUNDARY: ALL PASS")
