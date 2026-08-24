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
from typing import NamedTuple

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


class Claim(NamedTuple):
    """One statement of §7, as a whole rather than as loose properties.

    Comparing spends, outcomes and results as three sets let their associations
    dissolve: TV-4's `spent 0` and `spent 3` could change places between budgets
    0 and 3, and TV-11's two evaluations could exchange results, with every set
    unchanged and the audit green. A claim is matched against **one** record that
    satisfies all of its stated fields at once, or against one named rule."""
    test: str
    text: str                  # normalised, and the identity used by declarations
    subject: str | None
    budget: int | None
    variable_budget: bool
    outcome: str | None
    result: str | None
    spend: int | None


# Statements §7 makes that no record decides. Keyed by the statement itself, so
# editing or deleting one invalidates its declaration and forces a fresh look —
# a marker like "C1[" covered several statements at once and stayed satisfied
# when one of them changed.
DECLARED = {
    "∀n: eval(Ω,n) = DISSONANCE(ATP Exhausted)":
        "quantified over every budget; the suite records two instances and this "
        "audit does not decide quantified statements",
    "C1[λx.x] = ⟨I⟩":
        "what the compiler emits, not what an evaluation produces. The suite "
        "records how C1's output behaves and not the compilation",
    "C1[λx.λy.x] = APPLY(APPLY(⟨S⟩,APPLY(⟨K⟩,⟨K⟩)),⟨I⟩), hash "
    "bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d":
        "same: a compilation, whose output hash the suite's store proves but "
        "whose production it does not record",
}

# The one statement the suite proves without filing. It binds the whole claim —
# subject, result and spend — to one witness, so changing any part of the
# sentence or any part of the evidence breaks it.
EXCEPTIONS = {
    "Голий intrinsic-товк: eval(H(I), n) = ⟨I⟩, 0 ATP, сховище не потрібне": {
        "witness": "EV-GENESIS-BARE",
        "result_glyph": "I",
        "expects": {"outcome": "normal_form", "atp_spent": 0},
        "why": "EV-GENESIS-BARE records exactly this, and its note does not name "
               "TV-12, so nothing machine-readable connects the paragraph to its "
               "evidence. Filing it edits an anchored file; ADR-008.",
    },
    "A bare intrinsic thunk: eval(H(I), n) = ⟨I⟩, 0 ATP, no store needed": {
        "witness": "EV-GENESIS-BARE",
        "result_glyph": "I",
        "expects": {"outcome": "normal_form", "atp_spent": 0},
        "why": "the same statement in the English rendering",
    },
}


def vector_digests(vector: dict) -> set[str]:
    return set(re.findall(r'\b[0-9a-f]{64}\b', json.dumps(vector)))


def vectors_by_test(suite: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for vector in suite["vectors"]:
        for number in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            grouped.setdefault(number, []).append(vector)
    return grouped


def subjects_by_test(suite: dict) -> dict[str, str]:
    """Which test each evaluated term or serialized object belongs to."""
    owner: dict[str, str] = {}
    for vector in suite["vectors"]:
        for number in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            for field in ("term", "bytes"):
                if vector.get(field):
                    owner[vector[field]] = number
    return owner


def test_vector_blocks(text: str) -> list[tuple[str, str]]:
    section = text[text.index("## 7. Test Vectors"):text.index("## 8. Specification")]
    return re.findall(r'\*\*(TV-\d+)[^*]*\*\*:?(.*?)(?=\n\*\*|\Z)', section, re.S)


def normalise(statement: str) -> str:
    return re.sub(r'\s+', ' ', statement.replace("`", "").replace("**", "")).strip(" .;—")


def split_statements(body: str) -> list[str]:
    """Semicolons and sentence stops, but never inside a backticked span."""
    pieces, current, quoted = [], [], False
    for character in body:
        if character == "`":
            quoted = not quoted
        if character == ";" and not quoted:
            pieces.append("".join(current))
            current = []
            continue
        current.append(character)
    pieces.append("".join(current))
    out = []
    for piece in pieces:
        # A sentence stop, unless it is inside a version number. The earlier
        # look-behind demanded the character before the stop be a bracket or a
        # digit, so a stop after a closing backtick — which is how §7 writes most
        # of them — never split, and whole paragraphs stayed one statement.
        out.extend(re.split(r'(?<!\d)\.\s+(?=[«"`A-ZА-ЯҐЄІЇ])', piece))
    return [normalise(part) for part in out if normalise(part)]


def term_hash(expression: str, glyphs: dict[str, str]) -> str | None:
    """A glyph, or APPLY of two such. Anything else is not decidable from text."""
    expression = expression.strip().strip("`")
    glyph = re.fullmatch(r'⟨(\w+)⟩', expression)
    if glyph:
        return glyphs.get(glyph.group(1))
    apply = re.fullmatch(r'APPLY\((.*)\)', expression, re.S)
    if not apply:
        return None
    depth, split = 0, None
    for index, character in enumerate(apply.group(1)):
        depth += (character == "(") - (character == ")")
        if character == "," and depth == 0:
            split = index
            break
    if split is None:
        return None
    left = term_hash(apply.group(1)[:split], glyphs)
    right = term_hash(apply.group(1)[split + 1:], glyphs)
    if left is None or right is None:
        return None
    return node_hash(0x02, 0x06, bytes.fromhex(left) + bytes.fromhex(right))


def parse_claim(test: str, statement: str) -> Claim | None:
    """A statement becomes a claim when it says what something evaluates to,
    costs, or normalises to. Commentary stays commentary."""
    budget, variable = None, False
    evaluation = re.search(r'eval\((.*),\s*([0-9]+|n)\s*\)', statement)
    subject = None
    if evaluation:
        subject = evaluation.group(1).strip()
        if evaluation.group(2).isdigit():
            budget = int(evaluation.group(2))
        else:
            variable = True
    else:
        arrow = re.search(r'^(.*?)(?:→|=)', statement)
        if arrow and arrow.group(1).strip():
            subject = arrow.group(1).strip()

    outcome = None
    for words, value in OUTCOME_WORDS.items():
        if re.search(r'(?:=|→)\s*(?:DISSONANCE\()?' + words, statement):
            outcome = value

    result = None
    tail = re.search(r'(?:=|→|нормальна форма|normal form)\s*'
                     r'(APPLY\(.*?\)(?=,|$)|⟨\w+⟩)', statement)
    if tail:
        result = tail.group(1).strip()

    spend = None
    spends = [int(n) for n in re.findall(r'\b(\d+) ATP\b', statement)] \
        + [int(n) for n in re.findall(r'spent (\d+)', statement)]
    if spends:
        spend = spends[0]

    if outcome is None and result is None and spend is None:
        return None
    return Claim(test, normalise(statement), subject, budget, variable,
                 outcome, result, spend)


def satisfies(record: dict, claim: Claim, glyphs: dict[str, str]) -> bool:
    expected = record["expected"]
    if claim.outcome is not None and expected.get("outcome") != claim.outcome:
        return False
    if claim.spend is not None and expected.get("atp_spent") != claim.spend:
        return False
    if claim.result is not None:
        wanted = term_hash(claim.result, glyphs)
        if wanted is None or expected.get("result_hash") != wanted:
            return False
    return True


def decide(claim: Claim, records: list[dict], glyphs: dict[str, str]) -> str | None:
    """One record must satisfy the whole claim. Returns why it could not."""
    if claim.variable_budget:
        return "the budget is a variable"
    candidates = records
    rule = ""
    if claim.budget is not None:
        exact = [r for r in records if r.get("atp") == claim.budget]
        if exact:
            candidates = exact
        else:
            # Deterministic evaluation: a run given more than it needed and
            # spending exactly N would have finished on N (§3.3, §3.4). This is
            # the audit's assumption, stated, not the Book's sentence.
            candidates = [r for r in records
                          if r.get("atp", 0) > claim.budget
                          and r["expected"].get("outcome") == "normal_form"
                          and r["expected"].get("atp_spent") == claim.budget]
            rule = " (via the larger-budget rule)"
            if not candidates:
                return f"no record uses budget {claim.budget}, and none normalises "\
                       f"spending exactly that much"
    if any(satisfies(record, claim, glyphs) for record in candidates):
        return None
    return (f"no single record{rule} among "
            f"{', '.join(r['id'] for r in candidates) or 'none'} has "
            + ", ".join(filter(None, [
                f"outcome {claim.outcome}" if claim.outcome else "",
                f"result {claim.result}" if claim.result else "",
                f"spend {claim.spend}" if claim.spend is not None else ""])))


def prose_matches_vectors(text: str, glyphs: dict[str, str], proved: set[str],
                          derived: set[str],
                          problems: list[str]) -> tuple[set[str], int, list[str]]:
    suite = json.loads(VECTORS.read_text())
    grouped = vectors_by_test(suite)
    owner = subjects_by_test(suite)
    by_id = {v["id"]: v for v in suite["vectors"]}
    blocks = test_vector_blocks(text)
    if not enough(blocks, 10, "test-vector paragraphs in §7", problems):
        return set(), 0, []

    bound: set[str] = set()
    checked = 0
    unchecked: list[str] = []
    seen_declarations: set[str] = set()
    tally_per_test: dict[str, int] = {}

    for name, body in blocks:
        number = name.split("-")[1]
        mine = grouped.get(number, [])
        digests = set(re.findall(r'`([0-9a-f]{64})`', body))
        claims = [claim for claim in
                  (parse_claim(name, statement) for statement in split_statements(body))
                  if claim is not None]

        tally_per_test[name] = len(claims)
        if not mine:
            outstanding = [c for c in claims
                           if c.text not in DECLARED and c.text not in EXCEPTIONS]
            if outstanding or (digests - derived):
                problems.append(
                    f"§7 {name} states {len(outstanding)} claim(s) and "
                    f"{len(digests - derived)} constant(s) that no record in the "
                    "suite is filed under, so nothing checks them")
                continue

        for digest in digests:
            elsewhere = owner.get(digest)
            if any(digest in vector_digests(v) for v in mine):
                bound.add(digest)
                checked += 1
            elif elsewhere is not None:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which the suite files as the "
                    f"subject of TV-{elsewhere}. Presence in the suite is not the "
                    "same claim as belonging to this test")
            elif digest in proved and mine:
                bound.add(digest)
                checked += 1
            elif digest not in derived:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which is in no record filed "
                    f"under {name} and is not proved by the suite's store")

        for claim in claims:
            if claim.text in EXCEPTIONS:
                seen_declarations.add(claim.text)
                exception = EXCEPTIONS[claim.text]
                # Still needed? If the suite has since filed a record that decides
                # this claim, the exception is spent and must go, or it becomes a
                # permanent licence to skip a claim that is now checkable.
                # A variable budget makes `decide` refuse on sight, so the test
                # for "still needed" ignores the budget and asks only whether some
                # record filed here already satisfies the claim's other fields.
                if any(satisfies(record, claim, glyphs) for record in mine):
                    problems.append(
                        f"§7 {name}: the exception for “{claim.text[:48]}…” is no "
                        "longer needed — a record filed under this test now "
                        "decides the claim. Delete the entry")
                    continue
                witness = by_id.get(exception["witness"])
                if witness is None:
                    problems.append(
                        f"§7 {name}: the exception for “{claim.text[:48]}…” names "
                        f"{exception['witness']} and the suite has no such record — "
                        "the exception is resting on nothing")
                    continue
                for field, wanted in exception["expects"].items():
                    if witness["expected"].get(field) != wanted:
                        problems.append(
                            f"§7 {name}: {exception['witness']} was to show "
                            f"{field}={wanted} and shows "
                            f"{witness['expected'].get(field)}")
                if witness["expected"].get("result_hash") != \
                        glyphs.get(exception["result_glyph"]):
                    problems.append(f"§7 {name}: {exception['witness']} no longer "
                                    f"produces ⟨{exception['result_glyph']}⟩")
                if claim.result != f"⟨{exception['result_glyph']}⟩" or \
                        claim.spend != exception["expects"]["atp_spent"]:
                    problems.append(
                        f"§7 {name}: the statement the exception covers now claims "
                        f"result {claim.result} at {claim.spend} ATP, which is not "
                        "what its witness records")
                unchecked.append(f"{name}: {claim.text[:60]} — {exception['why']}")
                continue
            if claim.text in DECLARED:
                seen_declarations.add(claim.text)
                unchecked.append(f"{name}: {claim.text[:60]} — {DECLARED[claim.text]}")
                continue
            failure = decide(claim, mine, glyphs)
            if failure:
                problems.append(f"§7 {name}: “{claim.text[:70]}” — {failure}")
            else:
                checked += 1

    return bound, checked, unchecked, seen_declarations, tally_per_test


def texts_state_the_same_claims(left: dict[str, int], right: dict[str, int],
                                problems: list[str]) -> None:
    """The two texts must make the same statements, test by test.

    Otherwise a claim can be deleted from one language and its declaration stays
    satisfied by the other — which is how deleting TV-10's compiler statement
    from the normative text left this file green."""
    for test in sorted(set(left) | set(right)):
        if left.get(test, 0) != right.get(test, 0):
            problems.append(
                f"§7 {test} states {left.get(test, 0)} claim(s) in the normative "
                f"text and {right.get(test, 0)} in the English rendering; the two "
                "are supposed to say the same thing")


def declarations_still_apply(seen: set[str], problems: list[str]) -> None:
    """Judged once, after both texts.

    A declaration written for the English rendering is absent from the normative
    one and vice versa; checking per pass reported each as stale in the other's
    run, which would have taught a reader to ignore the message."""
    for statement in list(DECLARED) + list(EXCEPTIONS):
        if statement not in seen:
            problems.append(
                f"the declaration for “{statement[:60]}…” matches no statement in "
                "§7 in either language any more. If the statement changed it must "
                "be looked at again; a declaration that outlives its claim "
                "excuses nothing")


def inventory(text: str, derived: set[str], bound: set[str],
              problems: list[str]) -> int:
    """Every constant the Book prints must be accounted for.

    Two routes, and only two: re-derived from a construction the text states, or
    bound to the record of the test that names it. Store proof is *not* a third
    route on its own — a digest the store happens to contain can be quoted under a
    paragraph it has nothing to do with, so store proof only ever strengthens a
    binding that already exists."""
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
    derived = derivable_constants(uk, problems)
    glyphs = dict(axioms)
    false_hash = re.search(r'Bytes\s*`0206‖H\(K\)‖H\(I\)`;\s*Hash\s*`([0-9a-f]{64})`', uk)
    if false_hash:
        glyphs["FALSE"] = false_hash.group(1)
    anchor_matches(problems)
    suite_pins_this_spec(problems)
    bound, checked, unchecked, seen, claims_uk = prose_matches_vectors(
        uk, glyphs, proved, derived, problems)
    printed = inventory(uk, derived, bound, problems)
    english = translation_parity(uk, en, problems)

    # The same derivation, driven by the English text alone: an implementer who
    # cannot read the normative language must still reach every constant.
    english_derived = derivable_constants(en, problems)
    english_bound, _, _, seen_en, claims_en = prose_matches_vectors(
        en, glyphs, proved, english_derived, problems)
    declarations_still_apply(seen | seen_en, problems)
    texts_state_the_same_claims(claims_uk, claims_en, problems)
    inventory(en, english_derived, english_bound, problems)

    # Counted against what the Book prints, not against everything the tools
    # touched: a figure larger than its own subject is the defect this file spent
    # two rounds learning to state precisely.
    printed_set = set(re.findall(r'\b[0-9a-f]{64}\b', uk))
    print(f"constants printed in the normative text        : {printed}")
    print(f"  derived from a construction the Book states  : {len(printed_set & derived)}")
    print(f"  bound to the record of the test that names it : {len(bound)}")
    print(f"    of those, also proved by the suite's store  : {len(bound & proved)}")
    print(f"  unaccounted for                              : "
          f"{len(printed_set - derived - bound)}")
    print(f"same inventory from the English text alone     : "
          f"{len(set(re.findall(r'[0-9a-f]{{64}}', en)) - english_derived - english_bound)}"
          " unaccounted")
    print(f"§7 claims decided                              : {checked}")
    print(f"§7 claims explicitly left undecided            : {len(unchecked)}")
    for claim in unchecked:
        print(f"    unchecked  {claim}")
    print(f"elements compared across the two texts         : {english}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"\nSPEC-AUDIT: every constant the Book prints is accounted for without\n"
          f"  reading an implementation — re-derived from a construction the Book\n"
          f"  states, or bound to the record of the very test that names it, in\n"
          f"  either language. Every §7 paragraph has records filed under it or a\n"
          f"  named exception whose witness is verified. Of its claims, {checked}\n"
          f"  were decided against those records and {len(unchecked)} are listed\n"
          f"  above as undecided, each with the reason it cannot be. The suite is\n"
          f"  pinned to these exact bytes, and the English rendering carries the\n"
          f"  same hashes, keywords and code.\n"
          f"\n  This is a statement about the anchored revision and the predicates\n"
          f"  named here. It is not a proof that the prose and the suite say the\n"
          f"  same thing, and no earlier revision was audited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
