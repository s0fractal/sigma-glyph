#!/usr/bin/env python3
"""Can Book I be implemented from Book I?

The paper says the single most valuable missing datum is an implementation by
someone who has not read this code, and names a reason: that the specification
sends an implementer to `impl/sigma_glyph.py`. This checks that claim instead of
repeating it, in three parts.

A. **Every constant the Book prints is accounted for without an implementation.**
   Each is either recomputed from a construction the text states, or proved by
   recomputation from the normative suite's own store, or bound to the record of
   the test that names it. A printed constant accounted for by none of the three
   is reported — that, not a missing digit, is what would force a reader into the
   reference implementation.

B. **The prose and the machine-readable vectors agree.** §7 says the oracle wins
   in a discrepancy. A precedence rule is only ever exercised when there *is* a
   discrepancy, so this checks whether one exists — per test, not per file. An
   earlier version asked whether a digest appeared anywhere in the suite and
   stayed green when two tests' hashes were swapped, which is presence mistaken
   for binding. Budgets, spends, outcomes and normal forms are compared too.

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

def derivable_constants(text: str, problems: list[str]) -> set[str]:
    """Recompute each printed hash from the construction the Book states.

    Returns the digests actually re-derived, so `inventory` can name the printed
    constants that nothing here accounts for."""
    derived: set[str] = set()

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
            derived.add(printed)

    # §5.3 — reason hashes. These also pin what SHA-256("...") means for §5.1:
    # a reader who reproduces these has confirmed the convention is the ASCII
    # bytes with no terminator, which is the only thing §5.1 leaves to inference.
    reasons = re.findall(r'SHA-256\("([^"]+)"\)\s*=\s*([0-9a-f]{64})', text)
    if enough(reasons, 4, "reason hashes in §5.3", problems):
        for name, printed in reasons:
            if sha(name.encode()) != printed:
                problems.append(f"§5.3 SHA-256({name!r}) is {sha(name.encode())}, "
                                f"printed as {printed}")
            derived.add(printed)

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
        derived.add(false_hash.group(1))

    # §7 — every test vector that prints whole bytes must hash to its printed hash.
    # Both forms the Book uses: inline in §7 (`Bytes ...; Hash ...`) and on
    # separate lines in §4.2's code block. A pattern matching only one of them
    # silently leaves the Canonical Invalid Object out of the inventory, which is
    # exactly what the first version of this file did.
    printed_bytes = re.findall(r'Bytes:?\s*`?([0-9a-f]{4,})`?;?\s*Hash:?\s+`?'
                               r'([0-9a-f]{64})`?', text)
    if enough(printed_bytes, 2, "constants printed as bytes and hash", problems):
        for raw, printed in printed_bytes:
            if sha(bytes.fromhex(raw)) != printed:
                problems.append(f"bytes {raw[:12]}… hash to "
                                f"{sha(bytes.fromhex(raw))}, printed {printed}")
            derived.add(printed)
    return derived


def store_verified(problems: list[str]) -> set[str]:
    """Digests the suite's own store proves, by recomputation.

    `objects` maps a hash to the bytes that produce it, so an entry is not merely
    a value appearing in a file — it is a claim a reader checks with one SHA-256.
    A digest accounted for this way needs no implementation either."""
    suite = json.loads(VECTORS.read_text())
    store = suite.get("objects", {})
    if not enough(store, 20, "objects in the suite's store", problems):
        return set()
    verified = set()
    for digest, raw in store.items():
        if sha(bytes.fromhex(raw)) != digest:
            problems.append(f"the suite's store lists {digest[:12]}… for bytes "
                            f"that hash to {sha(bytes.fromhex(raw))[:12]}…")
        else:
            verified.add(digest)
    return verified


# Claims the §7 prose makes that no record is *filed under* their test. Each entry
# must keep reproducing: a waiver that outlives its defect is how an exception
# becomes permanent, so this fails when an item is fixed as loudly as when a new
# one appears.
UNFILED = {
    ("TV-12", 0): "EV-GENESIS-BARE records exactly this — eval(H(I)) is a normal "
                  "form at 0 ATP — but its note does not name TV-12, so nothing "
                  "machine-readable connects the paragraph to the record that "
                  "proves it. Filing it means editing an anchored file; it joins "
                  "the governed change in ADR-008.",
}


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

OUTCOME_WORDS = {"ATP Exhausted": "atp_exhausted",
                 "Unresolved Reference": "unresolved_reference",
                 "Invalid Object": "invalid_object"}


def vector_digests(vector: dict) -> set[str]:
    """Every 64-hex value this one record carries, in any field."""
    return set(re.findall(r'\b[0-9a-f]{64}\b', json.dumps(vector)))


def vectors_by_test(suite: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for vector in suite["vectors"]:
        for number in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            grouped.setdefault(number, []).append(vector)
    return grouped


def test_vector_blocks(text: str) -> list[tuple[str, str]]:
    section = text[text.index("## 7. Test Vectors"):text.index("## 8. Specification")]
    return re.findall(r'\*\*(TV-\d+)[^*]*\*\*:?(.*?)(?=\n\*\*|\Z)', section, re.S)


def claimed_spends(body: str) -> set[int]:
    """Totals the prose states, in either of the two forms it uses."""
    return {int(n) for n in re.findall(r'\*\*(\d+) ATP\*\*', body)} \
        | {int(n) for n in re.findall(r'(?<!\*)\b(\d+) ATP\b', body)} \
        | {int(n) for n in re.findall(r'spent (\d+)', body)}


def subjects_by_test(suite: dict) -> dict[str, str]:
    """Which test each evaluated term or serialized object belongs to.

    A digest can be proved by the store and still be quoted under the wrong
    paragraph — that is precisely the swap this check exists to catch — so the
    subject of a test is tracked separately from the values it merely contains."""
    owner: dict[str, str] = {}
    for vector in suite["vectors"]:
        for number in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            for field in ("term", "bytes"):
                if vector.get(field):
                    owner[vector[field]] = number
    return owner


def prose_matches_vectors(text: str, axioms: dict[str, str], proved: set[str],
                          problems: list[str]) -> set[str]:
    """Bind each §7 paragraph to *its own* records, not to the file at large.

    The first version of this check asked whether a digest appeared anywhere in
    `vectors.json`. Swapping TV-4's and TV-5's hashes left it green: every value
    was still present, attached to the wrong test. Presence is not binding, and a
    check that confuses them proves less than the sentence describing it.
    """
    suite = json.loads(VECTORS.read_text())
    grouped = vectors_by_test(suite)
    owner = subjects_by_test(suite)
    blocks = test_vector_blocks(text)
    if not enough(blocks, 10, "test-vector paragraphs in §7", problems):
        return set()
    if not enough(grouped, 8, "test-vector numbers named by the suite's notes",
                  problems):
        return set()

    bound: set[str] = set()
    for name, body in blocks:
        number = name.split("-")[1]
        mine = grouped.get(number, [])
        if not mine:
            continue          # inventory requires these digests to be derived

        theirs: set[str] = set()
        for vector in mine:
            theirs |= vector_digests(vector)
        for digest in set(re.findall(r'`([0-9a-f]{64})`', body)):
            elsewhere = owner.get(digest)
            if digest in theirs:
                bound.add(digest)
            elif elsewhere is not None:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which the suite files as the "
                    f"subject of TV-{elsewhere}. Presence in the suite is not the "
                    "same claim as belonging to this test")
            elif digest in proved:
                # Not this test's subject and not another's: an artifact whose
                # hash the suite's store proves by recomputation. Accounted for
                # without an implementation, which is the question being asked.
                bound.add(digest)
            else:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which is in no record filed "
                    f"under {name} ({', '.join(v['id'] for v in mine)}) and is not "
                    "proved by the suite's store")

        # What the prose says an evaluation costs, against what the suite recorded.
        observed = {v["expected"].get("atp_spent") for v in mine}
        unmatched = claimed_spends(body) - {o for o in observed if o is not None}
        for spend in sorted(unmatched):
            if (name, spend) in UNFILED:
                continue
            problems.append(
                f"§7 {name} states {spend} ATP, which is not the spend of any "
                f"record filed under {name}: {sorted(o for o in observed if o is not None)}")
        for waived_name, waived_spend in UNFILED:
            if waived_name == name and waived_spend not in unmatched:
                problems.append(
                    f"§7 {name}: the recorded exception for {waived_spend} ATP no "
                    "longer reproduces. If it was fixed, delete the entry; a "
                    "waiver that outlives its defect is a permanent exception")

        # Where the prose names a budget, that exact budget must be recorded, with
        # the outcome and spend the prose gives it.
        for budget, tail in re.findall(r'eval\([^)]*?,\s*(\d+)\)(.{0,90})', body, re.S):
            exact = [v for v in mine if v.get("atp") == int(budget)]
            if not exact:
                continue
            spent = re.search(r'spent (\d+)', tail)
            if spent and exact[0]["expected"].get("atp_spent") != int(spent.group(1)):
                problems.append(
                    f"§7 {name} says budget {budget} spends {spent.group(1)}; "
                    f"{exact[0]['id']} records "
                    f"{exact[0]['expected'].get('atp_spent')}")
            for words, outcome in OUTCOME_WORDS.items():
                if words in tail and exact[0]["expected"].get("outcome") != outcome:
                    problems.append(
                        f"§7 {name} says budget {budget} gives {words}; "
                        f"{exact[0]['id']} records "
                        f"{exact[0]['expected'].get('outcome')}")

        # A normal form the prose names by glyph must be the glyph the suite got.
        for budget, glyph in re.findall(r'eval\([^)]*?,\s*\d+\)\s*=\s*⟨(\w)⟩', body) \
                and re.findall(r'eval\([^)]*?,\s*(\d+)\)\s*=\s*⟨(\w)⟩', body) or []:
            exact = [v for v in mine
                     if v["expected"].get("outcome") == "normal_form"]
            if exact and glyph in axioms and \
                    exact[0]["expected"].get("result_hash") != axioms[glyph]:
                problems.append(
                    f"§7 {name} says the normal form is ⟨{glyph}⟩ "
                    f"({axioms[glyph][:12]}…); {exact[0]['id']} records "
                    f"{str(exact[0]['expected'].get('result_hash'))[:12]}…")
    return bound


def inventory(text: str, derived: set[str], bound: set[str],
              problems: list[str]) -> int:
    """Every constant the Book prints must be accounted for by one of the two.

    A digest that is neither re-derived from a stated construction nor bound to
    the record of the test that names it is a value a reader can only obtain by
    trusting us — which is the whole question this file exists to answer."""
    printed = set(re.findall(r'\b[0-9a-f]{64}\b', text))
    if not enough(printed, 12, "constants printed in the text", problems):
        return 0
    unaccounted = sorted(printed - derived - bound)
    for digest in unaccounted:
        where = re.findall(r'\*\*(TV-\d+|[^*]{0,30})\*\*',
                           text[max(0, text.find(digest) - 300):text.find(digest)])
        problems.append(f"{digest[:12]}… is printed near "
                        f"{where[-1][:28] if where else 'no labelled block'} but is "
                        "neither re-derived from a stated construction nor bound to "
                        "a record of the test that names it")
    return len(printed)


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

    axioms = dict(re.findall(r'\|\s*(\w)\s*\|\s*`0001`\+SHA-256\("\w"\)\s*\|\s*'
                             r'`([0-9a-f]{64})`\s*\|', uk))
    proved = store_verified(problems)
    derived = derivable_constants(uk, problems) | proved
    anchor_matches(problems)
    suite_pins_this_spec(problems)
    bound = prose_matches_vectors(uk, axioms, proved, problems)
    printed = inventory(uk, derived, bound, problems)
    english = translation_parity(uk, en, problems)

    # The same derivation, driven by the English text alone: an implementer who
    # cannot read the normative language must still reach every constant.
    english_derived = derivable_constants(en, problems) | proved
    english_bound = prose_matches_vectors(en, axioms, proved, problems)
    inventory(en, english_derived, english_bound, problems)

    # Counted against what the Book prints, not against everything the tools
    # touched: a figure larger than its own subject is the defect this file spent
    # two rounds learning to state precisely.
    printed_set = set(re.findall(r'\b[0-9a-f]{64}\b', uk))
    print(f"constants printed in the normative text        : {printed}")
    print(f"  derived from a construction the Book states  : "
          f"{len(printed_set & derivable_constants(uk, []))}")
    print(f"  proved by recomputation from the suite's store: "
          f"{len(printed_set & proved)}")
    print(f"  bound to the record of the test that names it : {len(bound)}")
    print(f"  unaccounted for                              : "
          f"{len(printed_set - derived - bound)}")
    print(f"same inventory from the English text alone     : "
          f"{len(set(re.findall(r'[0-9a-f]{{64}}', en)) - english_derived - english_bound)}"
          " unaccounted")
    print(f"elements compared across the two texts         : {english}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nSPEC-AUDIT: every constant the Book prints is accounted for without\n"
          "  reading an implementation — re-derived from a construction the Book\n"
          "  states, or bound to the record of the very test that names it, in\n"
          "  either language; each §7 paragraph's stated budgets, spends, outcomes\n"
          "  and normal forms match the records filed under it; the suite is pinned\n"
          "  to these exact bytes; and the English rendering carries the same\n"
          "  hashes, keywords and code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
