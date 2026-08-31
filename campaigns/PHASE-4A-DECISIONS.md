# Phase 4A — decisions, recorded before the first measurement

**Non-normative.** Nothing here changes a Book, a suite, a schema or an anchor.
Written before any number in the final report was produced; anything changed
after results carries a visible amendment note at the bottom.

## Starting state

```text
sigma-glyph  origin/master  2ff111bb818e00da6f943516841326053cd96600
manifesto    origin/main    e370c42c7e0e3598ebd74fc4dfd3a4c9dcce1045
```

Both matched the heads named in the task; no drift. Worktrees created fresh
from those refs, at `.worktrees/sigma-4a` and `.worktrees/manifesto-4a`. No
existing checkout was switched, cleaned, or otherwise touched.

## Scope

One internal vertical, first consumer `manifesto` only:

```text
adopted specification -> candidate artifact + external manifest
  -> clean isolated install -> manifesto imports the installed package
  -> one new dependency-bound replay fixture
```

This supersedes ADR-012 Appendix A, S0–S3 and the earlier four-state
replay/drift sketch. ADR-012 stays a historical design record and is **not** an
authorisation for the rest of its appendix.

## Legacy verdict, fixed now

The existing SSD pack is a **sealed historical artifact**. Its receipt, its
numbers, its acceptance verdict and its dependency metadata are not modified,
and no sidecar is written that would claim its dependencies were pinned at
settlement time. They were not.

A replay tool handed such a pack refuses with `LEGACY_UNPINNED`. It does not
read current files and call the difference `REFUTED`, does not simulate a
successful replay, and does not reconstruct missing pins after the fact.

## Version policy for the candidate artifact

`spec/VERSIONS.md` states that the bundle number names an adopted set of bytes
and is **not** the version of the software; reading it as such is the mistake
that page exists to prevent. So the candidate wheel is **not** renumbered to
`0.7.0` because the adopted bundle is `v0.7.0`.

It is also not built as a bare `0.6.7`: that is a published PyPI release, and a
second artifact carrying the same version with different bytes is exactly the
confusion this phase is supposed to remove.

**Decision:** build with a PEP 440 **local version identifier** —
`0.6.7+phase4a.<short-source-commit>`. Two reasons, and the second is the one
that matters: it cannot be mistaken for the published release, and PyPI
**rejects local versions outright**, so the artifact is structurally
unpublishable rather than merely unauthorised.

`pyproject.toml` in the repository is left at `0.6.7`. The local version is
applied to a build copy, so the checkout's declared version never disagrees
with what is published.

`api_version` is recorded separately in the manifest and means the shape of the
consumed surface (`eval_receipt`, `Receipt`), not the package version.

## Manifest

External and non-self-referential: a JSON file beside the wheel, naming the
wheel's digest rather than embedding its own. Fields fixed now:

```text
artifact_sha256, artifact_filename, source_commit, software_version,
api_version, adopted_anchor_set_sha256, adopted_bundle,
conformance_inputs[] = (path, sha256), build_environment
```

`conformance_inputs` is a **closed list of (path, sha256)** rather than one
aggregate digest, because there is more than one suite and schema and an
aggregate would not say which one moved.

The manifest asserts exactly one thing:

> This artifact was built from this source commit and checked against these
> adopted specification inputs.

It does **not** assert that the artifact was adopted by the roster.

## New pack shape

Minimal, for one fixture. Not a general evidence framework.

```text
dependencies[]: { dependency_id, sha256, embedded_path }
computation:    { evaluator_artifact_sha256, profile_id, budget, receipt }
```

Dependency bytes are **embedded in the pack**. No network CAS, no shared store.

Field names were chosen after reading `manifesto/drafts/ssd-pack/manifest.json`
and `tools/settle_gate.py`'s receipt shape, and deliberately do not reuse
`dep`/`claims` from the old receipt, so the two formats cannot be confused by a
reader or by a parser.

## Replay and drift are two operations

```text
replay(pack)            -> MATCH | REPLAY_MISMATCH | DEPENDENCY_MISSING | LEGACY_UNPINNED
drift(pack, checkout)   -> SAME  | DRIFT           | CURRENT_MISSING
```

Never one enum. `historical replay = MATCH` together with `current = DRIFT` is a
normal, expected result. Neither value, alone or combined, produces `REFUTED`.
`REFUTED` is reserved for a subject predicate being false on the operands the
pack itself declared.

## Artifact transfer

The wheel is built from an exact Sigma revision, its digest verified, and handed
to a clean environment as a file. It is **not** published and **not** committed
as a binary. If CI cannot be made to do this without publishing, committing a
binary, or a hidden sibling-checkout dependency, the phase stops and reports the
constraint with options rather than inventing a workaround.

`manifesto` CI may separately exercise the already-published `sigma-glyph==0.6.7`
for general API compatibility. That is not evidence about the candidate artifact
and is not to be reported as such.

## Acceptance checks

The fifteen criteria of the task, verbatim in intent: wheel builds; digest
verified before install; manifest binds artifact to source and adopted inputs;
clean isolated install imports from site-packages; conformance passes against
the installed artifact; manifesto runs with no absolute path and no sibling
fallback; one new pack has a full dependency closure; its replay is `MATCH`;
changing the current checkout alone yields `DRIFT`; the old SSD pack yields
`LEGACY_UNPINNED`; every mutation control committed and failing for its own
reason; both trees clean; CI runs real steps; no normative byte changes; no
publish, release, tag, merge or Zenodo action.

## Kill criteria

Stop and report if: a normative change is required; the consumer can only run
via a sibling checkout; the exact candidate artifact cannot reach the test
environment without publishing or committing a binary; the work requires copying
the evaluator or serializer into manifesto; the legacy pack would need an
invented historical dependency; scope grows toward Warrant, S2/S3, a pytest
adapter or a general CAS; the new packaging glue makes more local semantic
decisions than it removes; a control cannot be made discriminating by mutation.

A green CI does not cancel a kill criterion.

## Not checked by this phase

- External portability, independent implementability, public adoption.
- That the candidate artifact would be accepted by the roster.
- Reproducibility of the wheel beyond what is measured and reported here; if two
  clean builds are not byte-identical, that is recorded as a measurement, not
  hidden, and the manifest pins one specific artifact.
- Any consumer other than `manifesto`.
- Migration of existing packs.
