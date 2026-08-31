# Engine paper v2 — deposit candidate manifest

**NOT PUBLISHED.** Nothing here has been uploaded, no Zenodo version has been
created, and no DOI has been reserved. This manifest exists so that the deposit
can be rebuilt and checked by someone who was not present when it was made.

## Source

| | |
| --- | --- |
| repository | `https://github.com/s0fractal/sigma-glyph` |
| source commit (the PDF was built from this) | `47cf57dd6ec2f671d5aaf521094420f97cf566d6` |
| branch | `paper/v2-candidate` |
| adopted release at that commit | `v0.7.0` |
| anchor set | `abf10f2a9c932f31e28973c41658ba728501fef438b35b7538e78c21d37adf59` |
| adoption warrant | `0e634c176b002d02d835e5c6436e4b254d065adeab4bc7704585339567ba46e1` |
| Book I anchor | `e3e5d00863d7dcf875258168029611949339fe307ad3d9e5e565c12543cc94fd` |
| Book I document version | 0.6.0 |

**Why the source commit is not the commit carrying this file.** A manifest that
named its own commit would be impossible to write: adding it changes the commit,
which changes the name. So it records the commit the artifact was *built from*.
`paper.pdf` depends only on `paper.md`, `references.bib` and `build.sh` — pandoc
reads nothing else — so later commits that do not touch those three leave the
digest unchanged, and that was verified by rebuilding at the commit that carries
this manifest and comparing.

## Build

```sh
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
git checkout 47cf57dd6ec2f671d5aaf521094420f97cf566d6
export SOURCE_DATE_EPOCH=1788134400            # 2026-08-31T00:00:00Z
cd papers/one-integer-for-work-and-memory && sh build.sh
```

| | |
| --- | --- |
| pandoc | 3.10.2 |
| tectonic | 0.17.0 |
| git | 2.50.1 (Apple Git-155) |
| `SOURCE_DATE_EPOCH` | `1788134400` |
| host | arm64 Darwin 25.5.0 |

**Reproducibility is byte-identity, conditional on `SOURCE_DATE_EPOCH`.** Two
clean checkouts of `47cf57d`, extracted with `git archive` and built
independently, produced the same `paper.pdf` byte for byte. Built a third time
with `SOURCE_DATE_EPOCH` unset, the digest differed — tectonic stamps the build
time. So the claim is *byte-identical given the pinned epoch and the tool
versions above*, not *byte-identical under any environment*, and `build.sh`
prints which of the two it is doing on every run.

The source archive is `git archive`, which derives its entries from the commit
rather than from the filesystem; regenerating it produced the same digest.

## Files

| SHA-256 | file | bytes |
| --- | --- | ---: |
| `8970a3af97c5e497361a80560e8804c386ec52eb18cf687b22e3a8905ccf9565` | `paper.pdf` | 197645 |
| `2286931cb5ea151ac897d20869c83a71dc52ff03d58ccb8151c6938580d7b900` | `paper.md` | 83777 |
| `fe4ad6c7a60a8515ba03722eb50edacb723b37e4cd04a773a739124384935666` | `references.bib` | 17486 |
| `4c51ad927eafc775bda2919ad7c4251fdd85715db06930f8c39620b110ef4720` | `build.sh` | 1317 |
| `725f613611fa2cb80af54b048e926292879d910f0e8fc57c9b07cbffbc95475d` | `sigma-glyph-47cf57d.zip` | 4526116 |

`paper.pdf` is 25 pages. Every page was rasterised and inspected; title,
author, e-mail, date, table of contents, both §6.3 tables, the §3.9 gate table,
code blocks, Unicode (`λ`, `→`, `Σ`, `×`, `−`) and the bibliography render
correctly, and no page shows an overfull line or a broken link.

The staging directory holds the binaries and is **not committed**:
`.gitignore` excludes `papers/*/paper.pdf`, and this repository has never
tracked a paper PDF. This manifest is the committed artifact.

## The v1 deposit, for comparison

Downloaded from the record, not from any local copy, and verified against the
record's own metadata before use:

| | v1 | v2 candidate |
| --- | --- | --- |
| version DOI | `10.5281/zenodo.22069651` | — not created — |
| concept DOI | `10.5281/zenodo.22069650` | `10.5281/zenodo.22069650` |
| version label | `0.6.7-paper1` | `0.7.0-paper2` *(proposed)* |
| published | 2026-08-23 | — |
| `paper.pdf` md5 | `f07e9c3a6301cf2be34771746d7e5c63` | `483b83a52fc8cf89e4cbcab127f41726` |
| `paper.pdf` sha256 | `dae8a53ad769ba9c843c3b316494e061fa8286f85bd0af3f65057ab702f519c6` | `8970a3af97c5e497361a80560e8804c386ec52eb18cf687b22e3a8905ccf9565` |
| `paper.pdf` bytes | 168286 | 197645 |
| pages | 20 | 25 |
| source archive | `sigma-glyph-7ecba6a.zip`, md5 `73067de1bd2c334621813b25717e4ce4`, sha256 `4b95c4588eeb0a711698d55832781a0d5a22078fa32a4580ff3966c99f85b7d7` | `sigma-glyph-47cf57d.zip` |

The v1 files are kept under `v1-deposited/` with names that cannot be mistaken
for a build output. **v2 must never be written to a path where a reader could
take it for v1**, and v1 is not overwritten by anything here — it could not be,
since it exists only at the DOI.

## Verification after publication

Once a version is created and files are uploaded — a separate, owner-authorised
action that has not happened:

```sh
curl -s https://zenodo.org/api/records/<new-id> -o rec.json
python3 - <<'PY'
import json, hashlib, urllib.request
rec = json.load(open("rec.json"))
for f in rec["files"]:
    data = urllib.request.urlopen(f["links"]["self"]).read()
    algo, digest = f["checksum"].split(":")
    assert len(data) == f["size"], (f["key"], len(data), f["size"])
    assert hashlib.new(algo, data).hexdigest() == digest, f["key"]
    print("ok", f["key"], hashlib.sha256(data).hexdigest())
PY
```

Then compare each printed SHA-256 against the Files table above. A download that
matches Zenodo's own checksum but not this table means the uploaded bytes are
not the reviewed bytes.

## What this manifest does not establish

- That the paper's arguments are correct. The claim audit checks arithmetic,
  digests, revisions and status statements; `tools/paper_claims.py` prints its
  own unchecked list.
- That the build reproduces on another OS, another architecture, or other
  versions of pandoc/tectonic. One host, one toolchain, three builds.
- That anyone other than the author has built it.
