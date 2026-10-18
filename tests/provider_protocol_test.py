#!/usr/bin/env python3
"""sigma_provider serve answers every request with one protocol envelope.

    python3 tests/provider_protocol_test.py [--python PY]

With --python, runs the INSTALLED module (`PY -m sigma_provider serve`) from a
directory outside the checkout; without it, impl/sigma_provider.py. Malformed
requests must be refused (S64-01: `blobs: []` and `expr: []` ended in a
traceback and an empty stdout). The control runs the same requests against a
copy whose operand guards are removed, and requires a traceback: the guards are
what keeps these answers defined.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MALFORMED = [
    {"sigma_provider": 1, "op": "term", "args": {"expr": "I"}, "blobs": []},
    {"sigma_provider": 1, "op": "term", "args": {"expr": []}, "blobs": {}},
    {"sigma_provider": 1, "op": "term", "args": {"expr": "I"}, "blobs": None},
    {"sigma_provider": 1, "op": "term", "args": {"expr": "I"}, "blobs": "x"},
    {"sigma_provider": 1, "op": "term", "args": {"expr": None}},
    {"sigma_provider": 1, "op": "verify", "args": {"chain": "x"}},
]
CONTROL = {"sigma_provider": 1, "op": "term", "args": {"expr": "I"}, "blobs": {}}


def serve(argv, req, cwd):
    p = subprocess.run(argv, input=json.dumps(req), capture_output=True, text=True, cwd=cwd, timeout=60)
    return p.returncode, p.stdout, p.stderr


def main():
    args = sys.argv[1:]
    out_dir = tempfile.mkdtemp()
    if args[:1] == ["--python"]:
        argv, where = [args[1], "-m", "sigma_provider", "serve"], "installed"
    else:
        argv, where = [sys.executable, str(ROOT / "impl" / "sigma_provider.py"), "serve"], "impl/"
    failures = []
    for req in MALFORMED:
        rc, out, err = serve(argv, req, out_dir)
        try:
            resp = json.loads(out)
        except ValueError:
            resp = None
        if not (rc == 0 and isinstance(resp, dict) and set(resp) == {"sigma_provider", "refused"} and "Traceback" not in err):
            failures.append((req, rc, out[:80], err.strip().splitlines()[-1:] if err else ""))
    rc, out, _ = serve(argv, CONTROL, out_dir)
    control_ok = rc == 0 and "ok" in json.loads(out)
    # Negative control: the same requests against impl/ with the guards removed.
    tmp = Path(tempfile.mkdtemp())
    for n in ("sigma_glyph.py", "sigma_resume.py", "sigma_provider.py"):
        shutil.copy(ROOT / "impl" / n, tmp / n)
    src = (tmp / "sigma_provider.py").read_text()
    for guard in ('        _need(isinstance(raw, dict) and all(_hex64(h) and isinstance(v, str) for h, v in raw.items()),\n'
                  '              "blobs must map 64-hex hashes to base64 strings")\n',
                  '        _check_args(req["op"], req["args"])\n'):
        assert src.count(guard) == 1, "guard text moved; update the control"
        src = src.replace(guard, "")
    (tmp / "sigma_provider.py").write_text(src)
    bites = sum("Traceback" in serve([sys.executable, str(tmp / "sigma_provider.py"), "serve"], r, out_dir)[2]
                for r in MALFORMED[:2])
    for f in failures:
        print("FAIL ", f)
    print(f"{'OK  ' if control_ok else 'FAIL'} a well-formed request still answers ok")
    print(f"{'OK  ' if bites == 2 else 'FAIL'} without the guards the two reported requests crash ({bites}/2)")
    passed = not failures and control_ok and bites == 2
    print(f"PROVIDER-PROTOCOL ({where}): {'ALL PASS' if passed else 'FAILURES'} ({len(MALFORMED)} malformed requests refused)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
