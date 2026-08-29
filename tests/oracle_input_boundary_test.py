#!/usr/bin/env python3
"""Negative controls for the public Book I oracle input boundary.

The Lean store looks bytes up by their actual SHA-256 and the Rust loader
verifies every key.  The Python API also accepts plain mappings, so these tests
ensure that convenience cannot bypass content addressing or the normative
``uint32`` ATP domain.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))

import sigma_glyph as sg  # noqa: E402


class ExplodingStore(dict):
    """Any lookup proves validation happened too late."""

    def get(self, key, default=None):
        raise AssertionError("store read before ATP input validation")


def main() -> int:
    problems: list[str] = []

    # A valid node under a different key is not an invalid SigmaNodeV2.  It is
    # a broken CAS, which must be a local fault rather than a canonical result.
    claimed = sg.sha(b"not the hash of the bytes below")
    try:
        sg.eval_hash(claimed, 10, {claimed: sg.I_BYTES})
        problems.append("valid bytes stored under a foreign hash were executed")
    except sg.ResourceFault as fault:
        if "CAS key mismatch" not in str(fault):
            problems.append(f"CAS mismatch raised the wrong local fault: {fault}")

    try:
        sg.eval_hash(claimed, 10, {claimed: "not bytes"})
        problems.append("a non-bytes CAS value reached deserialization")
    except sg.ResourceFault as fault:
        if "non-bytes" not in str(fault):
            problems.append(f"non-bytes CAS value raised the wrong fault: {fault}")

    # Store.put remains the positive path; the new boundary must not reject a
    # genuine content-addressed lookup.
    store = sg.Store()
    key = store.put(sg.FALSE_BYTES)
    term, spent = sg.eval_hash(key, 3, store)
    if sg.term_hash(term) != sg.FALSE_H or spent != 3:
        problems.append("a valid Store.put lookup changed under the CAS guard")

    # bool is deliberately included: isinstance(True, int) is true in Python.
    for bad in (-1, 2**32, 1.5, True, "10"):
        try:
            sg.eval_hash(sg.I_H, bad, ExplodingStore())
            problems.append(f"non-uint32 ATP {bad!r} was admitted")
        except ValueError:
            pass
        except AssertionError as touched:
            problems.append(f"ATP {bad!r} reached the store: {touched}")
        except Exception as exc:  # a late TypeError is not fail-before-access
            problems.append(f"ATP {bad!r} failed as {type(exc).__name__}, not ValueError")

    for edge in (0, 2**32 - 1):
        try:
            term, spent = sg.eval_hash(sg.I_H, edge, {})
        except Exception as exc:
            problems.append(f"uint32 boundary {edge} was refused: {exc}")
            continue
        if sg.term_hash(term) != sg.I_H or spent != 0:
            problems.append(f"uint32 boundary {edge} changed intrinsic evaluation")

    for bad_hash in (b"", b"x" * 31, b"x" * 33, "x" * 64, bytearray(32)):
        try:
            sg.eval_hash(bad_hash, 0, ExplodingStore())
            problems.append(f"invalid term hash {bad_hash!r} was admitted")
        except ValueError:
            pass
        except AssertionError as touched:
            problems.append(f"invalid term hash reached the store: {touched}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("ORACLE-INPUT-BOUNDARY: ALL PASS (foreign CAS bytes refused; uint32 "
          "validated before store access)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
