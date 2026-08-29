# Qwen — critique of the deposited paper (2026-08-27)

**Registered, not dispositioned.** This file records the review as received. No
finding here has been reproduced, accepted, refuted or acted on, and nothing in
the repository changed because of it. A response, if one is written, goes in a
separate `-response.md` as the protocol requires.

| | |
| --- | --- |
| reviewer | Qwen, relayed by the author |
| subject | the paper *One Integer for Work and Memory*, as deposited at [10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651) |
| kind | essayistic critique of a publication — **not** a Book I spec review |
| received | 2026-08-27 |

**What it is not, under `reviews/README.md`.** The protocol asks a spec review for
a verdict, a statement of which vectors were re-run, findings on the P0–P3 ladder,
and concrete text proposals; and it holds that *a finding is a reproduction, not
an opinion*. This review states no verified-vectors line, runs nothing, and is
organised as strengths / weaknesses / recommendations. It is filed because it is a
reading of the published artifact worth keeping, not because it meets that bar.
Several of its factual claims — about `native_decide` usage, the deposit's version
label, and what the bridge checks cover — are recorded as written and have not
been checked against the tree.

---

## Загальна оцінка

Це **незвичайна стаття**, яка намагається зробити щось рідкісне: поєднати формальну верифікацію (Lean 4), інженерну практику (три незалежні імплементації), та епістемологічну чесність про те, що *не* доведено. Автор (Serhii Glova / s0fractal) явно намагається вирішити проблему довіри до артефактів доказів у епоху AI-generated code.

## Сильні сторони

### 1. Елегантність єдиного метричного простору (ATP)

Ідея, що **один беззнаковий integer** може цінувати одночасно і роботу (work), і пікову пам'ять (peak memory), математично красива. Це не просто оптимізація — це **онтологічне спрощення**. Більшість систем мають окремі лічильники для CPU cycles, memory allocations, stack depth, тощо, що створює проблему агрегування. ATP вирішує це радикально.

**Теорема `size ≤ atp + 1`** — це сильна гарантія: на кожному кроці виконання розмір терму обмежений бюджетом. Це означає, що: немає OOM (Out of Memory) surprises; немає нескінченних циклів (якщо ATP обмежений); виконання є **детермінованим і тотальним**.

### 2. Шарування до байтів

Більшість формальних верифікацій працюють на абстрактних моделях, які потім "компілюються" в реальний код з надією, що компілятор збереже властивості. Σ-GLYPH йде іншим шляхом: SHA-256 реалізований **з нуля** в core Lean (FIPS 180-4); ін'єктивність серіалізації доведена; канонічність round-trip доведена; **redex recognition by hash** є *виведеним*, а не аксіоматизованим.

Це означає, що довіра до Lean kernel є **єдиною точкою довіри**, а не компілятор, рантайм, чи бібліотеки.

### 3. Методологічна чесність: "21 bypass"

Це, мабуть, **найцінніша частина статті**. Автор відкрито описує, як CI-механізм, який мав би гарантувати, що теореми доведені і спираються на правильні аксіоми, був **переможений 21 раз**:

| Bypass | Опис |
|--------|------|
| `sorryAx` | Теорема з `sorry` проходила як доведена |
| String literal bypass | Коментар-стриппер осліпнув на рядковому літералі |
| `#print axioms` override | Аудитований модуль сам перевизначив команду |
| Vacuous theorems | Теореми, які істинні, але нічого не стверджують |
| Definition gutting | Визначення змінене, але ім'я залишилось тим самим |
| Non-recursive file walk | Аудит не заходив у підкаталоги |

Це **не просто баги** — це систематична демонстрація того, що **контроль, чий scope обирається тим, що він контролює**, є фундаментально ненадійним (§5 thesis). Це глибокий інсайт про **мета-верифікацію**.

### 4. Три незалежні імплементації

Python, Rust, Go (`warrant-go`) — всі три погоджуються на **49 conformance vectors** byte-for-byte. Це не просто тестування — це **диференціальна верифікація**.

### 5. AI authorship disclosure

Автор явно вказує: *"The Lean formalizations, the reference implementations and much of the prose were written by AI models under the author's direction"*. Це **радикально чесна позиція** для 2026 року. Більшість статей приховують або мінімізують роль AI. Тут же є **per-model review ledger** в `reviews/`.

## Критика та слабкі сторони

### 1. Проблема "Proof vs. Practice Gap"

Стаття стверджує, що Lean модель доводить властивості **реального hash-thunk евалюатора**. Але є тонкий gap:

```
Lean model → Compiled Lean code → Reference oracle → Production implementation
```

Диференціальні мости (`bridge_check.py`) перевіряють відповідність між скомпільованою Lean моделлю, reference oracle (Python) та production binaries (Rust, Go). Але **хто гарантує, що compiled Lean code зберігає властивості доведені в Lean source?** Lean 4 має `native_decide`, `#eval`, та інші механізми, які можуть відрізнятись від pure kernel semantics. Стаття згадує, що `native_decide` обмежений 10 теоремами, але не деталізує, як саме verified compilation gap закривається.

**Критика**: Доведення в Lean ≠ доведення про скомпільований код. Це відомий problem в спільноті (див. CompCert, CakeML). Без verified compiler або extraction proof, gap залишається.

### 2. ATP як єдина метрика: надмірне спрощення?

- **Робота vs. Пам'ять**: Чи завжди вони лінійно залежні? Рекурсивні алгоритми можуть мати O(n) work але O(log n) memory (tail recursion), або O(n) memory але O(1) work (lazy evaluation). ATP примусово лінеаризує це.
- **Cache effects, I/O, network**: ATP не враховує latency, cache misses, disk seeks.
- **Амортизована складність**: Деякі операції дорогі, але рідкісні. ATP може over-charge або under-charge.

**Критика**: ATP працює для **чистих комбінаторних обчислень** (SKI calculus), але не очевидно, що це generalize-иться на реальні системи з side effects, I/O, concurrency.

### 3. 21 bypass: вражаюче, але чи достатньо?

**Це не вичерпний перелік** — лише те, що знайшли за 6 раундів. **Хто перевіряв checker?** Якщо CI-механізм був настільки вразливим, хто гарантує, що **зараз** він правильний? Стаття каже "six internal hardening rounds and five external reviews", але це все ще **self-reported**. **Lean kernel trust**: весь цей elaborate CI machinery припускає, що Lean kernel правильний, а він має ~10k рядків C++.

**Критика**: Стаття демонструє проблему мета-верифікації, але не вирішує її повністю.

### 4. Відсутність performance benchmarks

Скільки часу займає evaluation 1000 термів? Як ATP overhead порівняно з native execution? Який memory footprint Lean runtime vs. Rust implementation? Для системи, яка претендує на practical use, performance критичний.

### 5. AI authorship: double-edged sword

- **Reproducibility**: якщо AI моделі змінюються, чи можна відтворити proof development process?
- **Auditability**: чи можуть люди зрозуміти *чому* AI обрала саме таку стратегію доведення?
- **Trust**: якщо 80% коду написане AI, хто несе відповідальність за помилки?

### 6. Limited scope: тільки SKI calculus

Чи generalize-иться це на **Turing-complete мови** з mutable state, exceptions, concurrency? Чи працює для **real-world programs**? Чи можна інтегрувати в існуючі системи (Wasm, blockchain smart contracts)?

## Методологічні зауваження

1. **Preprint status** — опубліковано на Zenodo як preprint (Version 0.6.7-paper1), не peer-reviewed.
2. **Single author** — Serhii Glova єдиний автор; для системи, яка претендує на "three independent implementations", це виглядає як **centralization risk**.
3. **Repository-centric publication** — сучасний підхід (executable paper), але припускає, що repo залишиться доступним і незмінним.

## Філософські питання

### 1. Чи вирішує це проблему довіри?

*"A claim that arrives with a check attached is worth exactly as much as your ability to run the check yourself"*. Але більшість людей **не можуть** запустити Lean 4 proofs, **не розуміють** SHA-256 at byte level, і **довіряють** експертам. Σ-GLYPH робить verification **можливою**, але не **practical** для більшості.

### 2. Чи це "trustless" або "trust-shifted"?

Насправді довіра **переміщується**: від "trust the author" → "trust the Lean kernel"; від "trust the compiler" → "trust the SHA-256 implementation"; від "trust the runtime" → "trust the CI machinery". Це **trust minimization**, не **trust elimination**.

## Порівняння з існуючими підходами

| Підхід | Переваги | Недоліки | Σ-GLYPH порівняно |
|--------|----------|----------|-------------------|
| **CompCert** | Доведена correctness компілятора | Тільки C, великий TCB | Σ-GLYPH менший scope, але більш end-to-end |
| **CakeML** | Full language verification | Дуже складний, повільний | Σ-GLYPH простіший, швидший, але обмежений |
| **Wasm** | Widely adopted, practical | Не verified, runtime bugs possible | Σ-GLYPH більш формальний, але менш practical |
| **Blockchain smart contracts** | Deterministic, auditable | Gas models ad-hoc, no memory bounds | Σ-GLYPH більш rigorous, але не deployed |

## Рекомендації для покращення

1. Додати verified compilation proof.
2. Performance benchmarks.
3. Generalization roadmap.
4. Third-party audit.
5. Formal peer review (POPL, ICFP, JAR).

## Висновок

**Σ-GLYPH Book I** — це **вражаюча робота**: елегантне рішення проблеми resource bounding (ATP), глибоке розуміння мета-верифікації (21 bypass), радикальна чесність про обмеження та AI authorship, practical multi-implementation validation.

Але це також **обмежена робота**: вузький домен (SKI calculus), проблема довіри лише trust-shifted, немає performance data, лишаються gaps (verified compilation, broader applicability).

**Для академічної спільноти**: сильний preprint, але потребує peer review та розширення scope.
**Для практиків**: цікавий proof-of-concept, ще не ready для production.
**Для філософів**: глибокий експеримент в епістемології довіри в епоху AI, який ставить більше питань, ніж дає відповідей — і це, мабуть, його найбільша цінність.
