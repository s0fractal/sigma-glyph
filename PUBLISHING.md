# Publishing `sigma-glyph` to PyPI

Publishing is automated with **Trusted Publishing (OIDC)** — no API tokens are
stored anywhere. Cutting a GitHub Release builds, validates, and publishes the
package (`.github/workflows/publish.yml`). You do a **one-time** setup on PyPI,
then every release publishes itself.

- **Distribution name:** `sigma-glyph` — claimed, and held by this repository's
  Trusted Publisher: <https://pypi.org/project/sigma-glyph/>.
- **Import modules:** `sigma_glyph` (Book I), `sigma_resume` (the DRAFT
  resumable kernel) and `sigma_provider` (its consumer surface and process
  protocol). No console scripts; each module is runnable with `python -m`.
  Through 0.8.0 the distribution also shipped `sigma_wave` (Book II) and
  `sigma_federation` (Book III); both were retired on 2026-10-31, and the next
  distribution does not ship them.
- **What ships:** those modules. Not the spec, not `tests/`, not the Rust
  implementation, not the proofs.
- **Released so far:** **0.6.6.post1** (2026-07-30, packaging only), **0.6.7**
  (2026-07-31) and **0.7.0** (2026-09-17, the latest release, the first that
  packages the adopted v0.7.0 bundle). All three went out through the workflow
  below; no release has ever been uploaded by hand. `master` carries release
  tags from `v0.5.0` through `v0.7.0`. A bundle adopted in `spec/ANCHORS.txt`
  still creates no tag and no release of its own: `v0.7.0` was adopted on
  2026-08-30 and released on 2026-09-17, two separate acts. README's "Status by surface" keeps the adopted
  bundle and the distribution apart.
- **What has been checked about the published artifact:** for 0.6.7, the
  maintainer installed it from PyPI into a clean venv and ran the three
  self-tests to `ALL PASS`. For 0.7.0 the same was done, plus: the PyPI wheel
  and sdist digests were compared against the release run's own `dist`
  artifact and matched exactly; the installed modules were compared to `impl/`
  at the tag and matched; and the anchored Book I/II/III suites — which the
  distribution does not ship — were replayed from a corpus outside any
  checkout against the installed modules (148/148, 33/33, 40/40), with
  mutation controls showing that replay can fail. All of it on one host, by
  the same party that cut the release; nobody else is known to have installed
  either version — see `SECURITY-ASSUMPTIONS.md` SA-8. If this file and PyPI
  ever disagree, PyPI is right.

## Governance note

`AGENTS.md` rule 5: publishing is a hard-to-reverse, outward-facing action and
needs explicit human authorization for the specific action. This file describes
how; it is not an approval, and nothing in the pipeline publishes without a human
cutting a Release.

## One-time setup (you, on the web — I can't do this part)

> **Already done.** The publisher exists and has minted tokens for two real
> releases. This section is kept for the next project, and for re-establishing
> the publisher if it is ever lost; skip it unless one of those applies. Note
> that the project now exists on PyPI, so re-establishing it is an ordinary
> publisher, not a *pending* one.

### 1. Add a "pending publisher" on PyPI

Before the first publish the project did not exist on PyPI, so this was a
*pending* publisher: it creates the project on the first publish. Go to
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
(recommended: "Required reviewers" = you). The name is already claimed; the gate
is now about not shipping a bad artifact, and a version number on PyPI cannot be
reused even after a delete.

## Releasing (every version, automated)

1. Bump `version` in `pyproject.toml` and merge to `master` through the normal
   branch + review path (`AGENTS.md` rule 1 — never commit to `master` directly).
2. Cut a GitHub Release with tag **`v<version>`** — the `v` plus the exact
   pyproject version. The workflow fails the build if they disagree:

   ```bash
   gh release create v0.8.0 --generate-notes
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
   /tmp/v/bin/python -m sigma_provider     # -> PROVIDER: ALL PASS (16/16), since 0.8.0
   ```

## Dry run on TestPyPI (never actually performed)

Both real releases went straight to PyPI; the `testpypi` job has never executed,
so this is a documented plan and not a tested procedure. After the TestPyPI
pending publisher + `testpypi` environment exist:

```bash
gh workflow run publish.yml
gh run watch
python3 -m venv /tmp/tv && /tmp/tv/bin/pip install -i https://test.pypi.org/simple/ sigma-glyph
/tmp/tv/bin/python -m sigma_glyph
```

## What an installed copy can and cannot re-derive

The replay corpus (`tests/spec_conformance/vectors.json`) lives in the repo and
is **not** part of the distribution; full re-derivation requires a checkout:

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
tools/test-all.sh
```

Until 0.8.0 the Book II and III modules announced their recorded-vector replay
as an explicit SKIP from an installed copy and refused their `gen` verb there
(`tools/check_release_surface.py` asserted both); the history of those two
fixes is in `CHANGELOG.md` and at commit `96414ab`.

## After the first publish — done

- `README.md` and `QUICKSTART.md` carry the install one-liner alongside the
  `git clone` path, with the checkout named as what full re-derivation still
  requires.
- The published versions are recorded at the top of this file.

## Manual fallback (if you ever bypass CI)

```bash
python3 -m build && twine check dist/*
twine upload dist/*                    # needs your PyPI token in ~/.pypirc
```

Bypassing CI bypasses the release gate, which is the only thing that has ever
looked at this package as an installed artifact. Run
`tools/check_release_surface.py --wheel … --bin …` by hand first.
