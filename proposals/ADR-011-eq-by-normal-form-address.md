# ADR-011: Receipted Equality of Admitted Canonical Data by Normal-Form Address

**Status:** DRAFT — non-normative candidate. Not gated, not adopted, and it
proposes no change to any anchored byte. The Book I semantics it is read against
*are* adopted (document version 0.6.0, anchor `e3e5d008…`, adopted as part of
anchor-set release v0.7.0 by warrant `0e634c176b00`); that says nothing about
this ADR's own status.

**BLOCKED on the case that motivated it.** The profile below is a safety
reference for numerals written out. It does **not** admit `PLUS 7 5`, so it
cannot perform the `7+5=12` settlement this ADR exists because of. See
"The admission gap" and `EXP-ADR011-01`.

**Working thesis:** *an address settles equality only after an admitted profile
has made the observation canonical.*

## Correction note (2026-08-31)

This ADR was written on 2026-08-30 by Claude (Fable 5) during the manifesto
RVB/SSD sessions, at s0fractal's direction, from
`manifesto/drafts/ADDRESSING-IS-EQUALITY.md` (AIE-0.1). That version is
preserved unedited at commit `3f58ab6` (sha256
`44c9696167085189831a7d9c511e98e6d9e1ffb0180ad69adbf43651bbc50510`); this is a
narrowing of it, not a replacement of its finding.

**What was narrowed.** The original stated:

> **Soundness is unconditional:** `na == nb ⇒ equal` (modulo SHA-256, which is
> already in the trust base).

That is false as written, and the counterexample runs on this repository's own
evaluator:

```text
a = λf.λx.x                 b = λf.λx.X          (X is the profile's own marker)
Y = the literal sha("sigma-glyph/adr-011/church@v0/Y-probe"), a second
    observation point that is NOT a marker of this profile

observation at (F, X), the profile's markers:
  a → e37391c4fac298b2…  exit normal_form  spent 12
  b → e37391c4fac298b2…  exit normal_form  spent 15

observation at (F, Y), a different point:
  a → 2b0e36974e076c00…  exit normal_form  spent 12
  b → e37391c4fac298b2…  exit normal_form  spent 15
```

`na == nb` at the profile's observation point, and the two terms are different
functions. One observation point does not prove equality of arbitrary terms.
Addressing is not equality; addressing is *identity of what came back*. Carrying
that back to the inputs is a property of a profile, and profiles have domains.

The phrase "addressing is equality" may stand as the historical name of the
engineering finding. It is not a theorem and is not used as a conclusion here.

**What survives, and what does not follow from it.** The engineering result is
real and is why this ADR exists: in-language Church equality is catastrophically
expensive on measured fixtures, and `7+5=12` settled for 601 ATP in the harness
that measured it — `manifesto/tools/glyphlib.py`, whose `settle_nat_eq` admits
any lambda expression it is handed.

That harness had no admission argument. This ADR supplies one, and the profile it
can currently justify is **narrower than the experiment**: it admits numerals as
written and refuses `PLUS 7 5`. So the 601-ATP result is cited here as the
motivation and **is not a result of `church@v0`** — the profile has never settled
it and, as specified, cannot. Letting a safe, nearly trivial profile inherit the
credit of that experiment would be the same substitution this correction note is
about, one level up.

## The problem, unchanged

Equality expressed *inside* the object language pays a combinatorial tax on
computed arguments. `EQN = ISZERO ∘ SUB`, `SUB = iterated PRED`: under lazy
tree-semantics reduction the unevaluated argument (`PLUS 7 5`) is duplicated by
every `PRED` application. Measured on the reference oracle by
`manifesto/tools/glyphlib.py` (2026-08-30):

| fact | in-language EQN (ATP) |
| --- | --- |
| 3+2=5 | 260 780 |
| 5+5=10 | 26 212 480 |
| 7+5=12 | >59 452 030 (ATP Exhausted) |

In *that* harness, an agent comparing those values in-language pays those
figures. That is the whole scope of the claim: it is not a statement that
address equality is the only alternative, or the best one. WPL predicates,
typed host-side equality and other encodings exist, this ADR measures none of
them, and nothing here rules them out. What it does is specify one idiom that
was already in use unspecified, and say on which domain it is admitted.
Specifying it is worth doing. Specifying it as more than it is, is not.

## What is unconditional

Exactly one thing, and it is worth stating alone because everything else is
qualified:

> **Σ-lemma.** Two evaluations that both exit `normal_form` with the same
> `result_hash` returned one canonically addressed result — modulo SHA-256 and
> the correctness of the implementations.

It says nothing about the terms that were evaluated. It is a statement about two
results, not about two inputs.

## What a profile must fix

```text
EqualityProfile = {
    profile_id,             # what the profile CALLS itself. A string it picks.
                            # NOT an identity: see profile_commitment below.
    profile_commitment,     # a digest over every field that changes what a
                            # settlement MEANS, including `observe` and `admit`
                            # themselves
    admitted_domain,        # what may be submitted, and by what check
    equivalence_relation,   # which `~` is being claimed
    observe,                # term -> observation term
    marker_definition,      # exact bytes, NodeHashes, distinctness, freshness
    budget_policy,          # each side's budget, explicitly
    environment_policy,     # which content environment, and whose
    book_anchor,            # EXACTLY 64 hex — the anchor itself, comparable
    book_context            # the prose: which edition, adopted how
}
```

Two properties, separately, each qualified by the admitted domain, **neither
unconditional**:

```text
reflection     same_address(observe(a), observe(b))  =>  a ~ b
preservation   a ~ b  =>  same_address(observe(a), observe(b))
```

Reflection is what a verdict of EQUAL rests on; preservation is what a verdict
of UNEQUAL rests on. A profile that argues only one of them may issue only the
verdict that one supports.

## The settlement algorithm, corrected

```text
settle_eq(profile, a, b, budget_a, budget_b, env):
    commitment = profile_commitment(profile)   # BEFORE anything executes
    require 64-hex book_anchor                 # or refuse; no receipts

    admit(a); admit(b)                      # refusal is REFUSED, not a verdict

    ra = eval_receipt(observe(profile, a), budget_a, env)
    rb = eval_receipt(observe(profile, b), budget_b, env)

    if ra.exit != normal_form or rb.exit != normal_form:
        return UNSETTLED, {profile_id, profile_commitment, book_anchor,
                           book_context, ra, rb, which_side_did_not_finish}

    return {verdict: EQUAL if ra.result_hash == rb.result_hash else UNEQUAL,
            profile_id, profile_commitment, book_anchor, book_context,
            lhs: ra, rhs: rb}
```

Four differences from the candidate's pseudocode, each reproduced as a defect
before being fixed:

**It reads receipts, not `eval_hash`.** The candidate compared result hashes
with no exit check. `DISSONANCE(ATP Exhausted)` has one address, so two
exhausted runs compare equal: `church(3)` against `church(5)` at `atp=30`
settles **"equal"** that way. And one address carries two exits — a stored
`DISSONANCE(ATP Exhausted)` evaluates to `8bb0006f4c0a…` with
`exit=normal_form`, while a genuine exhaustion returns the same digest with
`exit=atp_exhausted`. This is the receipt gap ADR-010 closed; the candidate was
written before that landed, and `eval_hash` is now only a named compatibility
profile.

**Each side has its own budget.** The candidate gave the second side
`atp - spent_left`. That is a different protocol with observably different
answers: at `atp=600`, `church(12)` settles **UNEQUAL to itself** (left spends
456, right gets 144 and exhausts at 142). And the verdict flips with argument
order — `church(0)` against `church(12)` at `atp` of 100, 200 or 300 gives
"unequal" one way round and "equal" the other. The reference implementation in
`manifesto/tools/glyphlib.py` already gives both sides the full budget; the
pseudocode and the code were two protocols.

**Exhaustion is UNSETTLED, and the receipt says which side.** Not a verdict of
inequality, and not a silent merge of "did not finish" into "different".

**Admission refusal and local resource faults are neither.** They are `REFUSED`
and `FAULT`, never a Book I exit and never serialized as a DISSONANCE (Book I
§3.6).

`spend_total` may be reported as the sum of the two spends. It is **not** a Book
I Receipt: Book I prices one evaluation, this is arithmetic over two, and it
prices neither the construction and materialization of the observation terms nor
the CAS I/O that serves them.

## The Church profile, and what it does not cover

`sigma-glyph/adr-011/church@v0` — reference implementation in
[`adr-011/equality_profile.py`](adr-011/equality_profile.py).

**Markers.** Domain-separated from the profile id:

```text
F: atom SHA-256("sigma-glyph/adr-011/church@v0/F")
   node 92b1cec9ba6035599d1977c2f6bab8fbc2d74b9248775260baf5c710664126c1
X: atom SHA-256("sigma-glyph/adr-011/church@v0/X")
   node e37391c4fac298b26e097562e8411695e989d4dc3a391a28f2ac5287eaa80211
F ≠ X
```

**The grammar is closed, with exact arity.** The check indexed the positions it
wanted and ignored the rest, so both of these were admitted as written-out
numerals and settled EQUAL against `church(0)`:

```text
("lam", "f", ("lam", "x", ("var", "x")), "EXTRA")
("lam", "f", ("lam", "x", ("var", "x"), "EXTRA"))
```

Reading a tuple by index accepts every superset of the shape asked for. Nodes
are now required to be tuples of exactly their arity — `var`/`lit` 2,
`lam`/`lapp`/`app` 3 — with binder names required to be strings, and the whole
term is validated before admission. Six malformed shapes are controls (16), the
numerals 0–8 remain admitted (16b), and mutation M9 restores index-only checks
and requires 16 to go red.

**Binder distinctness.** The admission check is syntactic, and `λf.λf.f(f)`
passed an earlier version of it: both binders were compared by NAME, so the
spine walked and the body matched. Under shadowing the inner binder wins, and
the term denotes `λa.λb.b(b)`, whose observation agrees with no numeral. That
is over-acceptance *outside* the domain reflection and preservation rest on —
the one direction this profile must not fail in — and it is now refused, with
control 12 and mutation M4 in the selftest.

The same requirement refuses terms that shadow and still denote a numeral, e.g.
`λx.λx.x`, which is `church(0)`. Refusing an admissible term costs a caller a
settlement; admitting an inadmissible one costs the claim.

**Freshness** means: the markers are fixed by the profile id **before any term
is submitted**, and a submitted term naming either is refused at admission. The
counterexample above is exactly a term that names a marker. A profile deriving
fresh markers per settlement instead would have to commit to the terms first;
that is the same requirement seen from the other side, and this profile takes
the simpler branch.

**Observation** is `O(n) = n F X`. A written-out numeral `λf.λx.fⁿ(x)` compiled
by C1 and applied to two inert literals reduces to the constructor spine
`Fⁿ(X)`, which is injective in `n`; the markers are inert, so nothing else in
the admitted domain produces that spine. That argument is what reflection rests
on, and it is an argument about the admitted domain only.

**The admission gap, which is where this ADR is blocked.** The profile admits
numerals **as written**, by a syntactic check. It does **not** admit computed
expressions: `PLUS 7 5` is refused, and the selftest asserts that refusal.

There is no mechanical admission of "Church-natural computations" in this
repository. Substituting a syntactic heuristic for that semantic precondition is
precisely the error this correction is about, so the gap is left open rather than
bridged by a guess. The consequence is stated plainly: **`church@v0` cannot
settle the motivating case.** Closing that needs a domain whose closure can be
argued — a closed grammar over numeral literals with pinned `PLUS`/`MULT`
encodings is the obvious candidate — and that is pre-registered as a separate
bounded experiment, `EXP-ADR011-01`, rather than smuggled in here. Until it
lands, this ADR proposes a profile that is correct and insufficient.

Nothing here applies to higher-order terms. η and extensionality are not
decided by this observation, and no claim is made that they are.

## `profile_id` names a profile; it does not identify one

A settlement that carried only `profile_id` was under an unknown profile. Build
a second profile with the **same id** and an observer returning the marker `X`
for every term, and:

```text
same profile_id: sigma-glyph/adr-011/church@v0
  real profile      church(5) vs church(7)  ->  UNEQUAL
  forged observer   church(5) vs church(7)  ->  EQUAL
```

**The commitment is taken before the profile runs, not while the settlement is
being written.** It was computed last. A profile whose source became unreadable
between import and settlement therefore had its admission run, both observers
run and the store written, and only then raised — the system executed a profile
and afterwards discovered it could not say which profile it had executed.
Control 15/15b requires the observer to have been called **exactly zero times**
before the refusal; mutation M8 moves the commitment back to the end and
requires 15b, not 15, to go red.

**The Book anchor is the anchor.** This field carried the prose *"Book I
document version 0.6.0, anchor e3e5d008…, adopted …"*, and the control over it
asked only that the string was non-empty and copied from the profile — both true
of a value no verifier could compare to anything. It is now exactly 64 hex,
`e3e5d00863d7dcf875258168029611949339fe307ad3d9e5e565c12543cc94fd`, with the
prose moved to `book_context`. Control 13c recomputes it from
`spec/book-1-truth.md` by a route that does not call the profile's own function;
13e flips one hex character, which the shape check cannot see; 13f refuses a
settlement outright when the anchor is not 64 hex.

Both settlements print the same profile name. So the settlement carries a
`profile_commitment`: a digest over the prose contract, the markers, the Book I
edition, and code digests of `observe` and `admit` — the fields that change what
a verdict means. Control 13/13b holds the pair apart; mutation M7 makes the
commitment blind to `observe` and requires 13b, specifically, to go red.

The commitment digests **source text, not bytecode**. The first version
digested `co_code` and CI caught it on the first run: the same profile
committed to `98d3432c…` on CPython 3.14 and `f2592195…` on 3.12. A digest that
cannot distinguish "a different profile" from "a different Python" is not a
commitment. The receipt is generated on the author's interpreter and verified
in CI on 3.12, and that differential is the whole of the evidence: the property
held is agreement between **3.12 and 3.14**, not across CPython in general.
`inspect.getsource` and `repr` carry no cross-version canonicality contract that
this ADR establishes.

**Portable settlement is BLOCKED, and the commitment does not unblock it.**
That digest identifies a profile to another run of the same Python module,
on CPython 3.12 and 3.14 — the two it is verified on, not a general
cross-version guarantee: `inspect.getsource` and `repr` carry no canonical
contract this ADR establishes. It commits to one file's bytes,
so a Go or Rust
implementation of the same profile computes a different value, and two
implementations cannot agree that they settled under one profile. Closing this
needs a profile descriptor that is itself canonical bytes in the store, with
admission and observation expressed in something both implementations execute.
**No such descriptor exists in Book I today and this ADR does not propose one.**
Until it does, a settlement is portable evidence only alongside the module that
produced it. A profile whose `observe` has no readable source is refused a
commitment outright rather than given a partial one (control 14).

## Executable reference and controls

- [`adr-011/equality_profile.py`](adr-011/equality_profile.py) — the profile and
  `settle_eq`.
- [`adr-011/selftest.py`](adr-011/selftest.py) — controls, digest oracles and
  mutations. The count is deliberately not quoted here: it has changed four
  times while this ADR was being corrected, and a number in prose that nobody
  re-runs is exactly the kind of claim this document exists to stop making. Run
  it.
- [`adr-011/benchmark.json`](adr-011/benchmark.json) — machine-readable receipt.

Each mutation restores one of the candidate's defects and requires the control
that guards it, for its own reason, to go red: no exit check (two exhausted runs
compare equal), sequential budget (a number is unequal to itself; the verdict
flips with order), no marker admission (`λf.λx.X` settles equal to `church(0)`),
and admission of a computed expression.

## Measurements, restated

From `benchmark.json` — at the oracle source commit, measurement-input
digests and Book I anchor recorded there — both sides reported separately:

| case | verdict | ATP per side |
| --- | --- | ---: |
| church(0) | EQUAL | 12 |
| church(1) | EQUAL | 49 |
| church(5) | EQUAL | 197 |
| church(12) | EQUAL | 456 |
| church(50) | EQUAL | 1 862 |
| church(100) | EQUAL | 3 712 |
| church(200) | EQUAL | 7 412 |

**What this shows.** On the measured Church family, the cost of obtaining the
observation normal form scaled roughly linearly with the length of the spine
`Fⁿ(X)` — about 37 ATP per unit on this revision and this interpreter.

**What it does not show.** Not that normal-form equality is linear in general.
Normalizing an arbitrary term may be expensive or may not terminate. These are
ATP measurements on one revision and one interpreter, not a complexity result,
and nothing in CI protects the shape of the curve. What *is* constant is the comparison of two
already-obtained addresses: two 32-byte digests, regardless of the data behind
them. Obtaining them is the cost above.

## Addendum: what the Warrant execution actually showed

A raw `ski@v1` check with a non-boolean `expect` — `term = (PLUS 74 1) F X`,
`expect = NodeHash(F⁷⁵(X))`, `atp = 2108` — was filed into a live evidence pack
and re-executes to `pass`.

**It shows:** `ski@v1` permits a non-boolean `expect`; one program can be
re-executed against a fixed normal-form address; `validate_ski_blob` requires
only hex64 there; and no new boolean encoding is needed for that.

**It does not show:** a two-sided equality receipt — it is one execution against
a constant, not two executions compared. Nor domain soundness, nor that the
bundled oracle returned two exits, nor that "no machinery is missing." The
machinery that was missing is the profile: the domain, the marker discipline,
the per-side budgets and the exits.

## Prior art

Hash-consing (Ershov 1958; ATerm maximal sharing) — constant-time equality of
built terms. Merkle trees, git, Nix — identity of data by root hash.
Normalization-by-evaluation — deciding conversion by evaluating at a generic
point.

The Church profile uses a domain-specific reification/observation into a
canonical constructor spine. It is **adjacent to** NbE, hash-consing and Merkle
identity; no novelty is claimed for those components, and it is not "exactly
NbE" — classical NbE has an evaluation and a reflect/reify pair, and no formal
correspondence is established here.

The only candidate contribution is the composition: domain-qualified
normalization, explicit per-side budgets, two execution receipts, and address
comparison as a settlement artifact. **If a prior statement of that composition
exists, this ADR becomes a profile-with-citation.** That is an acceptable
outcome and is not treated as a falsification of anything worth keeping.

## Epistemic ledger

**PROVED / DERIVED**
- The Σ-lemma above, from Book I §3.4's Receipt and the collision resistance of
  SHA-256. That is the only entry in this class.

**ARGUED / DERIVED UNDER ASSUMPTIONS**
- Reflection and preservation for `church@v0` on its admitted domain. The
  argument is prose about the shape of the spine `Fⁿ(X)`, and it inherits the
  correctness of the C1 λ→SKI compilation (Book I §6) for every admitted `n`.
  There is no general proof of that compilation here and none is cited, so
  these two properties are *argued*, not derived: they are checked on the
  measured values and believed beyond them. Demoted from `PROVED / DERIVED`
  during review, where the distinction was pointed out.

**MEASURED**
- The per-side ATP costs in `benchmark.json`, at a recorded SHA, anchor and
  interpreter.
- The four defects of the candidate pseudocode, each with concrete inputs,
  budgets and hashes.
- The in-language EQN figures, by a different harness, cited not reproduced.

**ASSUMED**
- SHA-256 collision resistance.
- The correctness of `impl/sigma_glyph.py` as the oracle these receipts are read
  against.
- That both sides resolve against environments agreeing on the demanded hashes
  (Book I §3.5).

**NOT ESTABLISHED**
- Equality of arbitrary SKI terms.
- Equality of higher-order terms; η/extensionality is not decided.
- Mechanical admission of computed Church-natural expressions — **there is
  none**.
- Any asymptotic complexity claim for terms outside the measured family.
- Novelty over the prior art above.
- Independent interoperability: no second implementation of this profile exists.
- Any need for a kernel-level `EQ` primitive. The idiom runs at the API layer
  and no case has been shown that requires otherwise.

## Falsifiers

- A prior statement of the settlement composition → this ADR reduces to a
  citation.
- A term in `church@v0`'s admitted domain where the observation yields a false
  verdict → the domain argument is wrong, not merely narrow.
- A mechanical admission for computed Church expressions → the largest gap here
  closes, and the profile becomes useful for the case that motivated it.
- A C1-grade compiler bringing in-language equality within ~10× → the design
  argument collapses to convenience.
