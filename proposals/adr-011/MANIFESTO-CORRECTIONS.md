# Corrections owed to `manifesto/drafts/ADDRESSING-IS-EQUALITY.md` (AIE-0.1)

**Status:** a list, not an edit. Nothing in `~/Projects/manifesto` is touched by
this ADR, and no Zenodo record is created or updated. Whether and how to apply
these is a separate decision for the manifesto's own process.

**Basis:** `proposals/ADR-011-eq-by-normal-form-address.md` and the executable
profile in this directory. AIE-0.1 is the note ADR-011 was written against; one
correction (commit `7add656`, "AIE soundness was NOT unconditional") is already
in the manifesto tree and is *not* repeated here. Everything below is still
outstanding as of this file's date.

Each item names what the draft says, what is actually established, and the
smallest change that would make the sentence true.

---

## C1 — The status line promises a kernel primitive that this ADR does not propose

> **Статус:** виміряний принцип + кандидат у kernel-примітив Σ-GLYPH.

and §5.1:

> **Кандидат у kernel-примітив Σ-GLYPH:** `EQ(h₁, h₂, atp)` …

ADR-011 proposes **no** `EQ` kernel primitive, and adding one was excluded from
its scope. What it specifies is a non-normative *profile* over the existing
`eval` — no new Book I opcode, no change to any anchored byte. A reader of
AIE-0.1 who then reads ADR-011 will find the promised candidate missing.

**Change:** drop "кандидат у kernel-примітив" from the status line; rewrite §5.1
as an open question ("чи потрібен kernel-рівень взагалі — не вирішено; ADR-011
свідомо його не пропонує"), or delete it.

## C2 — §1 states the principle without the three conditions that make it hold

The displayed implication carries no profile, no exit condition and no budget:

$$a =_{\text{settled}} b \Longleftarrow \mathrm{hash}(\mathrm{NF}(a\,F\,X)) = \mathrm{hash}(\mathrm{NF}(b\,F\,X))$$

Three things are load-bearing and absent. **(a)** Both evaluations must exit
`normal_form`; two `atp_exhausted` runs also agree on a hash and mean nothing —
this was defect 2 of the ADR's own candidate pseudocode. **(b)** Each side needs
its own budget; a shared, sequentially-drained budget makes the verdict depend
on argument order — defect 3, reproducible at atp 100/200/300. **(c)** $a$ and
$b$ must be *admitted by a named profile*; §3 now says this in prose, but §1 is
what gets quoted.

**Change:** put the profile, the two-`normal_form` requirement and per-side
budgets into the formula's own statement, or mark §1 explicitly as the informal
version of §3.

## C3 — The two columns of the §2 table come from different harnesses, and the table does not say so

The hash-idiom column was produced by `manifesto/tools/glyphlib.py`, which
admits any lambda expression and states no domain. The EQN column came from a
different harness again. Neither is `church@v0`, whose measured costs for the
*same shape* of work are 12 / 49 / 123 / 197 / 456 ATP per side (see
`benchmark.json`) — different numbers, because different markers, a different
observation and a different budget policy.

The `~250` and `~500` entries are also marked approximate while `601` is exact,
with no note on where the tilde comes from.

**Change:** label each column with the harness, revision and date that produced
it; either resolve the tildes or say what they approximate. Add: "числа з різних
harness-ів не порівнювані порядково без ре-вимірювання на одному."

## C4 — "~50 ATP/одиницю" is a per-harness constant presented as a property of the idiom

`church@v0` measures ≈37 ATP per unit of spine on the same family. The figure is
not wrong; it is unattributed, and it is attached to a claim about "the
hash idiom" rather than about one implementation on one revision.

**Change:** attribute it, and state that the slope is a measurement, not a bound
— nothing in CI protects the shape of that curve.

## C5 — The counterexample digest is real but belongs to a different marker set than the profile cited beside it

§3 gives the collision address as `8785b7dd…` and, in the same sentence, cites
`EqualityProfile` with `admitted_domain`. `8785b7dd…` is the LITERAL node of the
ad-hoc marker `sha("X")` used by the *candidate* ADR. The profile that actually
exists uses domain-separated markers, and its collision address is

```
X_node   e37391c4fac298b26e097562e8411695e989d4dc3a391a28f2ac5287eaa80211
F_node   92b1cec9ba6035599d1977c2f6bab8fbc2d74b9248775260baf5c710664126c1
```

Both digests are genuine; the sentence mixes two marker sets, so a reader
recomputing it against `equality_profile.py` will not reproduce the number.

**Change:** use `e37391c4…` and name the marker definition, or keep `8785b7dd…`
and say explicitly that it comes from the ad-hoc `sha("F")/sha("X")` markers of
the candidate, not from the profile.

## C6 — The admitted domain is described far more widely than the profile implements

> Соундність тримається лише на admitted domain — множині термів, які **НЕ
> іменують маркери профілю**.

That describes a profile admitting everything except marker-naming terms.
`church@v0` admits far less: **literally written numerals only**. It refuses
`PLUS 7 5` — that is, it cannot perform the very `7+5=12` settlement that the
draft's own origin story is about. Mechanical admission of computed Church
naturals is pre-registered as `EXP-ADR011-01` and **not started**.

**Change:** replace the description with the profile's actual domain, and state
plainly that the `601` ATP headline figure is not currently reproducible under
any admitted profile.

## C7 — "метод повний" for first-order data is asserted, not established

> Для даних першого порядку … NF канонічна → **метод повний**.

ADR-011 files completeness beyond the measured family under **NOT ESTABLISHED**,
and files reflection/preservation for `church@v0` under **ARGUED / DERIVED UNDER
ASSUMPTIONS** — the spine argument is prose and inherits the correctness of the
C1 λ→SKI compilation for every admitted `n`, for which no general proof is given
or cited here.

**Change:** downgrade to "аргументовано для виміряної сім'ї, не доведено
загально", and name the C1 dependency.

## C8 — §5.2–§5.4 inherit the unconditional reading

Semantic mass (`M(C)` dedup by address), the SSD gate's arithmetic claims, and
Warrant justification-dedup are each stated as standing *on* the principle. With
the principle now conditional on an admitted profile, three consumers inherit
conditions they do not state. In particular §5.4 — "два агенти, що дійшли до
однієї NF, довели одне й те саме" — is exactly the inference the counterexample
breaks when the terms are not admitted.

**Change:** each of the three gets the qualifier, or is marked as depending on a
profile that has not yet been written for its domain. §5.4 needs it most.

## C9 — The title should be marked historical everywhere, not only in §3

§3 already concedes that "Addressing is equality" is "історична назва інженерної
знахідки, не теорема". The title, the status line and §1 still assert it. The
ADR's thesis is the corrected form: *an address settles equality only after an
admitted profile has made the observation canonical.*

**Change:** carry the concession into the title line or a subtitle, so the
retraction is not three sections downstream of the claim.

## C10 — F3 is closer to live than the draft suggests

> **F3:** kernel-EQ виявиться непотрібним — компілятор кращої якості (C1) зведе
> внутрішньомовну рівність до порівнянних цін → 10⁵-аргумент зникає.

The EQN blow-up is attributed in §2 to lazy reduction without sharing — i.e. to
a property of the reducer that measured it, not of the language. That makes the
10⁵ ratio an artifact of one compiler-plus-reducer pair until it is re-measured
on another, which is F3's own condition. It should not be read as refuted, but
neither is it dormant.

**Change:** note that F3 has not been tested, and that the ratio is a
harness-relative measurement.

## C11 — §5.4's cross-agent dedup needs portable settlement, which is blocked

> **Warrant:** дедуплікація обґрунтувань за адресою закриття — два агенти, що
> дійшли до однієї NF, довели одне й те саме, і це видно без читання доказів.

Two agents agreeing on an address have settled the same thing only if they
settled under the same profile — and naming a profile is not identifying one.
A profile carrying the id `sigma-glyph/adr-011/church@v0` with an observer that
returns the marker for every term settles `church(5)` EQUAL to `church(7)`, and
its settlement prints that same id.

ADR-011 answers this with a `profile_commitment`, which is enough *within one
Python module* and explicitly not enough across implementations: it commits to
CPython code objects and one file's bytes. Cross-agent dedup is precisely the
cross-implementation case, so it needs a content-addressed profile descriptor
that does not exist in Book I today and that ADR-011 does not propose.

**Change:** mark §5.4 as depending on portable settlement, and name the missing
descriptor as its blocker rather than presenting the dedup as available.

---

## Not corrections

- The **direction of the asymmetry** is not disputed. In-language EQN on
  computed numerals was measured expensive on that harness, and nothing here
  claims otherwise.
- The **prior art section (§4)** is honest, and ADR-011 keeps its posture: if a
  prior statement of the settlement composition exists, the contribution
  degrades to a citation, which is an acceptable outcome.
- The **already-applied soundness correction** (`7add656`) is correct in
  direction; C5–C7 refine it rather than reverse it.
