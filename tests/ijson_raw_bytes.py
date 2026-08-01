#!/usr/bin/env python3
"""Raw-byte I-JSON gate: the one test that cannot go through the differential.

    python3 tests/ijson_raw_bytes.py

`tests/federation_differential.py` builds every request with Python's `json`
encoder, and that encoder refuses to emit a lone surrogate -- so the harness
physically cannot carry the input that exposed the bug it was meant to cover.
For one commit this file's absence was disclosed in a comment reading "the
executable evidence lives outside this file", which on inspection meant manual
reproduction and nothing else. A disclosed gap is still a gap; this closes it.

What is being pinned (Book III §4, I-JSON, RFC 7493 §2.1): impl-go MUST refuse
input whose strings are not sequences of Unicode scalar values, and MUST make
that decision on the RAW BYTES, before decoding -- because `encoding/json`
silently substitutes U+FFFD and by the time there is a Go string the evidence is
gone. Python's `json` preserves the surrogate instead. Measured on identical
bytes, the two implementations selected different warrants.

The negatives are the point, and the positives are what make them mean anything:
a gate that rejects everything containing the letters `ud800` would pass every
negative here and is caught by the last two cases.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_federation as sf  # noqa: E402

GO_DIR = ROOT / "impl-go"


def build_go():
    out = Path(tempfile.gettempdir()) / "sigma-federation-go-ijson"
    env = os.environ.copy()
    env["GOCACHE"] = str(GO_DIR / ".gocache")
    subprocess.run(["go", "build", "-o", str(out), "."], cwd=GO_DIR,
                   env=env, check=True)
    return out


GO = build_go()

CAND = {
    "warrant_id": "1" * 64,
    "actor": "__ACTOR__",
    "ts": 1,
    "assertion": {"annotation": sf.ASSERTION_TAG, "jurisdiction": sf.J,
                  "node": sf.NODE, "epoch": 1, "wave": sf.W(0, 1, 0)},
}


def request_bytes(actor_json_literal):
    """Build the request as TEXT, splicing the actor in as raw JSON source.

    Deliberately not json.dumps(actor): the whole point is to transmit byte
    sequences Python's encoder would refuse or normalise away.
    """
    req = {"candidates": [CAND], "policy": sf.POLICY_TIE,
           "jurisdiction": sf.J, "node": sf.NODE, "epoch": 1}
    text = json.dumps(req)
    assert '"__ACTOR__"' in text
    return text.replace('"__ACTOR__"', actor_json_literal).encode("utf-8")


def run(raw):
    p = subprocess.run([str(GO), "select"], input=raw,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode().strip()


CASES = [
    # (label, actor literal in raw JSON, must_reject)
    ("unpaired high surrogate", r'"\ud800"', True),
    ("unpaired low surrogate", r'"\udc00"', True),
    ("high surrogate then a plain char", r'"\ud800x"', True),
    ("high surrogate then another high", r'"\ud800\ud801"', True),
    ("surrogate inside a longer string", r'"ok\ud834tail"', True),
    # Positive controls. Without these, "reject anything with ud800 in it"
    # would score a clean sweep above.
    ("valid surrogate pair \\ud834\\udd1e", r'"\ud834\udd1e"', False),
    ("escaped literal backslash-u-d800", r'"\\ud800"', False),
    ("ordinary actor", r'"a"', False),
    ("non-ASCII scalar via escape", r'"\u00e9"', False),
]

fails = []
for label, literal, must_reject in CASES:
    code, err = run(request_bytes(literal))
    rejected = code != 0
    ok = rejected == must_reject
    want = "reject" if must_reject else "accept"
    got = "reject" if rejected else "accept"
    print(f"  {'OK  ' if ok else 'FAIL'}  {label:<36} want={want:<6} got={got}"
          + (f"  ({err[:50]})" if rejected and ok else ""))
    if not ok:
        fails.append(label)

# Trailing data: one JSON text, not a stream.
code, err = run(request_bytes(r'"a"') + b"{}")
ok = code != 0
print(f"  {'OK  ' if ok else 'FAIL'}  {'trailing JSON value after request':<36} "
      f"want=reject  got={'reject' if ok else 'accept'}")
if not ok:
    fails.append("trailing JSON")

# Invalid UTF-8 that is not an escape at all.
code, err = run(request_bytes(r'"a"').replace(b'"a"', b'"\xc3\x28"'))
ok = code != 0
print(f"  {'OK  ' if ok else 'FAIL'}  {'invalid UTF-8 byte sequence':<36} "
      f"want=reject  got={'reject' if ok else 'accept'}")
if not ok:
    fails.append("invalid UTF-8")

print()
if fails:
    print(f"IJSON-RAW-BYTES: FAILURES ({len(fails)}): {', '.join(fails)}")
    raise SystemExit(1)
print(f"IJSON-RAW-BYTES: ALL PASS ({len(CASES) + 2}/{len(CASES) + 2})")
