#!/usr/bin/env python3
"""One node, one wave — and the checks that say so must be able to fail.

    python3 tests/wave_identity_selftest.py

Book I §3.2 is Identity by Hash. Book II §2 derives an APPLY node's wave as
`complete(interfere(wave(f), wave(a)), pin(APPLY(f,a)))`, and §6.2 pins
`FALSE ≡ APPLY(K,I)` at `Ph=49152` by NodeHash. Until the round-5 gate,
`wave("FALSE")` answered ph 49152 and `wave(["APPLY","K","I"])` answered ph
32768 — one node, two waves — because the pin was reachable only through a table
keyed by NAME. That is not a wrong vector; it is the identity discipline failing.

Two things are proved here, and neither can be proved by the live alias table.

**The alias-equivalence check can fail.** Remove the structural pin and the
equality must break — and break *there*, not somewhere downstream.

**The distinctness check can fail.** `ALIASES` holds exactly one entry, so
"distinct aliases are distinct nodes" over the live table compares 1 with 1 and
would pass with the check inverted, deleted, or misspelt. Adding a second alias
to the normative table to make a test non-vacuous would be inventing
specification to satisfy a test, so the second alias is synthetic and lives
here: two aliases over different structures must hash apart, and two names for
the SAME structure must be seen to collide.
"""
import contextlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))

import sigma_wave as wave_module  # noqa: E402
import sigma_glyph as book1       # noqa: E402

results = []


def chk(name, condition, detail=""):
    results.append(condition)
    print(("  OK    " if condition else "  FAIL  ") + name
          + (f" — {detail}" if detail and not condition else ""))


def without_structural_pin():
    """The module as it was before the fix: pins reachable only by name."""
    saved = wave_module.DERIVED_PINS
    wave_module.DERIVED_PINS = {}
    try:
        return wave_module.wave(["APPLY", "K", "I"]), wave_module.wave("FALSE")
    finally:
        wave_module.DERIVED_PINS = saved


@contextlib.contextmanager
def staged_edition(contradictory):
    """A temporary copy of the edition, optionally with two Pins for one node.

    A context manager rather than a bare mkdtemp: these probes run on every
    matrix run and in CI, and a test that leaves a directory behind each time is
    a test that litters a build agent.
    """
    staged = Path(tempfile.mkdtemp())
    for name in ("sigma_wave.py", "sigma_glyph.py"):
        (staged / name).write_text((ROOT / "impl" / name).read_text())
    if contradictory:
        source = (staged / "sigma_wave.py").read_text()
        original = ('ALIASES = {\n'
                    '    "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),\n'
                    '}')
        if original not in source:
            raise SystemExit("the ALIASES table changed shape; update this control")
        (staged / "sigma_wave.py").write_text(source.replace(original, (
            'ALIASES = {\n'
            '    "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),\n'
            '    "ALSO-FALSE": (["APPLY", "K", "I"], {"ph": 1}),\n'
            '}')))
    try:
        yield staged
    finally:
        shutil.rmtree(staged, ignore_errors=True)


def probe(staged, program):
    finished = subprocess.run([sys.executable, "-c", program],
                              cwd=staged, capture_output=True, text=True)
    return finished.returncode, finished.stdout.strip(), finished.stderr


def import_alone_refuses_contradiction():
    """Importing a contradictory edition must fail — with NO query made.

    The first version of this control ran `import; print(wave(...))` and asked
    whether the PROCESS failed. Under lazy validation the process also fails —
    at the query — so the control passed on the very behaviour it was written to
    forbid, which a mutation test caught. Importing alone is what separates
    them: a lazily validated module imports cleanly.
    """
    with staged_edition(contradictory=True) as staged:
        code, out, err = probe(staged, "import sigma_wave")
    return code != 0 and "ContradictoryPin" in err, out


def profile_exists_before_any_query():
    """After a bare import, the index is already built.

    This is the discriminating statement: under lazy construction DERIVED_PINS
    is None until something asks, and the answer here is `NoneType`.
    """
    with staged_edition(contradictory=False) as staged:
        code, out, _err = probe(
            staged,
            "import sigma_wave as w; "
            "print(type(w.DERIVED_PINS).__name__, len(w.DERIVED_PINS or ()))")
    return code == 0, out


def main():
    # 1. The invariant holds as the module ships.
    structural = wave_module.wave(["APPLY", "K", "I"])
    named = wave_module.wave("FALSE")
    chk("as shipped: wave(APPLY(K,I)) == wave(FALSE)", structural == named,
        f"{structural} vs {named}")
    chk("as shipped: neither side is absent",
        structural is not None and named is not None)

    # 2. The negative control: remove the structural pin and the equality must
    #    break at the alias-equivalence check, in the phase field the pin sets.
    broken_structural, broken_named = without_structural_pin()
    chk("negative control: without the structural pin the two disagree",
        broken_structural != broken_named,
        "removing the pin changed nothing — the check is not load-bearing")
    chk("negative control: they disagree in ph, which is the field FALSE pins",
        broken_structural is not None and broken_named is not None
        and broken_structural["ph"] != broken_named["ph"]
        and {k: v for k, v in broken_structural.items() if k != "ph"}
        == {k: v for k, v in broken_named.items() if k != "ph"},
        f"{broken_structural} vs {broken_named}")
    restored = wave_module.wave(["APPLY", "K", "I"])
    chk("negative control restored the module", restored == named)

    # 3. Distinctness, over a table big enough for the word to mean anything.
    synthetic = {
        "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),
        "OTHER": (["APPLY", "I", "K"], {"ph": 12345}),
    }
    hashes = wave_module.alias_node_hashes(synthetic)
    chk("two aliases over different structures hash apart",
        len(set(hashes.values())) == 2, str(hashes))
    chk("the synthetic FALSE still hashes to Book I's FALSE_H",
        hashes["FALSE"] == book1.FALSE_H.hex())

    colliding = {
        "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),
        "ALSO-FALSE": (["APPLY", "K", "I"], {"ph": 1}),
    }
    collided = wave_module.alias_node_hashes(colliding)
    chk("two names for one structure are seen to collide",
        len(set(collided.values())) == 1,
        "distinctness would have passed on a table that is not distinct")

    # Two names for one node with DIFFERENT pins is a contradiction in the
    # table, and a dict would settle it by iteration order. It must fail closed,
    # and the message must carry the digest and both names, or the operator
    # learns only that something is wrong somewhere.
    #
    # The check that stood here asserted `len(pins) == 1` over exactly this
    # table and called it "the contradiction is visible". It was not visible:
    # ALSO-FALSE had silently overwritten FALSE, and the green check was the
    # cover. That is the defect class this repository exists to name, committed
    # in the test written to prevent it.
    try:
        pins = wave_module.load_annotation_profile(colliding)
        chk("contradictory pins are refused, not silently resolved", False,
            f"returned {pins} instead of refusing")
    except wave_module.ContradictoryPin as refusal:
        message = str(refusal)
        chk("contradictory pins are refused, not silently resolved", True)
        chk("the refusal names the digest",
            collided["FALSE"] in message, message)
        chk("the refusal names both aliases",
            "FALSE" in message and "ALSO-FALSE" in message, message)
        chk("the refusal shows both pins",
            "49152" in message and "'ph': 1" in message, message)

    # Synonyms are not contradictions: one node named twice, pinned the same
    # way, says one thing twice.
    synonyms = {
        "FALSE": (["APPLY", "K", "I"], {"ph": 49152}),
        "ALSO-FALSE": (["APPLY", "K", "I"], {"ph": 49152}),
    }
    chk("identical pins under two names are allowed",
        wave_module.load_annotation_profile(synonyms)
        == {book1.FALSE_H.hex(): {"ph": 49152}})

    # 3b. The refusal is at LOAD, and the proof has to be about timing rather
    #     than about the loader raising. A contradictory edition is built in a
    #     temporary copy of the module and imported in a subprocess: the import
    #     itself must fail, and the query placed after it must never run. If the
    #     validation were lazy the import would succeed and the query would be
    #     answered for every node except the pinned one.
    #
    #     The control that stood here defined a `watched_wave` wrapper, never
    #     installed it, and asserted an always-empty list. It proved only that
    #     the loader raises — the same disease this file exists to catch, in the
    #     file itself.
    refused, _out = import_alone_refuses_contradiction()
    chk("a contradictory edition fails on `import` alone, with no query made",
        refused, "the module imported cleanly and would answer until asked "
                 "about the pinned node")
    built, shape = profile_exists_before_any_query()
    chk("after a bare import the index already exists (not None)",
        built and shape == "dict 1", f"got {shape!r}")

    # 3c. And the lookup reads the index built at load rather than rebuilding
    #     it. Break the loader after admission has succeeded; a query must still
    #     answer, because it must never call the loader.
    saved_loader = wave_module.load_annotation_profile

    def exploding_loader(*_args, **_kwargs):
        raise AssertionError("the lookup called the loader; it must read the "
                             "index built at load")

    wave_module.load_annotation_profile = exploding_loader
    try:
        after = wave_module.wave(["APPLY", "K", "I"])
        chk("a query does not re-enter the loader",
            after == named, f"got {after}")
    except AssertionError as broke:
        chk("a query does not re-enter the loader", False, str(broke))
    finally:
        wave_module.load_annotation_profile = saved_loader

    # 4. An alias whose structure this language cannot hash has no derived pin,
    #    rather than a pin under some improvised key.
    unhashable = {"GHOST": (["APPLY", "V", "I"], {"ph": 7})}
    chk("an alias over a Ph-only leaf has no computable identity",
        wave_module.alias_node_hashes(unhashable)["GHOST"] is None)
    chk("and therefore contributes no derived pin",
        wave_module.load_annotation_profile(unhashable) == {})

    print()
    if all(results):
        print(f"WAVE-IDENTITY-SELFTEST: ALL PASS ({len(results)}/{len(results)})")
        return 0
    print(f"WAVE-IDENTITY-SELFTEST: FAILURES "
          f"({sum(results)}/{len(results)})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
