#!/usr/bin/env python3
"""Measure the Church profile and write a machine-readable receipt.

    python3 proposals/adr-011/benchmark.py > benchmark.json

Every side is reported separately: root, exit, result hash, ATP. What the
numbers do NOT establish is written into the receipt itself, because a table of
costs with no scope is how "linear" became a claim about arbitrary terms.
"""
import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "impl"))

import equality_profile as ep      # noqa: E402
import sigma_glyph as sg           # noqa: E402

ROOT = HERE.parents[1]


def oracle_source_commit():
    """The commit that last changed the ORACLE, not whatever HEAD is now.

    This was `git rev-parse HEAD` under the name `oracle_base_sha`. HEAD moves
    every time anything in the repository is committed, including this ADR, so
    regenerating the receipt after a commit dirtied it although
    `impl/sigma_glyph.py` had not changed by a byte.
    """
    return subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%H",
         "--", "impl/sigma_glyph.py"],
        capture_output=True, text=True, check=True).stdout.strip()


def _digest(name):
    import hashlib
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


MEASUREMENT_INPUTS = ("proposals/adr-011/equality_profile.py",
                      "proposals/adr-011/benchmark.py",
                      "impl/sigma_glyph.py")

# Shipped alongside and checked against these numbers, but they do not produce
# them. Calling all five "the files that determine the numbers" was wrong: the
# ADR and the selftest document and verify the receipt, they do not compute it.
CO_RELEASED_CONTEXT = ("proposals/ADR-011-eq-by-normal-form-address.md",
                       "proposals/adr-011/selftest.py",
                       "proposals/EXP-ADR011-01-church-nat-admission.md")


def source_digests():
    return ({name: _digest(name) for name in MEASUREMENT_INPUTS},
            {name: _digest(name) for name in CO_RELEASED_CONTEXT})


def book_anchor():
    import hashlib
    data = (ROOT / "spec/book-1-truth.md").read_bytes()
    return hashlib.sha256(bytes([0, 1]) + hashlib.sha256(data).digest()).hexdigest()


def measure(pairs, budget=5_000_000):
    rows = []
    for label, a, b in pairs:
        settlement = ep.settle_eq(ep.CHURCH_V0, a, b, budget, budget,
                                  ep.fresh_env())
        rows.append({
            "case": label,
            "verdict": settlement.verdict,
            "profile_id": settlement.profile_id,
            "lhs": settlement.lhs.__dict__ if settlement.lhs else None,
            "rhs": settlement.rhs.__dict__ if settlement.rhs else None,
            "spend_total": settlement.spend_total,
        })
    return rows


# Fields that are facts about WHERE it ran, not about what it measured. Everything
# else is compared exactly.
HOST_SPECIFIC = ("interpreter",)


def check(path):
    """Verify a receipt by rebuilding it and comparing the whole structure.

    The previous version walked the RECORDED rows and compared three fields per
    row. Three counterexamples passed it:

      * a deleted measurement row — invisible, because the walk was over the
        recorded rows;
      * `lhs.exit` changed from `normal_form` to `atp_exhausted` with the
        `result_hash` untouched — the exact receipt gap this ADR is about,
        undetected by the gate written to guard the ADR;
      * `lhs.atp_spent + 1` and `rhs.atp_spent - 1`, leaving `spend_total`
        unchanged.

    So nothing is enumerated by hand any more: `build_receipt()` produces the
    document, `--check` produces a fresh one, and the two are compared
    recursively after removing the host-specific fields.
    """
    import json as _json
    recorded = _json.loads(Path(path).read_text())
    fresh = build_receipt()
    return _differences(_without_host(recorded), _without_host(fresh), "")


def _without_host(receipt):
    return {key: value for key, value in receipt.items()
            if key not in HOST_SPECIFIC}


def _differences(recorded, fresh, where):
    """Every place the two structures disagree, named by path."""
    problems = []
    if type(recorded) is not type(fresh) and not (
            isinstance(recorded, (int, float)) and isinstance(fresh, (int, float))):
        return [f"{where or '<root>'}: recorded {type(recorded).__name__}, "
                f"fresh {type(fresh).__name__}"]
    if isinstance(fresh, dict):
        for key in sorted(set(recorded) | set(fresh)):
            here = f"{where}.{key}" if where else key
            if key not in recorded:
                problems.append(f"{here}: missing from the receipt")
            elif key not in fresh:
                problems.append(f"{here}: in the receipt, not produced any more")
            else:
                problems += _differences(recorded[key], fresh[key], here)
        return problems
    if isinstance(fresh, list):
        if len(recorded) != len(fresh):
            return [f"{where}: recorded {len(recorded)} entries, fresh run "
                    f"produces {len(fresh)}"]
        for index, (was, now) in enumerate(zip(recorded, fresh)):
            problems += _differences(was, now, f"{where}[{index}]")
        return problems
    if recorded != fresh:
        problems.append(f"{where}: recorded {recorded!r}, fresh run gives {fresh!r}")
    return problems


def _pairs():
    pairs = [(f"church({n}) vs church({n})", ep.church(n), ep.church(n))
             for n in (0, 1, 3, 5, 12, 50, 100, 200)]
    return pairs + [("church(5) vs church(7)", ep.church(5), ep.church(7))]


def build_receipt():
    """The receipt. Generation and verification both call THIS."""
    inputs, context = source_digests()
    return {
        "artifact": "sigma-glyph/adr-011/church@v0 benchmark receipt",
        "normative": False,
        "oracle_source_commit": oracle_source_commit(),
        "measurement_inputs": inputs,
        "co_released_context": context,
        "book_1_anchor": book_anchor(),
        "book_1_edition": ep.CHURCH_V0.book_anchor,
        "interpreter": f"{platform.python_implementation()} "
                       f"{platform.python_version()} on {platform.platform()}",
        "budget_each_side": 5_000_000,
        "limits": "impl/sigma_glyph.py DEFAULT limits; no max_atp",
        "markers": ep.CHURCH_V0.marker_definition,
        "profile_id": ep.CHURCH_V0.profile_id,
        "profile_commitment": ep.profile_commitment(ep.CHURCH_V0),
        "profile_commitment_is_local": (
            "identifies the profile to another run of THIS Python module. Not "
            "a content-addressed profile descriptor: another implementation of "
            "the same profile computes a different value. Portable settlement "
            "is blocked until such a descriptor exists."),
        "measurements": measure(_pairs()),
        "profile_cannot_settle": (
            "the case that motivated ADR-011. church@v0 refuses computed "
            "expressions, so `PLUS 7 5` is not measurable here; the 601-ATP "
            "figure belongs to manifesto/tools/glyphlib.py, which admitted any "
            "expression and argued no domain. See EXP-ADR011-01."),
        "what_these_numbers_do_not_establish": [
            "that normal-form equality is linear in general: this is the cost "
            "of obtaining the OBSERVATION normal form on one measured family, "
            "and it scaled roughly linearly with the length of the constructor "
            "spine F^n(X)",
            "anything about terms outside the admitted domain; normalizing an "
            "arbitrary term may be expensive or may not terminate at all",
            "an asymptotic bound of any kind — these are ATP measurements on "
            "one revision and one interpreter, not a complexity result, and "
            "nothing in CI protects the shape of the curve",
            "any comparison against in-language equality: the EQN figures in "
            "the candidate ADR were measured by a different harness and are "
            "cited there, not reproduced here",
        ],
        "what_is_constant": (
            "comparing two ALREADY-OBTAINED addresses is constant in the size "
            "of the data, because it compares two 32-byte digests. Obtaining "
            "them is the cost measured above."),
    }


def main():
    if "--check" in sys.argv:
        problems = check(HERE / "benchmark.json")
        for problem in problems:
            print("  FAIL  " + problem, file=sys.stderr)
        if problems:
            print(f"BENCHMARK-RECEIPT: {len(problems)} field(s) differ from a "
                  f"fresh run")
            return 1
        print("BENCHMARK-RECEIPT: every field except the host bears rebuilding")
        return 0
    json.dump(build_receipt(), sys.stdout, indent=2, sort_keys=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
