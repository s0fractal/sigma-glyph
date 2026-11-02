#!/usr/bin/env python3
"""The mutants of tests/document_test.py: the generator's rendering, each of its refusals, and the records themselves,
through the runner of tests/claims_mutants.py (a fresh copy per mutant, a kill only on a printed `FAIL`, a refused run
over a red baseline). Not cited by a claim: they burn the projection, not a sentence of the specification.

Needs warrant-graph, as the test does. Exits 0 only when every mutant is killed.

    python3 tests/document_mutants.py [--list | IDS...]"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claims_mutants as H  # noqa: E402

T = "tests/document_test.py"
G = "tools/document.py"
STORE = ".warrant/records.jsonl"
PROSE = ".warrant/blobs/9304d8f6f47f30487b5373cd679c7ca98c4aefdf88d701e42f96eca3e5eb8a82"

H.MUTANTS = [
    # The correctness proof: anything that changes a byte of the rendering.
    ("D-M01", G, "        out += [text, gap]\n", "        out += [text]\n", T, ["D01"]),
    ("D-M02", G, '    for c in claims:\n        r = rep["_recs"].get(c)\n', '    for c in sorted(claims):\n        r = rep["_recs"].get(c)\n', T, ["D01"]),
    ("D-M03", G, '    return "".join(out).encode("utf-8")\n', '    return "".join(out).rstrip().encode("utf-8")\n', T, ["D01"]),
    # ... and the records: one byte of the prose, one of a sentence.
    ("D-M04", PROSE, "Book I governs the transition;", "Book I governs a transition;", T, ["D01"]),
    ("D-M05", STORE, "**No signature is consulted (MUST NOT).**", "**No signature is consulted (MUST).**", T, ["D01"]),
    # The refusals of a version.
    ("D-M06", G, "    bad = C.store_problems(rep)\n    if bad:\n", "    bad = C.store_problems(rep)\n    if False:\n", T, ["D20"]),
    ("D-M07", G, 'rec["schema"] != DOCUMENT or ', "", T, ["D18"]),
    ("D-M08", G, ' or rep["_basis"].get(version) != "SIGNED"', "", T, ["D22"]),
    ("D-M09", G, " and len(prose) == len(claims) + 1", "", T, ["D14"]),
    ("D-M10", G, ' or r["body"]["source"] != body["source"]', "", T, ["D15"]),
    ("D-M11", G, ' or rep["_basis"].get(c) != "SIGNED"', "", T, ["D23"]),
    # What keeps a version from being the source's whole, current form.
    ("D-M12", G, "        if L in seen:\n", "        if False:\n", T, ["D11"]),
    ("D-M13", G, '        if L not in live or rep["lineages"][L]["leaf"] != c:\n', '        if L not in live:\n', T, ["D12"]),
    ("D-M14", G, '        if L not in live or rep["lineages"][L]["leaf"] != c:\n', '        if rep["lineages"][L]["leaf"] != c:\n', T, ["D13"]),
    ("D-M15", G, 'if b["source"] == source and L not in seen]', "if False]", T, ["D10"]),
    ("D-M16", G, "        if not any(a <= m.start() and m.end() <= b for a, b in spans):\n", "        if False:\n", T, ["D16", "D19"]),
    ("D-M17", G, '        if text.startswith("#", text.rfind("\\n", 0, m.start()) + 1):\n', "        if False:\n", T, ["D24"]),
    ("D-M18", G, "    if committed is not None and committed != interleave(", "    if False and committed != interleave(", T, ["D17"]),
    # Which version is current.
    ("D-M19", G, '        if lin["verdict"] == "FORK" or lin["leaf"] is None:\n', "        if False:\n", T, ["D25"]),
    ("D-M20", G, '        if body["source"] in out:\n', "        if False:\n", T, ["D26"]),
    ("D-M21", G, '        if body["state"] == "retired":\n', "        if False:\n", T, ["D27"]),
    ("D-M22", G, "        docs = current(rep)\n        if not docs:\n", "        docs = current(rep)\n        if False:\n", T, ["D28"]),
    ("D-M23", G, "            if not versions:\n", "            if False:\n", T, ["D29"]),
    # The parser of a first version.
    ("D-M24", G, "        if text.count(s) != 1:\n", "        if text.count(s) > 1:\n", T, ["D31"]),
    ("D-M25", G, "        if text.count(s) != 1:\n", "        if text.count(s) == 0:\n", T, ["D30"]),
    ("D-M26", G, "        if at < end:\n", "        if False:\n", T, ["D32"]),
    ("D-M27", G, "    if source in current(rep):\n", "    if False:\n", T, ["D34"]),
]

if __name__ == "__main__":
    # The copies of the tree have no .git: the test reads the release from this repository.
    os.environ.setdefault("SIGMA_RELEASE_GIT", str(H.ROOT))
    sys.exit(H.main(sys.argv[1:]))
