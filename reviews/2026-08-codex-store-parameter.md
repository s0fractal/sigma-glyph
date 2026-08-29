# Codex (ChatGPT) — the evaluator's implicit world parameter (2026-08-27)

**Registered, not dispositioned.** This file records the review as received.
Nothing here has been reproduced, accepted or refuted, and nothing in the
repository changed because of it. A response goes in a separate `-response.md`.

| | |
| --- | --- |
| reviewer | Codex (ChatGPT), relayed by the author |
| subject | Book I semantics, the public `eval` surface, both papers, and the proof guard |
| kind | spec review under `reviews/README.md`, with a stated severity table |
| received | 2026-08-27 |

**Why this one is filed differently from the Qwen critique.** The protocol holds
that *a finding is a reproduction, not an opinion*. This review's headline finding
arrives with an executable counterexample — two conforming nodes, the same
`term_hash` and the same budget, different canonical result hashes — which is
exactly the shape the protocol asks for. **It has not been run here.** Filing it
is not agreeing with it; the reproduction, and the disposition that follows from
whether it reproduces, are separate work.

The reviewer marks one item as unconfirmed themselves: the V22 guard candidate is
labelled a threat-model candidate rather than a reproduced exploit, because they
could not read this repository's branch-protection policy. Recorded as written.

---

Так ))) І тут я вже знайшов штуку, яка мені подобається **ще більше, ніж `expect`-дірка у Warrant**.

Головна проблема Σ-GLYPH зараз не в Lean, не в SHA і навіть не в proof guard. Вона сидить просто в цій красивій формулі:

```text
result_hash = eval(term_hash, atp)
```

**Насправді машина реалізує**

```text
eval(term_hash, atp, store)
```

і це дуже багато чого міняє. У README прямо заявлено: два незалежні вузли з однаковими `term_hash` і budget отримають той самий `result_hash`. Але Lean-модель має `Store`, `force(h, st)`, `step(..., st)` і `evalHash(h, atp, st)`; відсутній hash повертає `unresolved`. Нормативна Book I робить те саме: відсутній у store demanded hash → канонічний `DISSONANCE(Unresolved Reference)`.

### Попередній verdict

| Severity | Де болить | Проблема |
| --- | --- | --- |
| **BLOCKER** | core semantics | прихований третій input — `store` |
| **MAJOR** | public API | `result_hash` не кодує тип exit |
| **MAJOR** | paper thesis | "memory/work" сильніше за реально доведену семантичну міру |
| **MAJOR** | threat model | bounded computation ≠ practically safe computation |
| **MAJOR** | specification | при prose/vector conflict арбітром є Python oracle |
| **MAJOR / candidate V22** | proof guard | guard контролює artifact, але сам живе в artifact |
| **PAPER** | methodology | taxonomy хороша, але causal/generalization claims ще можна притиснути |

## 1. `Store` — це прихований world-state. І він ламає headline claim

Контрприклад елементарний.

Нехай `X` — валідний LITERAL node, `hX = hash(X)`. Створюємо root:

```text
R = APPLY(I, hX)
```

І дві чесні conforming ноди:

```text
S1 = { R, X }
S2 = { R }
```

Даємо обом:

```text
term_hash = hash(R)
atp = достатній бюджет
```

На `S1`:

```text
R → X
```

На `S2`:

```text
R → DISSONANCE(Unresolved Reference)
```

**Той самий `term_hash`. Той самий ATP. Дві conforming реалізації. Різні canonical result hashes.**

Тобто правильна теорема зараз приблизно така:

```text
∀ h, atp, S:
    eval(h, atp, S) is deterministic
```

а не:

```text
∀ h, atp:
    eval(h, atp) is deterministic
```

Причому це не теоретична придирка: сам Python oracle теж має `eval_hash(h, atp, store, ...)`. А три реалізації на conformance vectors отримують спільно підготовлений corpus/store, тому їхнє 49/49 agreement **не тестує store-independence взагалі**.

Для content-addressed computation це фундаментально. Hash каже: якщо байти існують — ось їхня identity. Hash **не каже**: ці байти зараз доступні цьому evaluator. Зараз availability випадково стала частиною denotational semantics.

Три нормальних архітектурних виходи. Найчистіший — evidence містить commitment на **closed evaluation bundle / store root**, і тоді функція чесно стає `eval(term, ATP, bundle_root)`. Інший варіант — `Unresolved Reference` зробити local availability fault, а не canonical result. Третій — визначити абстрактний immutable `ContentMap` як explicit semantic input і більше ніколи не малювати двоаргументну функцію.

Це я б реально вважав **paper correction worthy**.

## 2. `result_hash` недостатньо, щоб сказати, *що сталося*

`DISSONANCE(ATP Exhausted)` — звичайний term. Його можна покласти в store і успішно обчислити як normal form. Отже одна execution може завершитися:

```text
exit = NormalForm
result = H(DISSONANCE(ATP Exhausted))
```

а інша:

```text
exit = ATPExhausted
result = H(DISSONANCE(ATP Exhausted))
```

**Result однаковий. Причина завершення різна.**

Paper прямо визнає, що trichotomy стосується **machine exit**, а не term, і що caller, якому треба відрізнити завершення від exhaustion, мусить отримати exit окремо. А README при цьому продає саме `result_hash = eval(...)`. Це класичний in-band sentinel problem.

Canonical API мав би бути:

```text
EvalReceipt {
  exit: NormalForm | ATPExhausted | Unresolved,
  result_hash,
  spent
}
```

і вже hash від **receipt**, якщо потрібна identity execution outcome.

## 3. `One Integer for Work and Memory` — title зараз сильніший за theorem

Lean доводить `size(configuration) ≤ atp + 1`, де `size` — семантична tree-like materialized node measure. `Store` взагалі не входить у `size`. Book I сама чесніше називає це "семантична межа пам'яті".

Але це не theorem `process_RSS ≤ f(ATP)` і навіть не `actual_heap_bytes ≤ f(ATP)`: поза theorem лишились representation overhead, evaluator stack, temporary old+new term during rewrite, GC, SHA buffers, CAS, store index, allocator fragmentation, runner state.

Так само з **work**. ATP prices semantic actions, але host work включає search along the spine, `size(z)` traversal, hashing, store lookup. Lean `Store` взагалі `List Bytes`, тобто lookup cost залежить від розміру store; Python oracle використовує dict. Сам paper визнає, що Lean Store не доведений refinement реального CAS.

Найсильніше чисте твердження:

> **One integer bounds semantic reduction cost and peak semantic materialization.**

Я б у наступній версії paper перейменував центральну величину на `semantic materialization measure` і окремо намалював refinement gap:

```text
ATP
 ↓ theorem
semantic work / materialized-size
 ↓ NOT YET PROVEN
runtime operations / heap / stack / RSS
```

## 4. "Safe to run a stranger's reason" теж поки трохи нахабно

`uint32 ATP` означає максимум **4,294,967,295** одиниць дозволеної роботи. Reference implementation має local limits на depth, materialized nodes і fetches, але admission limit типу `max_atp` я не бачу.

Stranger може дати маленький по пам'яті diverging term і величезний валідний ATP. Математично — terminate eventually. Операційно — побачимось після кількох мільярдів semantic actions. "Finite" ≠ "safe".

Не треба міняти consensus semantics — потрібна verifier policy:

```text
if claimed_atp > local_policy.max_atp:
    refuse to execute
```

і ця refusal — **не canonical Σ-GLYPH result**, а verifier admission decision. Особливо важливо для Warrant integration: attacker не повинен сам визначати, скільки CPU verifier зобов'язаний витратити на attacker-supplied reason.

## 5. STANDARD, в якому при конфлікті стандарту з тестами перемагає Python

Book I §7 каже, що vectors normative, а при розбіжності з prose виграє `impl/sigma_glyph.py`. Це майже анекдот: *specification: implementation is the specification.*

Paper уже відчув: limitation прямо називає відсутність external implementation найціннішим missing datum і зазначає, що reference oracle як arbiter змушує implementer читати код. У свіжих комітах ви вже почали розбирати саме цю проблему.

Правило має бути іншим:

```text
prose disagrees with normative vectors
→ specification release is inconsistent
→ FAIL
```

І тоді "three independent implementations" я б замінив на: **three separately implemented engines from one development lineage.**

## 6. `Twenty-One Ways Past a Proof Guard` просить 22-й спосіб

Я б назвав: **V22 — Edit the Cop.**

Центральна теза — control scope must come from something the controlled artifact cannot edit. Але `proof_guard.py`, `theorem_pins.json`, `GUARD_CLAIMS.txt`, regression suite і GitHub workflow лежать у тому ж repo. `GUARD_CLAIMS.txt` навіть визнає: хто може змінити registry, може змінити й claims; це visibility control, не authority.

```text
proof ← checked by guard
guard ← checked by tests
tests ← invoked by workflow
workflow + guard + tests ← editable artifact
??? ← checks that those controls weren't neutered
```

Я **не називаю це reproduced V22**, бо не зміг перевірити вашу external branch-protection policy: connector не дав прочитати branch protection; visible rulesets endpoint повернув порожній список. Тому це threat-model candidate, а не confirmed exploit.

Концептуальний фінал guard-paper мав би бути: **trusted verifier must live outside the candidate revision** — base-branch/reusable verifier pinned externally, окремий verifier repo/action, або governance commitment на verifier hash.

## 7. Про самі papers

"Опубліковані" тут не настільки страшно: repository сам каже, що engine paper — Zenodo-deposited, not peer reviewed, а guard paper узагалі без deposit.

`Twenty-One Ways...` — гарний experience report / adversarial case study. Але "21" — це taxonomy count, а не незалежні 21 vulnerabilities, і більшість з'являлася адаптивно після попередніх fixes. Теза "всі вони один shape" є post-hoc класифікацією: вона настільки широка, що треба показати, **які guard bugs не потрапляють у цей shape**, інакше вона ризикує стати нефальсифікованим "усе є scope problem".

"Literature has almost nothing to say" я б послабив — є adjacent literature про proof engineering, reproducible proof environments та CI (Proof Engineering project, Coq/Nix CI work). Novelty claim краще формулювати вузько: *"we are unaware of a systematic reproduced taxonomy of CI-to-proof-claim binding bypasses."*

EXP-004 — приклад того, чому "preregistered" не магічне слово. Пререгістрація справді була до reducer, але після першого result знайшлося **дев'ять** проблем measurement/control apparatus, включно з неправильною equal-work метрикою, не-reproducible Python hash, experiment-not-in-CI і controls, що вимірювали не те. Тому я б називав його не "clean confirmatory preregistered experiment", а:

> **preregistered research question and frozen corpus, followed by post-result audited repair of the measurement apparatus.**

Strong-confluence частину я намагався загавнити й не зміг: у Lafont справді strong confluence дає однакову довжину terminating reductions і uniqueness up to permutation. Тут математику можна залишити в спокої.

---

Після всього цього я не думаю, що Σ-GLYPH розвалюється. Після зняття маркетингового шару лишається чітка штука:

> Для фіксованого immutable content environment `S`, Σ-GLYPH задає deterministic total evaluator `eval(h, ATP, S)`; ATP обмежує semantic reduction expenditure, а Lean-модель доводить `materialized_size ≤ ATP + 1` для кожної configuration. Відповідність цієї моделі executable implementations поки емпірична, а physical CPU/RAM і data availability лежать на наступному refinement layer.

**Оце твердження я поки не зміг зламати.** А двоаргументне `eval(term_hash, atp)` — зміг.

Тому papers не ховати. Я б навпаки залишив цей шрам максимально видимим: **"Correction: the evaluator had an implicit world parameter."**

### Посилання, як подані рецензентом

- Proof Engineering — <https://proofengineering.org/>
- Lafont, *Interaction Combinators* — copy cited via Scribd
