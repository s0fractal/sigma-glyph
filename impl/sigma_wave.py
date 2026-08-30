"""Sigma-GLYPH Book II reference implementation (wave layer; current release bundle v0.6.1).

LUT_COS generation (SHA-256 arbitrated), interfere() with the v0.5
entropy–coherence coupling (ADR-002 adopted): coherent interference
creates order (delta_en < 0), destructive creates disorder. Pure math,
zero effect on Book I hashes — waves are views, never identity.

    python3 impl/sigma_wave.py         # selftest + replay wave_vectors.json
    python3 impl/sigma_wave.py gen     # regenerate tests/spec_conformance/wave_vectors.json
"""
import hashlib
import json
import re
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
    """Book II §5 with the v0.5 entropy–coherence coupling (ADR-002).

    Implementer note (Book II §3 widths): this reference rides on Python
    bignums; ports MUST use the mandated int64/uint64 intermediates —
    (r+32767)*65535 ≈ 4.29e9 overflows int32 — and explicitly cast new_am
    to uint16 / new_en to int16 (here guaranteed by the am<=65535 proof
    and clamp_i16)."""
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

# ---- ADR-005 (R1): field-level pins, wave() as a partial function ----------
# Full pins (Book II §6.1, Trinity) supply complete vectors; partial pins
# override exactly the fields they list (§2); everything else derives via
# interfere() on APPLY, and is ABSENT (None) otherwise (§2.1).
FULL_PINS = {
    "I": W(0, 65535, -32768),
    "S": W(16384, 65535, -32768),
    "K": W(32768, 65535, -32768),
}
# Named APPLY-structures with partial pins (Book II §6.2): alias -> (term, pin)
ALIASES = {
    "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),
}


# Ph-only entries (§6.2-§6.4): a Pin on `ph`, with `am`/`en` underived, so
# `wave()` is ABSENT for them (§2.1). Absent wave is not absent identity, and
# conflating the two was a real defect: `SATOSHI` and the six Pantheon nodes have
# NodeHashes printed in the Book and are node-level Pin entries that admission
# MUST cover, while `V` has no NodeHash at all and is only a sector coordinate.
#
# §6.4 states the forging method normatively. §6.3 does NOT follow it: SATOSHI's
# atom is the BTC genesis block hash rather than SHA-256 of its name, so its
# NodeHash is the constant the Book prints and cannot be derived from "SATOSHI".
SATOSHI_NODE_HASH = "11c856acd4b6868a91c2cc2cf6331d57bf268f56adcae0c0f3070c4ec00ed3c7"


def forge_node_hash(name):
    """Book II §6.4: `NodeHash = SHA-256(0x00 0x01 ‖ SHA-256(ASCII-name))`."""
    return hashlib.sha256(bytes([0x00, 0x01])
                          + hashlib.sha256(name.encode("ascii")).digest()).hexdigest()


PANTHEON_PH = {"TESLA": 8192, "TURING": 20480, "BACH": 21845,
               "LEIBNIZ": 24576, "GODEL": 40960, "HEGEL": 57344}

# name -> (NodeHash hex, partial WavePin). Node-level: admission covers these.
PH_ONLY_NODE_PINS = {"SATOSHI": (SATOSHI_NODE_HASH, {"ph": 8192})}
PH_ONLY_NODE_PINS.update({name: (forge_node_hash(name), {"ph": ph})
                          for name, ph in PANTHEON_PH.items()})

# §6.2's V row: a sector coordinate with no NodeHash. NOT a node-level pin, and
# deliberately outside the annotation profile.
SECTOR_COORDINATES = {"V": 16384}

# Every phase coordinate a reader can ask for, whether or not it names a node.
PH_ONLY_LEAVES = dict(SECTOR_COORDINATES)
PH_ONLY_LEAVES.update({name: pin["ph"] for name, (_h, pin) in PH_ONLY_NODE_PINS.items()})

def canonical(term, alias_table=None):
    """A term reduced to what it IS: every alias replaced by its structure.

    Identity is by hash (Book I §3.2), so `FALSE` and `APPLY(K,I)` are one node
    and must have one wave. `canonical` is the identity handle this symbolic term
    language can compute without Book I's serializer; `alias_node_hashes()` binds
    it to the NodeHashes Book II §6.2 actually prints, so the handle is grounded
    rather than merely conventional.
    """
    table = ALIASES if alias_table is None else alias_table
    if isinstance(term, str) and term in table:
        return canonical(table[term][0], table)
    if isinstance(term, list) and term and term[0] == "APPLY":
        return ["APPLY", canonical(term[1], table), canonical(term[2], table)]
    return term


# Pins on DERIVED nodes, keyed by canonical identity rather than by name.
#
# Book II §2 states the derived case as
# `wave(APPLY(f,a)) = complete(interfere(wave(f), wave(a)), pin(APPLY(f,a)))`,
# and §6.2 pins `FALSE ≡ APPLY(K,I)` at `Ph=49152` BY NODEHASH, leaving `Am`/`En`
# derived field-by-field. The pin therefore belongs to the node.
#
# It used to be reachable only through the alias table, keyed by NAME, so the
# `complete(..., pin(...))` step was absent from the structural path and one node
# had two waves: `wave(["APPLY","K","I"])` answered ph 32768 and `wave("FALSE")`
# answered ph 49152. That is a violation of Identity by Hash, not a wrong test
# vector. Found by the round-5 gate (Gemini 3.1 Pro). The defect is older than
# this candidate and could not surface while the oracle outranked the prose --
# whatever the oracle did WAS the answer.
# The key is the NodeHash itself. Keying by the JSON of the canonical structure
# would have been a claim about structural equality after alias expansion, which
# is a weaker statement than §3.2 makes and would have been worth saying out
# loud rather than calling it identity.
def node_hash_of(term):
    """Book I's NodeHash for a term, or None when this language cannot name one.

    Ph-only leaves (§6.2-§6.4) and unpinned LITERALs have a node somewhere, but
    the wave term language does not carry their bytes; a term containing one has
    no computable identity here and therefore no derived pin. Its wave is absent
    for other reasons anyway (§2.1), so nothing hinges on the fallback.
    """
    import sigma_glyph as book1

    leaves = {"I": book1.I_H, "K": book1.K_H, "S": book1.S_H}
    # Ph-only NODES have identity even though their wave is absent (§2.1).
    leaves.update({name: bytes.fromhex(digest)
                   for name, (digest, _pin) in PH_ONLY_NODE_PINS.items()})
    if isinstance(term, str):
        return leaves.get(term)
    if isinstance(term, list) and term and term[0] == "APPLY":
        left, right = node_hash_of(term[1]), node_hash_of(term[2])
        if left is None or right is None:
            return None
        return book1.node_hash(book1.ser(book1.APPLY, book1.F_LEFT | book1.F_RIGHT,
                                         left=left, right=right))
    return None


HEX64 = re.compile(r"[0-9a-f]{64}")


class AnnotationProfileError(ValueError):
    """The annotation profile is not admissible."""


class ContradictoryPin(AnnotationProfileError):
    """Two names for one node, pinning it differently."""


class MalformedNodeHash(AnnotationProfileError):
    """A node-level entry declares something that is not a NodeHash."""


class ContradictoryIdentity(AnnotationProfileError):
    """One label bound to two different NodeHashes."""


class UnresolvableIdentity(AnnotationProfileError):
    """A pin-bearing entry whose node cannot be named."""


class AliasCycle(AnnotationProfileError):
    """An alias chain that never reaches a node."""


def load_annotation_profile(alias_table=None, full_pins=None, node_pins=None):
    """Validate the node-level annotation profile and return NodeHash -> Pin.

    Book II §2.3 says `NodeHash(x) = NodeHash(y)` implies `pin(x) = pin(y)`, and
    that admission is what establishes it — so admission has to see EVERY
    node-level §6 source at once, not one table at a time.

    It used to validate `ALIASES` alone. `FULL_PINS` and `ALIASES` are separate
    authorities, so `{"ALSO-K": ("K", {"ph": 1})}` was accepted while
    `FULL_PINS["K"]` said `{ph 32768, am 65535, en -32768}` — two different Pins
    for `bc0c2fe2…`, admitted, because no single check ever looked at both. The
    invariant was global and the enforcement was per-table.

    Ph-only entries are NOT all alike, and treating them as one class was the
    second half of the same defect. `SATOSHI` (§6.3) and the six Pantheon nodes
    (§6.4) have NodeHashes printed in the Book: their `wave()` is absent because
    `am`/`en` are underived (§2.1), but their identity and their `{ph}` Pin are
    real, and admission MUST cover them. Only `V` (§6.2) has no NodeHash at all;
    it is a sector coordinate and stays out.

    Node-level entries are admitted **at the NodeHash they declare**, not at one
    re-derived from a global table — otherwise a caller could hand this function
    a different hash and admission would quietly validate the old one.
    """
    aliases = ALIASES if alias_table is None else alias_table
    fulls = FULL_PINS if full_pins is None else full_pins
    ph_only = PH_ONLY_NODE_PINS if node_pins is None else node_pins
    import sigma_glyph as book1

    # Identity is resolved WITHIN this profile. A node entry declares a
    # NodeHash, and every reference to that label — an alias, or a composite
    # term containing it — must resolve to the same one. Re-reading the
    # edition's global tables here split one symbol into two nodes by route:
    # with `SATOSHI -> aaaa…` declared, `ALSO-SATOSHI -> SATOSHI` was admitted
    # under the *edition's* `11c856ac…`, so the profile held both.
    # A label binds to exactly one NodeHash, and every source that names it
    # must agree. `local[name] = declared` used to overwrite silently, so
    # `node_pins={"K": ("aaaa…", …)}` moved genesis K to a hash of the caller's
    # choosing and dropped the real one.
    bindings = {}

    def bind_label(name, digest, source):
        if name in bindings and bindings[name][0] != digest:
            existing, first_source = bindings[name]
            raise ContradictoryIdentity(
                f"label {name!r} is bound to {existing} by {first_source} and to "
                f"{digest} by {source}. Within one admitted profile a lookup "
                f"label must resolve unambiguously to one NodeHash; the label is "
                f"not identity (Book II §2.3 leaves labels as descriptors). Two "
                f"resolutions for one label make the profile inadmissible.")
        bindings[name] = (digest, source)

    for glyph, digest in (("I", book1.I_H), ("K", book1.K_H), ("S", book1.S_H)):
        bind_label(glyph, digest.hex(), "Book I §5.1")
    for name in sorted(ph_only):
        declared = ph_only[name][0]
        if not isinstance(declared, str) or HEX64.fullmatch(declared) is None:
            raise MalformedNodeHash(
                f"{name!r} declares {declared!r}, which is not a 32-byte "
                f"NodeHash in lowercase hexadecimal")
        bind_label(name, declared, "node-level Pin table (§6.3-§6.4)")

    def resolve(term, seen=frozenset()):
        """A term's NodeHash under THIS profile's labels, or None.

        Cycles are detected by the alias names already visited, not by a depth
        limit: a bound on chain length would invent a normative maximum, and a
        long acyclic chain is well-formed.
        """
        if isinstance(term, str):
            if term in aliases:
                if term in seen:
                    raise AliasCycle(
                        f"alias chain revisits {term!r}: "
                        f"{' -> '.join(sorted(seen | {term}))}")
                return resolve(aliases[term][0], seen | {term})
            binding = bindings.get(term)
            return binding[0] if binding else None
        if isinstance(term, list) and len(term) == 3 and term[0] == "APPLY":
            left, right = resolve(term[1], seen), resolve(term[2], seen)
            if left is None or right is None:
                return None
            return book1.node_hash(
                book1.ser(book1.APPLY, book1.F_LEFT | book1.F_RIGHT,
                          left=bytes.fromhex(left), right=bytes.fromhex(right))).hex()
        return None

    profile, claimed_by = {}, {}

    def admit(name, key, pin, what):
        # A pin whose node cannot be named is REFUSED, not skipped. Skipping it
        # produced an empty profile that admitted cleanly -- a check whose
        # subject had quietly gone away.
        if key is None:
            raise UnresolvableIdentity(
                f"{what} {name!r} carries a Pin {pin!r} but no NodeHash can be "
                f"resolved for it under this profile; a Pin with no node is not "
                f"admissible. Sector coordinates (§6.2 V) carry no Pin and "
                f"belong in SECTOR_COORDINATES, not here.")
        if key in profile and profile[key] != pin:
            raise ContradictoryPin(
                f"{claimed_by[key]!r} and {name!r} are the same node {key} but "
                f"pin it differently: {profile[key]!r} vs {pin!r}. One node has "
                f"one wave (Book I §3.2, Book II §2.3); pick one pin. This is an "
                f"annotation-profile refusal at load time, not an eval exit: it "
                f"is not a Receipt.exit and not a DISSONANCE.")
        profile[key] = pin
        claimed_by[key] = name

    # Sorted so a contradictory profile always names the same pair, whatever
    # the dict order happens to be.
    for name in sorted(fulls):
        admit(name, bindings.get(name, (None,))[0], fulls[name], "full Pin")
    for name in sorted(ph_only):
        admit(name, bindings[name][0], ph_only[name][1], "node-level Pin")
    for name in sorted(aliases):
        term, pin = aliases[name]
        digest = resolve(term)
        if digest is not None:
            # An alias is also a label: it cannot name a node different from the
            # one its own label is already bound to.
            bind_label(name, digest, "alias table")
        admit(name, digest, pin, "alias")
    return profile


# The edition's own profile, validated at import. A contradictory ALIASES table
# makes this module fail to load, which is what "refused at load" means.
DERIVED_PINS = load_annotation_profile()


def structural_pin(term):
    """The Pin of a derived node, found by what the node is, not what it is called.

    Reads the index built at load; never builds one. A lookup is not the place to
    discover that the profile was never valid.
    """
    digest = node_hash_of(canonical(term))
    return None if digest is None else DERIVED_PINS.get(digest.hex())


def coordinate(name):
    """Book II §2.1/§6: the pinned phase coordinate of a named entity —
    visible even where wave() is absent. Returns uint16 ph or None."""
    if name in FULL_PINS:
        return FULL_PINS[name]["ph"]
    if name in ALIASES:
        return ALIASES[name][1].get("ph")
    return PH_ONLY_LEAVES.get(name)


def complete(w, pin):
    """Pin overrides exactly the fields it lists (Book II §2, R1)."""
    if w is None:
        w = {}
    out = dict(w)
    out.update(pin)
    return out if set(out) == {"ph", "am", "en"} else None


def wave(term):
    """Book II wave() over symbolic terms; returns a WaveVectorQ or None (absent).
    Terms: glyph name | alias | {"lit": ...} (unpinned LITERAL) | ["APPLY", f, a]."""
    if isinstance(term, str):
        if term in FULL_PINS:
            return dict(FULL_PINS[term])
        if term in ALIASES:
            sub, pin = ALIASES[term]
            return complete(wave(sub), pin)
        return None                                   # Ph-only leaf or unknown: absent (§2.1)
    if isinstance(term, dict):
        return None                                   # unpinned LITERAL: absent (§2.1)
    if isinstance(term, list) and term[0] == "APPLY":
        wl, wr = wave(term[1]), wave(term[2])
        if wl is None or wr is None:
            return None                               # interfere with absent operand -> absent
        derived = interfere(wl, wr)
        pin = structural_pin(term)
        return derived if pin is None else complete(derived, pin)
    raise ValueError(f"bad term: {term!r}")

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

# ADR-005 vectors: kind=term (pin completion / absence) and kind=iterate
TERM_CASES = [
    ("WV-FALSE-DERIVED", "FALSE",
     "FALSE = APPLY(K,I) with Ph-only pin 49152: am/en derive per R1 -> "
     "{49152, 0, -32512}; the normative Book II §6.2 row"),
    ("WV-FALSE-ANCESTOR-SILENT", ["APPLY", "FALSE", "I"],
     "any APPLY whose derived subtree contains FALSE has am=0: silence "
     "propagates, phase coordinates stay visible"),
    ("WV-PH-ONLY-ABSENT", "SATOSHI",
     "Ph-only pin on a non-APPLY leaf: coordinate visible, wave absent (§2.1)"),
    ("WV-UNPINNED-LITERAL-ABSENT", {"lit": "unpinned"},
     "unpinned LITERAL: wave absent (§2.1); absence is not an error"),
]
ITER_CASES = [
    ("WV-ITER-DECAY", W(0, 49151, 0),
     "repeated self-interference from partial amplitude decays quadratically "
     "to 0 (Book II §5.1); pins the full rounding chain"),
]
COORD_CASES = [
    ("WV-COORD-SATOSHI", "SATOSHI",
     "Ph-only leaf: wave absent (WV-PH-ONLY-ABSENT) but the coordinate stays "
     "visible (Book II §2.1/§6.3)"),
    ("WV-COORD-V", "V",
     "sector coordinate: shares phase with S (density cluster, not a collision)"),
    ("WV-COORD-FALSE", "FALSE",
     "alias pin coordinate: FALSE ph=49152 regardless of derived am=0"),
]

# WHERE THE RECORDED VECTORS LIVE — and why "absent" has two meanings.
#
# The vectors live in the REPO, at tests/spec_conformance/. The wheel installs
# three modules and nothing else (pyproject: `py-modules`), so from
# site-packages this path does not exist and never will. `pip install
# sigma-glyph` + `python -m sigma_wave` therefore used to print
# `FAIL wave_vectors.json present` and exit 1 — a false accusation: nothing was
# wrong, the replay corpus simply is not part of the distribution.
#
# But a missing file in a CHECKOUT *is* a defect, and the two must not be
# reported the same way. A skip that can hide a real deletion is the pattern
# this project keeps finding. So the distinction is made structurally: a
# checkout is `impl/` next to `pyproject.toml` AND a `tests/spec_conformance/`
# directory to hold the corpora. Anything else — a site-packages install, or an
# unpacked sdist, which ships impl/ and pyproject.toml but no tests/ — announces
# the replay as SKIPPED, never as passed and never as failed.
#
# The one case this cannot tell apart is someone deleting the whole
# `tests/spec_conformance/` directory in a real checkout. That is a far louder
# act than deleting one file, and CI regenerates into that directory, so it
# fails there instead.
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_CORPUS_DIR = _REPO / "tests" / "spec_conformance"
FROM_CHECKOUT = (_HERE.name == "impl" and (_REPO / "pyproject.toml").is_file()
                 and _CORPUS_DIR.is_dir())
VEC_PATH = _CORPUS_DIR / "wave_vectors.json"

# ============================================================================
# Spec-declared expectations — hand-written from spec/book-2-navigation.md
# ============================================================================
# Same discipline as tests/spec_conformance/generate.py and the governance
# suite: these values are read off the SPEC, not computed by this oracle, and
# `gen` REFUSES to write wave_vectors.json if interfere()/wave()/coordinate()
# disagrees with one. Vectors absent from this table stay oracle-generated and
# are regression-only — replaying them here proves nothing about correctness.
#
#   "quoted"  — the value is printed verbatim in the spec.
#   "derived" — hand-computed from the §3/§4/§5 formulas and the §4 LUT anchors;
#               the arithmetic is spelled out in the cite.
SPEC_EXPECT = {
    "WV-CONSTRUCTIVE": ("derived",
        "§5.1: delta=0 -> r=LUT[0]=32767 (§4 anchor) -> amp_factor=65535, "
        "am=65535^2/65535=65535; delta_en=round(-32767/128)=-256; "
        "en=avg(0,0)-256; ph=w1.ph (§5.2)",
        W(0, 65535, -256)),
    "WV-ORTHOGONAL": ("derived",
        "§4 anchor LUT[16384]=0 -> delta_en=0, amp_factor=round(32767*65535/65534)"
        "=32768 (exact half rounds away from zero, §3) -> am=32768",
        W(0, 32768, 0)),
    "WV-DESTRUCTIVE": ("derived",
        "§4 anchor LUT[32768]=-32767 -> amp_factor=0 -> am=0; "
        "delta_en=round(32767/128)=+256",
        W(0, 0, 256)),
    "WV-CLAMP-LOW": ("quoted",
        "§5.1: {am=65535, en=-32768} is the unique nonzero fixed point",
        W(0, 65535, -32768)),
    "WV-CLAMP-HIGH": ("derived",
        "§3 clamp_i16: avg(32767,32767)+256 = 33023 clamps to 32767; "
        "destructive -> am=0",
        W(0, 0, 32767)),
    "WV-SELF-MAX": ("derived",
        "§5.1 Resonance Identity: phase kept (§5.2), am stable at 65535, en drifts -256",
        W(12345, 65535, -256)),
    "WV-SELF-PARTIAL": ("derived",
        "§5.1 am -> am^2/65535: 49151^2 = 2415820801; 2415820801/65535 = 36863 "
        "remainder 4096, and 2*4096 < 65535 so it rounds down (§3)",
        W(0, 36863, -256)),
    "WV-NEG-TIE": ("quoted",
        "§5: 'avg(-1,-2) = -2, together -258, not -257' — the exact sentence that "
        "makes floor-division implementations nonconforming",
        W(0, 65535, -258)),
    "WV-LEFT-DOMINANCE": ("quoted",
        "§5.2 Law of Left Dominance: interfere(A,B).ph = A.ph. The spec states "
        "nothing about am/en for this pair; they stay oracle-generated",
        {"ph": 8192}),
    "WV-FALSE-DERIVED": ("quoted",
        "§6.2: FALSE pins Ph=49152 only; am=0 (K/I orthogonality, "
        "LUT[32768]=-32767 -> amp_factor=0) and en=-32512 "
        "(avg(-32768,-32768)+256) are the derived row printed in the spec",
        W(49152, 0, -32512)),
    "WV-FALSE-ANCESTOR-SILENT": ("derived",
        "§6.2 normative consequence: any APPLY whose derived subtree contains "
        "FALSE has am=0. ph=49152 by §5.2; delta=|49152-0| -> min(49152,16384)"
        "=16384 -> r=0 -> en=avg(-32512,-32768)=-32640",
        W(49152, 0, -32640)),
    "WV-PH-ONLY-ABSENT": ("quoted",
        "§2.1: a Ph-only pin on a non-APPLY leaf leaves the wave ABSENT", None),
    "WV-UNPINNED-LITERAL-ABSENT": ("quoted",
        "§2.1: unpinned LITERALs have no wave; absence is a legitimate state", None),
    "WV-COORD-SATOSHI": ("quoted", "§6.3 Time Anchor table: SATOSHI Ph=8192", 8192),
    "WV-COORD-V": ("quoted", "§6.2 Grand Cross table: V Ph=16384", 16384),
    "WV-COORD-FALSE": ("quoted", "§6.2 Grand Cross table: FALSE Ph=49152", 49152),
}
# Left oracle-generated on purpose (regression-only): the spec states the decay
# is quadratic but prints no term of the sequence.
ORACLE_ONLY = {"WV-ITER-DECAY"}

# Book II §4 states the LUT anchors, control points and the arbiter hash
# outright — the one place the spec is fully self-contained. Gate `gen` on them
# too, so a regenerated vector file can never carry a drifted table.
SPEC_LUT_CHECKS = [
    ("§4 arbiter SHA-256(LUT_BLOB)",
     lambda: hashlib.sha256(b"".join(struct.pack(">h", v) for v in LUT_COS)).hexdigest(),
     LUT_ARBITER),
    ("§4 anchors [0], [16384], [32768]",
     lambda: (LUT_COS[0], LUT_COS[16384], LUT_COS[32768]), (32767, 0, -32767)),
    ("§4 controls [1],[8192],[16383],[16385],[24576],[32767]",
     lambda: (LUT_COS[1], LUT_COS[8192], LUT_COS[16383], LUT_COS[16385],
              LUT_COS[24576], LUT_COS[32767]),
     (32767, 23170, 3, -3, -23170, -32767)),
    ("§4 format: 32769 entries", lambda: len(LUT_COS), 32769),
    ("§6.1 Trinity pins (I, S, K)",
     lambda: (FULL_PINS["I"], FULL_PINS["S"], FULL_PINS["K"]),
     (W(0, 65535, -32768), W(16384, 65535, -32768), W(32768, 65535, -32768))),
]


def check_spec_expectations(vectors):
    """Return the list of ways the oracle contradicts the declared spec values."""
    failures = []
    for label, probe, want in SPEC_LUT_CHECKS:
        got = probe()
        if got != want:
            failures.append(f"LUT/pins {label}: got {got}, spec declares {want}")
    seen = set()
    for v in vectors:
        _check_spec_vector(v, seen, failures)
    for vid in sorted(set(SPEC_EXPECT) - seen):
        failures.append(f"declared expectation {vid} was never exercised "
                        f"(vector renamed or deleted?)")
    return failures


def _check_spec_vector(vector, seen, failures):
    vid = vector["id"]
    decl = SPEC_EXPECT.get(vid)
    if decl is None:
        if vid not in ORACLE_ONLY:
            failures.append(f"{vid}: neither declared in SPEC_EXPECT nor listed "
                            f"in ORACLE_ONLY — classify it before it ships")
        return
    seen.add(vid)
    _, cite, want = decl
    got = vector.get("expected", vector.get("expected_ph"))
    if isinstance(want, dict) and isinstance(got, dict):
        got = {key: got.get(key) for key in want}      # partial declaration
    if got != want:
        failures.append(f"{vid}: got {got}, spec ({cite}) declares {want}")


def iterate_am(w0):
    w, seq = dict(w0), [w0["am"]]
    while w["am"]:
        w = interfere(w, w)
        seq.append(w["am"])
    return seq


#: The refusal every corpus-writing verb owes an installed copy. Book III
#: imports it: one wording, one exit status, one place to correct.
REFUSAL_TAG = "REFUSING"


def require_checkout(verb, module_file, vec_path, from_checkout):
    """`gen` writes into the repo. Outside a checkout there is nowhere to write.

    From an installed copy `_REPO` is site-packages' parent, so this used to end
    in a FileNotFoundError traceback: a maintainer verb crashing instead of
    saying it does not apply. The corpus is deliberately NOT shipped as package
    data — regenerating it is only meaningful next to the spec text the values
    are read off and the committed vectors the result must be diffed against —
    so the honest answer is a refusal, not a traceback and not a silent success.
    """
    if from_checkout:
        return
    name = Path(module_file).stem
    print(f"{REFUSAL_TAG}: `{verb}` regenerates the conformance corpus at "
          f"tests/spec_conformance/{vec_path.name} and requires a source "
          f"checkout of sigma-glyph.\n"
          f"  This copy is installed at {Path(module_file).resolve().parent}. "
          f"The repository's tests/ tree is not part of the distribution, and "
          f"regenerated vectors would have neither the spec text they are read "
          f"off nor the committed corpus they must be diffed against.\n"
          f"  From a checkout: git clone "
          f"https://github.com/s0fractal/sigma-glyph && "
          f"python3 impl/{name}.py {verb}\n"
          f"  Nothing was written. This copy CAN run the self-test: "
          f"python -m {name}", file=sys.stderr)
    raise SystemExit(2)


def gen_vectors():
    require_checkout("gen", __file__, VEC_PATH, FROM_CHECKOUT)
    vectors = [
        {"id": vid, "note": note, "w1": w1, "w2": w2,
         "expected": interfere(w1, w2)}
        for vid, w1, w2, note in CASES
    ]
    vectors += [
        {"id": vid, "kind": "term", "note": note, "term": term,
         "expected": wave(term)}
        for vid, term, note in TERM_CASES
    ]
    vectors += [
        {"id": vid, "kind": "iterate", "note": note, "start": w0,
         "expected_am_sequence": iterate_am(w0)}
        for vid, w0, note in ITER_CASES
    ]
    vectors += [
        {"id": vid, "kind": "coordinate", "note": note, "name": name,
         "expected_ph": coordinate(name)}
        for vid, name, note in COORD_CASES
    ]
    failures = check_spec_expectations(vectors)
    if failures:
        print("REFUSING TO GENERATE — the oracle disagrees with "
              "spec/book-2-navigation.md:")
        for f in failures:
            print("  " + f)
        print("\nEither impl/sigma_wave.py is wrong, or the spec is wrong and needs "
              "an erratum. Do not 'fix' this by editing SPEC_EXPECT to match the "
              "oracle: that is the circularity this block exists to prevent.")
        raise SystemExit(1)
    doc = {
        "format": "sigma-glyph-wave-conformance",
        "format_version": 2,
        "spec_version": "0.7.0",   # Book II
        "lut_arbiter": LUT_ARBITER,
        "notes": [
            "interfere() per Book II v0.5 (entropy-coherence coupling adopted).",
            "div_round_half_up is round-half-AWAY-FROM-ZERO (Book II §3).",
            "v0.5.1 (ADR-005, R1): kind=term vectors pin field-level pin completion "
            "and absent-wave semantics (expected=null means wave absent); "
            "kind=iterate pins repeated self-interference; vectors without kind "
            "are raw interfere(w1,w2) as in format_version 1.",
            "expected values computed by impl/sigma_wave.py; regenerate: python3 impl/sigma_wave.py gen",
        ],
        "vectors": vectors,
    }
    VEC_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    n_spec = len(SPEC_EXPECT)
    print(f"wrote {VEC_PATH.name}: {len(vectors)} vectors "
          f"({n_spec} spec-derived/constraining, {len(vectors) - n_spec} "
          f"oracle-generated/regression-only)")


def alias_node_hashes(alias_table=None):
    """Each alias's canonical structure, hashed as Book I hashes it.

    `canonical` is a handle this term language can compute; the identity the
    Books speak of is a NodeHash. This binds the two, so "pins are keyed by
    identity" is a checkable statement rather than a convention. Book I is
    imported for this and for nothing else -- Book II's algebra does not depend
    on the evaluator, only on its notion of identity (§3.2).
    """
    table = ALIASES if alias_table is None else alias_table
    out = {}
    for name, (term, _pin) in table.items():
        digest = node_hash_of(canonical(term, table))
        out[name] = None if digest is None else digest.hex()
    return out


def _check_identity_by_hash(chk):
    """One node, one wave — however it is spelled.

    Until the round-5 gate found it, `wave("FALSE")` answered ph 49152 and
    `wave(["APPLY","K","I"])` answered ph 32768 for the same NodeHash. The pin
    lived behind a name.

    Each equality is written as two named checks over two named values. The
    earlier one-liner `wave(name) == wave(term) is not None` was a chained
    comparison -- it did mean "equal AND the structural side is not None" -- but
    a reader has to know that to see it, and one of the two sides still went
    unasserted. Two statements say it once each.
    """
    import sigma_glyph as book1

    for name, (term, _pin) in ALIASES.items():
        named = wave(name)
        structural = wave(term)
        chk(f"alias equivalence: wave({name}) == wave(structure)",
            named == structural)
        chk(f"alias equivalence is not vacuous: both sides are waves, not absent",
            named is not None and structural is not None)
    hashes = alias_node_hashes()
    chk("FALSE's canonical structure hashes to Book I's FALSE_H, in full",
        hashes["FALSE"] == book1.FALSE_H.hex())


def _check_core_wave_properties(chk):
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
    chk("partial self am=49151 -> am^2/65535 rounded = 36863", r["am"] == div_round_half_up(49151 * 49151, 65535))
    r = interfere(W(0, 65535, -1), W(0, 65535, -2))
    chk("negative tie: avg(-1,-2) = -2 (away from zero) -> en -258", r["en"] == -258)
    # entropy drift sequence from en=0: -256, -512, ... linear
    en, seq = 0, []
    for _ in range(5):
        en = interfere(W(0, 65535, en), W(0, 65535, en))["en"]
        seq.append(en)
    chk("drift sequence linear", seq == [-256, -512, -768, -1024, -1280])

    # ADR-005 (R1) semantics
    chk("FALSE derived {49152,0,-32512}", wave("FALSE") == W(49152, 0, -32512))
    chk("FALSE ancestor silent", wave(["APPLY", "FALSE", "I"])["am"] == 0)
    chk("Ph-only leaf absent", wave("SATOSHI") is None)
    chk("unpinned LITERAL absent", wave({"lit": "x"}) is None)
    chk("interfere with absent operand absent", wave(["APPLY", "SATOSHI", "I"]) is None)


def _check_recorded_vector(chk, vector):
    kind = vector.get("kind", "interfere")
    vid = vector["id"]
    if kind == "interfere":
        got = interfere(vector["w1"], vector["w2"])
        chk(f"vector {vid}", got == vector["expected"], f"got {got}")
    elif kind == "term":
        got = wave(vector["term"])
        chk(f"vector {vid}", got == vector["expected"], f"got {got}")
    elif kind == "iterate":
        got = iterate_am(vector["start"])
        chk(f"vector {vid}", got == vector["expected_am_sequence"], f"got {got}")
    elif kind == "coordinate":
        got = coordinate(vector["name"])
        chk(f"vector {vid}", got == vector["expected_ph"], f"got {got}")
    else:
        chk(f"vector {vid}", False, f"unknown kind {kind}")


def _replay_recorded_vectors(chk, skipped):
    if VEC_PATH.exists():
        doc = json.loads(VEC_PATH.read_text())
        for vector in doc["vectors"]:
            _check_recorded_vector(chk, vector)
    elif FROM_CHECKOUT:
        chk("wave_vectors.json present", False, "run: python3 impl/sigma_wave.py gen")
    else:
        skipped.append("recorded-vector replay")
        print(f"SKIP recorded-vector replay: {VEC_PATH.name} is not shipped in "
              f"the installed package (it lives in the repo at "
              f"tests/spec_conformance/). The property checks above ran in full; "
              f"the replay did not run and is not claimed. To run it, use a "
              f"checkout: python3 impl/sigma_wave.py")


def selftest():
    ok = []
    skipped = []

    def chk(name, cond, detail=""):
        ok.append(cond)
        print(("OK  " if cond else "FAIL"), name, "" if cond else detail)

    _check_core_wave_properties(chk)
    _check_identity_by_hash(chk)
    _replay_recorded_vectors(chk, skipped)

    print(("\nWAVE: ALL PASS" if all(ok) else "\nWAVE: FAILURES PRESENT")
          + f" ({sum(ok)}/{len(ok)})"
          + (f" — SKIPPED: {', '.join(skipped)}" if skipped else ""))
    return all(ok)


# Every verb this module accepts beyond the default (no-argument) self-test.
# tools/check_release_surface.py reads this constant and REFUSES to pass unless
# every verb in it is classified RUNNABLE or NOT_RUNNABLE for an installed copy
# and behaves that way when actually executed from outside a checkout. `gen`
# shipped for four releases with nobody running it that way.
VERBS = ("gen",)

if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv[:1] == ["gen"]:
        gen_vectors()               # refuses (exit 2) outside a checkout; exits
        sys.exit(0)                 # 1 if the oracle contradicts the spec
    if argv:
        print(f"usage: {sys.argv[0]} [{'|'.join(VERBS)}]\n"
              f"  unknown verb {argv[0]!r}. No argument runs the self-test; "
              f"refusing rather than running it under a name that does not "
              f"exist and reporting success.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if selftest() else 1)
