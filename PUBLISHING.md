# Publishing `sigma-glyph` to PyPI

Publishing is automated with **Trusted Publishing (OIDC)**; no API token is
stored anywhere. Cutting a GitHub Release builds, validates and publishes the
package (`.github/workflows/publish.yml`).

- **Distribution name:** `sigma-glyph`, held by this repository's Trusted
  Publisher: <https://pypi.org/project/sigma-glyph/>.
- **Import modules:** `sigma_glyph` (Book I), `sigma_resume` (the resumable
  kernel) and `sigma_provider` (its consumer surface and process protocol). No
  console scripts; each module runs with `python -m`. Through 0.8.0 the
  distribution also shipped `sigma_wave` (Book II) and `sigma_federation`
  (Book III); both were retired on 2026-10-31 and the next distribution does not
  ship them.
- **What ships:** those modules. Not the specification, not `tests/`, not the
  Rust implementation, not the proofs.
- **Released:** **0.6.6.post1** (2026-07-30, packaging only), **0.6.7**
  (2026-07-31), **0.7.0** (2026-09-17), **0.8.0** (2026-10-19, the first with
  `sigma_resume` and `sigma_provider`) and **1.0.0** (2026-11-01, Book I and
  sigma-resume only, cut by claude under the owner's delegation). All five went
  out through the workflow below; none was uploaded by hand. If this file and PyPI disagree, PyPI is
  right.
- **What has been checked about a published artifact:** 0.6.7 and 0.7.0 were
  installed from PyPI into a clean venv and their self-tests run. For 0.7.0 the
  served wheel and sdist digests were also compared with the release run's own
  artifacts and matched, the installed modules matched `impl/` at the tag, and
  the conformance suites the distribution does not ship were replayed against
  the installed modules from outside any checkout. All of it on one host, by the
  party that cut the release (`SECURITY-ASSUMPTIONS.md` SA-8). For 1.0.0 the
  same read-back held: wheel `36d3354d…` and sdist `7878e718…` as the release
  run (41339906440) built them, the three installed modules byte-identical to
  `impl/` at `v1.0.0`, and their self-tests passing from a clean venv.

## Authorization

Publishing is outward-facing and hard to reverse: a version number on PyPI
cannot be reused even after a delete. Nothing in the pipeline publishes until a
Release is cut. Since 2026-11-01 the owner delegates that to the agents, decided
by the evidence (`AGENTS.md` rule 5): master CI green on the commit, every backed
claim accepted, `pyproject.toml` naming the tag's version, and, for a normative
version, its adoption record accepted. This file describes how; it is not the
evidence.

## Releasing

1. Bump `version` in `pyproject.toml` and merge it to `master` through a pull
   request (`AGENTS.md` rule 1).
2. Cut a GitHub Release with tag **`v<version>`**, the exact pyproject version.
   The workflow fails the build if they disagree:

   ```bash
   gh release create v0.9.0 --generate-notes
   ```
3. The workflow builds, runs `twine check`, installs the wheel into a fresh
   venv, runs the self-tests **from /tmp** (not from the checkout), and runs
   `tools/check_release_surface.py`, which fails the build if the installed
   package does not behave the way the documentation says. Only then does it
   publish through OIDC (`gh run watch` to follow it).
4. Read back the public install:

   ```bash
   python3 -m venv /tmp/v && /tmp/v/bin/pip install sigma-glyph==<version>
   /tmp/v/bin/python -m sigma_glyph        # -> ALL PASS
   /tmp/v/bin/python -m sigma_provider     # -> PROVIDER: ALL PASS (16/16)
   ```

The publisher and the `pypi` environment already exist. Re-establishing them
(an ordinary, not pending, publisher: project `sigma-glyph`, owner `s0fractal`,
repository `sigma-glyph`, workflow `publish.yml`, environment `pypi`) is the
owner's act on PyPI and GitHub.

## Dry run on TestPyPI (never performed)

The `testpypi` job has never executed; this is a plan, not a tested procedure.
With a TestPyPI publisher and a `testpypi` environment in place:

```bash
gh workflow run publish.yml
python3 -m venv /tmp/tv && /tmp/tv/bin/pip install -i https://test.pypi.org/simple/ sigma-glyph
/tmp/tv/bin/python -m sigma_glyph
```

## What an installed copy can and cannot re-derive

The conformance corpus (`tests/spec_conformance/vectors.json`) and the claims
witnesses live in the repository, not in the distribution; full re-derivation
needs a checkout:

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
tools/test-all.sh
```
