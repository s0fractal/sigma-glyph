#!/usr/bin/env python3
"""Does `tools/spec_audit.py` fail when the Book stops being self-contained?

An audit reporting that a specification is implementable from itself is worth
nothing until breaking that property makes it fail. Six of the nine defects the
last preregistered experiment turned up were in its controls rather than in its
measurement, so the controls get their own controls here.

Each perturbation must produce **its own** complaint, and any further complaint
must be one this file names in advance and requires. Two kinds are named:

- the anchor and suite-pin complaints, which follow from editing the document at
  all, because §8 says a changed document is a new anchor;
- genuine cascades through the Book's own structure — changing `H(K)` must also
  break `FALSE`, which is built from it, and changing a hash in one language must
  also break parity with the other. Those are asserted rather than excused: if
  the cascade stops happening, the Book has stopped being internally linked and
  this file says so.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import spec_audit  # noqa: E402

EXPECTED_COLLATERAL = ("anchor", "vector suite pins")


def run(root: Path) -> tuple[int, str]:
    """Run the audit against a copy of the spec, not the repository's own."""
    spec_audit.UK = root / "spec/book-1-truth.md"
    spec_audit.EN = root / "spec/book-1-truth.en.md"
    spec_audit.ANCHORS = root / "spec/ANCHORS.txt"
    spec_audit.VECTORS = root / "tests/spec_conformance/vectors.json"
    errors = io.StringIO()
    with contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
        code = spec_audit.main()
    return code, errors.getvalue()


def copy_spec(into: Path) -> Path:
    root = into / "repo"
    (root / "spec").mkdir(parents=True)
    (root / "tests/spec_conformance").mkdir(parents=True)
    for relative in ("spec/book-1-truth.md", "spec/book-1-truth.en.md",
                     "spec/ANCHORS.txt", "tests/spec_conformance/vectors.json"):
        shutil.copy(ROOT / relative, root / relative)
    return root


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"perturbation target not present in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def expect(label: str, wanted: str, perturb, cascade: tuple[str, ...] = ()) -> list[str]:
    with tempfile.TemporaryDirectory() as temporary:
        root = copy_spec(Path(temporary))
        perturb(root)
        code, errors = run(root)

    problems = []
    if code == 0:
        problems.append(f"{label}: the audit passed with the perturbation in place")
    if wanted not in errors:
        problems.append(f"{label}: expected a complaint about {wanted!r}; got:\n"
                        f"{errors[:600]}")
    for consequence in cascade:
        if consequence not in errors:
            problems.append(f"{label}: expected this to cascade into {consequence!r} "
                            "as well; it did not, so the Book is no longer linked "
                            "the way this test assumes")
    accounted = (wanted,) + cascade + EXPECTED_COLLATERAL
    unattributed = [line for line in errors.splitlines()
                    if line.startswith("FAIL")
                    and not any(a in line for a in accounted)]
    if unattributed:
        problems.append(f"{label}: also complained about something neither the "
                        f"perturbation nor its declared cascade explains: "
                        f"{unattributed[:1]}")
    if not problems:
        print(f"OK   {label}")
    return problems


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        code, errors = run(copy_spec(Path(temporary)))
    if code != 0:
        print(f"FAIL the unperturbed specification does not pass its own audit, so "
              f"nothing below means anything:\n{errors[:600]}", file=sys.stderr)
        return 1
    print("OK   unperturbed: the Book passes its own audit")

    problems = []

    problems += expect(
        "A  a genesis hash that its stated construction does not produce",
        "the stated construction gives",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c",
                       "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486d"),
        # FALSE is built from H(K), so a wrong K must take FALSE with it.
        cascade=("§5.2 FALSE", "does not carry the same hashes"))

    problems += expect(
        "B  an axiom whose construction is removed from the table",
        "no subject",
        lambda r: edit(r / "spec/book-1-truth.md",
                       '| S | `0001`+SHA-256("S") |',
                       '| S | see the reference implementation |'))

    problems += expect(
        "C  the first theorem's construction deleted",
        "no longer states FALSE",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "`FALSE ≡ APPLY(K,I)`; Bytes `0206‖H(K)‖H(I)`; Hash",
                       "FALSE is defined in the reference implementation. Hash"))

    problems += expect(
        "D  a prose hash that no normative vector carries",
        "appears\nnowhere in the normative vector suite".replace("\n", " "),
        lambda r: edit(r / "spec/book-1-truth.md",
                       "0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198",
                       "0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8199"),
        cascade=("does not carry the same hashes",))

    problems += expect(
        "E  the English rendering carrying a different hash",
        "the same hashes in the same order".replace(
            "the same hashes in the same order", "does not carry the same hashes"),
        lambda r: edit(r / "spec/book-1-truth.en.md",
                       "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6",
                       "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a7"),
        # The audit derives constants from BOTH texts, so a wrong hash in the
        # English table must also fail the English derivation.
        cascade=("§5.1 S",))

    problems += expect(
        "F  the English rendering losing an RFC 2119 keyword",
        "does not carry the same RFC 2119 keywords",
        lambda r: edit(r / "spec/book-1-truth.en.md",
                       "MUST NOT affect this Book", "does not affect this Book"))

    problems += expect(
        "G  a code rule changed in translation",
        "differs between the two texts",
        lambda r: edit(r / "spec/book-1-truth.en.md",
                       "A(x, x)      = ⟨I⟩", "A(x, x)      = ⟨K⟩"))

    problems += expect(
        "H  a vector suite generated against different bytes",
        "vector suite pins",
        lambda r: (r / "tests/spec_conformance/vectors.json").write_text(
            json.dumps(dict(json.loads(
                (r / "tests/spec_conformance/vectors.json").read_text()),
                book1_anchor="0" * 64))))

    problems += expect(
        "I  the Book edited without re-anchoring",
        "which is not\namong the anchors".replace("\n", " "),
        lambda r: edit(r / "spec/book-1-truth.md",
                       "Все тепле живе деінде.", "Все тепле живе деінде. "))

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nSPEC-AUDIT SELFTEST: every check failed for its own reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
