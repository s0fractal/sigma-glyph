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

# A §7 claim this audit does not decide, each with the reason it cannot. An
# undeclared unchecked claim is an error, and a declaration that stops applying is
# an error too: the point of the ledger is that "not checked" is a recorded
# quantity rather than a silent gap.
UNCHECKED = {
    ("TV-7", "universal", "∀n"):
        "a claim over every budget; the suite records two instances, and this "
        "audit does not decide quantified statements",
    ("TV-10", "compiler", "C1"):
        "a claim about what the compiler emits, not about an evaluation. The "
        "suite records how C1's output behaves; it does not record the "
        "compilation, so nothing here decides it",
    ("TV-11", "historical", "0.4.x"):
        "a statement about a superseded version's behaviour (ADR-003). It is "
        "history, not a claim about this Book, and no record contradicts or "
        "confirms it",
    ("TV-12", "universal", "∀n"):
        "`eval(H(I), n)` quantifies over the budget; the exception below carries "
        "the instance the suite records",
}

# The one prose claim the suite proves but does not file under its test. The
# exception names its witness and the exact fields that must hold, so it fails
# both when the defect is fixed and when the evidence it rests on moves.
EXCEPTIONS = {
    ("TV-12", "spend", 0): {
        "witness": "EV-GENESIS-BARE",
        "expects": {"outcome": "normal_form", "atp_spent": 0},
        "result_glyph": "I",
        "covers_result": "⟨I⟩",
        "why": "eval(H(I)) is a normal form at 0 ATP and EV-GENESIS-BARE records "
               "exactly that, but its note does not name TV-12, so nothing "
               "machine-readable connects the paragraph to its evidence. Filing it "
               "edits an anchored file; it joins the governed change in ADR-008.",
    },
}


def vector_digests(vector: dict) -> set[str]:
    """Every 64-hex value this one record carries, in any field."""
    return set(re.findall(r'\b[0-9a-f]{64}\b', json.dumps(vector)))


def vectors_by_test(suite: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for vector in suite["vectors"]:
        for number in re.findall(r'\bTV-(\d+)\b', vector.get("note", "")):
            grouped.setdefault(number, []).append(vector)
    return grouped


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


def test_vector_blocks(text: str) -> list[tuple[str, str]]:
    section = text[text.index("## 7. Test Vectors"):text.index("## 8. Specification")]
    return re.findall(r'\*\*(TV-\d+)[^*]*\*\*:?(.*?)(?=\n\*\*|\Z)', section, re.S)


def claimed_spends(body: str) -> set[int]:
    """Totals the prose states, in either of the two forms it uses."""
    return {int(n) for n in re.findall(r'\*\*(\d+) ATP\*\*', body)} \
        | {int(n) for n in re.findall(r'(?<!\*)\b(\d+) ATP\b', body)} \
        | {int(n) for n in re.findall(r'spent (\d+)', body)}


def term_hash(expression: str, glyphs: dict[str, str]) -> str | None:
    """Build a term's hash from the way the prose writes it.

    Grammar is exactly what §7 uses for a stated result: a glyph, or APPLY of two
    such. Anything else — a name the text does not define, a variable — returns
    None and becomes a declared unchecked claim rather than a silent pass."""
    expression = expression.strip().strip('`')
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


def stated_results(body: str) -> list[str]:
    """What the prose says an *evaluation* produces.

    A compilation is a different claim: `C1[λx.x] = ⟨I⟩` says what the compiler
    emits, and the suite records how that output behaves rather than the
    compilation itself. Treating the two alike made the audit demand that TV-10's
    evaluation produce ⟨I⟩, which it never claimed."""
    # The look-behind spans whitespace: `C1[λx.x] = ⟨I⟩` puts a space before the
    # sign, so a non-space window sees nothing and lets the compilation through.
    # Compound expressions are read to their closing backtick rather than to the
    # first `)`, which truncated `APPLY(APPLY(...),⟨I⟩)` into something unparsable.
    found = []
    for before, backticked, bare in re.findall(
            r'([^\n]{0,18})(?:=|→|нормальна форма|normal form)\s*'
            r'(?:`(APPLY\([^`]*)`|(⟨\w+⟩))', body):
        if "C1[" in before:
            continue
        found.append(backticked or bare)
    return found


def stated_outcomes(body: str) -> set[str]:
    """Outcomes in result position only.

    TV-11 records that v0.4.x gave Unresolved Reference for terms this Book
    normalises. That is history and not a claim about this Book, and reading every
    mention of an outcome word as a claim turned it into a contradiction."""
    named = set()
    # `[A-Z][a-z]+` misses "ATP Exhausted", whose first word is an initialism —
    # so the outcome the Book uses most often was the one this never saw.
    for tail in re.findall(r'(?:=|→)\s*`?(?:DISSONANCE\()?([A-Z][A-Za-z]* [A-Za-z]+)',
                           body):
        if tail in OUTCOME_WORDS:
            named.add(OUTCOME_WORDS[tail])
    return named


def prose_matches_vectors(text: str, glyphs: dict[str, str], proved: set[str],
                          derived: set[str],
                          problems: list[str]) -> tuple[set[str], int, list[str]]:
    """Bind each §7 paragraph to *its own* records, and account for every claim.

    Returns the digests bound, how many claims were decided, and the claims
    deliberately left undecided. Nothing is skipped silently: a paragraph with no
    records is an error, and a claim this audit cannot decide must be declared.
    """
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
    exercised: set[tuple] = set()

    for name, body in blocks:
        number = name.split("-")[1]
        mine = grouped.get(number, [])
        digests = set(re.findall(r'`([0-9a-f]{64})`', body))
        spends = claimed_spends(body)
        results = stated_results(body)
        outcomes = stated_outcomes(body)
        historical = {w for w in OUTCOME_WORDS if w in body} - {
            w for w in OUTCOME_WORDS if OUTCOME_WORDS[w] in outcomes}
        exceptions = {key: value for key, value in EXCEPTIONS.items()
                      if key[0] == name}

        # Coverage. An aggregate count of filed tests says nothing about *this*
        # paragraph: every tag for one test can vanish and leave the total intact.
        undecided = (digests - derived) or spends or results or outcomes
        if not mine:
            if undecided and not exceptions:
                problems.append(
                    f"§7 {name} states claims and no record in the suite is "
                    "filed under it, so nothing checks them")
            if not exceptions:
                checked += len(digests & derived)
                continue

        recorded_spends = {v["expected"].get("atp_spent") for v in mine}
        recorded_spends.discard(None)
        recorded_outcomes = {v["expected"].get("outcome") for v in mine}
        recorded_results = {v["expected"].get("result_hash") for v in mine}
        theirs: set[str] = set()
        for vector in mine:
            theirs |= vector_digests(vector)

        # --- digests: this test's own, or store-proved *and* quoted here
        for digest in digests:
            elsewhere = owner.get(digest)
            if digest in theirs:
                bound.add(digest)
                checked += 1
            elif elsewhere is not None:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which the suite files as the "
                    f"subject of TV-{elsewhere}. Presence in the suite is not the "
                    "same claim as belonging to this test")
            elif digest in proved and mine:
                # Proved by one SHA-256 from the suite's store, and quoted in a
                # paragraph that does have records. Store proof alone is not
                # enough: an unrelated stored key must not satisfy a fabricated
                # paragraph.
                bound.add(digest)
                checked += 1
            else:
                problems.append(
                    f"§7 {name} names {digest[:12]}…, which is in no record filed "
                    f"under {name} and is not proved by the suite's store")

        # --- outcomes named anywhere in the paragraph
        for outcome in outcomes - recorded_outcomes:
            problems.append(
                f"§7 {name} states the outcome {outcome}, which no record filed "
                f"under it produces: {sorted(recorded_outcomes)}")
        checked += len(outcomes & recorded_outcomes)

        # --- stated results, built from the text and hashed
        # An exception is *needed* only while the claim it excuses is still
        # unmatched. Deciding that up front matters: the result branch used to
        # mark the exception exercised on its own, so filing the spend left the
        # waiver looking alive and the staleness check silent.
        needed = {key for key in exceptions if key[1] == "spend"
                  and key[2] not in recorded_spends}
        covered = {exceptions[key].get("covers_result") for key in needed}
        for expression in results:
            if expression in covered:
                continue
            built = term_hash(expression, glyphs)
            if built is None:
                unchecked.append(f"{name}: result {expression!r} is not built from "
                                 "glyphs this text defines")
                continue
            if built not in recorded_results:
                problems.append(
                    f"§7 {name} says the result is {expression} ({built[:12]}…); "
                    f"no record filed under it produces that: "
                    f"{sorted(str(r)[:12] for r in recorded_results if r)}")
            else:
                checked += 1

        # --- spends
        for spend in sorted(spends - recorded_spends):
            key = (name, "spend", spend)
            if key in needed:
                exercised.add(key)
                continue
            problems.append(
                f"§7 {name} states {spend} ATP, which is not the spend of any "
                f"record filed under {name}: {sorted(recorded_spends)}")
        checked += len(spends & recorded_spends)

        for key, why in ((k, v) for k, v in UNCHECKED.items() if k[0] == name):
            marker = {"compiler": "C1[", "historical": "0.4.x",
                      "universal": ","}.get(key[1], key[2])
            # `eval(H(I), n)` carries a nested `)`, so a pattern that cannot
            # cross one never sees it and the declaration reads as stale.
            present = ("∀n" in body or re.search(r'eval\(.*?,\s*n\)', body)) \
                if key[1] == "universal" else marker in body
            if present:
                exercised.add(key)
                unchecked.append(f"{name}: {why}")

        # --- exact budgets. A record at that exact budget decides it directly.
        # Otherwise a record of the same term at a larger budget that normalises
        # spending exactly N decides it too: evaluation is deterministic and a
        # budget only stops it early (§3.3, §3.4), so a run that needed N and was
        # given more would have finished on N. That rule is named here because it
        # is this audit's own assumption, not the Book's sentence.
        for budget in {int(n) for n in re.findall(r'eval\([^)]*?,\s*(\d+)\)', body)}:
            exact = [v for v in mine if v.get("atp") == budget]
            implied = [v for v in mine
                       if v.get("atp", 0) > budget
                       and v["expected"].get("outcome") == "normal_form"
                       and v["expected"].get("atp_spent") == budget]
            if exact or implied:
                checked += 1
                continue
            problems.append(
                f"§7 {name} states an evaluation at budget {budget}; no record "
                f"filed under it uses that budget, and none normalises spending "
                "exactly that much, so the claim is undecided and undeclared")

        # --- declared exceptions must still hold, and must still be needed
        for key, exception in exceptions.items():
            witness = by_id.get(exception["witness"])
            if witness is None:
                problems.append(
                    f"§7 {name}: the recorded exception names {exception['witness']} "
                    "as its evidence and the suite has no such record — the "
                    "exception is resting on nothing")
                continue
            for field, wanted in exception["expects"].items():
                if witness["expected"].get(field) != wanted:
                    problems.append(
                        f"§7 {name}: {exception['witness']} was to show "
                        f"{field}={wanted} and shows "
                        f"{witness['expected'].get(field)} — the exception's "
                        "evidence has moved")
            glyph = exception.get("result_glyph")
            if glyph and witness["expected"].get("result_hash") != glyphs.get(glyph):
                problems.append(
                    f"§7 {name}: {exception['witness']} no longer produces ⟨{glyph}⟩")
            if key not in exercised:
                problems.append(
                    f"§7 {name}: the recorded exception for {key[2]} no longer "
                    "reproduces. If it was fixed, delete the entry; a waiver that "
                    "outlives its defect is a permanent exception")

    for key in UNCHECKED:
        if key not in exercised:
            problems.append(f"the declaration for {key} matches nothing in §7 any "
                            "more; a stale declaration hides what it once excused")
    return bound, checked, unchecked


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
    bound, checked, unchecked = prose_matches_vectors(uk, glyphs, proved, derived,
                                                     problems)
    printed = inventory(uk, derived, bound, problems)
    english = translation_parity(uk, en, problems)

    # The same derivation, driven by the English text alone: an implementer who
    # cannot read the normative language must still reach every constant.
    english_derived = derivable_constants(en, problems)
    english_bound, _, _ = prose_matches_vectors(en, glyphs, proved, english_derived,
                                                problems)
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
