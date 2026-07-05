# Σ-GLYPH — Book I: TRUTH

**Version:** 0.4.3
**Type:** Bit-Exact Computational Core
**Status:** DRAFT STANDARD
**Scope:** Цей документ визначає все — і лише те — що необхідно двом незалежним нодам для консенсусу щодо хеша результату обчислення. Все інше (навігація, координати, лор) — в окремих документах, які MUST NOT впливати на цю Книгу.

Ключові слова MUST / MUST NOT / SHOULD / MAY — за RFC 2119.

---

## 1. Структури

### 1.1. SigmaNodeV2

```text
enum OpCode : uint8 { LITERAL=0x00, REF=0x01, APPLY=0x02, DISSONANCE=0xFF }
// 0x03 та всі інші значення: INVALID (див. §1.2)
// Flags: F_ATOM=0x01, F_LEFT=0x02, F_RIGHT=0x04
```

| OpCode     | Flags (MUST equal)  | Semantics                         |
| ---------- | ------------------- | --------------------------------- |
| LITERAL    | `F_ATOM`            | `atom = SHA-256(DataBLOB)`        |
| REF        | `F_ATOM`            | `atom = TargetHash`               |
| APPLY      | `F_LEFT \| F_RIGHT` | `left = Fn`, `right = Arg`        |
| DISSONANCE | `F_ATOM`            | `atom = ReasonHash`               |

Біти `Flags` поза маскою `0x07` MUST be zero.

**LITERAL — інертний commitment.** Канонічний вузол містить digest, не blob. Для редукції blob не потрібен ніколи: LITERAL — нормальна форма, комбінатори розпізнаються за NodeHash (§3.2). Отримання та валідація blob (`SHA-256(blob) == atom` MUST) — контракт сховища поза цією Книгою.

Нормативна поведінка `resolve(h)` для LITERAL: fetch blob, валідувати `SHA-256(blob) == atom`, і якщо валідація невдала — матеріалізувати Canonical Invalid Object (§4.2). Реалізації MAY валідувати eagerly при зберіганні або кешувати валідовані blobs, але зовнішньо спостережувана поведінка `eval()` MUST бути ідентичною до on-demand validation.

### 1.2. Невалідні опкоди та формат-версіонування

Будь-який опкод поза таблицею §1.1 (включно з `0x03`) робить буфер невалідним (§4). Розширення формату вузла в content-addressed системі є rehash за побудовою: канонічні байти є ідентичністю, тому "version bit" не забезпечив би сумісності хешів. Нормативна деградація для майбутніх форматів: валідатор V2, зустрівши невідомі байти, MUST детерміновано матеріалізувати Canonical Invalid Object (§4.2) — ніколи UB. `0xFF` для DISSONANCE обрано як sentinel, максимально віддалений від блоку даних-опкодів.

## 2. Канонічна Серіалізація та Хеш

* **Layout:** `[Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]`; опціональні поля строго в порядку Atom, Left, Right; `F_ATOM→Atom`, `F_LEFT→Left`, `F_RIGHT→Right`.
* **NodeHash = SHA-256(CanonicalBytes)**; внутрішньо 32 raw bytes; hex — presentation only.

## 3. Семантика Редукції

### 3.1. Правила (SKI Term Rewriting)

`⟨X⟩` — вузол, чий NodeHash дорівнює канонічній константі X (§5).

```text
R-I:  APPLY(⟨I⟩, x)                    →  x
R-K:  APPLY(APPLY(⟨K⟩, x), y)          →  x
R-S:  APPLY(APPLY(APPLY(⟨S⟩,x),y), z)  →  APPLY(APPLY(x,z), APPLY(y,z))
R-R:  REF(h)                           →  resolve(h)
```

**R-R розгортає рівно один рівень за крок (MUST).** Ланцюг `REF→REF→…→T` довжини n коштує n кроків (n ATP). Якщо після витрати бюджету терм не в нормальній формі — результат `DISSONANCE(ATP Exhausted)`, незалежно від того, скільки рівнів REF лишилося. Транзитивне розгортання в один крок заборонене.

### 3.2. Розпізнавання комбінаторів (MUST)

Вузол є I/K/S тоді й лише тоді, коли його NodeHash дорівнює відповідній константі §5.1. Identity by Hash.

### 3.3. Порядок редукції (MUST)

Normal order, leftmost-outermost. На кожному кроці — єдиний редекс:

```text
step(t):
  if t = REF(h):                           fire R-R
  elif t matches R-I|R-K|R-S at root:      fire that rule
  elif t = APPLY(f,a):
      if step(f) exists: reduce in f
      elif step(a) exists: reduce in a
      else: none                            // normal form
  else: none                                // LITERAL, DISSONANCE
```

### 3.4. ATP (MUST)

* Кожне спрацювання R-I/R-K/R-S/R-R коштує рівно 1 ATP.
* `eval(term_hash, atp: uint32)` → нормальна форма | `DISSONANCE(ATP Exhausted)` | `DISSONANCE(Unresolved Reference)`. Усі три — канонічні, детерміновані, однакові на всіх нодах.
* ATP-бюджет — `uint32` (діапазон 0..2³²−1). Для викликів з ATP > 2³²−1 поведінка implementation-defined: реалізація MAY відхилити виклик або clamp'нути бюджет — це локальний API-контракт, не консенсус. Консенсус-критичними є лише канонічні результати цього параграфа; вони не залежать від ширини цілого, якою реалізація представляє бюджет. (Знахідка: Claude Sonnet 4.5 review, 2026-07.)
* Нормативна модель обліку — **tree semantics**. Graph reduction зі спільними підтермами MAY застосовуватись, але спостережуваний результат і звітований ATP MUST збігатися з tree semantics (конформанс: TV-6).
* Результат — вузол; його NodeHash — канонічна адреса результату: `result_hash = eval(term_hash, atp)`.

### 3.5. Resolution Contract (MUST)

`resolve(h)` — єдина операція отримання вузла за хешем: для кореня, для R-R, для дітей APPLY при пошуку редекса. Два режими відмови розрізняються явно: (a) `resolve(h)` не може знайти `h` у сховищі → `DISSONANCE(Unresolved Reference)`; (b) `resolve(h)` повертає байти, що не проходять валідацію §4.1 → матеріалізується Canonical Invalid Object (§4.2).

### 3.6. Канонічні відмови vs локальні faults (MUST)

Канонічні результати — лише три з §3.4. Порушення локальних ресурсних лімітів реалізації (глибина, кількість матеріалізованих вузлів, кількість fetch, розміри) — **implementation fault**: відмова виконання, яка MUST NOT серіалізуватися як DISSONANCE. Мотивація: R-S подвоює підтерм за 1 ATP, розмір росте до O(2^ATP); ATP обмежує роботу, не пам'ять. Конкретні ліміти та їх значення — поза цією Книгою (implementation notes).

### 3.7. Tooling (MAY, non-consensus)

Інтерфейси на кшталт `trace_eval` (покрокова траса, проміжні терми, checkpointing) MAY існувати; вони не є частиною консенсусу і MUST NOT змінювати результати `eval`.

## 4. Валідація

### 4.1. Десеріалізація (MUST)

1. `len >= 2`; read `[Op][Flags]`.
2. `Flags & ~0x07 == 0`; OpCode ∈ таблиці §1.1; `Flags` точно дорівнює нормативному значенню.
3. `expected_len = 2 + 32·popcount(Flags & 0x07)`; `len == expected_len`.
4. Будь-яка помилка → Canonical Invalid Object.

### 4.2. Canonical Invalid Object (MUST)

```text
ff01 || SHA-256("Invalid Object")
Bytes: ff017cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8
Hash:  af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507
```

## 5. Genesis

### 5.1. Аксіоми (номінальні)

| Glyph | CanonicalBytes            | NodeHash |
| ----- | ------------------------- | -------- |
| I | `0001`+SHA-256("I") | `2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162` |
| K | `0001`+SHA-256("K") | `bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c` |
| S | `0001`+SHA-256("S") | `887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6` |

Повні 32-байтні значення SHA-256("I"/"K"/"S") — в `impl/sigma_glyph.py` (TV-1); тут вони навмисно не дублюються, щоб не створювати друге джерело істини.

### 5.2. Перша теорема

`FALSE ≡ APPLY(K,I)`; Bytes `0206‖H(K)‖H(I)`; Hash `65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098`.

### 5.3. Reason Hashes (MUST)

```text
SHA-256("Invalid Object")       = 7cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8
SHA-256("ATP Exhausted")        = dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090
SHA-256("Unresolved Reference") = 75daae55453d9a98bfadb847d70b73fdd0be91d3b6ef8511d22fc42aa2c7c8e2
```

**Reserved (Era-1 legacy):** `SHA-256("Signal Damped") = 7dc48fe882dc426083223e5fb26889ace68aa8f54abd4e37690b72327b87748c`. Це зарезервований *reason hash*, не опкод; не впливає на десеріалізацію. Жодне правило V2 не породжує цей DISSONANCE; хеш зарезервовано для можливого мережевого шару (damping) і MUST NOT використовуватись реалізаціями Книги I. (Знахідка: Qwen review, 2026-07.)

## 6. Canonical Lambda→SKI Compiler, Profile C1 (Normative Annex)

Consensus layer приймає лише SKI-терми. Для міжлюдської сумісності визначено рівно один канонічний компілятор. Вхід — лямбда-терм без вільних змінних; вихід — SKI-терм Книги I.

**Вільні змінні (FV)** визначаються в звичайному capture-avoiding sense: `FV(x) = {x}`, `FV(M N) = FV(M) ∪ FV(N)`, `FV(λx.M) = FV(M) \ {x}`. Компілятор MUST NOT зв'язувати змінну, що вільна в її тілі.

```text
C1[x]        = x
C1[(M N)]    = APPLY(C1[M], C1[N])
C1[λx.M]     = A(x, C1[M])

A(x, x)      = ⟨I⟩
A(x, M)      = APPLY(⟨K⟩, M)                      якщо x ∉ FV(M)
A(x, (M N))  = APPLY(APPLY(⟨S⟩, A(x,M)), A(x,N))
```

* Правила A перевіряються строго в цьому порядку. η-редукція та будь-які інші оптимізації в профілі C1 **MUST NOT** застосовуватись.
* C1 детермінований: однаковий вхід → однакові байти → однаковий хеш на будь-якій реалізації.
* C1 **не** мінімізує і **не** канонізує екстенсіонально: `C1[λx.λy.x] = S(KK)I ≠ ⟨K⟩` — окремий громадянин, екстенсіонально рівний K. Розв'язної екстенсіональної рівності не існує (Rice); канонічність C1 — синтаксична, не семантична.
* Фронтенди з іншими профілями MAY існувати поза стандартом; їхні артефакти — звичайні SKI-громадяни без особливого статусу.

## 7. Test Vectors (MUST PASS)

**TV-1 (LITERAL I):** Bytes `0001a83dd0ccbffe39d071cc317ddf6e97f5c6b1c87af91919271f9fa140b0508c6c`; Hash `2f33694d…330f4162` (повний у §5.1).

**TV-2 (FALSE):** Bytes `0206‖H(K)‖H(I)`; Hash `65cd957f…38a32098`.

**TV-3 (DISSONANCE ATP):** Bytes `ff01dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090`; Hash `8bb0006f4c0a51a645877c10db80b7360b0d34f6f826e5737d0847f8b1493176`.

**TV-4 (I·K):** `APPLY(⟨I⟩,⟨K⟩)` hash `51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e`; `eval(·,1)=⟨K⟩`, 1 ATP; `eval(·,0)=DISSONANCE(ATP Exhausted)`.

**TV-5 (SKK·I):** hash `c9f57b3f594d7b72b0855b0d6fabba89e6ccdf6840c8f84aeb5fd4707300bbfc`; `eval(·,2)=⟨I⟩`, 2 ATP; проміжна форма кроку 1 = `APPLY(⟨FALSE⟩,⟨FALSE⟩)`, hash `b45355fc…4eaba133`.

**TV-6 (Duplication Stress):** `S I I (I·K)` hash `0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198`; нормальна форма `APPLY(⟨K⟩,⟨K⟩)`; рівно **5 ATP** tree (шаринг дав би 4; звіт MUST = 5).

**TV-7 (Omega):** `Ω = (SII)(SII)` hash `0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211`; `∀n: eval(Ω,n) = DISSONANCE(ATP Exhausted)`.

**TV-8 (Unresolved Child):** `APPLY(⟨I⟩, ghost)` при відсутньому ghost → `DISSONANCE(Unresolved Reference)`.

**TV-9 (REF chain):** store: `r1=REF(H(K))`, `r2=REF(r1)`; `eval(r2, 2)=⟨K⟩`, рівно 2 ATP; `eval(r2, 1)=DISSONANCE(ATP Exhausted)`.

**TV-10 (C1 compiler):** `C1[λx.x] = ⟨I⟩`. `C1[λx.λy.x] = APPLY(APPLY(⟨S⟩,APPLY(⟨K⟩,⟨K⟩)),⟨I⟩)`, hash `bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d`; `eval(APPLY(APPLY(C1[λxy.x],⟨S⟩),⟨K⟩), 16) = ⟨S⟩`.

**Негативні:** flags поза 0x07; невідповідність Flags опкоду; опкод 0x03; довжина ≠ expected — усе → Canonical Invalid Object.

## 8. Specification Anchor (Update Protocol)

Кожна опублікована версія цієї Книги закріплюється в самій системі: `SpecAnchor(v) = NodeHash(LITERAL, atom = SHA-256(document_bytes))`. Анкер за побудовою не може міститися в документі, який хешує; він публікується detached (ANCHORS file / genesis-реєстр). Зміна стандарту = новий LITERAL = новий анкер; "оновлення" — це завжди форк з явним предком, узгодження версій — за анкерами, не за назвами файлів.

---

*Ця Книга визначає, що істинне. Все тепле живе деінде.*
