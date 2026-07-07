# Σ-GLYPH — Book I: TRUTH

**Version:** 0.5.0
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

Книга I валідує лише канонічні байти SigmaNodeV2. `resolve(h)` для LITERAL не вимагає blob: матеріалізація завжди успішна (1 ATP), поки вузол десеріалізується коректно за §4.1. Відсутність, доступність чи пошкодження зовнішніх blob-даних, закомічених через `atom`, MUST NOT змінювати канонічний result hash, вид канонічної відмови чи витрачений ATP, які звітує `eval()`. Blob-retrieval API MAY валідувати `SHA-256(blob) == atom` і звітувати storage-рівневі відмови, але ці відмови — поза Книгою I і MUST NOT серіалізуватися як DISSONANCE Книги I. (ADR-004, гейт 4/≥3, 2026-07.)

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

**R-R розгортає рівно один рівень за крок (MUST).** Транзитивне розгортання в один крок заборонене. Під тарифікацією v0.5 (§3.4) ланцюг `REF→REF→…→T` довжини n коштує n·(2+1) = 3n ATP: force кожного REF-вузла (2) + його розгортання (1); конформанс: вектор `EV-TV9`. Якщо бюджету не стає — `DISSONANCE(ATP Exhausted)`, незалежно від того, скільки рівнів лишилося.

### 3.2. Розпізнавання комбінаторів (MUST)

Вузол є I/K/S тоді й лише тоді, коли його NodeHash дорівнює відповідній константі §5.1. Identity by Hash.

### 3.3. Машина хеш-товків та порядок редукції (MUST)

Абстрактна машина v0.5 оперує **хеш-товками** (hash thunks): терм у процесі редукції — граф матеріалізованих вузлів, чиї діти — або матеріалізовані вузли, або нерозв'язані хеші (товки). Товк порівнюється з ⟨I⟩/⟨K⟩/⟨S⟩ за хешем без матеріалізації; товк матеріалізується лише коли його вимагає leftmost-outermost пошук. Кожна дія машини — спрацювання правила АБО матеріалізація одного вузла — тарифікується (§3.4).

```text
step(t):                                            // одна тарифікована дія
  if t = thunk(h):
      if h ∈ {H(I),H(K),H(S)}: none                 // NF-лист за хешем, §5.1
      else: force(h)                                // матеріалізація одного вузла
  elif t = REF(h):                fire R-R          // → thunk(h), один рівень
  elif t matches R-I|R-K|R-S at root: fire          // патерни — порівняння хешів,
                                                    // аргументи НЕ форсуються
  elif t = APPLY(f,a):
      if step(f) exists: act in f                   // спуск лівим хребтом
      elif step(a) exists: act in a                 // f нормальний → вимога a
      else: none                                    // normal form
  else: none                                        // LITERAL, DISSONANCE
```

**Клас розбіжностей закрито нормативно:** нерозв'язане піддерево, яке leftmost-outermost редукція не вимагає — включно з deadness, що з'являється лише після переписувань — MUST NOT впливати на результат. `APPLY(APPLY(⟨K⟩, x), missing)` → `x`, а не Unresolved Reference; `S (K I) (K K) missing` → ⟨K⟩. (ADR-003; знахідки Codex + Gemini + DeepSeek, 2026-07.)

### 3.4. ATP: size-priced, hash-leaf model (MUST)

**Розмір** (hash-leaf model): кожен матеріалізований вузол рахується як 1; нерозв'язаний хеш-лист рахується **рівно 1** незалежно від того, що він позначає; матеріалізований REF рахується 2 (вузол + товк цілі); `size(APPLY) = 1 + size(лівого) + size(правого)`.

**Ціни дій:**

```text
cost(force h)  = size(матеріалізованого вузла з товк-дітьми)
                 = 1 (LITERAL, DISSONANCE) | 2 (REF) | 3 (APPLY)
cost(R-R)      = 1        // REF-вузол → товк цілі, один рівень за крок
cost(R-I)      = 1
cost(R-K)      = 1        // відкинутий аргумент НЕ форсується і НЕ тарифікується
cost(R-S)      = 1 + size(z)   // z у поточній матеріалізації; товки в z = 1, не форсуються
```

* `eval(term_hash, atp: uint32)` → нормальна форма | `DISSONANCE(ATP Exhausted)` | `DISSONANCE(Unresolved Reference)`. Усі три — канонічні, детерміновані, однакові на всіх нодах. Результат — вузол; його NodeHash — канонічна адреса результату.
* ATP-бюджет — `uint32`; ATP > 2³²−1 — implementation-defined (MAY відхилити/clamp); консенсус-критичні лише канонічні результати. Окремий крок із ціною понад 2³²−1 недоступний для будь-якого канонічного бюджету → ATP Exhausted, не implementation-defined.
* **Перевірка вичерпання передує дії.** Дія з ціною `c > atp − spent` не виконується: результат `DISSONANCE(ATP Exhausted)` зі `spent` без змін. Мінімальна ціна будь-якої дії — 1, тому при `spent == atp` вичерпання вирішується **до** будь-якого звернення до сховища (`eval(REF(missing), 0)` = ATP Exhausted). Якщо ціна force стає відомою лише після отримання байтів (вид вузла), недоступні за бюджетом байти відкидаються без матеріалізації — детерміновано. Невдала дія (відмова resolve) не тарифікується. `eval` тотальний: жодна внутрішня відмова MUST NOT покидати `eval` інакше, ніж канонічним `DISSONANCE`. (Дисципліна v0.4.5, успадкована зі змінними цінами.)
* **Семантична межа пам'яті (теорема, нормативний інваріант):** уздовж будь-якого виконання `materialized_size(t) − 1 ≤ spent`. Кожна дія коштує строго більше, ніж додає розміру. Реалізація MAY використовувати це для безкоштовного size-guard. (ADR-001 + композиція ADR-003, hash-leaf model; доказ: Gemini review; незалежна передеривація: DeepSeek review, 2026-07.)
* Нормативна модель обліку — tree semantics над матеріалізованим графом: шаринг MAY застосовуватись у виконанні, але звітований ATP MUST збігатися з tree-обліком.

### 3.5. Resolution Contract (MUST)

`resolve(h)`/`force(h)` — єдина операція матеріалізації вузла за хешем. Два режими відмови розрізняються явно: (a) `h` не знаходиться у сховищі **і не є intrinsic-аксіомою §5.1** → `DISSONANCE(Unresolved Reference)`; (b) байти не проходять валідацію §4.1 → матеріалізується Canonical Invalid Object (§4.2), дія тарифікується як force вузла DISSONANCE (1).

**Матеріалізація — лінива, за вимогою пошуку (нормативно з v0.5).** Форсується лише товк, що його вимагає leftmost-outermost пошук: лівий хребет для розпізнавання редексів, аргумент — лише коли функціональна частина нормальна. Мертві гілки не форсуються ніколи (§3.3). Історична довідка: у 0.4.x нормативною була eager-матеріалізація; зміна результатів для термів із мертвими відсутніми гілками — свідомий breaking change v0.5 (ADR-003).

### 3.6. Канонічні відмови vs локальні faults (MUST)

Канонічні результати — лише три з §3.4. Порушення локальних ресурсних лімітів реалізації (глибина, кількість fetch) — **implementation fault**: відмова виконання, яка MUST NOT серіалізуватися як DISSONANCE. З v0.5 пам'ять обмежена семантично (§3.4: розмір ≤ 1 + spent), тож size-фолти досяжні лише за бюджетів порядку ліміту; guards лишаються другим парканом. Конкретні ліміти — поза цією Книгою (implementation notes).

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

**Genesis intrinsic (MUST, з v0.5).** Три аксіоми I, K, S — intrinsic-константи: конформна реалізація MUST обслуговувати `resolve/force` їхніх канонічних хешів без залежності від наявності цих байтів у сховищі — байти задані цим параграфом, синтез детермінований. `DISSONANCE(Unresolved Reference)` для H(I)/H(K)/H(S) MUST NOT виникати. Товк із intrinsic-хешем — нормальна форма без матеріалізації (§3.3). FALSE (§5.2) — теорема, не аксіома: intrinsic-статусу не потребує, її байти конструюються з H(K), H(I) без сховища. (Кандидатура: Codex + Gemini; підтвердження без розбіжностей: DeepSeek, 2026-07.)

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

Ціни нижче — v0.5 (size-priced, hash-leaf, §3.4). Вичерпний машинний набір — `tests/spec_conformance/vectors.json` (нормативний; при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`).

**TV-4 (I·K):** `APPLY(⟨I⟩,⟨K⟩)` hash `51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e`; `eval(·,4)=⟨K⟩`, **4 ATP** (force кореня 3 + R-I 1); `eval(·,0)` = ATP Exhausted, spent 0 — без жодного звернення до сховища; `eval(·,2)` = ATP Exhausted, spent 0 — байти кореня відкинуті (force коштує 3 > 2); `eval(·,3)` = ATP Exhausted, spent 3.

**TV-5 (SKK·I):** hash `c9f57b3f594d7b72b0855b0d6fabba89e6ccdf6840c8f84aeb5fd4707300bbfc`; `eval(·,12)=⟨I⟩`, **12 ATP** (3 force по 3 + R-S 2 + R-K 1).

**TV-6 (Duplication Stress):** `S I I (I·K)` hash `0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198`; нормальна форма `APPLY(⟨K⟩,⟨K⟩)`; рівно **21 ATP**; уздовж виконання `size − 1 ≤ spent` (семантична межа пам'яті, §3.4).

**TV-7 (Omega):** `Ω = (SII)(SII)` hash `0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211`; `∀n: eval(Ω,n) = DISSONANCE(ATP Exhausted)`.

**TV-8 (Unresolved Child):** `APPLY(⟨I⟩, ghost)` при відсутньому ghost → `DISSONANCE(Unresolved Reference)`, spent 4: R-I спрацьовує ліниво БЕЗ форсування ghost, потім ghost стає вимаганим коренем і не форсується.

**TV-9 (REF chain):** store: `r1=REF(H(K))`, `r2=REF(r1)`; `eval(r2, 6)=⟨K⟩`, рівно **6 ATP** (2 force по 2 + 2 R-R по 1); `eval(r2, 1)` = ATP Exhausted, spent 0 (force коштує 2).

**TV-10 (C1 compiler):** `C1[λx.x] = ⟨I⟩`. `C1[λx.λy.x] = APPLY(APPLY(⟨S⟩,APPLY(⟨K⟩,⟨K⟩)),⟨I⟩)`, hash `bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d`; `eval(APPLY(APPLY(C1[λxy.x],⟨S⟩),⟨K⟩), 20) = ⟨S⟩`, 20 ATP.

**TV-11 (Divergence class, v0.5):** ghost = SHA-256(ASCII `this node was never stored`), відсутній у сховищі. `APPLY(⟨FALSE⟩, ghost)` (= `(K I) ghost`) → ⟨I⟩, 7 ATP; `APPLY(S (K I) (K K), ghost)` → ⟨K⟩, 20 ATP. У 0.4.x обидва давали Unresolved Reference — це свідомий breaking change (ADR-003).

**TV-12 (Genesis intrinsic, v0.5):** `REF(H(K))` на **порожньому** сховищі → ⟨K⟩, 3 ATP. Голий intrinsic-товк: `eval(H(I), n)` = ⟨I⟩, 0 ATP, сховище не потрібне.

**Негативні:** flags поза 0x07; невідповідність Flags опкоду; опкод 0x03; довжина ≠ expected — усе → Canonical Invalid Object.

## 8. Specification Anchor (Update Protocol)

Кожна опублікована версія цієї Книги закріплюється в самій системі: `SpecAnchor(v) = NodeHash(LITERAL, atom = SHA-256(document_bytes))`. Анкер за побудовою не може міститися в документі, який хешує; він публікується detached (ANCHORS file / genesis-реєстр). Зміна стандарту = новий LITERAL = новий анкер; "оновлення" — це завжди форк з явним предком, узгодження версій — за анкерами, не за назвами файлів.

---

*Ця Книга визначає, що істинне. Все тепле живе деінде.*
