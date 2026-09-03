# Warrant verifier reduction — 2026-09-03

Status: **RETIRED FROM THE ACTIVE SURFACE**

Last trunk carrying the local partial verifier:
`f7f96e1e1e13f886865d945932646f695990c4a8`.

## Removed

`tools/warrant_verify.py` independently re-derived a Warrant v0.1/v0.2 subset
inside Sigma-Glyph. It intentionally disagreed with the live Warrant verifier on
signature severity and did not implement settlement. Its callers now use
`tools/warrant_gate.py`, the fail-closed consumer of Warrant's documented machine
report.

## Preserved invariants

- `.warrants/` remains verified in CI through a pinned Warrant implementation.
- malformed, contaminated, inconsistent, downgraded, or negative machine reports
  remain typed refusals; `tests/warrant_gate_test.py` keeps the hostile cases.
- the two-jurisdiction specimen still builds real stores and verifies both of
  them through the same boundary.
- signing-message construction remains centralized in `tools/warrant_sig.py`;
  Sigma-specific threshold and anchor governance remain local.

## Declared loss

A Sigma-Glyph checkout alone no longer performs a partial offline Warrant audit.
It needs `$WARRANT` or the default sibling Warrant checkout. This removes an
alternate semantics rather than an evidence path: the pinned full verifier is
the authority already used by CI and settlement.

Git history preserves the retired implementation and its stricter historical
behavior. Reintroducing it requires a new claim explaining why a second verifier
is more valuable than one shared machine boundary.
