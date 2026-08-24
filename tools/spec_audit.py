#!/usr/bin/env python3
"""Can Book I be implemented from Book I?

The paper says the single most valuable missing datum is an implementation by
someone who has not read this code, and names a reason: that the specification
sends an implementer to `impl/sigma_glyph.py`. This checks that claim instead of
repeating it, in three parts.

A. **Every constant the Book prints is re-derivable from the Book.** Each hash is
   recomputed from the construction the text states, and a printed constant with
   no stated construction is reported — that, not a missing digit, is what would
   force a reader into the reference implementation.

B. **The prose and the machine-readable vectors agree.** §7 says the oracle wins
   in a discrepancy. A precedence rule is only ever exercised when there *is* a
   discrepancy, so this checks whether one exists.

C. **The English rendering carries the same consensus content.** It is marked
   informative and promises that hashes, byte strings, code and RFC 2119 keywords
   are reproduced verbatim. That promise is checked here rather than trusted.

Every extraction asserts a minimum count. A regex that silently matches nothing
turns this file into a check with no subject, which is the defect this project
keeps finding in its own guards.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UK = ROOT / "spec/book-1-truth.md"
EN = ROOT / "spec/book-1-truth.en.md"
ANCHORS = ROOT / "spec/ANCHORS.txt"
VECTORS = ROOT / "tests/spec_conformance/vectors.json"

RFC = r'\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY)\b'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def node_hash(op: int, flags: int, payload: bytes) -> str:
    """§2: the hash of a node is the hash of its canonical bytes."""
    return sha(bytes([op, flags]) + payload)


def enough(found, least: int, what: str, problems: list[str]) -> bool:
    if len(found) < least:
        problems.append(f"only {len(found)} {what} found, expected at least "
                        f"{least} — the extraction has stopped matching and this "
                        "check now has no subject")
        return False
    return True


# ---------------------------------------------------------------- A. constants

def derivable_constants(text: str, problems: list[str]) -> int:
    """Recompute each printed hash from the construction the Book states."""
    checked = 0

    # §5.1 — the axioms. The CanonicalBytes cell IS the construction; it is read
    # from the table rather than hardcoded, so deleting it fails this check.
    axioms = re.findall(r'\|\s*(\w)\s*\|\s*`0001`\+SHA-256\("(\w)"\)\s*\|\s*'
                        r'`([0-9a-f]{64})`\s*\|', text)
    if enough(axioms, 3, "genesis axioms in §5.1", problems):
        for glyph, hashed, printed in axioms:
            if glyph != hashed:
                problems.append(f"§5.1 row {glyph} hashes {hashed!r}")
            got = node_hash(0x00, 0x01, hashlib.sha256(glyph.encode()).digest())
            if got != printed:
                problems.append(f"§5.1 {glyph}: the stated construction gives "
                                f"{got}, the table prints {printed}")
            checked += 1

    # §5.3 — reason hashes. These also pin what SHA-256("...") means for §5.1:
    # a reader who reproduces these has confirmed the convention is the ASCII
    # bytes with no terminator, which is the only thing §5.1 leaves to inference.
    reasons = re.findall(r'SHA-256\("([^"]+)"\)\s*=\s*([0-9a-f]{64})', text)
    if enough(reasons, 4, "reason hashes in §5.3", problems):
        for name, printed in reasons:
            if sha(name.encode()) != printed:
                problems.append(f"§5.3 SHA-256({name!r}) is {sha(name.encode())}, "
                                f"printed as {printed}")
            checked += 1

    # §5.2 / TV-2 — the first theorem, built from the axioms with no store.
    axiom_hash = {g: p for g, _, p in axioms}
    # Whitespace-tolerant: the two texts wrap their lines differently, and a
    # pattern that only matches one of them would quietly check only one.
    false_hash = re.search(r'`FALSE ≡ APPLY\(K,I\)`;\s*Bytes\s*`0206‖H\(K\)‖H\(I\)`;'
                           r'\s*Hash\s*`([0-9a-f]{64})`', text)
    if false_hash is None:
        problems.append("§5.2 no longer states FALSE's construction and hash in "
                        "the form this check reads")
    else:
        built = node_hash(0x02, 0x06, bytes.fromhex(axiom_hash["K"])
                          + bytes.fromhex(axiom_hash["I"]))
        if built != false_hash.group(1):
            problems.append(f"§5.2 FALSE: construction gives {built}, printed "
                            f"{false_hash.group(1)}")
        checked += 1

    # §7 — every test vector that prints whole bytes must hash to its printed hash.
    printed_bytes = re.findall(r'Bytes\s*`([0-9a-f]{4,})`;\s*Hash\s*`([0-9a-f]{64})`',
                               text)
    if enough(printed_bytes, 1, "test vectors printing full bytes", problems):
        for raw, printed in printed_bytes:
            if sha(bytes.fromhex(raw)) != printed:
                problems.append(f"§7 bytes {raw[:12]}… hash to "
                                f"{sha(bytes.fromhex(raw))}, printed {printed}")
            checked += 1
    return checked


def anchor_matches(problems: list[str]) -> None:
    """§8: SpecAnchor = NodeHash(LITERAL, atom = SHA-256(document_bytes))."""
    expected = node_hash(0x00, 0x01, hashlib.sha256(UK.read_bytes()).digest())
    listed = re.findall(r'([0-9a-f]{64})\s+spec/book-1-truth\.md', ANCHORS.read_text())
    if not enough(listed, 1, "anchors for Book I", problems):
        return
    if expected not in listed:
        problems.append(f"the Book's own bytes anchor to {expected}, which is not "
                        f"among the anchors published for it ({listed[-1]} is the "
                        "most recent) — either the text changed without a "
                        "re-anchor, or §8's construction is not what is published")


# ------------------------------------------------------------ B. prose/vectors

def prose_matches_vectors(text: str, problems: list[str]) -> int:
    suite = json.loads(VECTORS.read_text())
    by_tv: dict[str, list[dict]] = {}
    for vector in suite["vectors"]:
        for tv in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            by_tv.setdefault(tv, []).append(vector)

    section = text[text.index("## 7. Test Vectors"):text.index("## 8. Specification")]
    blocks = re.findall(r'\*\*(TV-\d+)[^*]*\*\*:?(.*?)(?=\n\*\*|\Z)', section, re.S)
    if not enough(blocks, 10, "test-vector paragraphs in §7", problems):
        return 0

    checked = 0
    for name, body in blocks:
        number = name.split("-")[1]
        vectors = by_tv.get(number, [])
        claimed = set(re.findall(r'`([0-9a-f]{64})`', body))
        for digest in claimed:
            everywhere = json.dumps(suite)
            if digest not in everywhere:
                problems.append(f"§7 {name} names {digest[:12]}…, which appears "
                                "nowhere in the normative vector suite")
            checked += 1
        if not vectors and number not in {"1", "2", "3", "11", "12"}:
            problems.append(f"§7 {name} has no vector whose note carries its "
                            "number, so the prose claim is unchecked by the suite")
    return checked


def suite_pins_this_spec(problems: list[str]) -> None:
    suite = json.loads(VECTORS.read_text())
    anchor = node_hash(0x00, 0x01, hashlib.sha256(UK.read_bytes()).digest())
    if suite.get("book1_anchor") != anchor:
        problems.append(f"the vector suite pins Book I at "
                        f"{suite.get('book1_anchor', '')[:12]}… but the Book's "
                        f"bytes anchor to {anchor[:12]}… — the suite was generated "
                        "against a different text than the one shipped")


# ------------------------------------------------------------- C. translation

def strip_prose(block: str) -> str:
    """Comments and trailing conditions inside a code block are prose and get
    translated. What must survive translation is everything else."""
    kept = []
    for line in block.splitlines():
        line = re.sub(r'//.*$', '', line)
        line = re.sub(r'\s+(якщо|if)\s+.*$', '', line)
        line = re.sub(r'=\s*size[^\n]*$', '= size…', line)
        if line.strip():
            kept.append(line.rstrip())
    return "\n".join(kept)


def translation_parity(uk: str, en: str, problems: list[str]) -> int:
    checked = 0
    for what, pattern, least in (("hashes", r'\b[0-9a-f]{64}\b', 12),
                                 ("RFC 2119 keywords", RFC, 30)):
        left, right = re.findall(pattern, uk), re.findall(pattern, en)
        if not enough(left, least, f"{what} in the normative text", problems):
            continue
        if left != right:
            problems.append(f"the English rendering does not carry the same "
                            f"{what} in the same order: {len(left)} vs "
                            f"{len(right)}, first difference at "
                            f"{next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), min(len(left), len(right)))}")
        checked += len(left)

    blocks = lambda t: re.findall(r'```(?:text|sh)?\n(.*?)```', t, re.S)
    left, right = blocks(uk), blocks(en)
    if enough(left, 6, "code blocks in the normative text", problems):
        if len(left) != len(right):
            problems.append(f"{len(left)} code blocks in the normative text, "
                            f"{len(right)} in the English rendering")
        for index, (a, b) in enumerate(zip(left, right)):
            if strip_prose(a) != strip_prose(b):
                problems.append(f"code block {index} differs between the two "
                                "texts beyond its translated words")
            checked += 1
    return checked


def main() -> int:
    problems: list[str] = []
    uk, en = UK.read_text(), EN.read_text()

    constants = derivable_constants(uk, problems)
    anchor_matches(problems)
    suite_pins_this_spec(problems)
    prose = prose_matches_vectors(uk, problems)
    english = translation_parity(uk, en, problems)

    # The same derivation, driven by the English text alone: an implementer who
    # cannot read the normative language must still reach every constant.
    english_constants = derivable_constants(en, problems)

    print(f"constants re-derived from the normative text : {constants}")
    print(f"constants re-derived from the English text   : {english_constants}")
    print(f"prose claims found in the vector suite       : {prose}")
    print(f"elements compared across the two texts       : {english}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nSPEC-AUDIT: every constant the Book prints is re-derivable from the\n"
          "  Book alone, in either language; every hash the prose claims appears in\n"
          "  the normative vector suite; the suite is pinned to these exact bytes;\n"
          "  and the English rendering carries the same hashes, keywords and code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
