# Proposal — Book III clarifications (NFC + unquota'd-policy cap)

**Status:** DRAFT, queued for the next governed release. Non-behavioral; the
reference implementations already behave as specified (`FEDERATION-DIFFERENTIAL:
ALL AGREE`). Adopting these edits re-hashes the `spec/book-3-federation.md`
anchor and therefore requires a new anchor-set adopted by the 2-of-3 roster
(ADR-007 / GOV-anchors §3). Source: Antigravity deep review, 2026-07-18
(`reviews/2026-07-antigravity-deep-review{,-response}.md`).

Both changes are **clarifications of existing behavior**, not new rules: they add
executable-conformance surface without changing any vector's outcome, so they are
a candidate for a PATCH-level governed release (like GOV 1.0.1/1.0.2).

## C-1 — Unicode normalization is not applied (add to §2 or §4)

Rationale: §4 already mandates comparing strings **directly** by Unicode scalar
values. Make the no-normalization choice explicit so no implementation diverges
by normalizing before comparing/hashing. (The review's stronger MUST-NFC/reject
is rejected as disproportionate — it would force a Unicode normalization database
into every implementation and reject legitimate content.)

Proposed text (append to §4, before "Деривація вибору"):

> **Нормалізація Unicode не застосовується (MUST NOT).** Рядкові поля (`actor`,
> будь-які інші текстові ключі/значення) порівнюються та хешуються як точна
> послідовність Unicode scalar values; реалізація MUST NOT застосовувати NFC/NFD
> (чи будь-яку) нормалізацію і MUST NOT відхиляти рядок за форму нормалізації.
> Два рядки, що різняться лише формою нормалізації, — це різний контент: різні
> байти, різний порядок сортування і різний внесок у ViewID/assertion_set_root,
> детерміновано на всіх нодах. Продюсери SHOULD емітити NFC, щоб рядок,
> спотворений *зовнішньою* системою (редактор, БД, ФС, що мовчки нормалізує), не
> перестав резолвитись — але це дисципліна продюсера, не правило верифікатора.

Conformance: add a vector `FV-SELECT-ACTOR-NFC-NFD` — two candidates whose
actor-ids are the NFC and NFD forms of the same text select deterministically
and identically across implementations (they are distinct actors).

## C-2 — Verifier cap for unquota'd policies (add to §4 or §7)

Rationale: an unquota'd policy (`quota_per_actor_epoch` absent) admits unbounded
per-actor candidates for one node in one epoch; a view build sorts them all.
§7(7) bounds re-verification to `O(Δ warrants)` but not candidate cardinality.

Proposed text (append to §4, note after the selection derivation):

> **Ліміт для неквотованих політик (SHOULD).** Політика без
> `quota_per_actor_epoch` не обмежує кількість кандидатів на вузол за епоху;
> оскільки новизна кандидата суто синтаксична (різний `warrant_id`), permissive-
> політика може накопичити необмежену множину. Реалізації SHOULD застосовувати
> конфігуровний локальний ліміт кардинальності кандидатів для неквотованих
> політик і, за перевищення, звітувати усічення — це операційний вибір, не
> вимога формату (пор. Warrant §7). Політики SHOULD оголошувати
> `quota_per_actor_epoch`.

Conformance: existing `FV-QUOTA-ACTOR-EPOCH` already covers the quota path; a
`FV-UNQUOTA-CAP` vector would pin the report-string for a truncated unquota'd set
(implementation-defined limit, so a SHOULD, exercised via a configured cap).

## Adoption checklist (for whoever runs the governed release)
1. Apply C-1, C-2 to `spec/book-3-federation.md`; bump Book III to v0.6.2.
2. Regenerate `spec/ANCHORS.txt` (new Book III anchor) + the anchor-set blob.
3. File the anchor-set adoption warrant under the current governance policy,
   satisfying the 2-of-3 threshold (`s0fractal` + `claude-fable-5`, or with
   `codex`). `claude-fable-5` can sign; one more roster signature is required.
4. `tools/verify_anchors.py` and `anchor_governance.py status --enforce` green.
