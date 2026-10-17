#!/usr/bin/env python3
"""Each mutant of impl/sigma_resume.py must make ITS case of tests/resume_test.py
fail. A mutant that only breaks some other case is OFF_TARGET, not killed.

    python3 tests/resume_mutants.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "impl" / "sigma_resume.py").read_text()

# (target case, what it breaks, exact text, replacement)
MUTANTS = [
    ("SG04", "a completed return skips the size ceiling",
     '                try:\n                    G.resource_check(term, limits)\n                except G.ResourceFault as e:\n                    return term, spent, actions, peak, RESOURCE_FAULT, str(e)\n                return term, spent, actions, peak, NORMAL_FORM, None',
     '                return term, spent, actions, peak, NORMAL_FORM, None'),
    # Codex review of PR #62 (R1-R3): each fix has a mutant that undoes it.
    ("R1", "cycle verification skips the shared context check",
     '    ctx = _context_error(root_doc, env)\n    if ctx:\n        return ctx\n',
     ''),
    ("R2", "replay runs to the claimed credit, not the claimed spent",
     '    replay = advance(b_doc, b_id, b_state, env, doc["spent_total"] - b_doc["spent_total"], limits, runtime)',
     '    replay = advance(b_doc, b_id, b_state, env, doc["credit_total"] - b_doc["spent_total"], limits, runtime)'),
    ("R3", "a malformed parent id is not refused",
     '    if doc["parent_checkpoint_id"] is not None and not _is_digest(doc["parent_checkpoint_id"]):',
     '    if False:'),
    ("N01", "state codec keeps only the term hash",
     '        else:\n            out += _TAG[t[0]] + t[1]\n    return bytes(out)',
     '        else:\n            out += _TAG[t[0]] + t[1]\n    return bytes(STATE_MAGIC + bytes.fromhex(computation_id) + b"T" + G.term_hash(term))'),
    ("N08", "unspent credit is dropped on resume",
     '    credit = ckpt["credit_total"] + additional_credit\n',
     '    credit = ckpt["spent_total"] + additional_credit\n'),
    ("N09", "spent counted from the start of each segment",
     '    doc, new_id = checkpoint(cid, sb, credit, ckpt["spent_total"] + spent,',
     '    doc, new_id = checkpoint(cid, sb, max(credit, spent), spent,'),
    ("N03", "a checkpoint is accepted without replay",
     '    b_doc, b_id, b_state = _replay_base(cid, root_doc, doc, cache)',
     '    return REPLAYED, "NORMAL_FORM", 0\n    b_doc, b_id, b_state = _replay_base(cid, root_doc, doc, cache)'),
    ("N04", "the verifier ignores the environment in the context",
     '    if root_doc.get("environment_id") != env.environment_id or runtime not in PROFILES \\',
     '    if runtime not in PROFILES \\'),
    ("N18", "undelivered bytes read as a semantic absence",
     '        if b is None:\n            raise EvidenceUnavailable(h.hex())',
     '        if b is None:\n            return None'),
    ("N06", "non-canonical checkpoint bytes are normalized, not refused",
     '    if _canon(doc) != raw:\n        raise InvalidEncoding("checkpoint bytes are not canonical")',
     '    pass'),
    ("N14", "credit is clamped instead of refused",
     '    if credit > MAX_INT:\n        raise IntegerOverflow(f"credit {credit} exceeds 2^53-1")',
     '    credit = min(credit, MAX_INT)'),
    ("N25", "the verified cache ignores the verifier identity",
     '        return self.entries.get((verifier_id or VERIFIER_ID, computation_id, ckpt_id))',
     '        return next((v for k, v in self.entries.items() if k[1:] == (computation_id, ckpt_id)), None)'),
    ("N30", "a cycle of zero priced actions is accepted",
     '    if n == 0 or cost == 0:\n        return "INVALID_CYCLE_WITNESS: a cycle needs at least one priced action"',
     '    pass'),
    ("N31", "the cycle verifier compares term hashes, not states",
     '    if encode_state(cid, term) != pre.state_bytes:',
     '    if G.term_hash(term) != G.term_hash(decode_state(pre.state_bytes)[1]):'),
    ("N33", "the claimed cycle cost is not checked",
     '    if spent != cost:\n        return f"INVALID_CYCLE_WITNESS: the period costs {spent}, not {cost}"',
     '    pass'),
    ("R-N16", "Y duplicates f for 1 ATP (the size bound breaks)",
     '        return ("app", a, ("app", f, a)), _dup(1 + G.size(a), remaining)',
     '        return ("app", a, ("app", f, a)), _dup(1, remaining)'),
    ("R-N29", "M is not a primitive in the rich profile",
     '    if G.glyph_eq(f, M_H):                                   # M x -> x x',
     '    if False:                                                # M x -> x x'),
    ("R-ISO", "the runtime profile is not part of the computation id",
     '           "environment_id": env.environment_id}\n    return doc, _digest(doc)',
     '           "environment_id": env.environment_id}\n    return doc, _digest({k: v for k, v in doc.items()'
     ' if k not in ("runtime_semantics_id", "cost_model_id")})'),
    ("N17", "the missing hash is not reported",
     '    missing = env.missing.hex() if outcome == BLOCKED_REFERENCE and env.missing else None',
     '    missing = None'),
]


def run(text):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy2(ROOT / "impl" / "sigma_glyph.py", tmp)
        Path(tmp, "sigma_resume.py").write_text(text)
        r = subprocess.run([sys.executable, str(ROOT / "tests" / "resume_test.py")],
                           env=dict(os.environ, RESUME_IMPL=tmp), capture_output=True, text=True, timeout=900)
    return r.stdout + r.stderr


def main():
    base = run(SRC)
    clean = "0 FAIL" in base
    print(("ok  " if clean else "FAIL"), "unmutated module: no FAIL")
    if not clean:
        print(base[-1500:])
        return 1
    ok = True
    for nid, what, old, new in MUTANTS:
        if SRC.count(old) != 1:
            print(f"FAIL  {nid}: mutant site missing or not unique ({what})")
            ok = False
            continue
        out = run(SRC.replace(old, new))
        hit = re.search(rf"^FAIL  {nid}\b", out, re.M) is not None
        crashed = "Traceback" in out
        verdict = "KILLED" if hit else ("CRASHED" if crashed else "OFF_TARGET" if " FAIL" in out else "SURVIVED")
        ok &= hit
        print(f"{verdict:10} {nid} {what}")
    print("RESUME MUTANTS:", "ALL KILLED ON TARGET" if ok else "NOT ALL KILLED ON TARGET")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
