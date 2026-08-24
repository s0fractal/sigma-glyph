#!/usr/bin/env python3
"""Does `tools/spec_audit.py` fail when the Book stops being self-contained?

An audit reporting that a specification is implementable from itself is worth
nothing until breaking that property makes it fail. Six of the nine defects the
last preregistered experiment turned up were in its controls rather than in its
measurement, so the controls get their own controls here.

Four of the thirteen below (J, K, L, M) exist because external review reproduced
the gap first: the audit's first version derived nine of fifteen constants while
its documents said "every constant", matched digests against the whole suite
rather than the test that named them, and compared no numbers at all. The pattern
is the one this project keeps finding — a green check with a narrower subject than
the sentence describing it — and the fix is a perturbation per gap.

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

# Editing one rendering is, mechanically, the two texts stating different things.
# That is a consequence of the edit rather than a separate finding, so it is
# expected everywhere — except where a control is aimed at it.
EXPECTED_COLLATERAL = ("anchor", "vector suite pins",
                       "does not state the same predicates in both texts")


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
        # FALSE is built from H(K); TV-4's stated normal form *is* ⟨K⟩. A wrong
        # K must take both with it, or the Book is not linked as this assumes.
        cascade=("§5.2 FALSE", "does not carry the same hashes",
                 "result ⟨K⟩",
                 "result APPLY(⟨K⟩,⟨K⟩)"))

    problems += expect(
        "B  an axiom whose construction is removed from the table",
        "no subject",
        # The digest it used to derive becomes unaccounted, and every claim whose
        # result is built from that glyph stops being decidable.
        lambda r: edit(r / "spec/book-1-truth.md",
                       '| S | `0001`+SHA-256("S") |',
                       '| S | see the reference implementation |'),
        cascade=("neither re-derived from a stated construction nor bound",
                 "result ⟨S⟩"))

    problems += expect(
        "C  the first theorem's construction deleted",
        "no longer states FALSE",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "`FALSE ≡ APPLY(K,I)`; Bytes `0206‖H(K)‖H(I)`; Hash",
                       "FALSE is defined in the reference implementation. Hash"),
        cascade=("neither re-derived from a stated construction nor bound",))

    problems += expect(
        "D  a prose hash that no record of its own test carries",
        "is in no record filed under TV-6",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198",
                       "0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8199"),
        # An unbound digest is also an unaccounted one: the inventory and the
        # binding check are two views of one requirement.
        cascade=("does not carry the same hashes",
                 "neither re-derived from a stated construction nor bound"))

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

    # --- the three gaps external review reproduced against the first version,
    # and the one that keeps its recorded exception from becoming permanent.

    tv4 = "51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e"
    tv5 = "c9f57b3f594d7b72b0855b0d6fabba89e6ccdf6840c8f84aeb5fd4707300bbfc"

    def swap_subjects(root: Path) -> None:
        """Both hashes stay in the suite; each is quoted under the other's test.
        The first version asked only whether a digest appeared in the file, so
        this passed."""
        for name in ("spec/book-1-truth.md", "spec/book-1-truth.en.md"):
            path = root / name
            path.write_text(path.read_text()
                            .replace(tv4, "@@").replace(tv5, tv4).replace("@@", tv5))

    problems += expect(
        "J  two tests' hashes swapped, both still present in the suite",
        "files as the subject of TV-", swap_subjects,
        # The paragraph's own term changes, so every statement whose subject is
        # written `·` stops resolving to the record it belongs to.
        # Every statement written `eval(·, …)` loses the term it referred to, so
        # the cascade is "the subject no longer matches", not one line of it.
        cascade=("neither re-derived from a stated construction nor bound",
                 "has subject"))

    def restate_price(root: Path) -> None:
        edit(root / "spec/book-1-truth.md", "**4 ATP** (force кореня 3 + R-I 1)",
             "**5 ATP** (force кореня 3 + R-I 1)")
        edit(root / "spec/book-1-truth.en.md", "**4 ATP**", "**5 ATP**")

    problems += expect(
        "K  a price restated in prose while the record keeps the old one",
        "result ⟨K⟩, spend 5", restate_price)

    problems += expect(
        "L  a constant printed that nothing derives, proves or binds",
        "neither re-derived from a stated construction nor bound",
        lambda r: edit(r / "spec/book-1-truth.md", "**Негативні:**",
                       "**TV-13 (fabricated):** Hash "
                       "`d34db33fd34db33fd34db33fd34db33fd34db33fd34db33fd34db33fd34db33f`.\n\n"
                       "**Негативні:**"),
        # A constant present in one language and not the other is a parity
        # failure; a fabricated paragraph is also a paragraph with no records.
        cascade=("does not carry the same hashes",
                 "TV-13 states 0 claim(s) and 1 constant(s)"))

    def file_the_waived_claim(root: Path) -> None:
        path = root / "tests/spec_conformance/vectors.json"
        path.write_text(path.read_text().replace(
            "bare intrinsic thunk: eval(H(I))",
            "TV-12: bare intrinsic thunk: eval(H(I))"))

    # Editing a note does not move `book1_anchor`, which pins the Book rather
    # than the suite, so this one has no cascade here. The suite's own bytes are
    # anchored too, and `tools/verify_anchors.py` is what catches that.
    problems += expect(
        "M  a recorded exception that is no longer needed",
        "is no\nlonger needed".replace("\n", " "), file_the_waived_claim)

    # --- the four paths a second independent audit reproduced against 9494a03.
    # Every one of them was a green run over a claim nothing decided.

    def untag(root: Path) -> None:
        """One test's filing disappears while the aggregate count stays fine."""
        path = root / "tests/spec_conformance/vectors.json"
        path.write_text(path.read_text().replace("TV-8:", "case:"))

    problems += expect(
        "N  every record's tag for one test removed",
        "TV-8 states 1 claim(s) and 0 constant(s)", untag)

    problems += expect(
        "O  a budget stated that no record uses and no rule implies",
        "no record uses budget 7",
        lambda r: [edit(r / f, "eval(·,4)", "eval(·,7)")
                   for f in ("spec/book-1-truth.md", "spec/book-1-truth.en.md")])

    problems += expect(
        "P  an outcome swapped for one the records do not produce",
        "outcome atp_exhausted",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "DISSONANCE(Unresolved Reference)`, spent 4",
                       "DISSONANCE(ATP Exhausted)`, spent 4"))

    problems += expect(
        "Q  a compound normal form changed",
        "result APPLY(⟨I⟩,⟨I⟩)",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "нормальна форма `APPLY(⟨K⟩,⟨K⟩)`",
                       "нормальна форма `APPLY(⟨I⟩,⟨I⟩)`"))

    def delete_witness(root: Path) -> None:
        path = root / "tests/spec_conformance/vectors.json"
        suite = json.loads(path.read_text())
        suite["vectors"] = [v for v in suite["vectors"] if v["id"] != "EV-GENESIS-BARE"]
        path.write_text(json.dumps(suite))

    problems += expect(
        "R  the recorded exception's witness deleted",
        "the exception is resting on nothing", delete_witness)

    def move_witness(root: Path) -> None:
        path = root / "tests/spec_conformance/vectors.json"
        suite = json.loads(path.read_text())
        for vector in suite["vectors"]:
            if vector["id"] == "EV-GENESIS-BARE":
                vector["expected"]["atp_spent"] = 9
        path.write_text(json.dumps(suite))

    problems += expect(
        "S  the recorded exception's evidence altered",
        "was to show atp_spent=0 and shows", move_witness)

    def fabricate(root: Path) -> None:
        """A paragraph with no records, quoting a digest the store happens to
        hold. Store proof alone must not stand in for belonging to a test."""
        key = list(json.loads(
            (root / "tests/spec_conformance/vectors.json").read_text())["objects"])[7]
        edit(root / "spec/book-1-truth.md", "**Негативні:**",
             f"**TV-13 (fabricated):** Hash `{key}`.\n\n**Негативні:**")
        edit(root / "spec/book-1-truth.en.md", "**Negative",
             f"**TV-13 (fabricated):** Hash `{key}`.\n\n**Negative")

    problems += expect(
        "T  a fabricated test quoting an unrelated stored digest",
        "TV-13 states 0 claim(s) and 1 constant(s)",
        fabricate, cascade=("neither re-derived from a stated construction nor bound",))

    # --- the six a third independent audit reproduced against e000628. Each is a
    # field that was correct *somewhere* in its paragraph and attached to the
    # wrong thing: what the audit compared were sets of properties, not claims.

    problems += expect(
        "U  two budgets' spends exchanged inside one test",
        "outcome atp_exhausted, spend 3",
        lambda r: edit(
            r / "spec/book-1-truth.md",
            "`eval(·,0)` = ATP Exhausted, spent 0 — без жодного звернення до "
            "сховища; `eval(·,2)` = ATP Exhausted, spent 0 — байти кореня "
            "відкинуті (force коштує 3 > 2); `eval(·,3)` = ATP Exhausted, spent 3",
            "`eval(·,0)` = ATP Exhausted, spent 3 — без жодного звернення до "
            "сховища; `eval(·,2)` = ATP Exhausted, spent 0 — байти кореня "
            "відкинуті (force коштує 3 > 2); `eval(·,3)` = ATP Exhausted, spent 0"),
        # A swap breaks both statements, not one: each now describes the other's
        # budget. Requiring both is what distinguishes a swap from a typo.
        cascade=("outcome atp_exhausted, spend 0",))

    problems += expect(
        "V  two evaluations' results exchanged inside one test",
        "result ⟨K⟩, spend 7",
        lambda r: edit(r / "spec/book-1-truth.md",
                       "→ ⟨I⟩, 7 ATP; `APPLY(S (K I) (K K), ghost)` → ⟨K⟩, 20 ATP",
                       "→ ⟨K⟩, 7 ATP; `APPLY(S (K I) (K K), ghost)` → ⟨I⟩, 20 ATP"),
        cascade=("result ⟨I⟩, spend 20",))

    problems += expect(
        "W  the excepted statement's subject changed",
        "matches no statement in §7 in either language",
        lambda r: edit(r / "spec/book-1-truth.md", "`eval(H(I), n)` = ⟨I⟩, 0 ATP",
                       "`eval(H(K), n)` = ⟨I⟩, 0 ATP"),
        cascade=("the budget is a variable",))

    problems += expect(
        "X  the excepted statement's result changed",
        "matches no statement in §7 in either language",
        lambda r: edit(r / "spec/book-1-truth.md", "`eval(H(I), n)` = ⟨I⟩, 0 ATP",
                       "`eval(H(I), n)` = ⟨K⟩, 0 ATP"),
        cascade=("the budget is a variable",))

    problems += expect(
        "Y  a declared compiler statement changed",
        "result ⟨K⟩",
        lambda r: edit(r / "spec/book-1-truth.md", "`C1[λx.x] = ⟨I⟩`",
                       "`C1[λx.x] = ⟨K⟩`"))

    problems += expect(
        "Z  a declared statement deleted from one language only",
        "does not state the same predicates in both texts",
        lambda r: edit(r / "spec/book-1-truth.md", "`C1[λx.x] = ⟨I⟩`. ", ""))

    # --- the contract as it now stands, in both directions.

    problems += expect(
        "AA a resolvable subject changed to another term",
        "has subject",
        lambda r: [edit(r / f, was, now) for f, was, now in (
            ("spec/book-1-truth.md", "`REF(H(K))` на **порожньому** сховищі",
             "`REF(H(I))` на **порожньому** сховищі"),
            ("spec/book-1-truth.en.md", "`REF(H(K))` on an **empty** store",
             "`REF(H(I))` on an **empty** store"))])

    problems += expect(
        "AB a subject changed in one rendering only",
        "does not state the same predicates in both texts",
        lambda r: edit(r / "spec/book-1-truth.en.md", "APPLY(⟨I⟩, ghost)",
                       "APPLY(⟨K⟩, ghost)"))

    # And the other direction: a clause outside the five predicates must appear in
    # the report rather than be absorbed by a passing run. This control asserts
    # what the audit *says*, not that it fails — inverting such a clause is
    # something this file cannot detect, and saying so is the honest contract.
    with tempfile.TemporaryDirectory() as temporary:
        root = copy_spec(Path(temporary))
        edit(root / "spec/book-1-truth.md", "без жодного звернення до сховища",
             "після звернення до сховища")
        spoken = io.StringIO()
        spec_audit.UK = root / "spec/book-1-truth.md"
        spec_audit.EN = root / "spec/book-1-truth.en.md"
        spec_audit.ANCHORS = root / "spec/ANCHORS.txt"
        spec_audit.VECTORS = root / "tests/spec_conformance/vectors.json"
        with contextlib.redirect_stdout(spoken), contextlib.redirect_stderr(io.StringIO()):
            spec_audit.main()
        said = spoken.getvalue()
        # Only the ledger line: the closing summary is not printed when the run
        # fails, and editing the Book always fails it on the anchor.
        if "uncovered  TV-4: storage access" not in said:
            problems.append("AC a clause outside the five predicates is not named "
                            "in the report, so a passing run would look like a "
                            "statement about it")
        else:
            print("OK   AC an inverted clause outside the predicates is reported, "
                  "not absorbed")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nSPEC-AUDIT SELFTEST: every check failed for its own reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
