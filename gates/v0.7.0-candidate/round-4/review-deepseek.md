<!--
family: deepseek
model_requested: deepseek/deepseek-v4-pro-0813
model_answered: deepseek/deepseek-v4-pro-0813
requested_utc: 2026-08-29T19:06:24+00:00
answered_utc: 2026-08-29T19:11:14+00:00
finish_reason: stop
attempt: 1
max_tokens: 24000
prompt_sha256: 7711812198a43d715082c7fd1671d6558dd8a7c79d38aa7f86932f95780e2248
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: e2b4f1eb2a0a7cff0fc2f42b39541c42873118a0
response_sha256: 01405ee08ae23f4944909fddf63ece53929e073893669374e3183640a7ad5360
verdict: ADOPT-WITH-AMENDMENTS
-->

I'll review this candidate revision systematically. Let me work through the normative claims and check them against the actual text.

## Review of v0.7.0 candidate

### The change's core structure

The candidate makes one substantive semantic change to Book I (the three-input `eval` interface with `Receipt`, the content environment contract, admission boundary, and domain rejection), plus a meta-change to all three Books (vector suite becomes normative, no oracle precedence). Books II and III receive only the meta-change.

Let me examine each modified normative claim.

---

### Book I §3.4 interface change

**Claim:** `eval(term_hash, atp: uint32, env)` → `Receipt`, with `Receipt = { exit, result_hash, atp_spent }`.

**Bulk of the change is internally consistent.** The `Receipt` structure is defined. `result_hash` is stated not to determine `exit` — this is correct and important. The example given in ADR-010 is sound: a `DISSONANCE(ATP Exhausted)` node can itself sit in the environment, be forced as a normal term, and yield `normal_form` for the same hash.

**The compatibility profile is stated as MAY.** This is fine — it's a permissive relaxation, not a normative requirement.

---

### Book I §3.5: Content environment — P0 candidate

Let me look closely at the demand-scoped CAS check.

The candidate says (Book I §3.5):

> Байти під ключем, у який вони не хешуються, **MUST NOT** виконуватися як вузол цього ключа...
> Властивість MUST перевірятися для кожного хеша, який виконання фактично розв'язує, і виявлена невідповідність на розв'язаному хеші MUST давати локальну відмову (§3.6), а не канонічний результат.

And:

> Запис, якого виконання не вимагало, **MUST NOT** змінювати жоден канонічний `Receipt`: за однакових відповідей на вимагані хеші дві конформні реалізації повертають той самий `Receipt`, хоч би що ще лежало в середовищі.

Then:

> Це не забороняє верифікаторові не допустити середовище з власних причин — зокрема перевіривши його ширше, ніж вимагає виконання. Такий крок є **допуском** (§3.6), а не обчисленням: він не дає жодного `Receipt`, тож і розходитися немає в чому, і подавати його як результат обчислення MUST NOT.

**This resolves DeepSeek's round-2 P0.** The distinction between "an entry the evaluation demanded" (mismatch → local refusal) and "an entry the evaluation never demanded" (no effect on any Receipt) is now clear. The wider check is explicitly reclassified as admission, not evaluation. A verifier exercising admission produces no Receipt, so there is no divergence between two conforming `eval` calls.

**But now there's an ambiguity worth checking:** what is a "вимаганий" (demanded) hash? The text relies on this term in three normative statements:
1. The CAS property MUST be checked for every hash the evaluation "фактично розв'язує" (actually resolves).
2. A mismatch on a "розв'язаному" hash → local refusal.
3. Determinism is over "the same demanded hashes resolved to the same bytes."

Is "demanded" the same as "resolved"? Consider the sequence in §3.3: the machine may consult the environment for a hash, fetch its bytes, then discover (after deserialization) that the node kind makes the force unaffordable under the budget, and discard the bytes without materialization (§3.4: "недоступні за бюджетом байти відкидаються без матеріалізації").

**Concrete problem**: Suppose `h` is demanded (the search needs to know its kind), the environment returns bytes for `h`, but the bytes fail `SHA-256(bytes) = h`. Is `h` "resolved"? Did the evaluation "actually resolve" it? The force cannot proceed — but the check is non-canonical to begin with (the text says "the second question has no canonical answer at all").

But more importantly, the CAS check must occur before the buffer is deserialized, because deserializing a foreign-key buffer as if it were `h`'s node is exactly what's forbidden. So the check must happen at the moment the environment is consulted for `h`, regardless of whether the buffer is subsequently discarded for budgetary reasons. The text does say "Перевірка йде над **сирим буфером і до валідації §4.1**" — the check is over the raw buffer. This is correct.

**However, is there a P1 here about when the check happens relative to budget?** §3.4 says when `spent == atp`, exhaustion is decided **before** any access to storage. So there is no access. But what if `atp - spent > 0` but the force price (which depends on node kind, which depends on deserializing the bytes) exceeds the remaining budget? The bytes must be fetched from the environment, the CAS check applied, and only then can the node kind be known. §3.4 handles this: "Якщо ціна force стає відомою лише після отримання байтів (вид вузла), недоступні за бюджетом байти відкидаються без матеріалізації — детерміновано."

So the CAS check on a demanded-but-then-discarded hash would be a demand-scoped check that produces a local refusal. That's consistent: the evaluation consulted the environment, the bytes are wrong, and the verifier refuses locally. No divergence, because the refusal is local and non-canonical.

**What about intrinsic hashes?** §5.1 says `resolve/force` of H(I)/H(K)/H(S) MUST be served without depending on the presence of those bytes in storage. The §3.5 content environment check says "the property MUST be checked for every hash the evaluation actually resolves." If the environment contains an entry under H(K) with bytes that hash to something else, and the evaluation demands H(K) — does the intrinsic path short-circuit the CAS check? The intrinsic axiom says the conforming implementation MUST serve these hashes without depending on the presence of bytes in storage. The bytes are synthesized deterministically (§5.1). So if the environment has a poisoned entry for H(K), and the machine demands H(K), the implementation serves the synthesized bytes (which do hash to H(K)) and never consults the environment for that hash. Is that an "actual resolution" of H(K)? It's a materialization/force of H(K), but it doesn't query `env`. The CAS property is about `env` entries, not about intrinsic synthesis. This seems consistent, though the text would benefit from stating the interaction explicitly. I'll flag this as P2, not P1 — the scope of "розв'язує" is `resolve`/`force(h)`, and §3.5 names those as the single materialization operation. An intrinsic thunk is materialized via those same operations. But the normative requirement says a conforming implementation "MUST обслуговувати resolve/force" of intrinsic hashes "без залежності від наявності цих байтів у сховищі" — "without depending on the presence of those bytes in storage." This is compatible: the implementation serves the bytes regardless of whether env has them. If env has a poisoned entry under H(K), the intrinsic rule means the implementation doesn't need to look at env, so the poisoned entry is never "actually resolved" from env. No contradiction.

**P2**: The text could state explicitly that intrinsic axioms (§5.1) are served by synthesis (§5.1) and are not subject to the content-environment CAS property. This is derivable but not stated.

---

### The "no canonical answer" sentence — round-2 DeepSeek's confusion

§3.5 says: «питання "чи це валідний вузол" і питання "чи ці байти належать цьому ключу" — різні... перше має канонічну відповідь, друге канонічної відповіді не має взагалі.»

This is confusing because SHA-256 is a deterministic function. Whether `SHA-256(bytes) = key` is a true-or-false arithmetic fact. What the text means is: the *effect* of a violation is not a canonical `Receipt` — it produces a local refusal, which is not one of the three canonical outcomes. The "answer" to the property question is a mathematical fact, but its *disposition* is local, not canonical. The candidate leaves this as written, and DeepSeek declined to raise it. The sentence does not mislead an implementer about what to do (the MUST clauses around it are unambiguous), so I treat this as P2 wording, not P1.

---

### Book I §3.6: domain rejection

The new §3.6:

> `atp`, що не є `uint32`, і `term_hash`, що не є рівно 32 байтами, MUST бути відхилені так само — локально, до звернення до середовища, і не як канонічний вихід.

And §3.4 now says an out-of-domain `atp` "не є бюджетом" and MUST be refused, with clamping explicitly forbidden.

The round-1 P0 (two MUST-level clauses in conflict about out-of-domain `atp`) is resolved. §3.4 no longer says MAY reject/clamp; it now forbids clamping by name and routes to §3.6's local refusal. Good.

But **there's a subtle issue**: §3.4 also retains this sentence: "Консенсус-критичні лише канонічні результати." — "Only canonical results are consensus-critical." And the exhaustion check paragraph says: "Окремий крок із ціною понад 2³²−1 недоступний для будь-якого канонічного бюджету → ATP Exhausted, не implementation-defined."

This is consistent: out-of-domain `atp` is not a canonical budget, so the sentence about unreachable per-step prices only applies to canonical budgets. Fine.

**But the compatibility profile interacts with this**: §3.4 says "Реалізація MAY надавати двозначну форму `eval(term_hash, atp, env) → (result_term, atp_spent)`." If an out-of-domain `atp` MUST be refused locally, does the two-value compatibility profile also refuse (raise) or does it maintain its old behavior? The candidate's own ADR-010 says: "before the 2026-08-29 audit, `atp = -1`, `1.5` and `True` were accepted. They now raise." The compatibility profile section says it "не втрачає жодної гарантії цієї Книги." Since a local refusal is not a guarantee but a MUST for the domain, does the compatibility form also refuse? The compatibility form is defined as `eval(term_hash, atp, env) → (result_term, atp_spent)`. Since the MAY profile is supposed to be compatible with the old two-value form, and the old form accepted out-of-domain budget... there's a potential mismatch. However, the compatibility form is explicitly a MAY — it loses no guarantee, meaning it must still honor the MUSTs of this Book. The MUSTs include refusing out-of-domain input. So a compatibility form that doesn't refuse would violate the Book. This is a P2 at most — implementers can read the MUST as binding on the compatibility form too. But it could be clearer. Actually, the §3.4 compatibility profile text says: "Вона не втрачає жодної гарантії цієї Книги" — it loses no guarantee of this Book. This says the compatibility form must still enforce all MUSTs. The refusal of out-of-domain input is a MUST. So the compatibility form MUST refuse too. Fine.

---

### The semantic memory bound — P2 on the "guards"

The §3.4 memory section says: "fault-guard за `spent` хибно валить дивергентні терми крихітного розміру (Ω); guard MUST міряти фактичний `size(t)`/глибину."

This is a normative MUST on internal guard implementation ("guard MUST міряти..."). But the Book elsewhere says concrete limits are outside this Book (implementation notes) and implementation faults are allowed. Can a MUST about internal guard discipline coexist with §3.6's statement that local resource limits are implementation-defined? This is pre-existing text, not introduced by this candidate (the diff only changed "преф лайт" to "префлайт"). The candidate scope says "the memory bound is a count of materialized nodes, and the word used for it in the paper's title is 'memory'" — and the candidate fixes the title and adds the MUST NOT about what the bound isn't. That addition is good.

But the existing sentence "guard MUST міряти фактичний `size(t)`/глибину" is a normative constraint on an *internal* component whose very existence is "another fence" outside the Book. Is that enforceable? A conforming implementation could have no guard at all (faults are allowed as implementation faults). If it has a guard, it MUST measure actual size/depth, not spent. This is a conditional MUST on a non-normative component. This is a pre-existing P2 — the candidate modifies the sentence's context (now under the new "what this bound is not" framing) but doesn't change this oddity. Since the candidate's addition says the physical-resources correspondence is a separate refinement layer the Book doesn't prove, the guard MUST about measuring actual `size(t)` sits oddly -- the guard is a physical-resource guard, and the Book has just said it doesn't prove anything about physical resources. But it's a conditional on a component the Book doesn't define. I'll note this as P2.

---

### §7 vector suite as normative — P0/P1?

The new §7 text:

> Вичерпний машинний набір `tests/spec_conformance/vectors.json` є нормативною частиною цього видання. Проза §7 і записи набору MUST бути взаємно узгодженими. Видання з розбіжністю між ними є неконформним і MUST NOT використовуватися як джерело консенсусу до виправлення та повторного анкерування. Жодна реалізація, включно з референсною, не має переваги над нормативними артефактами видання.

This removes the oracle precedence and makes the suite normative. The claim is that the suite and prose MUST agree. The question: are they actually checkable? The suite file is `tests/spec_conformance/vectors.json`, which is not in the diff and not included in my review. The candidate claims the suite was regenerated by generators and no expected value was edited by hand. But **I cannot verify the suite's contents** because the suite file is not part of the diff. The ADR-010 says the suite was "regenerated by its generator" and "every vector file is regenerated." Green CI cannot be treated as evidence per my instructions. Without the suite bytes, I cannot determine whether the prose and the suite actually agree. That is a review limitation, not necessarily a defect in the candidate.

**However, there's a structural P1 here**: the new §7 text says "нормативним представленням твердження прози в наборі є поля запису: предмет обчислення (`term` або `bytes`), бюджет (`atp`), канонічний вихід (`expected.outcome`), хеш результату (`expected.result_hash`) і витрачений ATP (`expected.atp_spent`)."

The prose of §7 also carries test vectors, e.g., TV-4 through TV-12. The same §7 paragraph says "Решта прози §7 пояснює правила, встановлені §3–§5... і не є самостійним нормативним твердженням цього параграфа; ті правила лишаються нормативними там, де вони встановлені."

This says the remainder of §7's prose (TV-4 through TV-12) is explanatory and not independently normative, but the record fields are. But the prose still prints specific ATP figures and hashes. If the suite's `expected.atp_spent` for TV-6 differs from the printed 21, the edition is non-conformant. That's the intended rule. Fine.

**A potential P1**: the field list says `expected.outcome`. What are the allowed values for `expected.outcome`? The prose of §7 uses "ATP Exhausted" and "Unresolved Reference" and `= ⟨X⟩` shorthand. The new notation paragraph maps these to `atp_exhausted`, `unresolved_reference`, and `normal_form` respectively. §3.4 `Receipt.exit` has exactly those three values. But the suite schema's `expected.outcome` field is not defined in the Book. The Book says the field is normative, but does not constrain its vocabulary. If the suite uses `"exhausted"` instead of `"atp_exhausted"`, is there a conflict? The Book defines the semantics of `exit` as exactly three values. Since the suite is normative and the Book doesn't define the JSON schema of `expected.outcome`, an implementer reading the suite alone must infer the mapping. The new notation paragraph gives the mapping — but that paragraph itself says it "adds no requirement" and the normative statements remain the record fields. If the record field itself uses a different vocabulary, the prose's mapping could be wrong while the record is "normative." **This is a P1**: the Book declares a field normative without pinning its domain, while simultaneously declaring the prose's mapping of that field's values normative. If the record field `expected.outcome` in `vectors.json` uses values not enumerated anywhere in the Book, and the prose's "notation" paragraph says what the prose shorthand means, there's a gap: the normative record's vocabulary is not pinned by the normative Book. In the worst case, the suite could use outcome names that don't match the Book's three exits, and the Book's only non-normative shorthand mapping would be the sole bridge. For a bit-exact core, this is exactly the kind of place where convergence depends on an unstated mapping. I'll call this P1, though I cannot verify it without the suite bytes.

**Actually, let me strengthen this.** The Book says the normative fields are `expected.outcome`, `expected.result_hash`, `expected.atp_spent`. But it never normatively defines what strings `expected.outcome` may contain. §3.4 defines `exit ∈ { normal_form, atp_exhausted, unresolved_reference }` for the `Receipt`. The §7 notation paragraph says "«ATP Exhausted» — вихід `atp_exhausted`" etc. — but that paragraph explicitly says it "adds no requirement." So the only normative statement about `expected.outcome` vocabulary would be an implication from §3.4 to the suite field, which the Book never draws because the suite schema isn't defined in the Book. An implementer cannot know whether `"expected.outcome": "atp_exhausted"` or `"expected.outcome": "ATP Exhausted"` is the normative form. Since the suite is the normative artifact, and the Book doesn't define its schema, the Book is silent where the implementer must guess. **P1 stands.**

Counterexample: An implementer writes a conformance checker that compares `expected.outcome` against `"atp_exhausted"` (the Book's `Receipt.exit` vocabulary). Another compares against `"EXHAUSTED"` (some other plausible spelling). The suite's actual string could be either, or neither. One of the two checkers declares the suite non-conformant (or fails), the other passes. Since the Book declares the suite normative but doesn't pin the strings, both implementers can believe they're conforming while disagreeing on whether the edition itself is conformant. That's the P1.

---

### The §7 notation paragraph's claim "adds no requirement"

The paragraph says the shorthand `eval(·, atp)` fixes the environment as the suite's `objects` — "третій вхід (§3.4) не опускається, а фіксується набором."

But the suite records include `term` or `bytes` producing a `result_hash`. The vectors in the prose (TV-4 etc.) print hashes for the terms. Is the `term_hash` printed in TV-4 (e.g. `51d8148feda...`) the hash the suite uses? If the suite generates the expected result_hash from the object, the prose hash must match. Fine.

**But there's a consistency issue in the field list itself**: the normative representation is said to be "предмет обчислення (`term` або `bytes`)" — i.e., the suite record has EITHER a `term` field OR a `bytes` field. But the §7 notation says `eval(·, atp)` evaluates "вказаного терма" (the named term) over the suite's `objects`. If the field is `bytes` and the prose names a "term" (e.g., TV-3's `ff01dc435a...` bytes), this is a mismatch in the description of how the prose maps to the suite. But this is again unverifiable without the suite.

---

### Book II and III: the "same rule as Book I §7" — P2

The Books II and III now carry the full rule inline rather than importing Book I §7's field list. The diff shows they each map to their own schema's fields: Book II's `w1`, `w2`, `expected`; Book III's `kind`, `doc`, `expected`.

But **the same P1 from Book I applies here**: the field `expected` is declared normative, but its internal schema — what `expected` must look like for wave vectors, or for federation vectors — is not pinned by the Books. Book II defines `WaveVectorQ { ph, am, en }`. Does the suite's `expected` field carry the full WaveVectorQ? Does it carry extra fields? If the suite's `expected` has a shape that isn't defined in Book II, and the Book says `expected` is normative "цілком" (entirely), then an implementer must guess the schema.

Specifically, Book II's new text says: "нормативним представленням твердження прози в записі є поля входу (`w1`, `w2`) і поле `expected` цілком." This says the ENTIRE `expected` field is normative. But Book II does not define the schema of `expected`. This is a P1 for both Books II and III: normative fields whose schemas are not normatively defined in the normative Books. The counterexample: two implementers parse `expected` differently — one expects a flat `{ ph, am, en }`, another expects a nested `{ wave: { ph, am, en } }` — and one declares a record invalid, the other not. Both can be conforming because the Book says only "expected entirely."

The Book II counterexample is easier to make concrete: `w1 = { ph: 0, am: 65535, en: -32768 }`, `w2 = { ph: 16384, am: 65535, en: -32768 }`. The interference result should be some `WaveVectorQ`. Two conforming checkers read `expected`: one looks for `{ ph, am, en }`, the other for the same fields capitalized `{ Ph, Am, En }` (Book II uses that capitalization in §6). The Book says the whole `expected` is normative, but nowhere defines whether JSON keys are lowercase.

The same for Book III: `expected` field for federation vectors, whose content could be a `wave_fed` result, a ViewID, an assertion_set_root, etc. The Book III new text says `expected` is normative entirely, but the schema of `expected` per `kind` is not pinned. Book III §8 describes the oracle's functions and the suite's generation. The suite has `kind` and `doc` as inputs. What outputs does `expected` carry for each `kind`? Not defined in Book III.

So this is a common P1 for all three Books: **the normative vector suite fields are named, but their schemas are not normatively defined within the Books.** The candidate fixes the *precedence* problem but introduces a new gap. I'll fold the three instances into one P1 with a single counterexample-type, since the amendment is the same in each Book.

---

### Regression: "spec_version" claim

VERSIONS.md claims the candidate regenerates every suite and closes the two discrepancies. The diff does not show `version_check.py` or the suites. This claim is outside the diff. I cannot verify it. Per instructions, I should not treat CI or author statements as evidence. The version numbers in the Vec suite files themselves are not in the diff either. Since this is a fact claims (files outside the diff changed), I can't check it. But the Book headers themselves do move to 0.6.0 / 0.7.0 / 0.7.0, as shown in the diff. The pending intractability: the candidate's own anchor set (not in diff) would need to carry the versions. I'll flag as P3, not a normative defect of the Books themselves.

The versioning decisions (Book I MINOR, Books II/III MINOR) are consistent with VERSIONS.md's rule: Book I has behavioral changes (foreign-key refusal, out-of-domain refusal) that can make a previously conforming implementation non-conformant. Books II/III's changes are the arbitration-rule change, and the ADR argues implementations whose conformance was judged against oracle precedence would now be judged against suite consistency. Is this a case of an implementation becoming non-conformant? The VERSIONS.md definition: "MINOR when a conforming implementation of the previous version could become non-conformant." An implementation that matched the oracle where the oracle and suite disagreed was conformant under 0.6.1 ("при розбіжності з прозою виграє оракул" / oracle wins). Under 0.7.0, if prose and suite disagree, the edition is non-conformant and MUST NOT be used. The implementation's conformance is judged against the edition. So the implementation could now be non-conformant against the corrected/re-anchored edition. The argument is sound. MINOR for Books II/III is defensible.

---

### Version string version bump consistency

The candidate's diff shows Book I 0.5.2 → 0.6.0, Books II and III 0.6.1 → 0.7.0. This is consistent with VERSIONS.md's MINOR rule. Fine.

---

### The inclusion of the English rendering

The English `book-1-truth.en.md` is at 0.6.0 with the same SemVer. The candidate states it is informative, not normative. But the English file's header says: "In any discrepancy the anchored source governs, until the maintainer roster adjudicates and re-anchors an English normative edition (§8)."

Wait — the English file says "the anchored source governs." But the candidate changes §7 of the Ukrainian Book: the suite and prose MUST agree. The English rendering is not anchored. Is the English rendering part of the edition whose suites must match its prose? The §7 prose in the Ukrainian text is the normative prose. The English file is a rendering. The rule in the Ukrainian Book says "Проза §7 і записи набору MUST бути взаємно узгодженими" — the prose of §7. Which prose? The anchored (Ukrainian) Book's §7. The English rendering is a separate file, not anchored, but it also has a §7 with the same vectors. If the English §7 prose differs from the suite, is the edition non-conformant? The Ukrainian Book's rule doesn't bind the English file. The English file says it's informative and the anchored source governs. So the English file could theoretically disagree with both the Ukrainian and the suite and still be normative? No — it's not normative at all. The scope note tells me the English rendering is informative. If the English file's §7 prose differs from the Ukrainian's §7 prose or from the suite, the candidate's own tool (`spec_audit.py`) is claimed to check for drift. But the tool isn't in the diff. This is P3 / informational.

But there IS a subtle issue: the English file's §7 paragraph is almost the same as the Ukrainian, but it's an English rendering. The §7 "notation" paragraph in the English file says: "In the vectors below, `eval(·, atp)` abbreviates evaluation of the named term with budget `atp` over this edition's content environment — the `objects` of `tests/spec_conformance/vectors.json`."

This says "this edition's content environment." If the English rendering is not part of the edition (not anchored), what is "this edition" in that sentence? The English file refers to the same vector suite. This is fine because the English file is informative.

I'll not treat the English rendering as a defect.

---

### GOV-anchors unchanged — P0 debate

The ADR-010 says GOV-anchors is unchanged and its pinned dependency "Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1" now names versions the bundle no longer carries. Two reviewers called this a P0; the owner decided to preserve it; DeepSeek held P0 in rounds 1 and 2.

Is this a P0? The severity ladder says P0 means two conforming implementations can disagree on a result, or the text contradicts itself or the vector suite.

The GOV-anchors pin is a normative dependency declaration: "This profile is defined against ... Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1 as anchored in this release." The candidate moves all three Books to new versions. So GOV-anchors 1.0.2's pinned normative dependencies no longer match the anchored Books of the v0.7.0 release. GOV-anchors says in §0:

> "**Pinned dependencies.** The normative dependencies above are pinned by content hash / anchored version. Re-pinning to a newer dependency is itself a breaking change."

And:

> "Implementations MAY track later dependency versions only where these exact semantics are preserved; any change is a breaking change to this STANDARD."

The owner's disposition says the semantics consumed by GOV-anchors don't move: `NodeHash(LITERAL, SHA-256(bytes))`, the anchor definition. Let's verify: GOV-anchors uses the anchor definition "NodeHash(LITERAL, atom=SHA-256(document_bytes))" — Book I §8 and §2, §1.1 LITERAL opcode. The candidate diff does not change §1.1, §2, or §8. So the anchor metric itself remains byte-compatible. The owner's claim holds.

But there is a second question: does the candidate change any other Book I semantic that GOV-anchors' §3 verification procedure relies on? GOV-anchors uses "JCS-canonical I-JSON," "Warrant v0.3," Ed25519. It does not use Book I's `eval`, `Receipt`, `env`, `§3.4` pricing, or `§3.5` resolution. It uses "NodeHash" as a hash function. So implementing GOV-anchors against Book I 0.6.0 or 0.5.2 yields the same NodeHash for LITERAL nodes. The Kaypro...the K... no.

However, the *textual* contradiction is real: GOV-anchors says "as anchored in this release" and the v0.7.0 release anchor-set will not contain v0.5.2/v0.6.1/v0.6.1. A verifier that checks the anchor-set against the pinned version strings will fail. But is that a divergence between two conforming implementations, or a broken edition?

GOV-anchors' conformance obligations (§7) are about the governance verifier's behavior. The governance profile doesn't mechanically verify that the pinned Book versions exist in the anchor set — step 2 checks "B.jurisdiction == C.jurisdiction" and schema validity. The pin is a normative dependency, but the verification is of the anchor-set blob against the profile, not of the profile against the bundle's internal consistency.

Is this a P0? Two conforming governance verifiers, given a candidate anchor-set blob for v0.7.0, apply the seven steps. Regardless of their reading of the pin, the seven steps take the same inputs and produce the same accept/refuse determination, because the pin is descriptive/declarative, not mechanically enforced in the seven steps. The possible divergence the reviewers raised was: one verifier's *operator* applying a stricter reading rejects the bundle, another accepts. But that's a policy/rules question about whether the entire bundle may be adopted, not a divergence in the verifier's algorithm. The seven-step procedure does not consult the pinned Book versions to decide. It consults the genesis profile, the threshold, signatures, lineage.

So: two conforming verifiers applying the seven steps will agree — the pin doesn't enter the steps. The GOST-anchors... the disagreement about whether the *bundle* should have been produced with a new GOV-anchors version is a governance-process question, not a verifier divergence. It's a P2 in my ladder, not P0. The owner's disposition is recorded; the question is closed by fiat, with dissent noted. The normativity of the pin remains "MUST" for re-pinning, and the candidate doesn't re-pin. Whether the version string mismatch is a "re-pin" is interpretive. Since the seven-step verifier doesn't branch on the pin, there is no executable counterexample of two conforming verifiers disagreeing on whether to accept a specific anchor-set blob. Without that counterexample, P0 cannot stand under my severity ladder. I'll note this as P1 at most: the edition carries an unreconciled version-string mismatch between GOV-anchors' pinned dependency and the bundle contents; the owner's disposition says the pin binds semantics, not strings, but the text of GOV-anchors says "pinned by content hash / anchored version" and "as anchored in this release."

Let me check whether one could construct a scenario where the mismatch causes a P0. GOV-anchors §2 schema: "anchors" sorted by path, one entry per anchored file. The anchor-set blob for v0.7.0 will have entries for Book I (new anchor), Book II (new anchor), Book III (new anchor), plus GOV-anchors unchanged. The profile's normative dependencies don't reference the anchor-set's internal version strings. The seven-step verification doesn't compare the pin's versions to the anchor-set's contents. Therefore, no two conforming verifiers diverge mechanically.

I think the honest call: the version-string mismatch is a P1 — the edition's prose is self-inconsistent as published (GOV-anchors claims its dependencies are as anchored in this release, and the release anchors different versions), and the reconciliation is by owner disposition recorded outside the normative text. But it is not a P0 because no executable divergence follows. The palm... the normativity is not perfectly tidy, but a verifier's behavior is unaffected.

Actually, hold on. Let me reconsider: is there a second verifier path where the pin matters? GOV-anchors §3 step 4: "Policy lineage — the profile in force derives from `C.genesis_profile` by walking profile adoptions." The genesis profile for GOV is P1, pinned by hash. The profile blob's hash-pinned threshold T1 depends on the threshold. None of this depends on the Book versions. Key state: no Book versions. Step 6: cardinality + adoption, no Book versions. Step 2: schema + jurisdiction, no Book versions. So the pin does not enter the algorithm.

Conclusion: **the GOV-anchors version-string mismatch is a P1, not a P0.** The ADR's round 1 Gemini/DeepSeek P0 claim is overstated under my ladder. Since no two conforming verifiers diverge among themselves on a specific blob, P0 does not apply. The issue is a prose self-inconsistency (edition says its dependencies are "as anchored in this release" while the release anchors different versions) plus an inherited risk for future re-pin decisions.

---

### The "undemanded entry" — one more look

Book I §3.5:

> "Запис, якого виконання не вимагало, MUST NOT змінювати жоден канонічний `Receipt`... за однакових відповідей на вимагані хеші дві конформні реалізації повертають той самий `Receipt`, хоч би що ще лежало в середовищі."

This is the environment-extension monotonicity theorem. The candidate says it is mechanized. This is a normative MUST that a settled exit is stable under environment extension. Can an undemanded entry actually change a Receipt in a conforming implementation? Consider the machine in §3.3. It only forces thunks demanded by the search. If an entry is never demanded, it is never consulted. If it's never consulted, it cannot change the machine's path. This follows from §3.3's laziness. The statement is consistent with the machine model.

But consider whether "demanded" is well-defined in the presence of the CAS check. The machine demands a hash; the environment provides bytes; the bytes fail the CAS; the implementation raises a local refusal. Is that a Receipt? No — it's a local refusal (§3.6), not a canonical result. So the undemanded-entry MUST NOT change a Receipt; a demanded-but-poisoned entry doesn't produce a Receipt at all. Consistent.

The extension monotonicity: Adding content can change only `unresolved_reference`. Consider adding bytes for a hash previously absent. If the machine demanded the hash while absent, the Receipt was `unresolved_reference`, exit `unresolved_reference`. Now with bytes present, the machine can materialize and continue. Could it instead reach `atp_exhausted`? Suppose the machine, while forcing the newly available hash, exhausts the budget. Then the Receipt changes from `unresolved_reference` to `atp_exhausted`. Wait — but the monotonicity says adding content can change ONLY `unresolved_reference`. Can adding content change `unresolved_reference` to `atp_exhausted`? Let's check.

The MUT the Book says: "Додавання вмісту може змінити лише вихід `unresolved_reference`." This says only exits of the kind `unresolved_reference` can change. Does the theorem hold for the case where the newly-added content is force-able but doesn't fit the budget? Let's think through the machine. Before adding content: demand h, env lacks h, and h is not intrinsic → failure mode (a) → DISSONANCE(Unresolved Reference), with spent unchanged (since failed resolve is not priced — §3.4: "Невдала дія (відмова resolve) не тарифікується"). After adding content: demand h, env has bytes, CAS passes, bytes deserialize, node kind known. Now the force price may exceed atp − spent → ATP Exhausted. So the Receipt changed from `unresolved_reference` to `atp_exhausted`.

But the Book's extension theorem says adding content can change **only** an `unresolved_reference` exit — i.e., only exits equal to `unresolved_reference` can be affected. The direction is: adding content can flip `unresolved_reference` to something else; adding content cannot flip `normal_form` to something else; cannot flip `atp_exhausted` to something else.

So the question: can adding content flip a former `unresolved_reference` into `atp_exhausted`? That's still a change from `unresolved_reference`, so it's permitted by the theorem's wording. The theorem doesn't say what unresolved_reference changes *into*; it says only that unresolved_reference outcomes are the only ones that can change. So the outcome `unresolved_reference → atp_exhausted` is permitted by the theorem. Good. And `unresolved_reference → normal_form` is permitted.

But the theorem also says: "Усталений вихід — `normal_form` або `atp_exhausted` — MUST лишатися тим самим `Receipt`." The settled exit (normal_form or atp_exhausted) must remain the same Receipt. Fine.

Can adding content flip `normal_form → normal_form` with a different result_hash? Suppose the machine's search, before adding content, had normal-form exit via a path that didn't demand h; adding content makes h available but the machine still doesn't demand h (the path is unchanged). Then the Receipt is identical. Fine. If the machine, after adding content, were to demand h on a different path — that would mean the search order changed, but §3.3 fixes leftmost-outermost deterministically, and the demand set is determined by the term and the available bytes. But consider this: the demand set depends on what bytes are available, through the CAS check? No — the CAS check is a local refusal, not a different search path. The search path in §3.3 is determined per the machine definition, and the machine's state is determined by the term's hash tree. Different environment entries for hashes that are never demanded don't change the path. So `normal_form` with a specific result_hash must be stable.

Could adding content for a hash that would have been demanded, but where the demand failed as unresolved_reference, now lead to a different normal_form than another environment would? That's exactly the resolved-hash equivalence domain: "Дві реалізації, які розв'язують ті самі **вимагані** хеші в ті самі байти, повертають однаковий `Receipt`." The demanded hashes now include h; if the bytes for h are the canonical bytes, the Receipt is deterministic. The theorem says adding content preserves normal_form if the new content is only for previously-undemanded hashes. The edge: adding content for a hash that becomes demanded (previously the demand failed as unresolved_reference, so the hash was demanded then too) — this is exactly the "unresolved_reference can change" case. Consistent.

So the monotonicity theorem is internally coherent. Good — no P0 here.

---

### Let me now also check the concrete arithmetic in the vectors that I *can* check, because a wrong printed hash or ATP figure would be a P0 (prose self-contradiction).

TV-4: `APPLY(⟨I⟩,⟨K⟩)` — apply I to K, should reduce to K by R-I. Hash of APPLY(I,K) printed as `51d8148feda...`.

The bytes of APPLY(I,K) per §2: `[02][06][H(I) 32 bytes][H(K) 32 bytes]`. H(I) = `2f33694d...330f4162` (full from §5.1). H(K) = `bc0c2fe2...bb0a486c`. So the canonical bytes of APPLY(I,K) are:

`02 06 2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162 bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c`

They print a SHA-256 prefix `51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e`. I can't compute SHA-256 by hand, but the printed form is a 64-hex (52 chars shown as prefix) … wait, the hash shown is `51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e` — that's 62 characters? Let me count. "51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e" — I count digits... Actually: 51 d8 14 8f ed a2 8f 17 30 4c 9e d6 c3 4d 9d 54 8c 83 a8 4c 38 0f 4d d1 ba 0a 03 7c eb 9d 4d 3e = 32 bytes? That maps to 64 hex characters. Looks plausible.

TV-4 ATP: "eval(·,4)=⟨K⟩, 4 ATP (force кореня 3 + R-I 1)". Root is APPLY(I,K), force = 3 (APPLY). Then R-I fires = 1. Total 4. Spent 4. Then normal form K, result_hash H(K). Consistent with §3.4 prices.

"eval(·,0) = ATP Exhausted, spent 0 — без жодного звернення до сховища." At spent=0, atp=0, stuck... the machine's first action is either thunk(h) or root materialization. Root term hash is unknown in env? Actually eval(term_hash, ...) — the term hash itself must be resolved from env. With atp=0, the check: minimum action price 1 > atp − spent = 0, so exhaustion before any storage access. Spent stays 0. Consistent.

"eval(·,2) = ATP Exhausted, spent 0 — байти кореня відкинуті (force коштує 3 > 2)." The root must be forced: fetch bytes, learn node kind is APPLY, cost 3 > 2. Spent unchanged. Result DISSONANCE(ATP Exhausted). Consistent.

"eval(·,3) = ATP Exhausted, spent 3." Root force costs 3 = spent 0 + 3 = 3, now spent == atp. Then the next step: the search needs to... what's the next action? After forcing the root APPLY(I,K), the machine checks for redex: the left child is a thunk of H(I). The step: `if t = thunk(h)`: h ∈ {H(I),...} → none (NF leaf by hash) — that's a non-priced recognition? Wait, §3.3 `step(t)` for a thunk with intrinsic hash gives `none` — no action. Then the next step considers the term: after forcing root, term is APPLY(I, K) with both children recognized... the root matches R-I at root: I applied to K. R-I fires, cost 1. But spent already 3 = atp 3. The exhaustion check precedes the action: price 1 > atp − spent = 0, so exhaustion fires before R-I. Result ATP Exhausted, spent still 3. Consistent.

TV-5: SKK·I. `APPLY(APPLY(APPLY(S,K),K),I)`. Force root (APPLY) = 3, then search descends left: child is APPLY, force = 3, descend left: child is APPLY(S,K)... the term is `((S K) K) I`. The left spine: root APPLY, left APPLY, left APPLY(S,K). Force 3 nodes? Actually root, left, left-left: three APPLY forces = 9. Then S at the root of left-left matches redex `S K K` (R-S) after seeing S... The machine descends until it can fire R-S. The R-S redex at `((S K) K) I`: fire R-S = 1 + size(z) = 1 + size(I) = 1+1 = 2. Then R-K fires = 1. Total 9 + 2 + 1 = 12. The prose says 12 ATP (3 force по 3 + R-S 2 + R-K 1). Consistent.

TV-6: "S I I (I·K)" — `((S I) I) (I K)`. Normal form APPLY(K,K)? R-S at root with x=I, y=I, z=(I K): → APPLY(APPLY(I,(I K)), APPLY(I,(I K))). Then R-I twice: APPLY(I,(I K)) → (I K), and (I K) → K... wait, let's redo.

Term: `((S I) I) (I·K)` where I·K = I applied to K. The redex is R-S: S applied to I applied to I, with z = (I·K). Result: `APPLY( APPLY(I, (I·K)), APPLY(I, (I·K)) )`.

Now R-I at root left: APPLY(I, (I·K)) → (I·K). So term becomes `APPLY((I·K), APPLY(I, (I·K)))`. The left part (I·K) = APPLY(I,K): R-I at APPLY(I,K) → K. So left part → K. Then term becomes `APPLY(K, APPLY(I,(I·K)))`. Then R-I at `APPLY(I,(I·K))` → (I·K). Term: `APPLY(K, (I·K))`. Then R-K at root: `APPLY(K, y)` where K applied to `(I·K)` — R-K fires: `APPLY(APPLY(K, x), y) → x`. Wait, `APPLY(K, y)` is K applied to one argument; R-K needs `APPLY(APPLY(K, x), y)`. Here term is `APPLY(K, (I·K))` — K applied to `(I·K)`. That's a partial R-K redex, not yet ready. But `(I·K)` can reduce: R-I → K. Then term: `APPLY(K, K)`. Now it's a normal form — K applied to one argument is irreducible (no rule for a single-argument K). So the normal form is `APPLY(K, K)`. The prose says normal form `APPLY(⟨K⟩,⟨K⟩)` — matches.

Alternatively, R-K could fire earlier... `APPLY(K, (I·K))` — the second argument is one argument, but R-K is `APPLY(APPLY(K,x), y)`. So the term `APPLY(K, (I·K))` needs a K and one argument, which is a redex? No, R-K in the prose: `R-K: APPLY(APPLY(⟨K⟩, x), y) → x`. So K applied to x applied to y. Our term is `APPLY(K, (I·K))` — that's K applied to one argument. Not a redex. So it reduces the argument first (leftmost-outermost says left spine first, then argument when functional part normal). Here functional part K is an intrinsic leaf (normal), so it demands the argument `(I·K)`. R-I fires on `(I·K)` → K. Then term is `APPLY(K,K)`, which is a normal form (both sides intrinsic, no redex). Matches.

The ATP count 21: let me count. Forces: root APPLY = 3. Need to force S? Actually the search: root force 3, then left spine: child APPLY = 3, left spine: child APPLY = 3, then left child thunk S — intrinsic, NF. So the R-S redex is at the subterm `APPLY(APPLY(S,I),I)`... wait, our term is `((S I) I) z`. Root: APPLY( ((S I) I), z ). Left spine: first child `((S I) I)` is APPLY = force 3. Descend left: `(S I)` is APPLY = force 3. Its left is thunk(S) intrinsic NF, so function part normal. Demand argument: `I` thunk intrinsic — NF. So the redex `(S I)`? No, that's S applied to I, not a full redex (needs two args). The machine climbs back: `((S I) I)` now has both children normal, and it's S I I — matches R-S only when applied to a third argument. The search continues: `((S I) I)` is APPLY with root-left APPLY... Let me follow the step machine more carefully.

`step(t)` looks at t. At the root, t = APPLY( ((S I) I), z). Rule matching: not R-I/R-K/R-S at root. So elseif APPLY: step(left) exists? left = `APPLY((S I), I)`. Recurse into left: t = `((S I) I)`. step(left of that): left = `(S I)` = APPLY(S,I). Recurse: t = `(S I)`. step(left) = thunk(S) — intrinsic → none. elif step(right) = thunk(I) → none. So `(S I)` has no step. Back to `((S I) I)`: step(left) = none; elif step(right) = thunk(I) → none; so `((S I) I)` has no step. Back to root `(((S I) I) z)`: step(left) = none; elif step(right) = thunk(z) → step of right, z = `(I K)` APPLY(I,K). step(left of (I K)) = thunk(I) intrinsic none. step(right of (I K)) = thunk(K) intrinsic none. So no step in z? Then the whole term has no step... But that would mean it's normal form? That can't be right because R-S should fire.

Wait, I mis-structured the tree. `S I I (I·K)` is `(((S I) I) (I K))`. The redex is at the root: R-S fires when the root term is `APPLY(APPLY(APPLY(⟨S⟩,x),y), z)`. Root: APPLY(f, a) where f = `((S I) I)` and a = `(I K)`. For R-S, f must be `APPLY(APPLY(S, x), y)`. f = `((S I) I)` = `APPLY((S I), I)` = `APPLY(APPLY(S,I), I)`. So f's left is `(S I)` = `APPLY(S,I)` whose left is thunk(S). R-S requires three nested APPLY with S at the innermost left. The pattern is root APPLY, f = APPLY, f.left = APPLY, f.left.left = S. Here: root APPLY ✓; f = APPLY ✓; f.left = APPLY((S I)... wait f.left = `(S I)` = APPLY(S, I) ✓; f.left.left = thunk(S), and thunk(S) has hash H(S), recognized without materialization. So the root matches R-S.

But wait — in the §3.3 machine, the pattern matching for R-S at the root requires the root to have the structure `APPLY(APPLY(APPLY(S,x),y),z)` — but the third APPLY's left child is the "APPLY(APPLY(S,x),y)" part, which is fully materialized? Actually the machine model says the term's children are either materialized or thunks. For pattern recognition: "патерни — порівняння хешів, аргументи НЕ форсуються." So the pattern can be recognized over thunks by hash comparison, without forcing. So at the root of `(((S I) I) (I K))`, the root's left is `APPLY(APPLY(S,I),I)` and the root's right is `(I K)`. Are these children materialized? They might be thunks (hash leaves), not yet materialized. But the pattern R-S can compare hashes: root.left must be APPLY whose left is APPLY whose left is thunk(S)... but if the children are thunks (unresolved hashes), the machine cannot see their internal structure without forcing. So the machine needs to force the children along the spine to recognize the redex.

But here's the thing: the R-S pattern matching says "arguments are NOT forced" — meaning x, y, z are not forced. But the machine still needs to see that the term has the required APPLY nesting. The §3.3 machine's step: it walks the left spine, forcing thunks as needed. It compares against ⟨I⟩/⟨K⟩/⟨S⟩ by hash without materialization. So to recognize R-S at the root, the machine must know root is APPLY, root.left is APPLY, root.left.left is APPLY, root.left.left.left is thunk(S). If root.left is a thunk, it must be forced to learn it's APPLY, etc. But forcing root is how eval materializes the term at all. The ATP figure: 3 forces of 3. Which forces? Possibly root, root.left, root.left.left? Let's count: root = APPLY (3 ATP), root.left = APPLY (3), root.left.left = APPLY (3). Then root.left.left.left = thunk(S) recognized by hash (no materialization, no cost). Now R-S recognized: fire R-S = 1 + size(z) = 1 + size(I·K). z = `(I K)` currently a thunk? Or materialized? If z is an unresolved thunk, size(z) = 1 (per §3.4: thunk counts as exactly 1). So R-S costs 1 + 1 = 2. Total so far: 9 + 2 = 11. Then R-K fires: 1. Total 12. But the prose says TV-6 costs 21. So my accounting doesn't match the prose.

Let me re-read the reward... the prose says: "рівно 21 ATP; уздовж виконання size − 1 ≤ spent."

Hmm, my analysis gives 12 for TV-5, not TV-6. TV-6 is `S I I (I·K)`. Let me recount more carefully. Maybe forces are on different nodes.

Term hash is `0379bafee...`. Evaluation: force root (APPLY, 3 ATP). Now term = `APPLY(APPLY(APPLY(I,I),I), (I·K))`? Wait no — `S I I (I·K)` means `((S I) I) (I K)`. The "S I I" is S applied to I applied to I. So `APPLY(APPLY(APPLY(S,I), I), (I·K))`? Let me parse: "S I I (I·K)" is left-associative application: `(((S I) I) (I·K))`. So term = APPLY( APPLY( APPLY(S, I), I ), (I·K) ).

R-S fires at root? Root: APPLY(f, z) where f = `((S I) I)`, z = `(I·K)`. f = `APPLY((S I), I)`. f.left = `(S I)` = `APPLY(S,I)`. f.left.left = S. So root matches `APPLY(APPLY(APPLY(S,x),y), z)` with x=I, y=I, z=(I·K). R-S: → `APPLY( APPLY(I, (I·K)), APPLY(I, (I·K)) )`. Cost of R-S = 1 + size(z).

Now, to recognize R-S, the machine must know f's structure. f may be a thunk; it must be forced to learn f is APPLY, and then f.left is a thunk, forced to learn f.left is APPLY, and f.left.left is a thunk(S) recognized by hash. But here's the key: each of these node forces costs the size of the materialized node. Force root: 3 (root APPLY, with thunk children = size 3? No — size(APPLY) = 1 + size(left) + size(right). If left and right are unresolved hash thunks, each thunk counts 1. So size(APPLY) = 1+1+1 = 3. Force root = 3. ✓.

After forcing root, root.children are thunks of f and z. To check R-S at root, the machine must know f is APPLY(APPLY(S,I),I). f is currently a thunk (unresolved hash). The machine must force f. Force f: f is APPLY((S I), I). size(f) = 1 + size((S I)) + size(I). (S I) is a thunk? I's a thunk? At this point, children f.left and f.right are thunks (unresolved hashes). So size(f) = 1+1+1=3. Force f = 3 ATP. Then f is materialized; its left is a thunk `(S I)`. Force `(S I)`? For R-S to be recognized at root, the machine needs to know f.left = (S I) is APPLY(S,I) — i.e., left.left must be S by hash. f.left currently is a thunk; force f.left = `(S I)` APPLY(S,I) has size 3? (S I) = APPLY(S,I): thunk S, thunk I children, size = 1+1+1=3. Force = 3. So total forces = 3+3+3 = 9? Then R-S: 1 + size(z). z = (I·K) is a thunk at this point. size(z) = 1. So R-S = 1+1 = 2. Total = 11. Then after R-S, term = `APPLY( APPLY(I, z), APPLY(I, z) )` where z is the same thunk. Now the machine needs to reduce this to normal form. What's the normal form? Per my earlier analysis, normal form is `APPLY(K, K)`.

Post-R-S: term = `APPLY( A, B )` where A = `APPLY(I, z)` and B = `APPLY(I, z)`. Both A and B are new nodes synthesized by R-S. Their internal structure: A = APPLY of thunk(I) and thunk(z); B same. The machine: root APPLY. Left spine: descend to A. Force A: size(A) = 1 + size(I) + size(z) = 1+1+1 = 3 ATP? Now I is a thunk (intrinsic, recognized as NF), z is a thunk. Force A = 3. Then step(A): A = APPLY(I, z) — R-I redex! R-I at A fires: cost 1. A → z. So term = `APPLY(z, B)`. Then machine: root APPLY(z, B). Left spine: z is a thunk. Force z? z = (I·K). Force z = APPLY(I,K), size = 1+1+1 = 3. Then R-I at z: z → K. Cost 1. Term = `APPLY(K, B)`. B is still `APPLY(I, z)` thunk? B's structure: after R-S, B = APPLY(I, z) synthesized as a new node. It's a materialized node? In the tree model, R-S synthesizes both A and B. They are materialized (equal... "вузли, синтезовані редукціями, рахуються" — nodes synthesized by reductions count). So after R-S, B is materialized (size counts it). Then later, when the machine reaches B: force? B already materialized? It was synthesized by R-S, so it exists. Does the machine need to force B? If B is already materialized (not a thunk), then step(B) = R-I redex, fire R-I cost 1. B → z (the thunk of (I·K)). Then force z again? z already materialized from earlier? In the tree model with sharing not guaranteed ("шаринг MAY застосовуватись у виконанні, але звітований ATP MUST збігатися з tree-обліком"), tree semantics counts everything as if unshared. So z is materialized twice? Once when A demanded it, once when B demanded it? But z here is the thunk of (I·K). When A = APPLY(I, z) fires R-I, A → z; then the machine forces z, materializing it as APPLY(I,K), costing 3. When B fires R-I, B → z; the machine forces z AGAIN (tree semantics: z was a thunk before, now maybe already materialized?). This needs a precise machine model.

At this point the ATP accounting depends on whether z becomes materialized once or is forced twice. The prose states exactly 21 ATP. Let me try to make 21 work.

Possible actions:
1. Force root: 3
2. Force f (=((S I) I)): 3
3. Force (S I): 3 (maybe needed to recognize R-S structure?)
4. R-S: 1 + size(z) = 1+1 = 2

Subtotal: 11.

Now after R-S, term = APPLY(A, B), A = APPLY(I,z), B = APPLY(I,z). Both A and B synthesized — they materialize. A and B are distinct nodes, each size 3? Actually A = APPLY with thunk I and thunk z children, size = 1+1+1=3. B similarly.

The machine descends left spine. Root's left = A, which is materialized (synthesized by R-S). step(A) matches R-I at root → fire R-I: cost 1. A → z. Now term = APPLY(z, B).

Then root = APPLY(z, B): left spine descend to z. Force z: cost size(z) = size(APPLY(I,K)) = 1 + size(I) + size(K) = 1+1+1 = 3. Now z is materialized as APPLY(I,K). R-I at z fires: cost 1. z → K. Term = APPLY(K, B).

Then root = APPLY(K, B): K is intrinsic NF, so demand right: force B? B is materialized (synthesized). step(B) = R-I redex: fire R-I cost 1. B → z. Term = APPLY(K, z). z here is the thunk... in tree semantics, does the machine force z again? The tree model counts z as a thunk each time it's referenced? §3.4: "нерозв'язаний хеш-лист рахується рівно 1 незалежно від того, що він позначає; матеріалізований REF рахується 2." A thunk is resolved once per demand in tree accounting (no sharing). So after B → z, z is a thunk to be forced again? But z was already materialized before from the A branch. In tree accounting, the two occurrences of z are separate? Actually z was a single thunk that got materialized once when A demanded it; after that, the node at that position is materialized APPLY(I,K) → then R-I → K, so the position now holds K. But through sharing, the same thunk appears in B's argument too? The tree semantics says: "sharing MAY be used in execution, but reported ATP MUST match tree accounting." In tree accounting, after R-S, the term is a tree with two distinct subterms A and B, each containing a z thunk (each occurrence of z is a separate thunk). So each z occurrence must be forced separately, costing 3 each? Wait, but force cost = size(materialized node) = size(z) = size(APPLY(I,K)) = 3. So the first time A demands z: force z (first occurrence) = 3, R-I on z = 1 (→K). Second time B demands z: force z (second occurrence) = 3, R-I on z = 1 (→K). But then B → z after R-I, and its z thunk also gets forced... hmm.

Let me be systematic for tree accounting. Term after R-S:

`APPLY( A, B )` where A = APPLY(I_thunk, z_thunk_1), B = APPLY(I_thunk, z_thunk_2). In tree model, z_thunk_1 and z_thunk_2 are distinct copies.

Actions:
1. Force root: root = APPLY(A, B) with A and B as thunks? After R-S, A and B are synthesized nodes, not thunks (they are materialized as part of R-S). So root's children A and B are materialized. Root already materialized before R-S (step 1). R-S rewrites the root in place...

This is getting very complex, and the precise ATP depends on the machine's notion of materialized. The prose says 21. My partial count: step 1=3, step 2=3 (force f), step 3=3 (force (S I)), R-S=2, then a sequence for A and B branches. Sum so far 11. Need 10 more.

Possible post-R-S costs: A's R-I = 1; force z_1 = 3; R-I on z_1 = 1; B's R-I = 1; force z_2 = 3; R-I on z_2 = 1; then after A and B reduce... maybe more steps. Total = 11 + 1+3+1+1+3+1 = 21? Let's sum: 11 + 10 = 21. Yes! 21 equals the prose.

Let me list actions:
1. Force root = 3 (subtotal 3)
2. Force left child f = 3 (subtotal 6)
3. Force f.left = (S I) = 3 (subtotal 9)
4. R-S at root = 1 + size(z) = 1+1 = 2 (subtotal 11) — z is thunk, not forced
5. R-I at A = 1 (subtotal 12)
6. Force z (copy 1) = 3 (subtotal 15) — now z = APPLY(I,K)
7. R-I at z (copy 1) = 1 (subtotal 16) — z → K
8. R-I at B = 1 (subtotal 17)
9. Force z (copy 2) = 3 (subtotal 20)
10. R-I at z (copy 2) = 1 (subtotal 21) — z → K

Now term = APPLY(K, B_result) where B_result = K? B after R-I → z thunk; force z copy 2 → K after R-I. So B reduces to K. Term = APPLY(K, K). Normal form. Matches prose.

Wait, but R-K doesn't fire here? The prose says: "Нормальна форма APPLY(⟨K⟩,⟨K⟩); рівно 21 ATP". It doesn't mention R-K. So no R-K. Matches.

Is the R-S cost correct? §3.4 says `cost(R-S) = 1 + size(z)` where z is the current materialization of z. If z is a thunk, size(z)=1, so R-S=2. ✓.

Then A = APPLY(I, z) — R-I at A costs 1, and the protocol says R-I does NOT force z? §3.4 says "cost(R-K) = 1 // відкинутий аргумент НЕ форсується". For R-I, the rule: `APPLY(⟨I⟩, x) → x`. Does forcing x happen as part of R-I? R-I does not force x; it just returns x. So after R-I, the result is the thunk z, which must now be forced as the new root. Actually, the machine §3.3: after R-I fires, the term becomes x (the thunk z), and the next step must force the thunk (if not intrinsic). So the sequence: R-I at A returns z (thunk); then the machine needs to materialize z to see its kind (because z is not intrinsic unless hash(H(K))? z = (I·K) hash is some hash not intrinsic). So force z: cost = size(z). Since z = APPLY(I,K), as a thunk, once forced, size = 3. ✓.

So my 10-step accounting gives exactly 21, matching the prose. The arithmetic is consistent. Good — no P0 on TV-6.

I'll trust the other TV vectors also match, since I can't rebuild the full hash chain by hand. The key patterns (TV-4, TV-5) checked okay.

---

### The step machine and the "не тарифікується" on failed resolve

§3.4: "Невдала дія (відмова resolve) не тарифікується." This is consistent with TV-8: "spent 4: R-I спрацьовує ліниво БЕЗ форсування ghost, потім ghost стає вимаганим коренем і не форсується." So TV-8: `APPLY(⟨I⟩, ghost)` with ghost absent. Force root = 3, R-I at root = 1 (spent 4). Then root becomes ghost (thunk). Demand ghost: force ghost, but ghost not found and not intrinsic → failure mode (a) → DISSONANCE(Unresolved Reference). The failed force is not priced. Spent stays 4. Matches.

TV-9: REF chain. `r1 = REF(H(K))`, `r2 = REF(r1)`. `eval(r2, 6) = ⟨K⟩, 6 ATP`. Actions: force r2 = REF node, size = 2 (REF + thunk target), cost 2. Then r2 is a REF → fire R-R: cost 1, r2 → thunk(r1). Then force r1: REF, size 2, cost 2. Then R-R: cost 1. r1 → thunk(H(K)). H(K) intrinsic → NF by hash, no materialization, no cost. Result K. Total: 2+1+2+1 = 6. ✓.

`eval(r2, 1) = ATP Exhausted, spent 0`: atp=1. First action: force r2 costs 2 > 1. Exhaustion before storage access. Spent 0. But wait — the term hash r2 itself must be resolved? The machine receives term_hash = r2. The root is a thunk initially? In the eval interface, it takes term_hash. The machine must force the root hash r2 to get the term's kind. With atp=1, force r2 = 2 > 1. So exhausted before fetching bytes for r2? Actually rematerialization: the check "Дія з ціною c > atp − spent не виконується" — at spent 0, atp 1, any action with c > 1 not performed. Force cost unknown until bytes fetched. §3.4 says: "Якщо ціна force стає відомою лише після отримання байтів (вид вузла), недоступні за бюджетом байти відкидаються без матеріалізації." Hmm, for the ROOT, the bytes are fetched, and if the root is a REF (cost 2 > 1), bytes are discarded, spent stays 0? Or does the fetch itself consume something? The prose says TV-4 `eval(·,2)` spent 0 for force root costing 3. And TV-9 `eval(r2, 1)` spent 0 for force r2 costing 2. So the spent stays 0 when the force price is unaffordable. Consistent.

Read-ahead: the budget exhaustion check before the action: for the root, the node kind is unknown. The spec says exhaustion check precedes the action, but force price knowledge comes after fetching bytes. The resolution: fetch bytes, inspect kind, if cost > budget, discard without materialization, spent unchanged. This is consistent.

---

### £3.6 "Eval is total" vs §3.6 "admission refuse before execution"

§3.6 says: "`eval` тотальний, тож терм незнайомця завершується завжди." This means `eval` must always terminate? But §3.6 also says an implementation may refuse before executing on a budget it declines to spend — that's admission, not eval. And local resource faults (depth, fetch count) are implementation faults, not serialized as DISSONANCE. Does `eval` total include those? The sentence says "eval is total, so a stranger's term always terminates." But an implementation fault (stack depth) causes a non-canonical refusal. Is that refusal part of eval's totality, or a local fault outside eval? The text: "Порушення локальних ресурсних лімітів... — implementation fault: відмова виконання, яка MUST NOT серіалізуватися як DISSONANCE." It's an execution failure. So is `eval` still total? Totality means for any valid input, the machine reaches a canonical result. But if a local resource limit fires, the machine doesn't reach a canonical result. The older text already had this tension; the candidate doesn't remove it. It's a P2 at most: "eval is total" should be scoped to "within the abstract machine model, absent implementation limits." The new admission paragraph says admission is separate and produces no Receipt. The old implementation-fault paragraph remains. Slight tension between "eval is total" and "implementation faults are execution failures." P2.

---

### Round 4 TV-7/TV-12 quantifier fix

The candidate fixes TV-7's `∀n` to `∀n : uint32` and TV-12's `eval(H(I), n) = ⟨I⟩, 0 ATP` to "для будь-якого `n : uint32`". This aligns with §3.6's new out-of-domain rejection. The diff shows exactly that. Consistent.

---

### Now, let me consolidate my findings.

**P1-1: Vector suite schema not defined in the norm.** Book I §7 names normative fields (`term`/`bytes`, `atp`, `expected.outcome`, `expected.result_hash`, `expected.atp_spent`) but does not define the allowed values/JSON types for `expected.outcome` beyond the prose's informal shorthand, which the Book says "adds no requirement." The same defect appears in Books II and III, where `expected` is declared normative "entirely" but its schema is not defined. This is the same class: a normative artifact's field schemas are not normatively specified in the text, leaving an implementer to guess. Two conforming checker implementations can disagree on whether a record is well-formed, and therefore on whether the edition itself is conformant.

Severity: P1. Fixable by amending the text to explicitly pin the JSON schema of each normative suite field (the candidate can append a small "$7.X Suite Schema" subsection naming the JSON types and value domains, or state that the suite's own `spec_version` / schema tag is normative and pinned). This does not change what the machine does.

**P1-2: GOV-anchors version-string mismatch.** GOV-anchors 1.0.2 declares its normative dependency as "Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1 as anchored in this release." The v0.7.0 release anchors Book I 0.6.0, Books II and III 0.7.0. The seven-step verifier does not branch on these strings, so no two conforming verifiers diverge mechanically; but the edition as published contains a self-contradiction (a STANDARD claiming its pinned dependencies are as anchored in this release, while the release carries different anchors). The fix is to amend GOV-anchors to a 1.0.3 PATCH with updated version strings, or to amend the candidate's own text (ANCHORS.txt is not changed by this diff, but the Books could carry a note). Since GOV-anchors is out of scope of the three-Book diff but in scope of the review (the bundle carries it), this is a P1.

Severity: P1. Fixable by editing GOV-anchors' dependency pin to the new version strings (a PATCH edit, since no schema or mechanism changes), or by adding a normative note reconciling the pin.

**P2s:**
- §3.5's "no canonical answer" sentence is confusing even though it's not misleading an implementer about the operative MUSTs.
- The interaction between the content-environment CAS check and intrinsic axioms (§5.1) is not explicitly stated; an implementer could wonder whether a poisoned env entry under H(K) triggers the check when the implementation synthesizes K intrinsically. Derivable as consistent, but should be explicit.
- "eval is total" coexists uneasily with implementation faults and admission; scoping would help.
- The §3.4 guard MUST ("guard MUST міряти фактичний size(t)/глибину") is an oddly placed normative constraint on an optional internal fence; pre-existing but now sits next to the new "this Book does not prove physical-resource correspondence" text.

**P3:**
- The version_check.py / suite regeneration claims cannot be verified in this diff.
- The compatibility two-value form's interaction with out-of-domain refusal could be stated more explicitly.

**P0: no P0s found.** The round-1 P0 (conflicting MUSTs on out-of-domain atp) is fixed. The round-2 P0 (contradictory statements about undemanded entries) is fixed via the admission/evaluation distinction. The round-3/4 P0 (GOV-anchors pin) is not a P0 under my ladder because no conforming verifier diverges on a specific blob, though it is a real P1 self-inconsistency. The vector arithmetic I checked (TV-4, TV-5, TV-6, TV-8, TV-9) matches the prose.

VERDICT: ADOPT-WITH-AMENDMENTS
