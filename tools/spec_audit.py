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
DIGEST = r'\b[0-9a-f]{64}\b'


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

def derive_axioms(text: str, problems: list[str]) -> tuple[set[str], dict[str, str]]:
    """§5.1. The CanonicalBytes cell IS the construction; it is read from the
    table rather than hardcoded, so deleting it fails this check."""
    derived, table = set(), {}
    axioms = re.findall(r'\|\s*(\w)\s*\|\s*`0001`\+SHA-256\("(\w)"\)\s*\|\s*'
                        r'`([0-9a-f]{64})`\s*\|', text)
    if not enough(axioms, 3, "genesis axioms in §5.1", problems):
        return derived, table
    for glyph, hashed, printed in axioms:
        if glyph != hashed:
            problems.append(f"§5.1 row {glyph} hashes {hashed!r}")
        got = node_hash(0x00, 0x01, hashlib.sha256(glyph.encode()).digest())
        if got != printed:
            problems.append(f"§5.1 {glyph}: the stated construction gives {got}, "
                            f"the table prints {printed}")
        derived.add(printed)
        table[glyph] = printed
    return derived, table


def derive_reasons(text: str, problems: list[str]) -> set[str]:
    """§5.3. These also pin what SHA-256("...") means for §5.1: a reader who
    reproduces them has confirmed the convention is the ASCII bytes with no
    terminator, which is the only thing §5.1 leaves to inference."""
    derived = set()
    reasons = re.findall(r'SHA-256\("([^"]+)"\)\s*=\s*([0-9a-f]{64})', text)
    if not enough(reasons, 4, "reason hashes in §5.3", problems):
        return derived
    for name, printed in reasons:
        if sha(name.encode()) != printed:
            problems.append(f"§5.3 SHA-256({name!r}) is {sha(name.encode())}, "
                            f"printed as {printed}")
        derived.add(printed)
    return derived


def derive_first_theorem(text: str, axioms: dict[str, str],
                         problems: list[str]) -> set[str]:
    """§5.2 / TV-2, built from the axioms with no store."""
    found = re.search(r'`FALSE ≡ APPLY\(K,I\)`;\s*Bytes\s*`0206‖H\(K\)‖H\(I\)`;'
                      r'\s*Hash\s*`([0-9a-f]{64})`', text)
    if found is None:
        problems.append("§5.2 no longer states FALSE's construction and hash in "
                        "the form this check reads")
        return set()
    if "K" not in axioms or "I" not in axioms:
        return set()
    built = node_hash(0x02, 0x06, bytes.fromhex(axioms["K"]) + bytes.fromhex(axioms["I"]))
    if built != found.group(1):
        problems.append(f"§5.2 FALSE: construction gives {built}, printed "
                        f"{found.group(1)}")
    return {found.group(1)}


def derive_printed_bytes(text: str, problems: list[str]) -> set[str]:
    """Both forms the Book uses: inline in §7 and on separate lines in §4.2.
    A pattern matching only one silently left the Canonical Invalid Object out."""
    derived = set()
    printed = re.findall(r'Bytes:?\s*`?([0-9a-f]{4,})`?;?\s*Hash:?\s+`?'
                         r'([0-9a-f]{64})`?', text)
    if not enough(printed, 2, "constants printed as bytes and hash", problems):
        return derived
    for raw, stated in printed:
        if sha(bytes.fromhex(raw)) != stated:
            problems.append(f"bytes {raw[:12]}… hash to {sha(bytes.fromhex(raw))}, "
                            f"printed {stated}")
        derived.add(stated)
    return derived


def derivable_constants(text: str, problems: list[str]) -> set[str]:
    """Recompute each printed hash from the construction the Book states.

    Returns the digests actually re-derived, so `inventory` can name the printed
    constants that nothing here accounts for."""
    derived, axioms = derive_axioms(text, problems)
    derived |= derive_reasons(text, problems)
    derived |= derive_first_theorem(text, axioms, problems)
    derived |= derive_printed_bytes(text, problems)
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


# What this file decides, exhaustively. Everything a §7 statement says beyond
# these five is outside its reach, and is reported rather than absorbed.
PREDICATES = ("subject", "budget", "outcome", "result", "spend")

# Clauses §7 states that are not any of the five. They are recognised so they can
# be *counted and named*, not decided: this audit has no way to check that an
# evaluation touched no store, that a branch was never forced, that a memory
# invariant held along the way, or what a superseded version once did.
CLAUSES = (
    (r'звернення до сховища|store access|сховище не потрібне|no store|'
     r'порожнь\w* сховищ|empty store', "storage access"),
    (r'форсу\w*|forcing|ліниво|lazily|НЕ форсу', "forcing discipline"),
    (r'size\s*[−-]\s*1\s*≤\s*spent|size\s*[+]?\s*\d*\s*≤\s*spent', "memory invariant"),
    (r'0\.4\.x', "behaviour of a superseded version"),
)


class Report(NamedTuple):
    """What one pass over a text found. A NamedTuple rather than a dict so the
    fields carry their types to the caller instead of arriving as `object`."""
    bound: set
    decided: int
    declared: list
    unresolved: list
    uncovered: list
    seen: set
    signatures: dict


class Claim(NamedTuple):
    """One statement of §7, projected onto the five predicates above.

    The projection is the point and the limit. A statement is matched against
    **one** record that satisfies all of its *resolved* predicates at once — which
    is what keeps a spend from drifting to another budget or a result to another
    term — and everything the projection drops is reported as unresolved or as an
    uncovered clause. This file decides predicates. It does not decide statements,
    and it does not claim that an unmatched sentence is an error."""
    test: str
    text: str                  # normalised, and the identity used by declarations
    subject: str | None
    subject_hash: str | None
    formula: str | None
    budget: int | None
    variable_budget: bool
    outcome: str | None
    result: str | None
    spend: int | None

    def resolved(self) -> dict[str, object]:
        return {kind: value for kind, value in
                (("subject", self.subject_hash), ("budget", self.budget),
                 ("outcome", self.outcome), ("result", self.result),
                 ("spend", self.spend)) if value is not None}

    def signature(self) -> tuple:
        """Language-neutral where it can be, and the raw text where it cannot —
        so a subject changed in one rendering only still shows up as a difference."""
        # Every field rendered as text: a signature holding None beside a string
        # cannot be sorted, and sorting is what makes the comparison order-free.
        return tuple(str(field) for field in
                     (self.subject_hash or self.formula or "", self.budget,
                      self.variable_budget, self.outcome, self.result, self.spend))


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
    return set(re.findall(DIGEST, json.dumps(vector)))


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
    """Split on the bold headings rather than matching across them.

    The single expression this replaces nested a lazy `.*?` inside a lookahead
    and scanned super-linearly; splitting first is linear and says what it means.
    """
    section = text[text.index("## 7. Test Vectors"):text.index("## 8. Specification")]
    blocks = []
    for chunk in re.split(r'\n(?=\*\*)', section):
        heading = re.match(r'\*\*(TV-\d+)[^*]{0,40}\*\*:?', chunk)
        if heading:
            blocks.append((heading.group(1), chunk[heading.end():]))
    return blocks


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
    out: list[str] = []
    for piece in pieces:
        # A sentence stop, unless it is inside a version number. The earlier
        # look-behind demanded the character before the stop be a bracket or a
        # digit, so a stop after a closing backtick — which is how §7 writes most
        # of them — never split, and whole paragraphs stayed one statement.
        out.extend(re.split(r'(?<!\d)\.\s+(?=[«"`A-ZА-ЯҐЄІЇ])', piece))
    # Raw, not normalised: the backticks mark which part of a sentence is formula
    # and which is prose, and that distinction is what lets the two translations
    # be compared without comparing their languages.
    return [part for part in out if normalise(part)]


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


def resolve_subject(subject: str | None, glyphs: dict[str, str],
                    fallback: str | None) -> str | None:
    """The subject as an identity, when the text determines one.

    `·` refers back to the term the paragraph named; `H(X)` and glyph expressions
    build directly. A subject naming something the Book does not define — `ghost`,
    a store shape, a variable — has no identity here and is reported as such."""
    if subject is None:
        return None
    subject = subject.strip().strip("`")
    if subject in {"·", "·)"}:
        return fallback
    named = re.fullmatch(r'H\((\w+)\)', subject)
    if named:
        return glyphs.get(named.group(1))
    reference = re.fullmatch(r'REF\(H\((\w+)\)\)', subject)
    if reference and reference.group(1) in glyphs:
        return node_hash(0x01, 0x01, bytes.fromhex(glyphs[reference.group(1)]))
    return term_hash(subject, glyphs)


def uncovered_clauses(statement: str) -> list[str]:
    return [label for pattern, label in CLAUSES
            if re.search(pattern, statement, re.I)]


def stated_outcome(statement: str) -> str | None:
    for words, value in OUTCOME_WORDS.items():
        if re.search(r'[=→]\s*(?:DISSONANCE\()?' + words, statement):
            return value
    return None


def stated_result(statement: str) -> str | None:
    tail = re.search(r'(?:[=→]|нормальна форма|normal form)\s*'
                     r'(APPLY\(.{0,120}?\)(?=,|$)|⟨\w+⟩)', statement)
    return tail.group(1).strip() if tail else None


def stated_spend(statement: str) -> int | None:
    spends = [int(n) for n in re.findall(r'\b(\d+) ATP\b', statement)] \
        + [int(n) for n in re.findall(r'spent (\d+)', statement)]
    return spends[0] if spends else None


def parse_claim(test: str, raw: str, glyphs: dict[str, str],
                fallback: str | None) -> Claim | None:
    """A statement becomes a claim when it says what something evaluates to,
    costs, or normalises to. Commentary stays commentary."""
    # Whitespace-normalised: the two renderings wrap their lines differently, and
    # a formula carrying a line break compares unequal to the same formula on one
    # line, which reads as the texts disagreeing when they do not.
    formula = next(iter(re.findall(r'`([^`]+)`', raw)), None)
    if formula:
        formula = re.sub(r'\s+', ' ', formula).strip()
    statement = normalise(raw)
    budget, variable = None, False
    evaluation = re.search(r'eval\((.*),\s*(\d+|n)\s*\)', statement)
    subject = None
    if evaluation:
        subject = evaluation.group(1).strip()
        if evaluation.group(2).isdigit():
            budget = int(evaluation.group(2))
        else:
            variable = True
    else:
        arrow = re.search(r'^(.*?)[→=]', statement)
        if arrow and arrow.group(1).strip():
            subject = arrow.group(1).strip()

    outcome = stated_outcome(statement)
    result = stated_result(statement)
    spend = stated_spend(statement)

    if outcome is None and result is None and spend is None:
        return None
    # The formula is tried first: a subject often carries trailing prose — "REF(H(K))
    # on an empty store" — whose identity is determined by the formula alone.
    # Only when the statement actually has a subject. "нормальна форма `APPLY(…)`"
    # has none, and its single backticked span is the *result* — reading that as
    # an identity made the audit demand the record be the thing it produced.
    identity = None
    if subject is not None:
        identity = resolve_subject(formula, glyphs, fallback) \
            or resolve_subject(subject, glyphs, fallback)
    return Claim(test, statement, subject, identity, formula, budget,
                 variable, outcome, result, spend)


def satisfies(record: dict, claim: Claim, glyphs: dict[str, str]) -> bool:
    expected = record["expected"]
    if claim.subject_hash is not None and \
            claim.subject_hash not in {record.get("term"), record.get("bytes")}:
        return False
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
                f"subject {claim.subject_hash[:12]}…" if claim.subject_hash else "",
                f"outcome {claim.outcome}" if claim.outcome else "",
                f"result {claim.result}" if claim.result else "",
                f"spend {claim.spend}" if claim.spend is not None else ""])))


def account_for_digests(name: str, digests: set[str], mine: list[dict],
                        owner: dict[str, str], proved: set[str],
                        derived: set[str], problems: list[str]) -> set[str]:
    """A digest belongs to the test that prints it, or it is reported."""
    found = set()
    for digest in sorted(digests):
        elsewhere = owner.get(digest)
        here = any(digest in vector_digests(v) for v in mine)
        if not here and elsewhere is not None:
            problems.append(
                f"§7 {name} names {digest[:12]}…, which the suite files as the "
                f"subject of TV-{elsewhere}. Presence in the suite is not the "
                "same claim as belonging to this test")
        elif here or (digest in proved and mine):
            found.add(digest)
        elif digest not in derived:
            problems.append(
                f"§7 {name} names {digest[:12]}…, which is in no record filed "
                f"under {name} and is not proved by the suite's store")
    return found


def review_exception(name: str, claim: Claim, mine: list[dict], by_id: dict,
                     glyphs: dict[str, str], problems: list[str]) -> str | None:
    """An exception must still be needed, still have its witness, and still be
    about the statement it was written for. Returns its reason, or nothing when
    it has failed."""
    exception = EXCEPTIONS[claim.text]
    # A variable budget makes `decide` refuse on sight, so "still needed" ignores
    # the budget and asks only whether a record already satisfies the rest.
    if any(satisfies(record, claim, glyphs) for record in mine):
        problems.append(
            f"§7 {name}: the exception for “{claim.text[:48]}…” is no longer "
            "needed — a record filed under this test now decides the claim. "
            "Delete the entry")
        return None
    witness = by_id.get(exception["witness"])
    if witness is None:
        problems.append(
            f"§7 {name}: the exception for “{claim.text[:48]}…” names "
            f"{exception['witness']} and the suite has no such record — the "
            "exception is resting on nothing")
        return None
    for field, wanted in exception["expects"].items():
        if witness["expected"].get(field) != wanted:
            problems.append(f"§7 {name}: {exception['witness']} was to show "
                            f"{field}={wanted} and shows "
                            f"{witness['expected'].get(field)}")
    if witness["expected"].get("result_hash") != glyphs.get(exception["result_glyph"]):
        problems.append(f"§7 {name}: {exception['witness']} no longer produces "
                        f"⟨{exception['result_glyph']}⟩")
    if claim.result != f"⟨{exception['result_glyph']}⟩" or \
            claim.spend != exception["expects"]["atp_spent"]:
        problems.append(
            f"§7 {name}: the statement the exception covers now claims result "
            f"{claim.result} at {claim.spend} ATP, which is not what its witness "
            "records")
    return exception["why"]


def unfiled(name: str, claims: list[Claim], digests: set[str], derived: set[str],
            problems: list[str]) -> bool:
    """Nothing is filed under this paragraph. Does it need anything to be?

    An aggregate count of filed tests says nothing about *this* paragraph: every
    tag for one test can vanish and leave the total intact."""
    outstanding = [claim for claim in claims
                   if claim.text not in DECLARED and claim.text not in EXCEPTIONS]
    if not outstanding and not digests - derived:
        return False
    problems.append(
        f"§7 {name} states {len(outstanding)} claim(s) and "
        f"{len(digests - derived)} constant(s) that no record in the suite is "
        "filed under, so nothing checks them")
    return True


def review_claim(name: str, claim: Claim, mine: list[dict], by_id: dict,
                 glyphs: dict[str, str], seen: set[str], unresolved: list[str],
                 problems: list[str]) -> tuple[int, str | None]:
    """One statement: excused with a reason, or decided predicate by predicate."""
    if claim.text in EXCEPTIONS:
        seen.add(claim.text)
        why = review_exception(name, claim, mine, by_id, glyphs, problems)
        return 0, f"{name}: {claim.text[:60]} — {why}" if why else None
    if claim.text in DECLARED:
        seen.add(claim.text)
        return 0, f"{name}: {claim.text[:60]} — {DECLARED[claim.text]}"

    if claim.subject is not None and claim.subject_hash is None:
        unresolved.append(f"{name}: subject “{claim.subject[:40]}” names nothing "
                          "this text gives an identity to")
    if claim.variable_budget:
        unresolved.append(f"{name}: budget in “{claim.text[:40]}…” is a variable "
                          "rather than a value")
    failure = decide(claim, mine, glyphs)
    if failure:
        problems.append(f"§7 {name}: “{claim.text[:70]}” — {failure}")
        return 0, None
    return len(claim.resolved()), None


def prose_matches_vectors(text: str, glyphs: dict[str, str], proved: set[str],
                          derived: set[str],
                          problems: list[str]) -> Report:
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
    unresolved: list[str] = []
    uncovered: list[str] = []
    seen_declarations: set[str] = set()
    signatures: dict[str, list] = {}

    for name, body in blocks:
        number = name.split("-")[1]
        mine = grouped.get(number, [])
        digests = set(re.findall(r'`([0-9a-f]{64})`', body))
        statements = split_statements(body)
        first_digest = next(iter(re.findall(r'`([0-9a-f]{64})`', body)), None)
        claims = [claim for claim in
                  (parse_claim(name, statement, glyphs, first_digest)
                   for statement in statements) if claim is not None]
        for statement in statements:
            for label in uncovered_clauses(normalise(statement)):
                uncovered.append(f"{name}: {label}")
        signatures[name] = sorted(claim.signature() for claim in claims)

        if not mine and unfiled(name, claims, digests, derived, problems):
            continue

        found = account_for_digests(name, digests, mine, owner, proved, derived,
                                    problems)
        bound |= found
        checked += len(found)

        for claim in claims:
            decided, note = review_claim(name, claim, mine, by_id, glyphs,
                                         seen_declarations, unresolved, problems)
            checked += decided
            if note:
                unchecked.append(note)

    return Report(bound, checked, unchecked, unresolved, uncovered,
                  seen_declarations, signatures)


def texts_state_the_same_claims(left: dict[str, list], right: dict[str, list],
                                problems: list[str]) -> None:
    """The two texts must make the same statements, test by test.

    Compared as structured signatures rather than as counts: equal counts are not
    equal claims, and a subject changed in one rendering only kept the count
    intact while the sentence said something else."""
    for test in sorted(set(left) | set(right)):
        here, there = left.get(test, []), right.get(test, [])
        if here != there:
            differing = [a for a, b in zip(here + [None] * len(there),
                                           there + [None] * len(here)) if a != b]
            problems.append(
                f"§7 {test} does not state the same predicates in both texts: "
                f"{len(here)} and {len(there)} statement(s), first difference "
                f"{str(differing[:1])[:90]}")


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
    printed = set(re.findall(DIGEST, text))
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
    report_uk = prose_matches_vectors(uk, glyphs, proved, derived, problems)
    bound, checked, unchecked = (report_uk.bound, report_uk.decided,
                                 report_uk.declared)
    printed = inventory(uk, derived, bound, problems)
    english = translation_parity(uk, en, problems)

    # The same derivation, driven by the English text alone: an implementer who
    # cannot read the normative language must still reach every constant.
    english_derived = derivable_constants(en, problems)
    report_en = prose_matches_vectors(en, glyphs, proved, english_derived, problems)
    english_bound = report_en.bound
    declarations_still_apply(report_uk.seen | report_en.seen, problems)
    texts_state_the_same_claims(report_uk.signatures, report_en.signatures,
                                problems)
    inventory(en, english_derived, english_bound, problems)

    # Counted against what the Book prints, not against everything the tools
    # touched: a figure larger than its own subject is the defect this file spent
    # two rounds learning to state precisely.
    printed_set = set(re.findall(DIGEST, uk))
    print(f"constants printed in the normative text        : {printed}")
    print(f"  derived from a construction the Book states  : {len(printed_set & derived)}")
    print(f"  bound to the record of the test that names it : {len(bound)}")
    print(f"    of those, also proved by the suite's store  : {len(bound & proved)}")
    print(f"  unaccounted for                              : "
          f"{len(printed_set - derived - bound)}")
    print(f"same inventory from the English text alone     : "
          f"{len(set(re.findall(r'[0-9a-f]{{64}}', en)) - english_derived - english_bound)}"
          " unaccounted")
    print(f"§7 mechanical predicates decided               : {checked}")
    print("  the five it decides: subject identity, budget, canonical outcome,")
    print("  result hash, ATP spend — and nothing else")
    print(f"§7 predicates the text does not resolve        : "
          f"{len(report_uk.unresolved)}")
    for item in report_uk.unresolved:
        print(f"    unresolved {item}")
    print(f"§7 statements declared undecided               : {len(unchecked)}")
    for claim in unchecked:
        print(f"    declared   {claim}")
    clauses = sorted(set(report_uk.uncovered))
    print(f"§7 clauses outside those predicates entirely   : {len(clauses)}")
    for clause in clauses:
        print(f"    uncovered  {clause}")
    print(f"elements compared across the two texts         : {english}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"\nSPEC-AUDIT: every constant the Book prints is accounted for without\n"
          f"  reading an implementation — re-derived from a construction the Book\n"
          f"  states, or bound to the record of the very test that names it, in\n"
          f"  either language. Every §7 paragraph has records filed under it or a\n"
          f"  named exception whose witness is verified, and the two texts state the\n"
          f"  same predicates test by test. The suite is pinned to these exact bytes.\n"
          f"\n  WHAT THIS IS NOT. It decides five mechanical predicates and no more.\n"
          f"  {len(report_uk.unresolved)} predicate(s) name something the text gives no identity to,\n"
          f"  {len(unchecked)} statement(s) are declared undecided, and {len(clauses)} clause(s) — storage\n"
          f"  access, forcing discipline, the memory invariant, the behaviour of a\n"
          f"  superseded version — lie outside those predicates entirely and are\n"
          f"  listed above rather than absorbed. This is not a proof that §7 and the\n"
          f"  suite say the same thing, it does not claim an unmatched sentence is an\n"
          f"  error, and no earlier revision was audited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
