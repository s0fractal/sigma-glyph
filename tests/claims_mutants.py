#!/usr/bin/env python3
"""The mutants Book I's and sigma-resume's claims cite (.warrant/claims.json `mutants`), in the contract the
Warrant claims checker reads:

    python3 tests/claims_mutants.py --list                  # {id: [file, test file, [cases]]}
    python3 tests/claims_mutants.py [IDS...] [--matrix OUT] # run them; OUT gets {"rows": [{id, outcome, ...}]}

A mutant is one exact find/replace in one file. Each runs in a fresh copy of the tracked tree, alone, with
no bytecode cache, and is KILLED only when one of its cases prints `FAIL <case>`: a case that does not print
at all (an import error, a crash before it) is no kill, and a find text that does not occur exactly once is
STALE. Before any mutant, every test file named runs once unmutated in its own copy, and a named case that is
not `ok` there refuses the whole run (BASELINE_RED, exit 2): a kill over a red baseline means nothing."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK1 = "tests/book1_claims_test.py"
ORACLE = "impl/sigma_glyph.py"

# (id, file, find, replace, test file, [cases])
MUTANTS = [
    ("G01", ORACLE, "    if flags != FLAGS_REQ[op]: return None\n", "    if False: return None\n", BOOK1, ["B102"]),
    ("G02", ORACLE, "    if op not in FLAGS_REQ: return None            # covers RESERVED 0x03\n", "", BOOK1, ["B103"]),
    ("G03", ORACLE, '    if n is None: return ("dis", R_INVALID)\n', '    if n is None: return ("dis", R_ATP)\n', BOOK1, ["B103", "B104"]),
    ("G04", ORACLE, "    for f in (atom, left, right):\n", "    for f in (atom, right, left):\n", BOOK1, ["B105"]),
    ("G05", ORACLE, "def node_hash(b): return sha(b)\n", "def node_hash(b): return sha(b[1:])\n", BOOK1, ["B106"]),
    ("G06", ORACLE, "    if len(buf) != exp: return None\n", "    if len(buf) < exp: return None\n", BOOK1, ["B107"]),
    ("G07", ORACLE, 'R_INVALID = sha(b"Invalid Object")\n', 'R_INVALID = sha(b"Invalid object")\n', BOOK1, ["B104"]),
    ("G08", ORACLE, "        _require_budget(1, remaining)\n        return argument, 1\n",
     "        _require_budget(1, remaining)\n        return function, 1\n", BOOK1, ["B108"]),
    ("G09", ORACLE, "        return function[2], 1\n", "        return argument, 1\n", BOOK1, ["B109"]),
    ("G10", ORACLE, '    return ("app", ("app", x, z), ("app", y, z)), cost\n', '    return ("app", ("app", x, z), ("app", z, y)), cost\n',
     BOOK1, ["B110"]),
    ("G11", ORACLE, '        return ("thunk", t[1]), 1\n', '        return ("thunk", t[1]), 0\n', BOOK1, ["B111"]),
    ("G18", ORACLE, '        return ("thunk", t[1]), 1\n',
     '        v = force(t[1], store, stats, limits)\n'
     '        return (("thunk", v[1]) if v[0] == "ref" else ("thunk", t[1])), 1\n', BOOK1, ["B111"]),
    ("G12", ORACLE, '    if t[0] == "lit":   return node_hash(ser(LITERAL, F_ATOM, atom=t[1])) == gh\n',
     '    if t[0] == "lit":   return True\n', BOOK1, ["B112"]),
    ("G13", ORACLE, "    if glyph_eq(function[1], K_H):\n", '    if glyph_eq(function[1], K_H) and argument[0] != "thunk":\n',
     BOOK1, ["B113"]),
    ("G14", ORACLE, "        c = size(v)                                          # 1 (lit/dis) / 2 (ref) / 3 (app)\n",
     "        c = 1\n", BOOK1, ["B114"]),
    ("G15", ORACLE, "    cost = 1 + size(z)\n", "    cost = 1\n", BOOK1, ["B115", "B110"]),
    ("G16", ORACLE, "    if cost > remaining:\n", "    if cost > remaining + 1:\n", BOOK1, ["B116"]),
    ("G17", ORACLE, "        if t[1] in GENESIS: return None                      # NF leaf by hash\n", "", BOOK1, ["B117"]),
]


def listing():
    return {m: [f, t, cases] for m, f, _, _, t, cases in MUTANTS}


def copy_tree(dest):
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout.split(b"\0")
    for rel in filter(None, (f.decode() for f in files)):
        src = ROOT / rel
        if src.is_file() and not src.is_symlink():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)


def run_test(tree, test):
    """{case: 'ok' | 'FAIL'} the test file printed in `tree`."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", str(tree / test)], cwd=tree, capture_output=True, text=True, env=env, timeout=1800)
    out = {}
    for line in r.stdout.splitlines():
        if line.startswith("ok   ") or line.startswith("FAIL "):
            out[line.split()[1]] = "ok" if line.startswith("ok") else "FAIL"
    return out


def run(ids):
    rows = {m: (f, find, rep, t, cases) for m, f, find, rep, t, cases in MUTANTS}
    unknown = [m for m in ids if m not in rows]
    if unknown:
        print(f"UNKNOWN_MUTANT {unknown}")
        sys.exit(2)
    with tempfile.TemporaryDirectory(prefix="sigma-mutants-") as td:
        base = Path(td) / "base"
        copy_tree(base)
        for test in sorted({rows[m][3] for m in ids}):
            seen = run_test(base, test)
            red = sorted(c for m in ids if rows[m][3] == test for c in rows[m][4] if seen.get(c) != "ok")
            if red:
                print(f"BASELINE_RED {test}: {red}")
                sys.exit(2)
        out = []
        for m in ids:
            f, find, rep, test, cases = rows[m]
            tree = Path(td) / m
            copy_tree(tree)
            text = (tree / f).read_text()
            if text.count(find) != 1:
                out.append({"id": m, "outcome": "STALE", "why": f"the find text occurs {text.count(find)} times in {f}"})
                continue
            (tree / f).write_text(text.replace(find, rep))
            seen = run_test(tree, test)
            failed = sorted(c for c in cases if seen.get(c) == "FAIL")
            out.append({"id": m, "outcome": "KILLED" if failed else "SURVIVED", "killed_by": failed,
                        "silent": sorted(c for c in cases if c not in seen)})
            shutil.rmtree(tree)
    return out


def main(argv):
    if argv == ["--list"]:
        json.dump(listing(), sys.stdout, indent=1, sort_keys=True)
        print()
        return 0
    matrix = None
    if "--matrix" in argv:
        i = argv.index("--matrix")
        matrix = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    ids = argv or [m for m, *_ in MUTANTS]
    rows = run(ids)
    for r in rows:
        print(f"{r['id']} {r['outcome']}" + (f" by {r['killed_by']}" if r.get("killed_by") else "")
              + (f" ({r['why']})" if r.get("why") else ""))
    if matrix:
        Path(matrix).parent.mkdir(parents=True, exist_ok=True)
        Path(matrix).write_text(json.dumps({"rows": rows}, indent=1, sort_keys=True) + "\n")
    killed = sum(r["outcome"] == "KILLED" for r in rows)
    print(f"\nCLAIMS-MUTANTS: {killed} of {len(rows)} killed")
    return 0 if killed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
