#!/usr/bin/env python3
"""Recount the numbers the papers in `papers/` state about this repository.

    python3 tools/paper_claims.py
    python3 tools/paper_claims.py --selftest    # prove the gate can fail

The papers describe this repository. Until they lived in it they were outside
every gate: quantitative claims about `proof_guard.py`, the pin registry, the
Lean sources, the conformance vectors and the implementations, checked by nobody.
Every number happened to be correct on the day they moved in — which is the
point. Correct-by-luck and correct-by-construction look identical right up until
the file changes, and this repository's whole argument is that the difference is
the only thing that matters.

The first version of this script checked seven numbers, all of them in the guard
paper, and listed the engine paper's figures as unchecked "because re-measuring
them is `tools/test-all.sh`'s job". That was wrong twice over: `test-all.sh`
measures nothing and reports no durations, and the numbers it was excusing itself
from were exactly the ones that had gone stale — a Lean file that had grown by a
hundred lines, five evaluator theorems the paper had not counted, a statement-pin
total off by five, three implementation line counts off by hundreds. A checker
whose unchecked list is where the failures hide is the defect this repository
keeps finding in other people's guards.

So: every number a paper states about a file, a count or a registry in this tree
is recounted here, from the file itself. What genuinely cannot be recounted
without running something expensive is named in UNCHECKED, with the command that
would produce it — not with an excuse.

`--selftest` closes the other half. For every load-bearing number, it rewrites
that number in a copy of the paper text and reruns the whole audit, demanding
that the corresponding check fails. A check that cannot fail is not a check.
"""
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "papers"
ENGINE = "one-integer-for-work-and-memory"
GUARD = "twenty-one-ways-past-a-proof-guard"

# Spelled-out numbers are load-bearing too: "Forty-one theorems" going stale is
# exactly as wrong as "41" going stale, and prose is where it happens quietly.
UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90}
WORDS = {word: value for value, word in enumerate(UNITS)}
WORDS.update(TENS)
for _tens, _base in TENS.items():
    for _unit in range(1, 10):
        WORDS[f"{_tens}-{UNITS[_unit]}"] = _base + _unit


def word_int(literal):
    return WORDS[literal.lower()]


def word_of(value):
    for word, other in WORDS.items():
        if other == value:
            return word
    raise ValueError(value)


@dataclass
class Claim:
    """A number as the paper writes it, and where it writes it."""
    label: str
    slug: str
    span: tuple
    literal: str


@dataclass
class Audit:
    texts: dict
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    unchecked: list = field(default_factory=list)
    claims: list = field(default_factory=list)

    def chk(self, label, stated, actual):
        (self.passed if stated == actual else self.failed).append(
            (label, stated, actual))

    def note(self, reason):
        self.unchecked.append(reason)


# --------------------------------------------------------------------------
# What is actually in the tree. Every value here is recounted from a file, so
# this script never carries its own copy of an answer: two copies agreeing
# proves only that they were typed by the same hand on the same day.
# --------------------------------------------------------------------------

def lines(relative):
    """Count lines the way `wc -l` does, not the way `str.splitlines` does.

    `impl-go/main.go` contains a literal U+2028 and U+2029 in a comment about
    U+2028 and U+2029. Python treats both as line terminators and `wc` does not,
    so the two disagree by exactly two — which is how this check first went red.
    The paper's numbers are the `wc -l` ones, so that is what this counts."""
    data = (ROOT / relative).read_bytes()
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


def store_mono_totals():
    """Run the one bridge that is cheap enough to be a dependency.

    It invokes no `lean` — it is a differential over the reference oracle — so it
    costs under a tenth of a second, and running it is strictly better than
    copying its two totals into this file, where they would agree with the paper
    forever regardless of what the bridge does.
    """
    try:
        finished = subprocess.run(
            [sys.executable, str(ROOT / "proofs/store_mono_bridge_check.py")],
            capture_output=True, text=True, cwd=ROOT, timeout=120)
    except (OSError, subprocess.SubprocessError) as failure:
        return None, f"could not run store_mono_bridge_check.py: {failure}"
    if finished.returncode != 0:
        return None, ("store_mono_bridge_check.py exited "
                      f"{finished.returncode}; its totals are unavailable")
    match = re.search(r"\((\d+) grown, (\d+) shrunk over (\d+) eval vectors\)",
                      finished.stdout)
    if not match:
        return None, ("store_mono_bridge_check.py no longer prints its totals in "
                      "the form this checker reads")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))), None


def facts():
    pins = json.loads((ROOT / "proofs/theorem_pins.json").read_text())
    fronts = pins["fronts"]
    lean = {p.name: lines(p.relative_to(ROOT))
            for p in sorted((ROOT / "proofs").glob("*.lean"))}
    bridges = sorted((ROOT / "proofs").glob("*bridge_check.py"))
    vectors = json.loads((ROOT / "tests/spec_conformance/vectors.json").read_text())
    kinds, outcomes = {}, {}
    for vector in vectors["vectors"]:
        kinds[vector["kind"]] = kinds.get(vector["kind"], 0) + 1
        if vector["kind"] == "eval":
            outcome = vector["expected"]["outcome"]
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

    def suite(name):
        return len(json.loads(
            (ROOT / "tests/spec_conformance" / name).read_text())["vectors"])

    guard_machinery = (lines("proofs/proof_guard.py")
                       + lines("tests/proof_guard_test.py")
                       + sum(lines(b.relative_to(ROOT)) for b in bridges))
    lean_total = sum(lean.values())
    return {
        "fronts": {name: len(front["guarded"]) for name, front in fronts.items()},
        "front_count": len(fronts),
        "guarded_total": sum(len(front["guarded"]) for front in fronts.values()),
        "native_decide": len({name for front in fronts.values()
                              for name in front["native_decide_ok"]}),
        "statements": len(pins["statements"]),
        "definitions": len(pins["definitions"]),
        "unguarded": len(pins["unguarded"]),
        "pins_kb": (ROOT / "proofs/theorem_pins.json").stat().st_size // 1024,
        "lean": lean,
        "lean_total": lean_total,
        "lean_files": len(lean),
        "proof_guard": lines("proofs/proof_guard.py"),
        "guard_test": lines("tests/proof_guard_test.py"),
        "bridge_count": len(bridges),
        "bridge_lines": sum(lines(b.relative_to(ROOT)) for b in bridges),
        "ratio": round(guard_machinery / lean_total, 1),
        "objects": len(vectors["objects"]),
        "vectors": len(vectors["vectors"]),
        "kinds": kinds,
        "outcomes": outcomes,
        "wave": suite("wave_vectors.json"),
        "federation": suite("federation_vectors.json"),
        "governance": suite("governance_vectors.json"),
        "oracle_py": lines("impl/sigma_glyph.py"),
        "impl_rs": lines("impl-rs/src/main.rs"),
        "impl_go": lines("impl-go/main.go"),
    }


# --------------------------------------------------------------------------
# Reading a claim out of a paper. The paper is the source of the expectation;
# the tree is the source of the truth; this file is the source of neither.
# --------------------------------------------------------------------------

def stated(audit, slug, pattern, fields):
    """`fields` is [(label, actual, converter), ...], one per capture group."""
    match = re.search(pattern, audit.texts[slug])
    if match is None:
        labels = ", ".join(label for label, _, _ in fields)
        audit.note(f"{labels}: the paper no longer states this in the form the "
                   f"checker reads (/{pattern}/) — reword the check or the paper, "
                   f"but do not leave it unread")
        return
    for index, (label, actual, convert) in enumerate(fields, start=1):
        literal = match.group(index)
        audit.claims.append(Claim(label, slug, match.span(index), literal))
        try:
            audit.chk(label, convert(literal), actual)
        except (KeyError, ValueError):
            audit.note(f"{label}: {literal!r} is not a number this checker can read")


def audit_engine(audit, tree):
    """The engine paper's headline claims, checked one at a time.

    These are the sentences a reader quotes. They were the ones nobody checked.
    """
    stated(audit, ENGINE,
           r"([A-Za-z]+-[a-z]+) theorems across ([a-z]+) fronts are guarded",
           [("engine headline: guarded theorems", tree["guarded_total"], word_int),
            ("engine headline: fronts", tree["front_count"], word_int)])
    stated(audit, ENGINE,
           r"all ([a-z]+)\nevaluator theorems have axiom cone",
           [("engine headline: evaluator theorems", tree["fronts"]["eval"], word_int)])
    stated(audit, ENGINE,
           r"`native_decide` confined to ([a-z]+) theorems",
           [("engine headline: native_decide theorems", tree["native_decide"], word_int)])
    stated(audit, ENGINE,
           r"([A-Za-z]+) of the\n\s*(\d+) guarded theorems are permitted `native_decide`",
           [("contribution: native_decide theorems", tree["native_decide"], word_int),
            ("contribution: guarded theorems", tree["guarded_total"], int)])
    stated(audit, ENGINE,
           r"the other (\d+) are not, and all ([a-z]+) evaluator",
           [("contribution: theorems without native_decide",
             tree["guarded_total"] - tree["native_decide"], int),
            ("contribution: evaluator theorems", tree["fronts"]["eval"], word_int)])

    # Distribution, not just the total: five fronts summing to the right number
    # while two of them are wrong is a green this script used to allow.
    stated(audit, ENGINE,
           r"([A-Za-z]+-[a-z]+) theorems are guarded, distributed as: `size` (\d+), "
           r"`bytes` (\d+), `eval` (\d+),\n`wave` (\d+), `c1` (\d+)",
           [("§4.4 guarded theorems", tree["guarded_total"], word_int),
            ("§4.4 front distribution: size", tree["fronts"]["size"], int),
            ("§4.4 front distribution: bytes", tree["fronts"]["bytes"], int),
            ("§4.4 front distribution: eval", tree["fronts"]["eval"], int),
            ("§4.4 front distribution: wave", tree["fronts"]["wave"], int),
            ("§4.4 front distribution: c1", tree["fronts"]["c1"], int)])
    stated(audit, ENGINE, r"The registry pins \*\*(\d+)\*\* statements",
           [("§4.4 statement pins", tree["statements"], int)])
    stated(audit, ENGINE,
           r"([A-Za-z]+) further theorems are\nregistered as deliberately unguarded",
           [("§4.4 deliberately unguarded", tree["unguarded"], word_int)])
    stated(audit, ENGINE, r"the registry now pins (\d+)\ndefinitions",
           [("§6.1 definition pins", tree["definitions"], int)])

    # The Lean artifact, whole and per file. The total was right while three of
    # the parts were not; a checker that reads only the total says ALL PASS.
    stated(audit, ENGINE,
           r"([A-Za-z]+) `\.lean` files total (\d+)\nlines",
           [("§4.3 Lean file count", tree["lean_files"], word_int),
            ("§4.3 Lean line total", tree["lean_total"], int)])
    for name in ("Sha256", "MachineBytes", "EvalMachine", "WaveAlgebra",
                 "C1Compiler", "SizeBound", "LutData"):
        stated(audit, ENGINE, rf"`{name}\.lean` \((\d+)",
               [(f"§4.3 {name}.lean lines", tree["lean"][f"{name}.lean"], int)])
    stated(audit, ENGINE, r"I/O runners \((\d+) \+ (\d+) \+ (\d+)\)",
           [("§4.3 BytesRun.lean lines", tree["lean"]["BytesRun.lean"], int),
            ("§4.3 EvalRun.lean lines", tree["lean"]["EvalRun.lean"], int),
            ("§4.3 WaveRun.lean lines", tree["lean"]["WaveRun.lean"], int)])
    stated(audit, ENGINE, r"The Lean artifact is (\d+) lines across ([a-z]+) files",
           [("§6.3 Lean line total", tree["lean_total"], int),
            ("§6.3 Lean file count", tree["lean_files"], word_int)])

    # The guard machinery and the ratio it is quoted by.
    stated(audit, ENGINE,
           r"`proof_guard\.py` \((\d+)\), `theorem_pins\.json` \((\d+) KB\),\n"
           r"`tests/proof_guard_test\.py` \((\d+)\) and ([a-z]+) bridge scripts \((\d+)\) —\n"
           r"is now \*\*([\d.]+)×\*\*",
           [("§6.3 proof_guard.py lines", tree["proof_guard"], int),
            ("§6.3 pin registry KB", tree["pins_kb"], int),
            ("§6.3 proof_guard_test.py lines", tree["guard_test"], int),
            ("§6.3 bridge scripts", tree["bridge_count"], word_int),
            ("§6.3 bridge script lines", tree["bridge_lines"], int),
            ("§6.3 guard-to-proof ratio", tree["ratio"], float)])
    stated(audit, ENGINE,
           r"(\d+)\nlines of Python, a (\d+) KB pin registry and a (\d+)-line regression "
           r"suite asserting\n\d+ properties — machinery ([\d.]+)× the size of the (\d+) "
           r"lines of Lean",
           [("§5 proof_guard.py lines", tree["proof_guard"], int),
            ("§5 pin registry KB", tree["pins_kb"], int),
            ("§5 proof_guard_test.py lines", tree["guard_test"], int),
            ("§5 guard-to-proof ratio", tree["ratio"], float),
            ("§5 Lean line total", tree["lean_total"], int)])

    # The conformance suites, by name and by shape.
    stated(audit, ENGINE,
           r"holds \*\*(\d+)\*\* vectors: (\d+) `eval`, (\d+) `object`\n"
           r"\(serialization/hash\), (\d+) `deserialize` \(byte-rejection\), over (\d+) "
           r"preloaded CAS\nobjects",
           [("§6.2 vectors", tree["vectors"], int),
            ("§6.2 eval vectors", tree["kinds"]["eval"], int),
            ("§6.2 object vectors", tree["kinds"]["object"], int),
            ("§6.2 deserialize vectors", tree["kinds"]["deserialize"], int),
            ("§6.2 CAS objects", tree["objects"], int)])
    stated(audit, ENGINE,
           r"distribution is (\d+) normal form, (\d+) ATP-exhausted, (\d+) "
           r"unresolved-reference, (\d+)\ninvalid-object",
           [("§6.2 outcome: normal_form", tree["outcomes"]["normal_form"], int),
            ("§6.2 outcome: atp_exhausted", tree["outcomes"]["atp_exhausted"], int),
            ("§6.2 outcome: unresolved_reference",
             tree["outcomes"]["unresolved_reference"], int),
            ("§6.2 outcome: invalid_object", tree["outcomes"]["invalid_object"], int)])

    # The implementations, whose line counts are the easiest number in the paper
    # to leave stale and the easiest to check.
    stated(audit, ENGINE, r"\| `impl/sigma_glyph\.py` \(oracle\) \| (\d+) \|",
           [("§6.3 impl/sigma_glyph.py lines", tree["oracle_py"], int)])
    stated(audit, ENGINE, r"\| `impl-rs/src/main\.rs` \| (\d+) \|",
           [("§6.3 impl-rs/src/main.rs lines", tree["impl_rs"], int)])
    stated(audit, ENGINE, r"\| `impl-go/main\.go` \(in-tree\) \| (\d+) \|",
           [("§6.3 impl-go/main.go lines", tree["impl_go"], int)])
    stated(audit, ENGINE, r"worth a sentence: (\d+) lines, no dependencies",
           [("§6.3 Rust prose line count", tree["impl_rs"], int)])

    # The store-monotonicity bridge reports its own totals; §6a and §6.1 quote
    # them, and the two places must agree with each other as well as with it.
    totals, why = store_mono_totals()
    if totals is None:
        audit.note(f"the store-monotonicity totals of §3.6 and §6.1: {why}")
    else:
        grown, shrunk, over = totals
        stated(audit, ENGINE,
               r"\*\*(\d+) grown and (\d+) shrunk over (\d+) evaluation vectors\*\*",
               [("§3.6 grown perturbations", grown, int),
                ("§3.6 shrunk perturbations", shrunk, int),
                ("§3.6 eval vectors perturbed", over, int)])
        stated(audit, ENGINE,
               r"\| `store_mono_bridge_check\.py` \| [\d.]+ \| — \| (\d+) grown / (\d+) "
               r"shrunk over (\d+) eval vectors \|",
               [("§6.1 grown perturbations", grown, int),
                ("§6.1 shrunk perturbations", shrunk, int),
                ("§6.1 eval vectors perturbed", over, int)])
        stated(audit, ENGINE,
               r"and (\d+) store perturbations against the monotonicity bound",
               [("abstract: store perturbations", grown + shrunk, int)])

    # Per-front theorem counts as the §6.1 table states them, so the table and
    # the registry cannot drift apart.
    for script, front in (("bridge_check.py", "size"),
                          ("byte_bridge_check.py", "bytes"),
                          ("eval_bridge_check.py", "eval"),
                          ("wave_bridge_check.py", "wave"),
                          ("c1_bridge_check.py", "c1")):
        stated(audit, ENGINE,
               rf"\n\| `{re.escape(script)}`(?: \(SizeBound\))? \| [\d.]+ \| (\d+) \|",
               [(f"§6.1 table: {front} theorems", tree["fronts"][front], int)])
    stated(audit, ENGINE,
           r"\*\*all six, one cold sequential run\*\* \| \*\*[\d.]+\*\* \| \*\*(\d+)\*\*",
           [("§6.1 table: guarded total", tree["guarded_total"], int)])


def audit_guard(audit, tree):
    """The guard paper. Its four original checks, plus the ones it also states."""
    stated(audit, GUARD, r"(\d[\d,]*) lines of Python",
           [("guard paper: proof_guard.py lines", tree["proof_guard"],
             lambda s: int(s.replace(",", "")))])
    stated(audit, GUARD, r"(\d+) KB pin registry",
           [("guard paper: pin registry KB", tree["pins_kb"], int)])
    stated(audit, GUARD, r"(\d[\d,]*) lines of Lean",
           [("guard paper: Lean line total", tree["lean_total"],
             lambda s: int(s.replace(",", "")))])
    stated(audit, GUARD, r"(\d{1,9}) statement pins, (\d{1,9}) definition pins",
           [("guard paper: statement pins", tree["statements"], int),
            ("guard paper: definition pins", tree["definitions"], int)])

    # The regression suite's line count is stated as an adjective ("a 981-line
    # suite"), in whichever sentence does not talk about Lean.
    for sentence in audit.texts[GUARD].split("."):
        if "Lean" in sentence:
            continue
        match = re.search(r"(\d[\d,]*)-line\b", sentence)
        if match:
            offset = audit.texts[GUARD].index(sentence)
            audit.claims.append(Claim("guard paper: proof_guard_test.py lines",
                                      GUARD,
                                      (offset + match.start(1), offset + match.end(1)),
                                      match.group(1)))
            audit.chk("guard paper: proof_guard_test.py lines",
                      int(match.group(1).replace(",", "")), tree["guard_test"])
            break
    else:
        audit.note("guard paper: proof_guard_test.py lines — the claim is no "
                   "longer stated as an N-line adjective")

    # The title says twenty-one. If the body enumerates a different number, one
    # of them is wrong and a reader has no way to tell which.
    audit.chk("guard paper: bypasses enumerated in the body vs the title",
              len(set(re.findall(r"\*\*(V\d+) —", audit.texts[GUARD]))), 21)


UNCHECKED = [
    "The §6.1 wall-clock column. Timings are host-, load- and toolchain-"
    "dependent; reproduce with `python3 proofs/<name>_bridge_check.py` timed "
    "individually, and the sequential figure by timing the six in one loop. "
    "`tools/test-all.sh` does NOT produce these — it times nothing.",
    "The differential counts in the §6.1 table (861 oracle steps, 334 buffers, "
    "33 eval vectors, 582 boundary cases, 3000 lambda-terms). Each bridge prints "
    "its own total on the last line; running them here would put `lean` on this "
    "script's critical path, so `tools/test-all.sh` owns them.",
    "The 122 checks of `tests/proof_guard_test.py` and the 2103 of "
    "`tests/spec_conformance/test_properties.py`: both are emitted at runtime "
    "(`python3 tests/proof_guard_test.py | grep -c '^ok'`).",
    "The 5347 fuzzer-generated vectors per CI run and the three seeds behind "
    "them: generated, not stored, by `.github/workflows/ci.yml`'s three "
    "`tests/book1_fuzz.py --terms 200 --seed` invocations.",
    "Every claim about the external repositories — `warrant-go`'s evaluator, the "
    "PyPI versions and upload timestamps of §10. They are outside this tree; CI "
    "pins the first by commit hash and the second was checked against the PyPI "
    "JSON API by hand.",
    "Every prose claim about WHY a bypass worked, and every claim about an "
    "adoption warrant's signatures. Mechanically uncheckable here; the code is "
    "in `proofs/proof_guard.py` and the warrants in `.warrants/`.",
    "That the papers' arguments are correct. This checks arithmetic, not "
    "reasoning.",
]


def run(texts):
    tree = facts()
    audit = Audit(texts=texts)
    audit_engine(audit, tree)
    audit_guard(audit, tree)
    return audit


def read_papers():
    return {slug: (PAPERS / slug / "paper.md").read_text(encoding="utf-8")
            for slug in (ENGINE, GUARD)}


def perturb(literal):
    """A different number, written the way the paper writes this one."""
    if re.fullmatch(r"\d+", literal):
        return str(int(literal) + 1)
    if re.fullmatch(r"\d+\.\d+", literal):
        return f"{float(literal) + 0.1:.1f}"
    if re.fullmatch(r"\d[\d,]*", literal):
        return f"{int(literal.replace(',', '')) + 1:,}"
    value = word_int(literal)
    other = word_of(value + 1 if value + 1 in WORDS.values() else value - 1)
    return other.capitalize() if literal[0].isupper() else other


def selftest(texts):
    """Change each load-bearing number; demand that its own check goes red.

    A number the gate does not actually gate on is decoration. This is the same
    argument the guard paper makes about `proof_guard.py`, turned on this file.
    """
    baseline = run(texts)
    if baseline.failed:
        print("SELFTEST: refusing to run — the audit is already failing, so a "
              "mutation proving nothing would look like a pass", file=sys.stderr)
        return 1
    broken = []
    for claim in baseline.claims:
        text = texts[claim.slug]
        start, end = claim.span
        mutated = dict(texts)
        mutated[claim.slug] = text[:start] + perturb(claim.literal) + text[end:]
        after = run(mutated)
        if claim.label not in [label for label, _, _ in after.failed]:
            broken.append(claim.label)
    covered = {claim.label for claim in baseline.claims}
    print(f"  mutated {len(baseline.claims)} load-bearing numbers, one at a time")
    for label, _, _ in baseline.passed:
        if label not in covered:
            # Not a number read out of the text at a known offset, so there is
            # nothing to rewrite. Named rather than quietly excluded: an
            # exclusion nobody prints is how a check stops being one.
            print(f"  NOT MUTATED  {label} — derived by counting, not by reading "
                  f"a literal; no span to rewrite")
    for label in broken:
        print(f"  FAIL  changing '{label}' did not fail its check", file=sys.stderr)
    if broken:
        print(f"PAPER-CLAIMS-SELFTEST: {len(broken)} claim(s) are not gated on")
        return 1
    print("PAPER-CLAIMS-SELFTEST: ALL PASS — every load-bearing number, when "
          "changed, fails the gate")
    return 0


def main(argv):
    texts = read_papers()
    if "--selftest" in argv:
        return selftest(texts)
    audit = run(texts)
    for label, stated_value, actual in audit.passed:
        print(f"  OK    {label:<44} paper={stated_value} actual={actual}")
    for label, stated_value, actual in audit.failed:
        print(f"  FAIL  {label:<44} paper={stated_value} actual={actual}")
    print()
    for reason in UNCHECKED + audit.unchecked:
        print(f"  UNCHECKED  {reason}")
    print()
    total = len(audit.passed) + len(audit.failed)
    if audit.failed:
        print(f"PAPER-CLAIMS: FAILURES ({len(audit.failed)}/{total}): "
              + ", ".join(label for label, _, _ in audit.failed))
        return 1
    print(f"PAPER-CLAIMS: ALL PASS ({total}/{total} checked, "
          f"{len(UNCHECKED) + len(audit.unchecked)} categories deliberately "
          f"unchecked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
