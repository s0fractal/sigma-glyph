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
RESUME = "tests/resume_claims_test.py"
KERNEL = "impl/sigma_resume.py"
SUITE = "tests/spec_conformance/vectors.json"
SCHEMA = "spec/schemas/book1-conformance.schema.json"

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
    ("G21", ORACLE, '                return ("dis", R_UNRES), spent, "unresolved_reference"\n',
     '                return ("dis", R_UNRES), spent, "atp_exhausted"\n', BOOK1, ["B201"]),
    ("G22", ORACLE, '                return t, spent, "normal_form"\n',
     '                return t, spent, ("atp_exhausted" if term_hash(t) == node_hash(ser(DISSONANCE, F_ATOM, atom=R_ATP))'
     ' else "normal_form")\n', BOOK1, ["B202"]),
    ("G23", ORACLE, "    if type(atp) is not int or not 0 <= atp <= UINT32_MAX:\n", "    if type(atp) is not int or not 0 <= atp:\n",
     BOOK1, ["B203"]),
    ("G24", ORACLE, "        _require_budget(1, remaining)\n        v = force(", "        v = force(", BOOK1, ["B204"]),
    ("G25", ORACLE, '                return ("dis", R_UNRES), spent, "unresolved_reference"\n',
     '                return ("dis", R_UNRES), spent + 1, "unresolved_reference"\n', BOOK1, ["B205"]),
    ("G26", ORACLE, "            except BudgetExhausted:\n", "            except ZeroDivisionError:\n", BOOK1, ["B206"]),
    ("G27", ORACLE, "        c = size(v)                                          # 1 (lit/dis) / 2 (ref) / 3 (app)\n",
     "        c = 1\n", BOOK1, ["B207"]),
    ("G28", ORACLE, "    if node_hash(b) != h:\n", "    if False:\n", BOOK1, ["B208"]),
    ("G29", ORACLE, 'R_UNRES   = sha(b"Unresolved Reference")\n', 'R_UNRES   = sha(b"Unresolved reference")\n', BOOK1,
     ["B211", "B215"]),
    ("G30", ORACLE, '    if stats["fetches"] > limits["max_store_fetches"]: raise ResourceFault("fetches")\n',
     '    if stats["fetches"] > limits["max_store_fetches"]: raise BudgetExhausted()\n', BOOK1, ["B212"]),
    ("G31", ORACLE, "    if allowed is not None and atp > allowed:\n", "    if False:\n", BOOK1, ["B213"]),
    ("G32", ORACLE, "    if not isinstance(h, bytes) or len(h) != 32:\n", "    if not isinstance(h, bytes):\n", BOOK1, ["B214"]),
    ("G33", ORACLE, 'R_ATP     = sha(b"ATP Exhausted")\n', 'R_ATP     = sha(b"Signal Damped")\n', BOOK1, ["B215", "B216"]),
    ("G34", ORACLE, "FALSE_BYTES = ser(APPLY, F_LEFT | F_RIGHT, left=K_H, right=I_H)\n",
     "FALSE_BYTES = ser(APPLY, F_LEFT | F_RIGHT, left=I_H, right=K_H)\n", BOOK1, ["B106"]),
    ("G35", ORACLE, '    if k == "lam": return _abstract(t[1], c1(t[2]))\n',
     '    if k == "lam" and t[2][0] == "lapp" and t[2][2] == ("var", t[1]) and t[1] not in _fv(t[2][1]): return c1(t[2][1])\n'
     '    if k == "lam": return _abstract(t[1], c1(t[2]))\n', BOOK1, ["B217"]),
    ("G36", ORACLE, '    if x not in _fv(m): return ("app", KG, m)                       # A-2\n',
     '    if x not in _fv(m) and m[0] != "var": return ("app", KG, m)\n', BOOK1, ["B218"]),
    ("G37", ORACLE, "        return function[2], 1\n", "        return function[2], 2\n", BOOK1, ["B219"]),
    ("G38", ORACLE, "        _require_budget(c, remaining)                         # fetched bytes discarded\n", "", BOOK1, ["B220"]),
    ("G39", ORACLE, "    term, spent, _ = _eval_hash_raw(h, atp, store, limits)\n    return term, spent\n",
     "    term, spent, _ = _eval_hash_raw(h, atp, store, limits)\n    return term, spent + 1\n", BOOK1, ["B221"]),
    ("G40", ORACLE, '    if not isinstance(b, bytes):\n        raise ResourceFault("store returned non-bytes")\n',
     '    if False:\n        raise ResourceFault("store returned non-bytes")\n', BOOK1, ["B208"]),
    ("G41", ORACLE, "    if allowed is not None and atp > allowed:\n", "    if allowed is not None and atp >= allowed:\n", BOOK1, ["B213"]),
    ("G42", ORACLE, "    if type(atp) is not int or not 0 <= atp <= UINT32_MAX:\n", "    if type(atp) is not int or not 0 < atp <= UINT32_MAX:\n",
     BOOK1, ["B203"]),
    # §7: the suite and its schema are data the Book makes normative, so a mutant may break them too
    ("G44", SUITE, '"result_hash": "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c",\n        "atp_spent": 4\n',
     '"result_hash": "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c",\n        "atp_spent": 5\n', BOOK1, ["B222"]),
    ("G45", SUITE, '"outcome": "normal_form",\n        "result_hash": "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c",\n        "atp_spent": 4\n',
     '"outcome": "normal_form",\n        "result_hash": "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162",\n        "atp_spent": 4\n',
     BOOK1, ["B222"]),
    ("G48", SUITE, '= 4 ATP",\n      "term": "51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e",\n      "atp": 100,\n      "expected": {\n        "exit": "normal_form",',
     '= 4 ATP",\n      "term": "51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e",\n      "atp": 100,\n      "expected": {\n        "exit": "atp_exhausted",',
     BOOK1, ["B222"]),     # Codex finding 0dca7c5a on #80: the exit, not only the outcome
    ("G46", SCHEMA, '  "type": "object",\n  "additionalProperties": false,\n  "required": [\n    "format",\n',
     '  "type": "object",\n  "additionalProperties": true,\n  "required": [\n    "format",\n', BOOK1, ["B223"]),
    ("G47", SCHEMA, '                "unresolved_reference"\n              ]\n            },\n            "outcome": {',
     '                "unresolved_reference",\n                "invalid_object"\n              ]\n            },\n            "outcome": {', BOOK1, ["B224"]),
    ("H01", KERNEL, '    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()\n',
     '    return json.dumps(doc, sort_keys=True, separators=(", ", ": "), ensure_ascii=False).encode()\n', RESUME, ["R01"]),
    ("H02", KERNEL, '           "environment_id": env.environment_id}\n', '           "environment_id": env.environment_id, "credit": 0}\n',
     RESUME, ["R02"]),
    ("H03", KERNEL, '    doc = {"schema": SCHEMA_ROOT, "runtime_semantics_id": runtime,\n           "cost_model_id": PROFILES[runtime][1],',
     '    doc = {"schema": SCHEMA_ROOT, "runtime_semantics_id": RUNTIME_SEMANTICS_ID,\n           "cost_model_id": COST_MODEL_ID,',
     RESUME, ["R03"]),
    ("H04", KERNEL, 'SCHEMA_ENV = "sigma-resume.environment@draft-1"\n', 'SCHEMA_ENV = "sigma-resume.environment@draft-2"\n', RESUME, ["R04"]),
    ("H05", KERNEL, "        if h not in self.hashes:\n", "        if False:\n", RESUME, ["R05"]),
    ("H06", KERNEL, "            stack.append(t[2])\n            stack.append(t[1])\n",
     "            stack.append(t[1])\n            stack.append(t[2])\n", RESUME, ["R06"]),
    ("H07", KERNEL, "            out += _TAG[t[0]] + t[1]\n", '            out += b"L" + G.term_hash(t)\n', RESUME, ["R07"]),
    ("H08", KERNEL, '    if i != len(b):\n        raise InvalidEncoding("trailing bytes after state")\n',
     '    if False:\n        raise InvalidEncoding("trailing bytes after state")\n', RESUME, ["R08"]),
    ("H09", KERNEL, '    if doc["spent_total"] > doc["credit_total"]:\n', "    if False:\n", RESUME, ["R09"]),
    ("H10", KERNEL, '    if not isinstance(doc, dict) or set(doc) != want or doc["schema"] != SCHEMA_CHECKPOINT:\n',
     '    if not isinstance(doc, dict) or not want <= set(doc) or doc["schema"] != SCHEMA_CHECKPOINT:\n', RESUME, ["R10"]),
    ("H11", KERNEL, "    if type(v) is not int or not 0 <= v <= MAX_INT:\n", "    if not isinstance(v, int) or not 0 <= v <= MAX_INT:\n",
     RESUME, ["R10"]),
    ("H12", KERNEL, '    credit = ckpt["credit_total"] + additional_credit\n', '    credit = max(ckpt["credit_total"], additional_credit)\n',
     RESUME, ["R11"]),
    ("H13", KERNEL, "KERNEL = (NORMAL_FORM, PAUSED, BLOCKED_REFERENCE)\n",
     'KERNEL = (NORMAL_FORM, PAUSED, BLOCKED_REFERENCE, "EVIDENCE_UNAVAILABLE", "CAS_MISMATCH")\n', RESUME, ["R12"]),
    ("H14", KERNEL, "            except G.BudgetExhausted:\n                return term, spent, actions, peak, PAUSED, None\n",
     "            except G.BudgetExhausted:\n                return term, spent + 1, actions, peak, PAUSED, None\n", RESUME, ["R13"]),
    ("H15", ORACLE, "        _require_budget(1, remaining)\n        v = force(", "        v = force(", RESUME, ["R14"]),
    ("H16", KERNEL, "    if credit > MAX_INT:\n", "    if False:\n", RESUME, ["R15"]),
    ("H17", KERNEL, "    if len(state_bytes) > MAX_STATE_BYTES:\n", "    if False:\n", RESUME, ["R16"]),
    ("H18", KERNEL, '    if root_doc.get("environment_id") != env.environment_id or runtime not in PROFILES \\\n',
     "    if runtime not in PROFILES \\\n", RESUME, ["R17"]),
    ("H19", KERNEL, '    replay = advance(b_doc, b_id, b_state, env, doc["spent_total"] - b_doc["spent_total"], limits, runtime)\n',
     '    replay = advance(b_doc, b_id, b_state, env, doc["credit_total"] - b_doc["spent_total"], limits, runtime)\n', RESUME, ["R18"]),
    ("H20", KERNEL, '            and got["peak_semantic_size"] == doc["peak_semantic_size"])\n', "            )\n", RESUME, ["R19"]),
    ("H21", KERNEL, "    if spent != cost:\n", "    if False:\n", RESUME, ["R20"]),
    ("H22", KERNEL, "    if n > cost:\n", "    if False:\n", RESUME, ["R21"]),
    ("H23", KERNEL, 'RUNTIME_SEMANTICS_ID = "sigma-book1-0.6.0/hash-thunk/leftmost-outermost"\n',
     'RUNTIME_SEMANTICS_ID = "sigma-book1-0.6.0/hash-thunk/leftmost-outermost/2"\n', RESUME, ["R22"]),
    ("H24", KERNEL, 'SCHEMA_CYCLE = "sigma-resume.cycle@draft-1"\n', 'SCHEMA_CYCLE = "sigma-resume.cycle@draft-2"\n', RESUME, ["R21"]),
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
