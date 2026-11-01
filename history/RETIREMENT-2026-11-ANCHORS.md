# Retirement: the detached anchor registry (2026-11-01)

**Status:** APPLIED on branch `release/v1.0.0`. The before revision is `b691941a56fc2d6af740a9517fa8d166b146885c` (master).

**Authority:** the repository owner told the agent in the working session on 2026-11-01, when the agent proposed a `v1.0.0` section in `spec/ANCHORS.txt`: "та ці анхори вроді вже як і не потрібні, бо це ж все до warrant повноцінного було, шоб якусь цілісність тримати. ти часом стараєшся тягнути супровід того, що вже має дуже мало сенсу" ("these anchors seem no longer needed: they came before Warrant proper, to keep some integrity; you sometimes keep maintaining what makes very little sense any more"). This line records where the act was given.

## Why the registry adds nothing now

`spec/ANCHORS.txt` listed, per bundle, `NodeHash(LITERAL, SHA-256(bytes))` of every anchored file, adopted by threshold warrants of Warrant 0.x. Each thing it held is held elsewhere now:

- the bytes of a released version: its release tag (`v0.5.0` … `v0.8.0`, and `v1.0.0` on release);
- that the normative sentences are still the ones agreed: every claim quotes its sentence verbatim, and `warrant claims check` refuses one its document no longer holds; with `coverage`, every MUST, SHALL and REQUIRED lies in a claim;
- what was checked about those bytes: the claims checker's acceptances name the commit and the tree;
- adoption: a signed record of `.warrant/` (the roadmap goal "sigma-glyph 1.0" met), not a heading;
- the suite pinned to the Book: `book1_anchor` in `tests/spec_conformance/vectors.json`, checked by `tools/spec_audit.py` against the Book's own bytes.

Book I §8 keeps the SpecAnchor as the identity of a version, now computed from the bytes at its release tag rather than read from a registry.

## Subjects

| Path | SHA-256 at the before revision |
|---|---|
| `spec/ANCHORS.txt` | `7410d9732b91b623126fed74037ed1fb619ce4c43dbf409994abf25ca77665fd` |
| `tools/verify_anchors.py` | `fc935d1988e7661f8431e9b05ece2d5c35dc8c76ae4c0d2e32bcde6126be9bcd` |

With them: the adopted-bundle heading of README and its checks in `tools/version_check.py` (and their self-test cases), `anchor_matches` in `tools/spec_audit.py` (and its self-test case I), the anchor steps of `.github/workflows/ci.yml` and `tools/test-all.sh`.

## What is lost from the default tree

- The bundle history v0.1 … v0.7.0 as one file with its anchors: it stays at the before revision and in each release tag.
- Verifying the retired Books II and III, GOV-anchors and LORE at `96414ab` through `verify_anchors.py`: `history/RETIREMENT-2026-10-ECHO.md` lists their SHA-256 at that revision.

Retrieve with `git show b691941:spec/ANCHORS.txt`; anything retrieved carries `ARCHIVED / NOT CURRENT PRECEDENT`.
