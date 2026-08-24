# ADR-009: the specification is its own arbiter

**Status:** CANDIDATE — prepared, not adopted. The bytes below are frozen and the
anchors computed; adoption needs a fresh multi-family blind gate over *these*
bytes and a threshold-adoption warrant under
[`spec/GOV-anchors.md`](../spec/GOV-anchors.md) §3. Merging this branch is the
adoption; nothing here is adopted by being written.
**Numbered 009, not 008.** `proposals/ADR-008-*` and the remote branch
`adr-008-rev15-candidate` already carry the Resonant Precedent work, which
[`AGENTS.md`](../AGENTS.md) names. Two different ADR-008s is a provenance
collision even when only one reached `master`.
**Origin:** the accompanying paper names "an implementation of Book I by someone
who has not read this code" as the single most valuable missing datum, and gave a
reason for its absence. The reason was wrong. Two other sentences were not.
**Evidence:** [`tools/spec_audit.py`](../tools/spec_audit.py), in CI on every
push, and [`tests/spec_audit_selftest.py`](../tests/spec_audit_selftest.py),
which breaks each of its checks and requires it to fail for its own reason.

## Problem

### What is not a problem

The paper said §5.1 "defers the three 32-byte genesis atom values to
`impl/sigma_glyph.py` … so an implementer must currently read the reference
code". The premise is true and the inference is false: §5.1 states the
construction, §2 states the hash, §5.3 prints three hashes that pin what
`SHA-256("…")` means, and TV-1 prints `SHA-256("I")` in full. Three lines of
arithmetic give all three atoms with no store and no reference implementation.

### What is a problem

**§7 appoints an implementation as the arbiter of the specification.**

> Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний;
> **при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`**).

A stranger who disagrees with the Book is told the matter is settled by a Python
file — which they must read to consult, and cannot audit without reading. That is
the wrong place for the authority regardless of whether the clause has ever been
exercised.

**§5.1 points at that same file for values it has just fully determined,** and
leaves the one convention it does not spell out — that `SHA-256("X")` is the hash
of one ASCII byte — to be inferred from §5.3.

**One prose claim the suite proved was not filed under its test.** TV-12 claims
`eval(H(I), n) = ⟨I⟩` at 0 ATP; `EV-GENESIS-BARE` recorded exactly that and its
note did not name TV-12, so nothing machine-readable connected them.

## Proposal

Three edits. The genesis values are still not printed; the arbiter becomes the
edition; the filing goes through the generator rather than the generated file.

### §5.1 — from

> Повні 32-байтні значення SHA-256("I"/"K"/"S") — в `impl/sigma_glyph.py` (TV-1);
> тут вони навмисно не дублюються, щоб не створювати друге джерело істини.

### to

> Для `X ∈ {I,K,S}` вираз `SHA-256("X")` означає SHA-256 рівно одного
> ASCII-байта `X`, без лапок і термінатора. Значення повністю визначені цією
> конструкцією і навмисно не дублюються, щоб не створювати друге джерело істини;
> референсна реалізація не є нормативним джерелом цих значень.

### §7 — from

> Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний;
> при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`).

### to

> Вичерпний машинний набір `tests/spec_conformance/vectors.json` є нормативною
> частиною цього видання. Проза §7 і записи набору MUST бути взаємно
> узгодженими. Видання з розбіжністю між ними є неконформним і MUST NOT
> використовуватися як джерело консенсусу до виправлення та повторного
> анкерування. Жодна реалізація, включно з референсною, не має переваги над
> нормативними артефактами видання.

**No tool is named in the normative text.** An earlier draft of this ADR put
`tools/spec_audit.py` into §7, which would have replaced one implementation's
authority with another's. The audit is enforcement and evidence; where it reaches
and where it does not is stated in [`spec/IMPLEMENTING.md`](../spec/IMPLEMENTING.md)
and in CI, not in the Book.

The English rendering carries both changes verbatim; it is not anchored, and
`spec_audit.py` requires the two texts to state the same hashes, RFC 2119
keywords, code and §7 predicates.

### The filing, through the source that generates it

`tests/spec_conformance/generate.py` now writes `EV-GENESIS-BARE`'s note as
`TV-12: bare intrinsic thunk…`, and `vectors.json` is regenerated from it. The
generator refuses to write a suite that disagrees with the hand-declared
spec-derived expectations, so the filing cannot launder a value.

With the record filed, the audit's TV-12 waiver is gone — and with it the whole
exception mechanism, which existed for that one case. A statement whose budget is
a variable now has that predicate reported as unresolved while its remaining
predicates are decided against the records, which is what the exception was
standing in for. `tests/spec_audit_selftest.py` gains the direct control: unfile
the record again and the audit fails.

## Consequence, stated exactly

| | |
| --- | --- |
| Book I version | 0.5.2 → **0.5.3** (PATCH) |
| Book I anchor | `a98a03bd5fcc573d4850cdc9e8e80d66518fdc4888ce31c9888df1e24b48b47b` → `480752b7cf1a8c843e3e561216da117df11d8426ed20c82a862ed7fef3a205af` |
| suite anchor | `08116edb302a827858a95dd2a1533134a0fb90220f361085a213f5c93486fcd9` → `c94f1664bafc7d1b6ecc71ea70bb5091addcc5ec1a1b3e6a5c1c47cfa3d80cbb` |
| bundle | a candidate `v0.6.8` section in `spec/ANCHORS.txt`, marked as such |
| files whose anchored bytes change | exactly two: Book I and the vector suite |
| audit ledgers | 43 predicate instances decided (was 40), 7 unresolved (was 6), 3 declared (was 4), 5 clauses outside (unchanged) |

**Behavioural change, honestly.** *Evaluation semantics for a consistent
Book/suite bundle are unchanged: no rule, price, constant or vector moves.* What
changes is the conformance of an **inconsistent** bundle: it is now rejected until
corrected and re-anchored, instead of being resolved in favour of the Python
oracle. That is the point of the edit, and calling it "no behavioural change"
would be false.

## The objection, and the answer

*Removing a tie-break makes a discrepancy undefined rather than resolved.* It does
not: it makes the edition non-conformant, which is defined and stronger. Under the
old clause a discrepancy was silently legal and the implementer deferred; under
this one it is a defect that stops the edition being a source of consensus.

*Three implementations already agree.* They do, and it is weaker evidence than it
looks: Python, Go and Rust were written from the same text by the same author with
model assistance. Agreement is evidence about coding slips and ambiguity, not
about specification error — three implementations of a wrong sentence agree
perfectly.

## What adoption still requires, and this ADR does not do

1. A fresh **blind multi-family gate over these exact bytes**. Five review rounds
   have examined the *audit*; none has examined this candidate, which did not
   exist. Reviews of the enforcement are not reviews of the norm.
2. The gate to confirm the version arithmetic: Book I `0.5.3`, bundle `v0.6.8`.
3. A threshold-adoption warrant under GOV-anchors §3, and the candidate ANCHORS
   section promoted from CANDIDATE to a release section.
4. Merge and release as separate authorisations.
5. A Zenodo v2 of the paper **after** adoption, so it cites an anchor that was
   actually adopted rather than one that was proposed.

## Not decided here

Whether the English rendering should become normative, or be anchored at all. It
is unanchored, so the text an external implementer is most likely to read carries
no integrity guarantee of its own; the audit binds it to the normative file on
every consensus element, which is weaker than an anchor and stronger than the
present promise. That is a separate decision with its own gate.
