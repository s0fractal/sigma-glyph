# Publishing `sigma-glyph` to PyPI

Publishing is automated with **Trusted Publishing (OIDC)** — no API tokens are
stored anywhere. Cutting a GitHub Release builds, validates, and publishes the
package (`.github/workflows/publish.yml`). You do a **one-time** setup on PyPI,
then every release publishes itself.

- **Distribution name:** `sigma-glyph` (checked 2026-07-30:
  <https://pypi.org/simple/sigma-glyph/> returns **404**, i.e. the name is free —
  but PyPI is first-come, and that is only true until someone else takes it).
- **Import modules:** `sigma_glyph` (Book I), `sigma_wave` (Book II),
  `sigma_federation` (Book III). No console scripts; each module is runnable with
  `python -m`.
- **What ships:** those three modules. Not the spec, not `tests/`, not the Rust
  or Go implementations, not the proofs.
- **Nothing has ever been published from this repository.** This is the first
  release, and `master` carries no release tags.

## Governance note

`AGENTS.md` rule 5: publishing is a hard-to-reverse, outward-facing action and
needs explicit human authorization for the specific action. This file describes
how; it is not an approval, and nothing in the pipeline publishes without a human
cutting a Release.

## One-time setup (you, on the web — I can't do this part)

### 1. Add a "pending publisher" on PyPI

The project does not exist on PyPI yet, so this is a *pending* publisher: it
creates the project on the first publish. Go to
<https://pypi.org/manage/account/publishing/> → "Add a pending publisher" and
enter **exactly**:

| Field | Value |
|---|---|
| PyPI Project Name | `sigma-glyph` |
| Owner | `s0fractal` |
| Repository name | `sigma-glyph` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

Repeat on <https://test.pypi.org/manage/account/publishing/> with Environment
`testpypi` if you want the dry run below (recommended for a first release).

### 2. Create the GitHub Environments

In the repo → Settings → Environments, create `pypi` (and optionally `testpypi`).
Add protection to `pypi` if you want a manual approval gate before each publish
(recommended: "Required reviewers" = you). The first publish claims the name
permanently; a gate there is cheap.

## Releasing (every version, automated)

1. Bump `version` in `pyproject.toml` and merge to `master` through the normal
   branch + review path (`AGENTS.md` rule 1 — never commit to `master` directly).
2. Cut a GitHub Release with tag **`v0.6.6`** — the `v` plus the exact pyproject
   version. The workflow fails the build if they disagree:

   ```bash
   gh release create v0.6.6 --generate-notes
   ```
3. The `publish` workflow builds, runs `twine check`, installs the wheel into a
   fresh venv, runs all three self-tests **from /tmp** (not from the checkout),
   and then runs `tools/check_release_surface.py`, which fails the build if the
   installed package does not behave the way the documentation says. Only then
   does it publish via OIDC. Watch it:

   ```bash
   gh run watch
   ```
4. Confirm the public install:

   ```bash
   python3 -m venv /tmp/v && /tmp/v/bin/pip install sigma-glyph
   /tmp/v/bin/python -m sigma_glyph        # -> ALL PASS
   /tmp/v/bin/python -m sigma_wave         # -> WAVE: ALL PASS … SKIPPED: recorded-vector replay
   /tmp/v/bin/python -m sigma_federation   # -> FEDERATION: ALL PASS … SKIPPED: …
   ```

## Dry run before the first real release (recommended)

After the TestPyPI pending publisher + `testpypi` environment exist:

```bash
gh workflow run publish.yml
gh run watch
python3 -m venv /tmp/tv && /tmp/tv/bin/pip install -i https://test.pypi.org/simple/ sigma-glyph
/tmp/tv/bin/python -m sigma_federation
```

## What an installed copy can and cannot re-derive

The replay corpora (`tests/spec_conformance/*.json`) live in the repo and are
**not** part of the distribution. So from an installed copy the three self-tests
run their property checks in full and announce the recorded-vector replay — and
Book III's Book-I-unreachable fixture — as an explicit **SKIP**, with the reason
and the command that runs them for real. That is the documented behaviour, and
`tools/check_release_surface.py` asserts it.

Before 2026-07-30 they did something else: `python -m sigma_wave` printed
`FAIL wave_vectors.json present` (13/14, exit 1) and `python -m sigma_federation`
exited 1 with a `FileNotFoundError` traceback. Neither was a real failure; both
were a self-test mistaking "the distribution does not ship this" for "the check
failed". Full re-derivation still requires a checkout:

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
tools/test-all.sh
```

The gate derives its expectation from the wheel's own file list, so if the
corpora are ever shipped as package data it will start demanding that the replay
actually ran, instead of being satisfied by a skip.

### The `gen` verb is refused from an installed copy, on purpose

`sigma_wave` and `sigma_federation` also accept `gen`, which rewrites
`tests/spec_conformance/*.json`. Until 2026-07-31 it ended in a
`FileNotFoundError` traceback from an installed copy (`_REPO` is site-packages'
parent), and no gate had ever run it that way — the release gate ran
`python -m <module>` and nothing else.

It now refuses, with exit 2 and the reason:

```
$ /tmp/v/bin/python -m sigma_wave gen
REFUSING: `gen` regenerates the conformance corpus at
tests/spec_conformance/wave_vectors.json and requires a source checkout …
```

Shipping the corpus as package data would have made the verb "succeed" while
writing a file with no spec text beside it to read the values off and no
committed vectors to diff against — the appearance of a fix. `gen` is a
maintainer verb; the honest installed-copy answer is that it does not apply here.

`tools/check_release_surface.py` now carries a RUNNABLE / NOT_RUNNABLE table for
every verb the modules declare, and **executes all of them** from outside a
checkout. A verb the modules declare and the table does not classify fails the
gate, so a new verb cannot ship unexercised the way `gen` did.

Run it yourself before tagging:

```bash
python3 tools/check_release_surface.py --selftest       # the classifier
python3 tools/check_release_surface.py                  # this checkout
python3 -m build && python3 -m venv /tmp/sv && /tmp/sv/bin/pip install dist/*.whl
python3 tools/check_release_surface.py --wheel dist/*.whl --bin /tmp/sv/bin
```

## After the first publish

- Add the install one-liner to `README.md` / `QUICKSTART.md`, which currently
  only document the `git clone` path.
- Record the published version here; if this file and PyPI ever disagree, PyPI is
  right.

## Manual fallback (if you ever bypass CI)

```bash
python3 -m build && twine check dist/*
twine upload dist/*                    # needs your PyPI token in ~/.pypirc
```

Bypassing CI bypasses the release gate, which is the only thing that has ever
looked at this package as an installed artifact. Run
`tools/check_release_surface.py --wheel … --bin …` by hand first.
