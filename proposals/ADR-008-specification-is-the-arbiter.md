# ADR-008: two sentences that send an implementer to our code

**Status:** PROPOSED — not adopted, not anchored. A normative edit to Book I
requires a governed re-anchor (GOV-anchors §3) and the multi-family gate this
project uses for Book text. This ADR does the work and stops before the gate.
**Origin:** the accompanying paper names "an implementation of Book I by someone
who has not read this code" as the single most valuable missing datum, and gives
a reason for its absence. The reason turned out to be wrong; two other sentences
turned out to be right.
**Evidence:** [`tools/spec_audit.py`](../tools/spec_audit.py) accounts for all
fifteen constants the Book prints, in both languages — ten re-derived from
constructions the Book states, the rest proved by recomputation from the normative
suite's store and bound to the record of the test that names them — and compares
every budget, spend, outcome and normal form §7 states against those records.
[`tests/spec_audit_selftest.py`](../tests/spec_audit_selftest.py) breaks all of it
thirteen ways and requires the audit to fail for each.
**Revision:** the first version of this ADR said the audit "re-derives every
constant". It did not: it derived nine of fifteen, matched prose digests against
the whole suite rather than against the test that named them, and compared no
numbers at all. External review reproduced all three gaps; the sentences above
state what is now checked.

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
now checks whether one does, over the classes it can decide mechanically: every
digest §7 quotes must belong to the record of the test that quotes it; every
budget, spend, outcome and normal form the prose states must match those records;
and the suite must be pinned to the exact bytes of the Book that ships.

**Across those classes, one discrepancy exists**, and it is a filing gap rather
than a contradiction: TV-12 claims `eval(H(I), n) = ⟨I⟩` at 0 ATP, `EV-GENESIS-BARE`
records exactly that, and nothing machine-readable connects them. The audit
carries it as a named exception that fails the run if it stops reproducing.

At the current anchored revision, no contradiction was detected within the
predicates the audit checks explicitly — and it now reports what it leaves
undecided rather than passing over it. Whether the clause ever decided anything
historically was not audited, and this ADR does not claim it did not.

What can be said without any of that: the clause tells a stranger their
disagreement with the specification is settled by code, and that is the wrong
place for the authority regardless of whether it has ever been exercised.

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
| also in scope | `EV-GENESIS-BARE`'s note gains `TV-12:`, which files the one prose claim the suite proves but does not connect. That edits `tests/spec_conformance/vectors.json`, which is anchored, so it belongs to the same governed step |
| version | a PATCH to Book I: its semantics are unchanged — no rule, price, constant or vector moves. The suite's **metadata** does change (one note gains `TV-12:`) and is re-anchored with it, so "suite unchanged" would be false |

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
