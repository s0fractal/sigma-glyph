# ADR-009: the specification is its own arbiter

**Status:** CANDIDATE — prepared, not adopted. The bytes below are frozen and the
anchors computed. **Adoption is a threshold-authorised warrant over the
`v0.7.0` anchor-set blob**, under [`spec/GOV-anchors.md`](../spec/GOV-anchors.md)
§3, preceded by a fresh multi-family blind gate over these bytes. Merging this
branch does not adopt anything; it records already-authorised bytes on `master`.
Neither writing this document nor merging it is adoption.
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
>
> **Що саме має узгоджуватися (MUST).** Для кожного тестового вектора §7
> нормативним представленням твердження прози в наборі є поля запису: предмет
> обчислення (`term` або `bytes`), бюджет (`atp`), канонічна відмова чи нормальна
> форма (`expected.outcome`), хеш результату (`expected.result_hash`) і витрачений
> ATP (`expected.atp_spent`). […] Решта прози §7 пояснює правила, встановлені
> §3–§5 […], і не є самостійним нормативним твердженням цього параграфа.

**Why the second paragraph exists.** "Mutually consistent" alone does not say
*which* record fields carry a prose statement, so an implementer could not tell
what makes an edition non-conformant — and this audit's own ledgers show the gap
is real: seven predicates it cannot resolve, three statements it declares
undecided, five clauses outside its reach. Naming the five fields makes the
requirement decidable without naming any tool, and it does not weaken the Book:
the clauses it sets aside — store access, forcing discipline, the memory bound —
are normative in §3.3, §3.4 and §3.5, where they are established. §7 illustrates
them; it does not legislate them a second time.

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
| Book I version | 0.5.2 → **0.6.0** (MINOR) |
| Book I anchor | `a98a03bd5fcc573d4850cdc9e8e80d66518fdc4888ce31c9888df1e24b48b47b` → `629e86f0951e67346915a36328864d0ac9b091b06aad1af55af26700ac547d70` |
| suite anchor | `08116edb302a827858a95dd2a1533134a0fb90220f361085a213f5c93486fcd9` → `e7a6ece403520a6997dfdf640bcdd50bf842860b4cbdaa97ba20aa08a949165b` |
| bundle | a candidate `v0.7.0` section in `spec/ANCHORS.txt`, marked as such |
| files whose anchored bytes change | exactly two: Book I and the vector suite |
| audit ledgers | 43 predicate instances decided (was 40), 7 unresolved (was 6), 3 declared (was 4), 5 clauses outside (unchanged) |

**Why MINOR and not PATCH.** An earlier draft called this `0.5.3`, a PATCH, on
the grounds that no rule, price, constant or vector moves. That reasoning does not
survive its own next paragraph: the verdict for a **documented state** changes.
An edition whose prose and suite disagree used to be usable — the oracle settled
it — and is now non-conformant. The repository's previous PATCH releases either
changed nothing observable or tightened a case the specification already
forbade; this changes the answer for a case the specification previously allowed.
A conformant implementation of `0.5.2` can therefore be non-conformant under this
edition without changing a line, which is exactly what a MINOR is for.

*Evaluation semantics for a consistent Book/suite bundle are unchanged: no rule,
price, constant or vector moves.* What changes is the conformance of an
**inconsistent** bundle.

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

## What is frozen, and what is not

A git SHA cannot be the governance subject: after the gate this ADR's status
changes, the ANCHORS section loses its CANDIDATE label, `MAP.md` moves, and a
warrant appears. What is frozen now is the **normative anchor set**, and its
canonical unsigned blob:

| | |
| --- | --- |
| Book I anchor | `629e86f0951e67346915a36328864d0ac9b091b06aad1af55af26700ac547d70` |
| suite anchor | `e7a6ece403520a6997dfdf640bcdd50bf842860b4cbdaa97ba20aa08a949165b` |
| jurisdiction | `a30bd202…`, the governance genesis root named in GOV-anchors §5 |
| ancestor | `d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5`, the adopted `v0.6.7` anchor-set blob |
| **unsigned `v0.7.0` anchor-set blob** | **`1a4ebb99c56945d21ab0cef76e212b29205878d59e5b542724df8685f98d8111`** |

The blob is committed at
[`adr-009-v0.7.0-anchor-set.unsigned.json`](adr-009-v0.7.0-anchor-set.unsigned.json)
and is what a threshold warrant would sign. **It carries no trailing newline** — its
hash is over the canonical JSON exactly as `tools/anchor_governance.py make-blob`
emits it, and a newline changes the identity. `tests/anchor_blob_roundtrip.py`
runs that command in a copied tree and requires the result to be byte-identical to
the committed file; an earlier version of that test checked the command against
itself and the file against a constant, never against each other, and printed one
release's digest beside another's as agreement.

Reproducing it requires promoting the ANCHORS header from
`== v0.7.0 (CANDIDATE …) ==` to `== v0.7.0 ==` first: `make-blob` does not see a
labelled candidate section, which is why a candidate cannot be blobbed or adopted
by accident. Promoting that header is part of adoption, not of this document.

The candidate commit SHA is the provenance of the *package* — this prose, the
tests, the tooling — and not the identity of the adoption.

## What adoption still requires, and this ADR does not do

1. A fresh **blind multi-family gate over these exact bytes**. Five review rounds
   have examined the *audit*; none has examined this candidate, which did not
   exist. Reviews of the enforcement are not reviews of the norm.
2. The gate to confirm the version arithmetic: Book I `0.6.0`, bundle `v0.7.0`.
3. A threshold-adoption warrant over the blob above, under GOV-anchors §3, and
   the ANCHORS header promoted from CANDIDATE to a release section. The chain it
   extends is real and unbroken — `v0.6.2` through `v0.6.7` each have an adopted
   anchor-set blob in `.warrants/blobs` — and the trust config that decides
   authority is deliberately out of band: `anchor_governance.py status` refuses a
   path inside the verified tree, so no one can evaluate authority from these
   bytes alone.
4. Merge and release as separate authorisations.
5. A Zenodo v2 of the paper **after** adoption, so it cites an anchor that was
   actually adopted rather than one that was proposed.

## Consequences for the other Books, which this candidate does not resolve

Two anchored documents rest on the clause this edit removes, and the gate should
decide what to do about them rather than have me decide quietly:

- **Book III §… states** that on a disagreement between its prose and
  `impl/sigma_federation.py` the oracle wins, **and attributes that rule to
  "дисципліна Книги I §7"**. After this edition, Book I §7 no longer contains that
  discipline, so the attribution becomes false while Book III's own rule stands.
- **Book II** carries the same construction for `impl/sigma_wave.py`, without the
  cross-reference.

This candidate deliberately touches only Book I. Extending it would change two
more anchored files and two more version numbers, and harmonising federation and
wave precedence is a decision about those Books, not a consequence of this one.
But leaving Book III citing a rule that no longer exists is not acceptable
either: whichever way the gate rules, one of the two must change before adoption,
and the choice belongs to the gate.

## Not decided here

Whether the English rendering should become normative, or be anchored at all. It
is unanchored, so the text an external implementer is most likely to read carries
no integrity guarantee of its own; the audit binds it to the normative file on
every consensus element, which is weaker than an anchor and stronger than the
present promise. That is a separate decision with its own gate.
