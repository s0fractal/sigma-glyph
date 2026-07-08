#!/usr/bin/env python3
"""Differential bridge for proofs/WaveAlgebra.lean (Book II wave algebra).

The Lean theorems are about the Lean `interfere`; this bridge is the honest
seam that ties them to the live oracle:

  1. Freshness: proofs/LutData.lean regenerates byte-identically from the
     oracle's arbiter-checked LUT (a stale or hand-edited table fails).
  2. No-sorry guard: `lean` exits 0 even when a proof uses `sorry` (it is a
     warning) — this bridge fails on any sorry/axiom token in WaveAlgebra.lean.
  3. Differential: proofs/WaveRun.lean (the Lean `interfere`, executed) must
     agree with impl/sigma_wave.py `interfere` on a deterministic boundary
     grid plus the pinned special points (crystallization, the
     FV-FOLD-UNSOUND triple, negative-tie parities).

Needs a `lean` binary (elan). Exit 2 if unavailable — never a silent pass.
"""
import itertools, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "impl"))
from sigma_wave import interfere, W  # noqa: E402


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def main():
    lean = os.environ.get("LEAN", "lean")
    if shutil.which(lean) is None:
        print("wave bridge needs a `lean` binary (elan) — set LEAN=... ; exit 2")
        sys.exit(2)

    # 1. freshness
    with tempfile.TemporaryDirectory() as td:
        cur = open(os.path.join(HERE, "LutData.lean"), "rb").read()
        tmp_out = os.path.join(td, "LutData.lean")
        r = subprocess.run([sys.executable, os.path.join(HERE, "gen_lut_lean.py")],
                           capture_output=True, text=True,
                           env=dict(os.environ, LUT_LEAN_OUT=tmp_out))
        if r.returncode != 0:
            fail("LUT regeneration errored: " + r.stderr.strip())
        if open(tmp_out, "rb").read() != cur:
            fail("LutData.lean is stale — regenerate with proofs/gen_lut_lean.py")
    print("OK    LutData.lean regenerates byte-identically (arbiter-checked)")

    # 2. no-sorry guard
    body = open(os.path.join(HERE, "WaveAlgebra.lean")).read()
    if re.search(r"\b(sorry|admit)\b", body) or re.search(r"^\s*axiom\b", body, re.M):
        fail("WaveAlgebra.lean contains sorry/admit/axiom")
    print("OK    WaveAlgebra.lean carries no sorry/admit/axiom")

    # 3. differential grid
    phs = [0, 1, 8192, 16384, 32767, 32768, 49152, 65535]
    ams = [0, 1, 2, 32768, 65534, 65535]
    ens = [-32768, -32767, -1, 0, 1, 32767]
    waves = [W(p, a, e) for p, a, e in itertools.product(phs, ams, ens)]
    cases = []
    for i, w in enumerate(waves):
        cases.append((w, w))                                  # self (crystallization line)
        cases.append((w, waves[(i * 7 + 3) % len(waves)]))    # deterministic partner
    for tri in [(W(0, 65535, 0), W(16384, 65535, 0), W(16384, 65535, 0))]:
        w1, w2, w3 = tri                                      # FV-FOLD-UNSOUND
        cases += [(w1, w2), (w2, w3), (interfere(w1, w2), w3),
                  (w1, interfere(w2, w3))]
    cases.append((W(0, 65535, -32768), W(0, 65535, -32768)))  # crystal point
    cases.append((W(0, 100, -1), W(0, 100, -2)))              # negative tie (WV-NEG-TIE class)

    lines = "".join(f"{a['ph']} {a['am']} {a['en']} {b['ph']} {b['am']} {b['en']}\n"
                    for a, b in cases)
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, LEAN_PATH=td)
        for mod in ("LutData", "WaveAlgebra"):
            r = subprocess.run([lean, os.path.join(HERE, mod + ".lean"),
                                "-o", os.path.join(td, mod + ".olean")],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                fail(f"{mod}.lean does not compile: "
                     + (r.stderr or r.stdout).strip()[:500])
        print("OK    LutData + WaveAlgebra compile clean (theorems check)")
        r = subprocess.run([lean, "--run", os.path.join(HERE, "WaveRun.lean")],
                           input=lines, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        fail("WaveRun.lean failed: " + (r.stderr or r.stdout).strip()[:500])
    got = r.stdout.strip().splitlines()
    if len(got) != len(cases):
        fail(f"WaveRun emitted {len(got)} lines for {len(cases)} cases")
    bad = 0
    for (a, b), line in zip(cases, got):
        exp = interfere(a, b)
        want = f"{exp['ph']} {exp['am']} {exp['en']}"
        if line.strip() != want:
            bad += 1
            if bad <= 5:
                print(f"DISAGREE  {a} · {b}: lean={line.strip()!r} oracle={want!r}")
    if bad:
        fail(f"{bad}/{len(cases)} disagreements between Lean and the oracle")
    print(f"OK    Lean interfere == oracle interfere on {len(cases)} boundary cases")
    print(f"\nWAVE-BRIDGE: ALL AGREE ({len(cases)}/{len(cases)})")


if __name__ == "__main__":
    main()
