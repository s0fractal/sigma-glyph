"""Sigma-GLYPH v0.5.0 — Reference Implementation, Book II (wave layer).

LUT_COS generation (SHA-256 arbitrated), interfere() with the v0.5
entropy–coherence coupling (ADR-002 adopted): coherent interference
creates order (delta_en < 0), destructive creates disorder. Pure math,
zero effect on Book I hashes — waves are views, never identity.

    python3 impl/sigma_wave.py         # selftest + replay wave_vectors.json
    python3 impl/sigma_wave.py gen     # regenerate tests/spec_conformance/wave_vectors.json
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

LUT_ARBITER = "c16701c44851da342f5d1f977ba5284e66dde3abd2c6740b979e39ac1d4d38b2"


def div_round_half_up(n, d):
    """Book II §3: round-half-AWAY-FROM-ZERO; d > 0. (Floor-division variants
    diverge on negative odd sums — see the pinned negative-tie vector.)"""
    s = -1 if n < 0 else 1
    a = abs(n)
    q, r = a // d, a % d
    if 2 * r >= d:
        q += 1
    return s * q


def clamp_i16(x):
    return max(-32768, min(32767, x))


def gen_lut():
    lut = []
    for d in range(32769):
        v = 32767 * math.cos(math.pi * d / 32768)
        lut.append(int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1))
    blob = b"".join(struct.pack(">h", v) for v in lut)
    if hashlib.sha256(blob).hexdigest() != LUT_ARBITER:
        raise SystemExit("LUT arbiter mismatch — FAIL FAST (Book II §4)")
    return lut


LUT_COS = gen_lut()


def interfere(w1, w2):
    """Book II §5 with the v0.5 entropy–coherence coupling (ADR-002)."""
    new_ph = w1["ph"]                                        # Law of Left Dominance
    x = w1["ph"] - w2["ph"]
    d32 = abs(x)
    delta = min(d32, 65536 - d32)
    r = LUT_COS[delta]
    delta_en = div_round_half_up(-r, 128)                    # ∈ [−256, +256]
    new_en = clamp_i16(div_round_half_up(w1["en"] + w2["en"], 2) + delta_en)
    amp_factor = div_round_half_up((r + 32767) * 65535, 65534)
    prod01 = div_round_half_up(w1["am"] * w2["am"], 65535)
    new_am = div_round_half_up(prod01 * amp_factor, 65535)
    return {"ph": new_ph & 0xFFFF, "am": new_am, "en": new_en}


W = lambda ph, am, en: {"ph": ph, "am": am, "en": en}

# id, w1, w2 — expected values are COMPUTED by the oracle, never hand-written
CASES = [
    ("WV-CONSTRUCTIVE", W(0, 65535, 0), W(0, 65535, 0),
     "full constructive alignment: order created (delta_en = -256)"),
    ("WV-ORTHOGONAL", W(0, 65535, 0), W(16384, 65535, 0),
     "orthogonal: entropy-neutral, amplitude halves"),
    ("WV-DESTRUCTIVE", W(0, 65535, 0), W(32768, 65535, 0),
     "full destructive: disorder created (delta_en = +256), amplitude annihilates"),
    ("WV-CLAMP-LOW", W(0, 65535, -32768), W(0, 65535, -32768),
     "constructive at minimum entropy: clamp holds, {am=65535,en=-32768} is the fixed point"),
    ("WV-CLAMP-HIGH", W(0, 65535, 32767), W(32768, 65535, 32767),
     "destructive at maximum entropy: clamp holds"),
    ("WV-SELF-MAX", W(12345, 65535, 0), W(12345, 65535, 0),
     "self-application at max amplitude: phase kept, amplitude stable, entropy drifts -256"),
    ("WV-SELF-PARTIAL", W(0, 49151, 0), W(0, 49151, 0),
     "self-application at 0.75 amplitude: quadratic decay (Resonance Identity, amplitude part)"),
    ("WV-NEG-TIE", W(0, 65535, -1), W(0, 65535, -2),
     "negative odd-sum tie: avg(-1,-2) MUST round away from zero to -2 (Book II §3); "
     "floor-division implementations yield -257 instead of -258 here and are NONCONFORMING"),
    ("WV-LEFT-DOMINANCE", W(8192, 30000, 100), W(40960, 20000, -100),
     "phase is w1's, amplitude and entropy symmetric"),
]

VEC_PATH = Path(__file__).resolve().parents[1] / "tests/spec_conformance/wave_vectors.json"


def gen_vectors():
    doc = {
        "format": "sigma-glyph-wave-conformance",
        "format_version": 1,
        "spec_version": "0.5.0",
        "lut_arbiter": LUT_ARBITER,
        "notes": [
            "interfere() per Book II v0.5 (entropy-coherence coupling adopted).",
            "div_round_half_up is round-half-AWAY-FROM-ZERO (Book II §3).",
            "expected values computed by impl/sigma_wave.py; regenerate: python3 impl/sigma_wave.py gen",
        ],
        "vectors": [
            {"id": vid, "note": note, "w1": w1, "w2": w2,
             "expected": interfere(w1, w2)}
            for vid, w1, w2, note in CASES
        ],
    }
    VEC_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {VEC_PATH.name}: {len(CASES)} vectors")


def selftest():
    ok = []

    def chk(name, cond, detail=""):
        ok.append(cond)
        print(("OK  " if cond else "FAIL"), name, "" if cond else detail)

    chk("LUT arbiter", hashlib.sha256(
        b"".join(struct.pack(">h", v) for v in LUT_COS)).hexdigest() == LUT_ARBITER)
    chk("LUT anchors", (LUT_COS[0], LUT_COS[16384], LUT_COS[32768]) == (32767, 0, -32767))
    chk("LUT controls", (LUT_COS[1], LUT_COS[8192], LUT_COS[16383], LUT_COS[16385],
                         LUT_COS[24576], LUT_COS[32767]) == (32767, 23170, 3, -3, -23170, -32767))

    r = interfere(W(0, 65535, 0), W(0, 65535, 0))
    chk("constructive: am stable, en -256", r == W(0, 65535, -256))
    r = interfere(W(0, 65535, -32768), W(0, 65535, -32768))
    chk("fixed point {65535,-32768}", r == W(0, 65535, -32768))
    r = interfere(W(0, 49151, 0), W(0, 49151, 0))
    chk("0.75 self -> 0.5625 (36864)", r["am"] == div_round_half_up(49151 * 49151, 65535))
    r = interfere(W(0, 65535, -1), W(0, 65535, -2))
    chk("negative tie: avg(-1,-2) = -2 (away from zero) -> en -258", r["en"] == -258)
    # entropy drift sequence from en=0: -256, -512, ... linear
    en, seq = 0, []
    for _ in range(5):
        en = interfere(W(0, 65535, en), W(0, 65535, en))["en"]
        seq.append(en)
    chk("drift sequence linear", seq == [-256, -512, -768, -1024, -1280])

    if VEC_PATH.exists():
        doc = json.loads(VEC_PATH.read_text())
        for v in doc["vectors"]:
            got = interfere(v["w1"], v["w2"])
            chk(f"vector {v['id']}", got == v["expected"], f"got {got}")
    else:
        chk("wave_vectors.json present", False, "run: python3 impl/sigma_wave.py gen")

    print(("\nWAVE: ALL PASS" if all(ok) else "\nWAVE: FAILURES PRESENT")
          + f" ({sum(ok)}/{len(ok)})")
    return all(ok)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gen":
        gen_vectors()
    else:
        sys.exit(0 if selftest() else 1)
