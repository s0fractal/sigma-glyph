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
     proofs/README.md), still state what they are pinned to state, AND are
     still stated in terms of the definitions they are pinned to be about
     (`serialize`, `deserialize`, `Wf`, `Node`, `Sha256.sha256`, the atoms).
  2. FIPS 180-4 vectors: the Lean SHA-256 reproduces the standard digests.
  3. Conformance CAS: for EVERY object of tests/spec_conformance/
     vectors.json (36, incl. the deliberately malformed Era-1 0x03 one),
     the executed Lean pipeline recomputes the CAS key (hash), agrees with
     the oracle's §4.1 verdict, and round-trips valid buffers to identical
     bytes (canonicity, executed).
  4. Adversarial mutations of every object (truncation, padding, flag
     out-of-mask, wrong-but-in-mask flags, reserved opcode 0x03, op/flag
     swap): Lean and oracle verdicts must agree on all.
  5. Genesis bytes: I/K/S, FALSE, and the Canonical Invalid Object — the
     buffers through the executed pipeline, AND (new) what the five genesis
     theorems literally CLAIM, cross-checked against the oracle's constants.
     "Compiling IS the check" only ever said the hex in the file is the digest
     of whatever `hIT`/`hKT`/`hST` happen to be: swapping those two bodies and
     the two hex strings left every theorem true, every pin matched and this
     bridge printing ALL AGREE, with TV-1 `genesis_I` asserting K's hash
     (2026-07 round-3 review, F13).

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


#: (theorem, oracle buffer, expected preimage strings). What each genesis
#: theorem literally CLAIMS, checked against the oracle — the differential this
#: front did not have. "Compiling IS the check" only says the hex in the file
#: is the digest of whatever `hIT`/`hKT`/`hST` happen to be: swap the bodies of
#: `hIT` and `hKT` and swap the two hex strings, and every theorem stays true,
#: every pin still matched (the dump said only "a 64-character string"), and
#: the bridge printed ALL AGREE — with TV-1 `genesis_I` asserting K's hash
#: (2026-07 round-3 review, F13).
#: (theorem, oracle constant, inline literals the statement must carry,
#:  {atom definition: the string it must hash}).
GENESIS_CLAIMS = [
    ("MachineBytes.genesis_I", "I_BYTES", [], {"MachineBytes.hIT": "I"}),
    ("MachineBytes.genesis_K", "K_BYTES", [], {"MachineBytes.hKT": "K"}),
    ("MachineBytes.genesis_S", "S_BYTES", [], {"MachineBytes.hST": "S"}),
    ("MachineBytes.false_is_a_theorem", "FALSE_BYTES", [],
     {"MachineBytes.hKT": "K", "MachineBytes.hIT": "I"}),
    ("MachineBytes.invalid_object_pins", "INVALID_OBJECT", ["Invalid Object"],
     {}),
]


def check_genesis(envq):
    """Every genesis theorem's hex, and its atoms, against the oracle."""
    for thm, const, inline, atoms in GENESIS_CLAIMS:
        lits = proof_guard.strlits(envq["decls"][thm]["type"])
        if not lits:
            fail(f"{thm}: no string literal in the elaborated statement — the "
                 "dump cannot be cross-checked against the oracle")
        want = hashlib.sha256(getattr(g, const)).hexdigest()
        if lits[-1] != want:
            fail(f"{thm} asserts the hash {lits[-1]}, but the oracle's "
                 f"sha256(sigma_glyph.{const}) is {want} — the Lean claim and "
                 "the reference implementation disagree about which object "
                 "this is")
        if lits[:-1] != inline:
            fail(f"{thm} is stated over inline literals {lits[:-1]}, not "
                 f"{inline} — the preimage the pin is about changed")
        for atom, text in atoms.items():
            got = proof_guard.strlits(envq["deps"].get(atom, ""))
            if got != [text]:
                fail(f"{thm} is stated over {atom}, which hashes {got} and not "
                     f"['{text}'] — swapping two atoms' bodies keeps every "
                     "theorem true and every statement pinned")
    print(f"OK    the {len(GENESIS_CLAIMS)} genesis/FALSE/invalid-object "
          "theorems assert exactly the oracle's digests, over the atoms the "
          "oracle names (checked on the elaborated statements and definitions, "
          "independently of the pins)")


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
        # FRONT["build"] + FRONT["runner_sources"] is the single place this
        # front's compiled module set is spelled — the guard reads the same
        # field, so the two cannot drift apart (round-4 F17).
        err = proof_guard.build_front(lean, FRONT, td, runners=True)
        if err:
            fail(err)
        print("OK    Sha256 + MachineBytes compile clean "
              "(the genesis pins are theorems, so they are kernel-checked "
              "claims — but see the oracle cross-check below)")
        envq = {}
        err = proof_guard.guard_semantics(lean, FRONT, td, out=envq)
        if err:
            fail(err)
        print(f"OK    axiom cones clean, statements match their pins AND every "
              f"definition they are stated in terms of matches its pin, for "
              f"{len(THEOREMS)} byte-level theorems (std axioms; "
              "native_decide only for the pins)")
        check_genesis(envq)
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
