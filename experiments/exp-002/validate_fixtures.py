#!/usr/bin/env python3
"""A neutral reading of EXP-002's input contract, used only to freeze fixtures.

This is not a contestant. It imports neither benchmark implementation and will
not be measured; its single job is to decide, independently of both, what verdict
each frozen byte string deserves, so that a fixture whose author was mistaken is
caught before either side is written.

The contract, from `experiments/EXP-002-wasm-bakeoff-preregistration.md`:

  * at most 16 keys, nesting depth at most 3, at most 4 KiB;
  * keys ASCII; values are strings, integers within +/-2^53, booleans or null;
  * non-canonical input is rejected: duplicate keys, leading zeros, non-minimal
    escapes, trailing content, byte order marks, and any whitespace outside the
    minimal JCS form;
  * policy: amount_minor <= LIMIT_MINOR && currency == "UAH" && !flagged.

Canonicality is decided the only way that does not require a rule per defect:
parse strictly, re-serialise in canonical form, and require the result to equal
the input byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT_MINOR = 500_000
MAX_KEYS = 16
MAX_DEPTH = 3
MAX_BYTES = 4096
INT_BOUND = 2 ** 53
VERDICTS = {"ACCEPT", "REJECT", "MALFORMED"}


class Malformed(Exception):
    pass


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise Malformed(f"duplicate member name: {key}")
        seen[key] = value
    return seen


def _reject_constant(token):
    raise Malformed(f"non-JSON constant: {token}")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def depth_of(value, level: int = 1) -> int:
    if isinstance(value, dict):
        return max([level] + [depth_of(v, level + 1) for v in value.values()])
    if isinstance(value, list):
        return max([level] + [depth_of(v, level + 1) for v in value])
    return level


def check_values(value) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            if not key.isascii():
                raise Malformed(f"non-ASCII key: {key!r}")
            check_values(inner)
        return
    if isinstance(value, list):
        for inner in value:
            check_values(inner)
        return
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        if abs(value) > INT_BOUND:
            raise Malformed(f"integer outside +/-2^53: {value}")
        return
    raise Malformed(f"value type not in the contract: {type(value).__name__}")


def decide(raw: bytes) -> str:
    """ACCEPT, REJECT or MALFORMED for one raw byte string."""
    try:
        if len(raw) > MAX_BYTES:
            raise Malformed(f"{len(raw)} bytes, over the {MAX_BYTES} limit")
        if raw[:3] == b"\xef\xbb\xbf":
            raise Malformed("leading byte order mark")
        text = raw.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_no_duplicates,
                           parse_constant=_reject_constant)
        if not isinstance(value, dict):
            raise Malformed("the record must be a JSON object")
        if canonical(value) != raw:
            raise Malformed("not the canonical serialisation of itself")
        if len(value) > MAX_KEYS:
            raise Malformed(f"{len(value)} keys, over the {MAX_KEYS} limit")
        if depth_of(value) > MAX_DEPTH:
            raise Malformed(f"nesting depth {depth_of(value)}, over {MAX_DEPTH}")
        check_values(value)
        for field, kind in (("amount_minor", int), ("currency", str),
                            ("flagged", bool)):
            if field not in value:
                raise Malformed(f"missing policy field: {field}")
            if isinstance(value[field], bool) != (kind is bool) or not isinstance(
                    value[field], kind):
                raise Malformed(f"{field} has the wrong type")
    except (Malformed, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return "MALFORMED"
    allowed = (value["amount_minor"] <= LIMIT_MINOR
               and value["currency"] == "UAH"
               and not value["flagged"])
    return "ACCEPT" if allowed else "REJECT"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=HERE / "fixtures.json")
    arguments = parser.parse_args()
    manifest = json.loads(arguments.manifest.read_text())
    fixtures = manifest["fixtures"]

    counts, failures = {}, []
    for fixture in fixtures:
        path = HERE / "fixtures" / fixture["file"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != fixture["sha256"]:
            failures.append(f"{fixture['id']}: bytes changed since they were frozen")
            continue
        if fixture["expected"] not in VERDICTS:
            failures.append(f"{fixture['id']}: unknown verdict {fixture['expected']!r}")
            continue
        decided = decide(raw)
        counts[decided] = counts.get(decided, 0) + 1
        if decided != fixture["expected"]:
            failures.append(f"{fixture['id']}: author says {fixture['expected']}, "
                            f"this reading says {decided} — {fixture['why']}")

    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    if failures:
        return 1
    groups = {}
    for fixture in fixtures:
        groups[fixture["group"]] = groups.get(fixture["group"], 0) + 1
    promised = manifest["composition"]
    for name in ("positive", "negative", "adversarial"):
        if groups.get(name) != promised[name]:
            print(f"FAIL composition: {groups.get(name, 0)} {name}, the "
                  f"preregistration promised {promised[name]}", file=sys.stderr)
            return 1
    summary = ", ".join(f"{counts.get(v, 0)} {v}" for v in sorted(VERDICTS))
    shape = ", ".join(f"{groups[n]} {n}" for n in ("positive", "negative", "adversarial"))
    print(f"FIXTURES: {len(fixtures)} frozen, all agree ({summary}); "
          f"composition as preregistered ({shape})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
