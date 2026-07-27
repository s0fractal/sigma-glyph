# ADR-008 rev 15 + wave budget prototype — independent gate

Date: 2026-07-27  
Branch: `adr-008-rev15-candidate` (`173ab21`, `7031614`)  
Scope: the full precedent-profile branch, with emphasis on the new WRT-001 §8
prototype and current cross-repository synchronization  
Verdict: **AMEND — R0/STRUCTURAL PROBES REMAIN VALUABLE; THE BUDGET CODE IS AN
ACCOUNTING SKETCH, NOT YET A PROTOTYPE OF THE NORMATIVE SAFETY CONTRACT**

## Accepted

- The three original probes run and remain deterministic.
- Genuine R0 is non-filing and uses raw eligibility.
- The foreign-supersede R0 vector remains `pass`.
- The structural join continues to catch all supplied negative edges.
- The budget's check blob commits its integer value and repeated runs report the
  same current sketch cost.
- `tools/test-all.sh` is fully green.

## Findings

### [P1] The prototype accepts the exact schema that WRT-001 now forbids

WRT-001's closed check schema requires `budget`. `v_check()` accepts both the old
field set and the new one, and `verify_citation()` enforces a ceiling only when
the optional field is present. The branch's ordinary happy path therefore still
passes with no budget at all.

There is no adopted legacy `wave@v1` body requiring compatibility:
`0.2+sigma-wave.1` is intentionally not registered. Require `budget` in every
wave check used by this candidate version. If R0 needs a different local query
limit, specify it explicitly rather than making the committed field optional.

### [P1] The under-budget vector performs the full over-budget work

The probe meters only after `read_bytes()` and checks exhaustion at the end.
Its own output is the countervector:

```text
budget = 2350
work performed / reported cost = 4697
terminal result = budget exhausted
```

So the code does not bound re-execution and cannot validate §8's anti-DoS
property. It also omits §8's record, candidate, and schema-validation charges;
missing blob paths cost zero; and `_METER` is mutable global state.

Label this precisely as a **post-hoc blob-cost accounting sketch**, or implement
a per-invocation meter object whose `charge()` and bounded resolver stop before
every unaffordable action. Do not use this output as evidence that the normative
budget works.

### [P1] The prototype inherits the check-budget bootstrap problem

`verify_citation()` calls `load(check_hash, ...)`, which performs unbounded
`Path.read_bytes()`, before it can inspect `check["budget"]`. An attacker can
place an arbitrarily large wrong-digest payload at the check path and force its
materialization outside the committed ceiling.

The Warrant review recommends either placing the budget directly in the reason
or defining a protocol-level maximum encoded check size for the bootstrap read.
The Sigma prototype must exercise the chosen rule with a wrong-digest oversized
check vector.

### [P2] Required boundary vectors are not the vectors currently demonstrated

WRT-001 requires exact-limit and one-under. The probe uses half-cost and
double-cost. An exact fixed point does exist in the current fixture:

```text
budget 0    -> cost 4694
budget 4694 -> cost 4697
budget 4697 -> cost 4697, pass
```

Add the actual fixed-point exact-limit vector and `4696` one-under after the
normative cost trace is frozen. Keep zero, max-uint32, local-cap exact, and
local-cap-plus-one vectors too.

### [P2] ADR-008 is not synchronized with the new check schema

The C1 summary still lists:

```text
{check, entry, query_assertion, threshold, ruleset}
```

without required `budget`. Design criterion 9 still restates the superseded
single LIVE-HEAD formula, and “Remaining” still uses the older item numbering
instead of WRT-001 item 0 plus inseparable items 1–2.

Update the current normative-looking sections; historical changelog entries can
remain if clearly marked superseded.

### [P2] Rev 15 repeats an item-0 parity claim disproved by an in-scope vector

ADR rev 15 says identical trust/genesis bytes authorize identical roots. Escaped
lone-surrogate keys still split Python and Go, as documented in:

`warrant/reviews/2026-07-codex-wrt001-budget-spec-gate.md`.

Do not call item 0 fully closed until that trust and pinned-genesis vector is
permanent.

## Recommendation

Keep the structural/R0 work on the candidate branch. Before treating the budget
commit as more than an accounting sketch:

1. amend WRT-001 §8 per the Warrant review;
2. make `budget` mandatory;
3. implement stepwise bounded charging with invocation-local state;
4. add exact/one-under and oversized-bootstrap vectors; and
5. synchronize ADR's schema, mode criterion, and deferred numbering.

The budget proposal should not be merged or governance-adopted in its current
form. R1/key-state design can continue as specification research, but the meter
must be frozen only after that work fixes the scanned set and traversal.
