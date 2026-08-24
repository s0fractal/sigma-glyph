# ADR-008: two sentences that send an implementer to our code

**Status:** PROPOSED — not adopted, not anchored. A normative edit to Book I
requires a governed re-anchor (GOV-anchors §3) and the multi-family gate this
project uses for Book text. This ADR does the work and stops before the gate.
**Origin:** the accompanying paper names "an implementation of Book I by someone
who has not read this code" as the single most valuable missing datum, and gives
a reason for its absence. The reason turned out to be wrong; two other sentences
turned out to be right.
**Evidence:** [`tools/spec_audit.py`](../tools/spec_audit.py) re-derives every
constant the Book prints from the Book alone, in both languages, and
[`tests/spec_audit_selftest.py`](../tests/spec_audit_selftest.py) breaks that
property nine ways and requires the audit to fail for each.

## Problem

### What is not a problem

The paper says §5.1 "defers the three 32-byte genesis atom values to
`impl/sigma_glyph.py` rather than printing them — so an implementer must
currently read the reference code."

The premise is true and the inference is false. §5.1 states the construction
(`0001`+SHA-256("X")), §2 states `NodeHash = SHA-256(CanonicalBytes)`, §5.3 prints
three hashes of longer strings that pin what `SHA-256("…")` means, and TV-1 prints
`SHA-256("I")` in full. Three lines of code derive all three atoms with no store
and no reference implementation. The audit does exactly this, from the document.

### What is a problem

**§5.1, last line.** It sends the reader to `impl/sigma_glyph.py` for values it
has just fully determined. The stated reason — avoiding a second source of truth —
is sound, and the sentence does not need to be replaced by the digits to stop
pointing at code.

**§7, the vector-suite line.** It reads:

> Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний;
> **при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`**).

This is the real barrier, and it is more serious than a missing constant: it tells
an implementer that where they disagree with the specification, the matter is
settled by a Python file — which they must then read, and which they cannot
audit without reading. A specification that appoints an implementation as its own
arbiter is not the source of truth for its own semantics.

A precedence rule is exercised only when a discrepancy exists. `spec_audit.py`
now checks whether one does: every hash the §7 prose claims must appear in the
normative suite, and the suite must be pinned to the exact bytes of the Book that
ships. **Today no discrepancy exists**, so the clause has never decided anything —
it only tells a stranger where authority lives, and it puts it in the wrong place.

## Proposal

Replace both sentences. The genesis values are still not printed; the arbiter
becomes the Book.

**§5.1 — from:**

> Повні 32-байтні значення SHA-256("I"/"K"/"S") — в `impl/sigma_glyph.py` (TV-1);
> тут вони навмисно не дублюються, щоб не створювати друге джерело істини.

**to:**

> Значення SHA-256("I"/"K"/"S") тут навмисно не дублюються, щоб не створювати
> друге джерело істини. Вони повністю визначені конструкцією цього рядка:
> конвенцію («SHA-256(рядок)» — ASCII-байти без термінатора) фіксують три хеші
> §5.3, а TV-1 (§7) друкує SHA-256("I") повністю. Реалізація виводить їх сама;
> звіряння з референсною реалізацією не потрібне.

**§7 — from:**

> Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний;
> при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`).

**to:**

> Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний).
> Проза цього параграфа і набір MUST узгоджуватися; розбіжність між ними — дефект
> Книги або набору, який виправляється, а не вирішується перевагою однієї
> реалізації. `tools/spec_audit.py` перевіряє це на кожному CI-прогоні: кожен
> хеш, названий прозою §7, MUST бути присутнім у наборі, а набір MUST бути
> запінений до саме цих байтів Книги.

## Consequence, stated exactly

| | |
| --- | --- |
| current anchor | `a98a03bd5fcc573d4850cdc9e8e80d66518fdc4888ce31c9888df1e24b48b47b` |
| anchor after this edit | `d73740534d1d52e90fc7252b5065198800ca6b99fc702f42a77e51c8386d8ff7` |
| document bytes | 23,749 → 24,590 |
| behavioural change | none — no rule, price, constant or vector moves |
| version | a PATCH to Book I: prose only, oracle and suite unchanged |

Adopting it therefore requires a new ANCHORS bundle section, the `book1_anchor`
field of the vector suite re-pinned, and the English rendering updated in step —
all three of which `spec_audit.py` will fail on until they are done, which is the
§8 update protocol behaving as designed.

## The objection, and the answer

*Removing a tie-break makes a discrepancy undefined rather than resolved.*

True, and that is the intent. Under the current clause a discrepancy is silently
legal and an implementer is expected to defer. Under the proposal a discrepancy is
a defect, CI fails on the class of discrepancy that can be mechanically detected,
and the remedy is to fix whichever side is wrong. The Book keeps deciding what is
true; the oracle goes back to being an implementation that must conform like any
other.

*Three implementations already agree.* They do, and it is weaker evidence than it
looks: Python, Go and Rust were written from the same text by the same author with
model assistance. Agreement is evidence about coding slips and ambiguity, not
about specification error — three implementations of a wrong sentence agree
perfectly. This ADR does not claim otherwise.

## Not decided here

Whether the English rendering should become normative, or be anchored at all. It
is currently unanchored, so the text an external implementer is most likely to
read carries no integrity guarantee of its own. `spec_audit.py` binds it to the
normative file on every consensus element — the same hashes in the same order, the
same RFC 2119 keywords, the same code — which is weaker than an anchor and much
stronger than the present promise that it is "reproduced verbatim". Making it
normative is a separate decision with its own gate.
