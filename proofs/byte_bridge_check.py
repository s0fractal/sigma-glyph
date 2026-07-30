#!/usr/bin/env python3
"""Differential bridge for proofs/MachineBytes.lean + Sha256.lean (Book I bytes).

The Lean theorems are about the Lean model; this bridge is the honest seam
to the live oracle and to SHA-256 itself:

  1. Soundness guard (proof_guard.py, front "bytes") over MachineBytes.lean,
     Sha256.lean and the BytesRun.lean runner (`lean` exits 0 on sorry — this
     bridge does not): the source layer (literal-aware comment stripping,
     sorry/admit/axiom, import allowlist, metaprogramming denylist incl.
     `@[implemented_by]`, coverage registry) plus a data-only environment
     query asserting the load-bearing theorems stay within the documented TCB
     (std axioms; native_decide only for the genesis pins, per
     proofs/README.md) AND still state what they are pinned to state.
  2. FIPS 180-4 vectors: the Lean SHA-256 reproduces the standard digests.
  3. Conformance CAS: for EVERY object of tests/spec_conformance/
     vectors.json (36, incl. the deliberately malformed Era-1 0x03 one),
     the executed Lean pipeline recomputes the CAS key (hash), agrees with
     the oracle's §4.1 verdict, and round-trips valid buffers to identical
     bytes (canonicity, executed).
  4. Adversarial mutations of every object (truncation, padding, flag
     out-of-mask, wrong-but-in-mask flags, reserved opcode 0x03, op/flag
     swap): Lean and oracle verdicts must agree on all.
  5. Genesis bytes: I/K/S, FALSE, and the Canonical Invalid Object.

Needs a `lean` binary (elan). Exit 2 if unavailable — never a silent pass.
"""
import hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "impl"))
import proof_guard  # noqa: E402
import sigma_glyph as g  # noqa: E402

#: Load-bearing theorems (proofs/README.md, byte-level section); only the
#: genesis/FALSE/invalid-object pins may rest on native_decide. The lists, the
#: allowed axioms and the pinned statements live in theorem_pins.json.
FRONT = proof_guard.load_front("bytes")
THEOREMS = FRONT["guarded"]
PINS = FRONT["native_decide_ok"]

FIPS = [
    (b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    (b"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    (b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
     "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
    (bytes(range(256)) * 3,  # 768 bytes, crosses several blocks
     hashlib.sha256(bytes(range(256)) * 3).hexdigest()),
    (b"\x80" * 55, hashlib.sha256(b"\x80" * 55).hexdigest()),   # padding edge
    (b"\x00" * 64, hashlib.sha256(b"\x00" * 64).hexdigest()),   # exact block
]


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def mutations(b):
    yield b[:-1]                                  # truncated
    yield b + b"\x00"                             # padded
    if len(b) >= 2:
        yield bytes([b[0], 0x08]) + b[2:]         # flags out of 0x07 mask
        yield bytes([b[0], 0x02]) + b[2:]         # in-mask but wrong for op
        yield bytes([0x03, b[1]]) + b[2:]         # reserved opcode
        yield bytes([b[1], b[0]]) + b[2:]         # op/flags swapped
    yield b""                                     # empty buffer


def main():
    lean = proof_guard.find_lean()
    if lean is None:
        print("byte bridge needs a `lean` binary (elan) — set LEAN=... ; exit 2")
        sys.exit(2)

    problems = proof_guard.guard_sources(FRONT)
    if problems:
        fail("source guard: " + "; ".join(problems))
    print("OK    MachineBytes + Sha256 + BytesRun pass the source guard (no "
          "sorry/admit/axiom, no metaprogramming, imports in-set, every "
          "theorem accounted for)")

    objs = json.load(open(os.path.join(
        REPO, "tests", "spec_conformance", "vectors.json")))["objects"]
    genesis = [g.I_BYTES, g.K_BYTES, g.S_BYTES, g.FALSE_BYTES, g.INVALID_OBJECT]
    buffers = [bytes.fromhex(h) for h in sorted(objs.values())] + genesis
    cases = [m for b in buffers for m in mutations(b)] + buffers + [b for b, _ in FIPS]

    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, LEAN_PATH=td)
        for mod in ("Sha256", "MachineBytes", "BytesRun"):
            r = subprocess.run([lean, os.path.join(HERE, mod + ".lean"),
                                "-o", os.path.join(td, mod + ".olean")],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                fail(f"{mod}.lean does not compile: "
                     + (r.stderr or r.stdout).strip()[:500])
        print("OK    Sha256 + MachineBytes compile clean "
              "(genesis pins are theorems — compiling IS the check)")
        err = proof_guard.guard_semantics(lean, FRONT, td)
        if err:
            fail(err)
        print(f"OK    axiom cones clean AND statements match their pins for "
              f"{len(THEOREMS)} byte-level theorems (std axioms; "
              "native_decide only for the pins)")
        lines = "".join(b.hex() + "\n" for b in cases)
        r = subprocess.run([lean, "--run", os.path.join(HERE, "BytesRun.lean")],
                           input=lines, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        fail("BytesRun.lean failed: " + (r.stderr or r.stdout).strip()[:500])
    got = r.stdout.strip().splitlines()
    if len(got) != len(cases):
        fail(f"BytesRun emitted {len(got)} lines for {len(cases)} cases")

    bad = 0
    fips_map = {b: d for b, d in FIPS}
    for b, line in zip(cases, got):
        parts = line.split()
        if len(parts) != 3:
            bad += 1
            continue
        lhash, lverdict, lreser = parts
        ok = lhash == hashlib.sha256(b).hexdigest()
        if b in fips_map:
            ok &= lhash == fips_map[b]
        node = g.deser(b)
        ok &= lverdict == ("ok" if node is not None else "invalid")
        if node is not None:
            ok &= lreser == b.hex()          # canonicity, executed round-trip
        else:
            ok &= lreser == "-"
        if not ok:
            bad += 1
            if bad <= 5:
                print(f"DISAGREE  {b.hex()[:40]}…: lean={line!r}")
    if bad:
        fail(f"{bad}/{len(cases)} disagreements between Lean and the oracle")
    print(f"OK    Lean pipeline == oracle on {len(cases)} buffers "
          f"(CAS keys, verdicts, round-trips, FIPS)")
    print(f"\nBYTE-BRIDGE: ALL AGREE ({len(cases)}/{len(cases)})")


if __name__ == "__main__":
    main()
