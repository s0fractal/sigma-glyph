#!/usr/bin/env python3
"""Controls for ADR-011's reference profile, and the mutations that earn them.

    python3 proposals/adr-011/selftest.py

Non-normative. Every load-bearing negative control is followed by a mutation
that restores the defect it guards and requires THAT control, for ITS reason, to
go red. A control nobody has seen fail is not evidence.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "impl"))

import equality_profile as ep      # noqa: E402
import sigma_glyph as sg           # noqa: E402

results = []


def chk(name, condition, detail=""):
    results.append(condition)
    print(("  OK    " if condition else "  FAIL  ") + name
          + (f" — {detail}" if detail and not condition else ""))


def settle(a, b, ba=5000, bb=5000, profile=ep.CHURCH_V0):
    return ep.settle_eq(profile, a, b, ba, bb, ep.fresh_env())


def main():
    P = ep.CHURCH_V0

    # 1-2. The two ordinary answers.
    chk("1. equal Church naturals settle EQUAL",
        settle(ep.church(5), ep.church(5)).verdict == ep.EQUAL)
    chk("2. different Church naturals settle UNEQUAL",
        settle(ep.church(5), ep.church(7)).verdict == ep.UNEQUAL)

    # 3. The counterexample cannot be laundered into a proof of equality.
    #    λf.λx.X collides with λf.λx.x at the observation point, and is refused
    #    at admission for naming the marker.
    lam_zero = ep.church(0)
    lam_marker = ("lam", "f", ("lam", "x", ("lit", ep.MARKER_X_ATOM)))
    collision = settle(lam_zero, lam_marker)
    chk("3. a term naming a marker is REFUSED, not settled",
        collision.verdict == ep.REFUSED and "marker" in collision.detail,
        f"{collision.verdict}: {collision.detail}")
    env = ep.fresh_env()
    left = sg.eval_receipt(ep._observe_church(lam_zero, env), 5000, env)
    right = sg.eval_receipt(ep._observe_church(lam_marker, env), 5000, env)
    chk("3b. and the collision it would have hidden is real",
        left.result_hash == right.result_hash and left.exit == right.exit
        == "normal_form",
        "the two terms no longer collide at the observation point, so this "
        "control has stopped testing anything")

    # 3c. Admission is PER SIDE. Refusing one term must not mark the other
    #     refused, and the valid side must still produce its receipt.
    forward = settle(ep.church(3), lam_marker)
    reverse = settle(lam_marker, ep.church(3))
    chk("3c. valid / marker -> lhs ok, rhs REFUSED, and lhs still has a receipt",
        forward.verdict == ep.REFUSED and forward.lhs_status == "ok"
        and forward.rhs_status == ep.REFUSED and forward.lhs is not None
        and forward.rhs is None,
        f"{forward.verdict} lhs={forward.lhs_status} rhs={forward.rhs_status}")
    chk("3d. marker / valid -> the statuses swap with the sides",
        reverse.verdict == ep.REFUSED and reverse.lhs_status == ep.REFUSED
        and reverse.rhs_status == "ok" and reverse.lhs is None
        and reverse.rhs is not None,
        f"{reverse.verdict} lhs={reverse.lhs_status} rhs={reverse.rhs_status}")

    # 4-5. Exhaustion on either side, and the same answer either way round.
    chk("4. exhaustion on the left is UNSETTLED, not a verdict",
        settle(ep.church(12), ep.church(12), ba=5, bb=5000).verdict == ep.UNSETTLED)
    chk("5. exhaustion on the right is UNSETTLED, not a verdict",
        settle(ep.church(12), ep.church(12), ba=5000, bb=5).verdict == ep.UNSETTLED)

    # 6. A demanded hash that is not there. `observe` materializes into the
    #    environment it is given, so a starved settlement has to be run against
    #    an environment that ACCEPTS the writes and cannot serve them — a peer
    #    whose CAS does not have what it was told about. That is the honest
    #    shape of the failure, and it is why the profile has an environment
    #    policy at all.
    class DroppingStore(sg.Store):
        """Accepts puts, serves only what it was seeded with."""

        def put(self, blob):        # noqa: D401 - mirrors Store.put's signature
            return sg.node_hash(blob)

    starved = DroppingStore()
    for genesis in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
        sg.Store.put(starved, genesis)
    root = ep._observe_church(ep.church(3), starved)
    receipt = sg.eval_receipt(root, 5000, starved)
    chk("6. an unresolved reference is an exit, and it is not normal_form",
        receipt.exit == "unresolved_reference", receipt.exit)
    chk("6b. so a settlement over it is UNSETTLED",
        ep.settle_eq(P, ep.church(3), ep.church(3), 5000, 5000,
                     DroppingStore()).verdict == ep.UNSETTLED)

    # 7. One address, two exits. This is why the exit is checked at all.
    env7 = ep.fresh_env()
    dis = sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.R_ATP)
    env7.put(dis)
    settled_on_dissonance = sg.eval_receipt(sg.node_hash(dis), 100, env7)
    genuinely_exhausted = sg.eval_receipt(
        ep._observe_church(ep.church(12), env7), 5, env7)
    chk("7. DISSONANCE(ATP Exhausted) has ONE address and TWO exits",
        settled_on_dissonance.result_hash == genuinely_exhausted.result_hash
        and settled_on_dissonance.exit == "normal_form"
        and genuinely_exhausted.exit == "atp_exhausted")
    chk("7b. two exhausted runs of DIFFERENT numbers are never EQUAL",
        settle(ep.church(3), ep.church(5), ba=30, bb=30).verdict == ep.UNSETTLED,
        "the address-only comparison called these equal")

    # 8. Order.
    forward = settle(ep.church(0), ep.church(12), ba=100, bb=100)
    reverse = settle(ep.church(12), ep.church(0), ba=100, bb=100)
    chk("8. swapping the sides does not change the verdict class",
        forward.verdict == reverse.verdict,
        f"{forward.verdict} vs {reverse.verdict}")
    settled_fwd = settle(ep.church(0), ep.church(12))
    settled_rev = settle(ep.church(12), ep.church(0))
    chk("8b. nor when both sides finish",
        settled_fwd.verdict == settled_rev.verdict == ep.UNEQUAL)

    # 9. A settlement carries the profile that produced it.
    #    This proves the field is present and distinguishing. It does NOT prove
    #    two settlements "cannot be merged" — nothing here stops a consumer
    #    from ignoring the field. That is a property of consumers, not of this
    #    control.
    other = ep.EqualityProfile(
        **{**P.__dict__, "profile_id": "sigma-glyph/adr-011/church@v0-other-markers"})
    one = settle(ep.church(5), ep.church(5))
    two = ep.settle_eq(other, ep.church(5), ep.church(5), 5000, 5000, ep.fresh_env())
    chk("9. a settlement records the profile_id that produced it, and two "
        "profiles produce distinguishable settlements",
        one.profile_id != two.profile_id
        and one.profile_id == P.profile_id)

    # 10. A local fault is not a Book I outcome.
    tight = ep.fresh_env()
    root10 = ep._observe_church(ep.church(12), tight)
    try:
        sg.eval_receipt(root10, 5000, tight,
                        limits={"max_node_depth": 2, "max_materialized_nodes": 4,
                                "max_store_fetches": 4, "max_atp": None})
        chk("10. a local resource limit raises rather than returning a DISSONANCE",
            False, "no fault raised")
    except sg.ResourceFault:
        chk("10. a local resource limit raises rather than returning a DISSONANCE",
            True)

    # 11. DOCUMENTATION ASSERTION, not a strong executable control.
    #    It shows that a one-sided re-execution yields one receipt where a
    #    settlement yields two. It does not prevent anyone from reading a
    #    one-sided green as a settlement; no predicate here can.
    env11 = ep.fresh_env()
    root11 = ep._observe_church(ep.church(5), env11)
    single = sg.eval_receipt(root11, 5000, env11)
    both = settle(ep.church(5), ep.church(5))
    chk("11. (documentation assertion) a Warrant-style term+expect check "
        "produces ONE receipt where a settlement produces two",
        single.result_hash.hex() == both.lhs.result_hash
        and both.rhs is not None and single is not None,
        "a single re-execution against a fixed address carries no second side")

    # 12. Binder shadowing is over-acceptance, and it is refused.
    #    `λf.λf.f(f)` walked the numeral spine and matched, because both
    #    binders were compared BY NAME. Under shadowing the inner binder wins,
    #    so the term denotes `λa.λb.b(b)`, whose observation agrees with no
    #    numeral. Admitting it would put a term outside the domain that
    #    reflection and preservation rest on.
    shadowed = ("lam", "f", ("lam", "f", ("lapp", ("var", "f"), ("var", "f"))))
    refused12 = False
    try:
        P.admit(shadowed)
    except ep.Refused:
        refused12 = True
    chk("12. a shadowed binder `λf.λf.f(f)` is refused at admission",
        refused12, "admitted a term whose binders shadow")

    #    ...and it really is not a numeral: its observation matches none.
    env12 = ep.fresh_env()
    shadow_obs = sg.eval_receipt(
        ep._observe_church(shadowed, env12), 5000, env12)
    numeral_addresses = set()
    for n in (0, 1, 2, 3):
        env_n = ep.fresh_env()
        numeral_addresses.add(sg.eval_receipt(
            ep._observe_church(ep.church(n), env_n), 5000, env_n
        ).result_hash.hex())
    chk("12b. and its observation is not the observation of any small numeral",
        shadow_obs.exit == "normal_form"
        and shadow_obs.result_hash.hex() not in numeral_addresses,
        f"{shadow_obs.exit} {shadow_obs.result_hash.hex()[:16]}")

    # 13. `profile_id` is a name the profile picks; it is not an identity.
    #     A profile carrying the SAME id with an observer that returns the
    #     marker for every term settles church(5) EQUAL to church(7). The
    #     settlement must distinguish them, and `profile_id` cannot.
    forged = ep.EqualityProfile(**{
        **P.__dict__,
        "observe": lambda term, env: ep._materialize(
            env, ("lit", ep.MARKER_X_ATOM))})
    settled_true = settle(ep.church(5), ep.church(7))
    settled_forged = ep.settle_eq(forged, ep.church(5), ep.church(7),
                                  5000, 5000, ep.fresh_env())
    chk("13. two profiles with the SAME profile_id can disagree on a verdict",
        settled_forged.profile_id == settled_true.profile_id
        and settled_forged.verdict == ep.EQUAL
        and settled_true.verdict == ep.UNEQUAL,
        f"{settled_true.verdict} vs {settled_forged.verdict}")
    chk("13b. and the settlement separates them by profile_commitment",
        settled_forged.profile_commitment != settled_true.profile_commitment)
    # 13c. The Book anchor must BE the anchor.
    #      This field held the prose "Book I document version 0.6.0, anchor
    #      e3e5d008…, adopted …" and the control asked only that it was
    #      non-empty and copied from the profile. Both were true of a string no
    #      verifier could compare to anything. It is now 64 hex, recomputed
    #      here from the Book's own bytes by a route that does not import the
    #      profile's function.
    import hashlib as _hl
    book_bytes = (HERE.parents[1] / "spec/book-1-truth.md").read_bytes()
    independent_anchor = _hl.sha256(
        bytes([0x00, 0x01]) + _hl.sha256(book_bytes).digest()).hexdigest()
    chk("13c. the settlement's book_anchor is 64 hex and equals the anchor "
        "recomputed independently from spec/book-1-truth.md",
        len(settled_true.book_anchor) == 64
        and set(settled_true.book_anchor) <= set("0123456789abcdef")
        and settled_true.book_anchor == independent_anchor,
        f"{settled_true.book_anchor!r} vs {independent_anchor}")
    chk("13d. and the prose moved to book_context, where prose belongs",
        "0.6.0" in settled_true.book_context
        and settled_true.book_context != settled_true.book_anchor)

    #      One flipped hex character must break it — and must stop the
    #      settlement, not merely be visible in it. The shape check cannot see
    #      a flipped digit, and `settle_eq` always executes the LOCAL Book I
    #      oracle, so a foreign anchor that proceeded produced two receipts
    #      under one Book while claiming another.
    flipped = ("f" if settled_true.book_anchor[0] != "f" else "0") \
        + settled_true.book_anchor[1:]
    watched_anchor, anchor_calls = _watched_observer_profile(book_anchor=flipped)
    settled_flip = ep.settle_eq(watched_anchor, ep.church(3), ep.church(3),
                                5000, 5000, ep.fresh_env())
    chk("13e. a valid-but-foreign 64-hex anchor is REFUSED, with no receipts",
        settled_flip.verdict == ep.REFUSED
        and settled_flip.lhs is None and settled_flip.rhs is None
        and len(settled_flip.book_anchor) == 64,
        f"{settled_flip.verdict}, lhs={settled_flip.lhs is not None}")
    chk("13e2. and its observer was called EXACTLY 0 times",
        anchor_calls == [], f"observer ran {len(anchor_calls)} time(s)")
    chk("13e3. the refusal names both anchors, so the mismatch is readable",
        flipped in settled_flip.detail
        and independent_anchor in settled_flip.detail)

    #      A malformed anchor is refused outright, before anything runs.
    unshaped = ep.EqualityProfile(**{**P.__dict__,
                                     "book_anchor": "Book I version 0.6.0"})
    settled_unshaped = ep.settle_eq(unshaped, ep.church(3), ep.church(3),
                                    5000, 5000, ep.fresh_env())
    chk("13f. an anchor that is not 64 hex refuses the settlement outright",
        settled_unshaped.verdict == ep.REFUSED
        and settled_unshaped.lhs is None and settled_unshaped.rhs is None)

    # 15. The profile is committed to BEFORE it is executed.
    #     The commitment was computed while the Settlement was being built, so
    #     a profile whose source became unreadable between import and
    #     settlement had its admission run, both observers run and the store
    #     written, and only then raised. The system executed a profile and
    #     afterwards discovered it could not say which profile it had executed.
    watched, calls = _unreadable_observer_profile()
    settled_uncommitted = ep.settle_eq(watched, ep.church(3), ep.church(5),
                                       5000, 5000, ep.fresh_env())
    chk("15. a profile that cannot be committed to is refused",
        settled_uncommitted.verdict == ep.REFUSED
        and settled_uncommitted.profile_commitment is None
        and settled_uncommitted.lhs is None,
        str(settled_uncommitted.detail))
    chk("15b. and its observer was called EXACTLY 0 times",
        calls == [], f"observer ran {len(calls)} time(s) before the refusal")

    # 16. The grammar is closed. Reading a tuple by index accepts every
    #     superset of the shape asked for, so both of these were admitted as
    #     written-out numerals and settled EQUAL against church(0).
    malformed = [
        ("a trailing field on the outer lam",
         ("lam", "f", ("lam", "x", ("var", "x")), "EXTRA")),
        ("a trailing field on the inner lam",
         ("lam", "f", ("lam", "x", ("var", "x"), "EXTRA"))),
        ("a trailing field on a lapp",
         ("lam", "f", ("lam", "x", ("lapp", ("var", "f"), ("var", "x"),
                                    "EXTRA")))),
        ("a trailing field on a var",
         ("lam", "f", ("lam", "x", ("var", "x", "EXTRA")))),
        ("a non-string binder name",
         ("lam", 7, ("lam", "x", ("var", "x")))),
        ("a bare list where a tuple is required",
         ["lam", "f", ["lam", "x", ["var", "x"]]]),
    ]
    for why, term in malformed:
        refused16 = False
        try:
            P.admit(term)
        except ep.Refused:
            refused16 = True
        chk(f"16. malformed term refused: {why}",
            refused16 and not ep._is_church_literal(term))
    chk("16b. and every numeral 0..8 written by church() is still admitted",
        all(P.admit(ep.church(n)) is None for n in range(9)))

    # 14. A callable with no readable source cannot be committed to, and the
    #     commitment says so instead of degrading to a weaker digest.
    import types
    orphan = types.FunctionType(
        (lambda term, env: None).__code__, {"__name__": "nowhere"})
    orphan.__module__ = "a-module-that-is-not-imported"
    homeless = ep.EqualityProfile(**{**P.__dict__, "observe": orphan})
    failed_closed = False
    try:
        ep.profile_commitment(homeless)
    except ep.Refused:
        failed_closed = True
    chk("14. a profile whose observer has no readable source is refused a "
        "commitment, not given a partial one", failed_closed)

    adr_prints_real_values()
    receipt_is_fresh()
    mutation_evidence()

    print()
    if all(results):
        print(f"ADR-011-SELFTEST: ALL PASS ({len(results)}/{len(results)})")
        return 0
    print(f"ADR-011-SELFTEST: FAILURES ({sum(results)}/{len(results)})")
    return 1


def _independent_node_hash_of_literal(preimage: bytes) -> str:
    """Book I's NodeHash of `LITERAL(SHA-256(preimage))`, computed HERE.

    Deliberately uses only `hashlib`: no `ep.MARKER_*`, no `sg.ser`, no
    `sg.node_hash`. The previous version of this control asked the production
    module for a constant and then checked that the prose contained the same
    constant — if the module and the prose were wrong together, it stayed green.

    Book I §1.1 layout for a LITERAL: opcode 0x00, flags 0x01 (F_ATOM), atom.
    """
    import hashlib
    atom = hashlib.sha256(preimage).digest()
    return hashlib.sha256(bytes([0x00, 0x01]) + atom).hexdigest()


def _watched_observer_profile(**overrides):
    """A normal profile whose observer records every call.

    Used to assert that a refusal happened BEFORE any observation, rather than
    only that a refusal happened.
    """
    calls = []

    def observe(term, env):
        calls.append(term)
        return ep._observe_church(term, env)

    return ep.EqualityProfile(**{**ep.CHURCH_V0.__dict__, "observe": observe,
                                 **overrides}), calls


def _unreadable_observer_profile():
    """A profile readable at import whose source is gone by settlement time.

    Codex's reproduction. The observer records each call into a list, so the
    control can assert it was never reached rather than assert only that a
    refusal happened.
    """
    import importlib.util
    import linecache
    import tempfile

    calls = []
    handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    handle.write("def observe(term, env):\n"
                 "    RECORD.append(term)\n"
                 "    return OBSERVE(term, env)\n")
    handle.close()
    spec = importlib.util.spec_from_file_location("adr011_vanishing", handle.name)
    module = importlib.util.module_from_spec(spec)
    sys.modules["adr011_vanishing"] = module
    spec.loader.exec_module(module)
    module.RECORD = calls
    module.OBSERVE = ep._observe_church

    Path(handle.name).unlink()
    linecache.clearcache()
    return ep.EqualityProfile(**{**ep.CHURCH_V0.__dict__,
                                 "observe": module.observe}), calls


def receipt_is_fresh():
    """The benchmark receipt must describe this tree, not an older one.

    `benchmark.check` rebuilds the receipt with `build_receipt()` and compares
    the whole structure, so the mutations below are not a list the gate knows
    about — they are the reasons a receipt can drift, each required to surface
    with the field named. The three marked (P1) passed the previous gate, which
    walked only the recorded rows and compared only `verdict`, `spend_total` and
    `result_hash`.
    """
    import benchmark
    import copy
    import json

    path = HERE / "benchmark.json"
    problems = benchmark.check(path)
    chk("the benchmark receipt is not stale", not problems, "; ".join(problems))

    saved = path.read_text()
    base = json.loads(saved)

    def mutated(label, mutate, expect):
        receipt = copy.deepcopy(base)
        mutate(receipt)
        try:
            path.write_text(json.dumps(receipt, indent=2))
            found = benchmark.check(path)
        finally:
            path.write_text(saved)
        chk(label, any(expect in problem for problem in found), str(found))

    mutated("R-M1. a stale oracle digest is caught, by name",
            lambda r: r["measurement_inputs"].__setitem__(
                "impl/sigma_glyph.py", "0" * 64),
            "impl/sigma_glyph.py")
    mutated("R-M2. a DELETED measurement row is caught (P1: invisible to a "
            "walk over recorded rows)",
            lambda r: r["measurements"].pop(0),
            "measurements: recorded 8 entries")
    mutated("R-M3. an ADDED unknown row is caught",
            lambda r: r["measurements"].append({"case": "church(999)"}),
            "measurements: recorded 10 entries")
    mutated("R-M4. `exit` changed with `result_hash` untouched is caught "
            "(P1: the receipt gap this ADR is about)",
            lambda r: r["measurements"][0]["lhs"].__setitem__(
                "exit", "atp_exhausted"),
            "measurements[0].lhs.exit")
    mutated("R-M5. per-side spends moved with `spend_total` preserved is "
            "caught (P1)",
            lambda r: (
                r["measurements"][0]["lhs"].__setitem__(
                    "atp_spent", r["measurements"][0]["lhs"]["atp_spent"] + 1),
                r["measurements"][0]["rhs"].__setitem__(
                    "atp_spent", r["measurements"][0]["rhs"]["atp_spent"] - 1)),
            "measurements[0].lhs.atp_spent")
    mutated("R-M6. a changed observation root is caught",
            lambda r: r["measurements"][0]["lhs"].__setitem__("root", "0" * 64),
            "measurements[0].lhs.root")
    mutated("R-M7. a weakened `profile_cannot_settle` is caught, not merely "
            "found truthy",
            lambda r: r.__setitem__("profile_cannot_settle", "n/a"),
            "profile_cannot_settle")
    mutated("R-M8. a changed budget is caught",
            lambda r: r.__setitem__("budget_each_side", 1),
            "budget_each_side")
    mutated("R-M9. a changed Book I edition is caught",
            lambda r: r.__setitem__("book_1_edition", "0.9.9"),
            "book_1_edition")

    chk("R-M10. and the baseline is restored", not benchmark.check(path))


def digest_problems():
    """Reason-specific problems with the digests the ADR prints.

    Returns a list of strings, empty when the document is honest. Split out of
    the control so the mutations below can exercise the SAME code with the
    production route disturbed, rather than a copy of it.
    """
    import re
    import subprocess

    adr = (HERE.parents[0] / "ADR-011-eq-by-normal-form-address.md").read_text()
    problems = []

    for label, preimage, produced in (
            ("F", b"sigma-glyph/adr-011/church@v0/F", ep.MARKER_F.hex()),
            ("X", b"sigma-glyph/adr-011/church@v0/X", ep.MARKER_X.hex())):
        independent = _independent_node_hash_of_literal(preimage)
        if independent != produced:
            problems.append(
                f"marker {label}: independent computation == production "
                f"constant FAILED ({independent} vs {produced})")
        elif independent not in adr:
            problems.append(f"marker {label}: the ADR does not print {independent}")

    # The preserved original. A shallow checkout does not have this commit, and
    # the first CI run of this selftest died on the raw CalledProcessError. It
    # must not be skipped when unreachable — the point of the check is that the
    # ADR's stated digest of the original IS the git object's digest, and an
    # unverifiable claim is the failure, not an exemption. So it reports a
    # problem that names the remedy.
    ORIGINAL = "3f58ab6ed2eb26d48e2323dc09d50a3c4d86bf6e"
    fetched = subprocess.run(
        ["git", "-C", str(HERE.parents[1]), "show",
         f"{ORIGINAL}:proposals/ADR-011-eq-by-normal-form-address.md"],
        capture_output=True)
    if fetched.returncode != 0:
        problems.append(
            f"cannot reach the preserved original {ORIGINAL[:7]}, so the ADR's "
            f"digest of it is unverified here — a shallow clone needs "
            f"`git fetch --depth=1 origin {ORIGINAL}` first "
            f"({fetched.stderr.decode().strip().splitlines()[-1:] or ['']}[0])")
        return problems
    blob = fetched.stdout
    import hashlib
    original = hashlib.sha256(blob).hexdigest()
    if original not in adr:
        problems.append("the ADR's digest of the original is not the git "
                        f"object's digest ({original})")

    env = ep.fresh_env()
    y_atom = sg.sha(b"sigma-glyph/adr-011/church@v0/Y-probe")

    def observe_at(term, x_atom):
        return ep._materialize(env, ("app", ("app", sg.c1(term),
                                             ("lit", ep.MARKER_F_ATOM)),
                                     ("lit", x_atom)))

    zero = ep.church(0)
    marker_term = ("lam", "f", ("lam", "x", ("lit", ep.MARKER_X_ATOM)))
    accounted = {
        _independent_node_hash_of_literal(b"sigma-glyph/adr-011/church@v0/F"),
        _independent_node_hash_of_literal(b"sigma-glyph/adr-011/church@v0/X"),
        original,
        sg.eval_receipt(observe_at(zero, ep.MARKER_X_ATOM), 5000, env).result_hash.hex(),
        sg.eval_receipt(observe_at(zero, y_atom), 5000, env).result_hash.hex(),
        sg.eval_receipt(observe_at(marker_term, y_atom), 5000, env).result_hash.hex(),
        sg.term_hash(("dis", sg.R_ATP)).hex(),
        _book1_anchor(),
    }
    printed = set(re.findall(r"\b[0-9a-f]{16,64}\b", adr))
    unaccounted = {p for p in printed
                   if not any(full.startswith(p) for full in accounted)}
    if unaccounted:
        problems.append(f"digests the ADR prints that nothing here produces: "
                        f"{sorted(unaccounted)}")
    return problems


def adr_prints_real_values():
    """Every digest the ADR prints must be one an INDEPENDENT route produces.

    Written because I twice put placeholder digests into prose in this session:
    an invented middle for a Pantheon hash in a Go test, and invented marker
    NodeHashes here. Both were caught, once by a test and once by a print —
    "caught by luck" is not a control.
    """
    problems = digest_problems()
    chk("every digest the ADR prints survives an independent recomputation",
        not problems, "; ".join(problems))

    # And the independent route must be able to fail. Both mutations disturb the
    # PRODUCTION side only; the local hashlib computation is untouched, so a
    # control that merely asked the module for a constant and found it in the
    # prose would stay green through both.
    saved_atom, saved_node = ep.MARKER_F_ATOM, ep.MARKER_F
    try:
        ep.MARKER_F_ATOM = sg.sha(b"sigma-glyph/adr-011/church@v0/F-moved")
        ep.MARKER_F = sg.node_hash(sg.ser(sg.LITERAL, sg.F_ATOM,
                                          atom=ep.MARKER_F_ATOM))
        moved = digest_problems()
        chk("D-M1. a changed production preimage fails the independent check",
            any("independent computation == production constant FAILED" in p
                and p.startswith("marker F") for p in moved), str(moved))
    finally:
        ep.MARKER_F_ATOM, ep.MARKER_F = saved_atom, saved_node

    try:
        # Same atom, wrong node layout: DISSONANCE where Book I says LITERAL.
        ep.MARKER_F = sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM,
                                          atom=ep.MARKER_F_ATOM))
        relaid = digest_problems()
        chk("D-M2. a changed production serialization fails it too",
            any("independent computation == production constant FAILED" in p
                and p.startswith("marker F") for p in relaid), str(relaid))
    finally:
        ep.MARKER_F = saved_node

    chk("D-M3. and the baseline is restored", not digest_problems())


def _book1_anchor() -> str:
    import hashlib
    data = (HERE.parents[1] / "spec/book-1-truth.md").read_bytes()
    return hashlib.sha256(bytes([0, 1]) + hashlib.sha256(data).digest()).hexdigest()


def mutation_evidence():
    """Restore each defect and require ITS control, for ITS reason, to go red.

    These are the defects the candidate ADR's own pseudocode had. Each is
    re-created here as a small alternative settlement function rather than by
    editing the module, so the evidence is reproducible without a patched tree.
    """
    print()
    print("  -- mutations M1-M5 and M7 restore a defect and must be caught;")
    print("     M6 is a positive refusal check, not a mutation --")

    def address_only(a, b, atp):
        """No exit check: compare result hashes, as the candidate did."""
        env = ep.fresh_env()
        left = sg.eval_receipt(ep._observe_church(a, env), atp, env)
        right = sg.eval_receipt(ep._observe_church(b, env), atp, env)
        return left.result_hash == right.result_hash

    chk("M1. without the exit check, two exhausted runs compare EQUAL",
        address_only(ep.church(3), ep.church(5), 30) is True,
        "the defect no longer reproduces, so control 7b tests nothing")
    chk("M1b. and the profile's settlement refuses that verdict",
        settle(ep.church(3), ep.church(5), ba=30, bb=30).verdict == ep.UNSETTLED)

    def sequential_budget(a, b, atp):
        """Second side gets `atp - spent_left`, as the candidate pseudocode did."""
        env = ep.fresh_env()
        left = sg.eval_receipt(ep._observe_church(a, env), atp, env)
        right = sg.eval_receipt(ep._observe_church(b, env),
                                atp - left.atp_spent, env)
        return left.result_hash == right.result_hash

    chk("M2. with a sequential budget, church(12) is UNEQUAL to itself",
        sequential_budget(ep.church(12), ep.church(12), 600) is False,
        "the defect no longer reproduces")
    chk("M2b. and with independent budgets it is EQUAL",
        settle(ep.church(12), ep.church(12), ba=600, bb=600).verdict == ep.EQUAL)
    chk("M2c. with a sequential budget the verdict flips with argument order",
        sequential_budget(ep.church(0), ep.church(12), 200)
        != sequential_budget(ep.church(12), ep.church(0), 200))

    def no_marker_admission(a, b, atp=5000):
        """Admission that does not refuse terms naming a marker."""
        env = ep.fresh_env()
        left = sg.eval_receipt(ep._observe_church(a, env), atp, env)
        right = sg.eval_receipt(ep._observe_church(b, env), atp, env)
        return (left.exit == right.exit == "normal_form"
                and left.result_hash == right.result_hash)

    marker_term = ("lam", "f", ("lam", "x", ("lit", ep.MARKER_X_ATOM)))
    chk("M3. without marker admission, λf.λx.X settles EQUAL to church(0)",
        no_marker_admission(ep.church(0), marker_term) is True,
        "the collision no longer reproduces, so control 3 tests nothing")
    chk("M3b. and the profile refuses the term instead",
        settle(ep.church(0), marker_term).verdict == ep.REFUSED)

    def shared_admit(a, b):
        """Both admissions in ONE try, as an earlier version had them."""
        try:
            ep.CHURCH_V0.admit(a)
            ep.CHURCH_V0.admit(b)
        except ep.Refused as why:
            return ep.Settlement(
                verdict=ep.REFUSED, profile_id=ep.CHURCH_V0.profile_id,
                profile_commitment=ep.profile_commitment(ep.CHURCH_V0),
                book_anchor=ep.CHURCH_V0.book_anchor,
                book_context=ep.CHURCH_V0.book_context, lhs=None, rhs=None,
                detail=str(why), lhs_status=ep.REFUSED, rhs_status=ep.REFUSED)
        return settle(a, b)

    shared = shared_admit(ep.church(3), marker_term)
    chk("M5. a shared admission marks BOTH sides refused when one term is bad",
        shared.lhs_status == shared.rhs_status == ep.REFUSED
        and shared.lhs is None,
        "the defect no longer reproduces, so controls 3c/3d test nothing")
    per_side = settle(ep.church(3), marker_term)
    chk("M5b. and the per-side admission does not",
        per_side.lhs_status == "ok" and per_side.rhs_status == ep.REFUSED
        and per_side.lhs is not None)

    chk("M6. a computed expression is refused, not silently admitted",
        ep.settle_eq(ep.CHURCH_V0,
                     ("lapp", ("lapp", ep.church(2), ep.church(3)), ep.church(1)),
                     ep.church(6), 50_000, 50_000,
                     ep.fresh_env()).verdict == ep.REFUSED)

    # M4. Remove the binder-distinctness guard and require control 12 to be the
    #     control that goes red. Restores the over-acceptance Codex found.
    saved_is_church = ep._is_church_literal

    def name_blind(term) -> bool:
        """The guard as it was: binders compared by name, shadowing invisible."""
        if term[0] != "lam":
            return False
        f_name, inner = term[1], term[2]
        if inner[0] != "lam":
            return False
        x_name, body = inner[1], inner[2]
        while body[0] == "lapp":
            if body[1] != ("var", f_name):
                return False
            body = body[2]
        return body == ("var", x_name)

    shadowed = ("lam", "f", ("lam", "f", ("lapp", ("var", "f"), ("var", "f"))))
    try:
        ep._is_church_literal = name_blind
        admitted = True
        try:
            ep.CHURCH_V0.admit(shadowed)
        except ep.Refused:
            admitted = False
        chk("M4. without the binder-distinctness guard, `λf.λf.f(f)` is "
            "ADMITTED — control 12 is what catches it", admitted)
    finally:
        ep._is_church_literal = saved_is_church
    still_refused = False
    try:
        ep.CHURCH_V0.admit(shadowed)
    except ep.Refused:
        still_refused = True
    chk("M4b. and with the guard restored it is refused again", still_refused)

    # M7. Make the commitment blind to the observer and require control 13b —
    #     not 13 — to be the one that fails.
    saved_code_digest = ep._code_digest
    try:
        ep._code_digest = lambda fn: "0" * 64
        forged = ep.EqualityProfile(**{
            **ep.CHURCH_V0.__dict__,
            "observe": lambda term, env: ep._materialize(
                env, ("lit", ep.MARKER_X_ATOM))})
        collides = (ep.profile_commitment(forged)
                    == ep.profile_commitment(ep.CHURCH_V0))
        chk("M7. a commitment that does not cover `observe` lets a forged "
            "profile share the real one's commitment", collides)
    finally:
        ep._code_digest = saved_code_digest
    # M8. Move the commitment back to where it was — computed while building
    #     the Settlement, after admission and both observations. Control 15b is
    #     what must go red: the refusal still happens, so 15 stays green.
    watched, calls = _unreadable_observer_profile()

    def late_commitment(profile, a, b, ba, bb, env):
        """settle_eq as it was: execute first, commit at the end."""
        sides = (("lhs", a, ba), ("rhs", b, bb))
        problems = [ep._admit(profile, term) for _n, term, _b in sides]
        roots = []
        for index, (_n, term, budget) in enumerate(sides):
            if problems[index] is not None:
                roots.append(None)
                continue
            root, problem = ep._prepare(profile, term, budget, env)
            roots.append(root)
            problems[index] = problem
        # ...and only here does it ask which profile it just ran.
        return ep.profile_commitment(profile)

    ran_anyway = False
    try:
        late_commitment(watched, ep.church(3), ep.church(5), 5000, 5000,
                        ep.fresh_env())
    except ep.Refused:
        ran_anyway = True
    chk("M8. with the commitment computed last, the observer runs BEFORE the "
        "refusal — control 15b is what catches it",
        ran_anyway and len(calls) == 2,
        f"refused={ran_anyway}, observer ran {len(calls)} time(s)")

    watched2, calls2 = _unreadable_observer_profile()
    ep.settle_eq(watched2, ep.church(3), ep.church(5), 5000, 5000,
                 ep.fresh_env())
    chk("M8b. and with the preflight it runs 0 times", calls2 == [])

    # M9. Restore the ADMISSION PATH as it was, and require `P.admit` itself
    #     to accept the malformed term.
    #
    #     The first version of this mutation patched only `_is_node`, which
    #     made `_is_church_literal` permissive while `_is_well_formed` — added
    #     in the same fix and NOT mutated — still refused at admission. So the
    #     mutation showed a permissive helper next to a guard that still held,
    #     and the claim "control 16 catches it" was never exercised. A mutation
    #     that leaves any part of the guard standing tests the part it left.
    saved_is_node = ep._is_node
    saved_well_formed = ep._is_well_formed
    trailing = ("lam", "f", ("lam", "x", ("var", "x")), "EXTRA")
    try:
        ep._is_node = lambda term, head: (isinstance(term, tuple)
                                          and len(term) > 1
                                          and term[0] == head)
        ep._is_well_formed = lambda term: True
        admitted_m9 = True
        try:
            ep.CHURCH_V0.admit(trailing)
        except ep.Refused:
            admitted_m9 = False
        chk("M9. with the old admission path, `admit` ACCEPTS a term with a "
            "trailing field — control 16 is what catches it", admitted_m9)
    finally:
        ep._is_node = saved_is_node
        ep._is_well_formed = saved_well_formed
    refused_m9 = False
    try:
        ep.CHURCH_V0.admit(trailing)
    except ep.Refused:
        refused_m9 = True
    chk("M9b. and with the guard restored `admit` refuses it", refused_m9)

    # M10. Weaken the anchor preflight back to a shape check, and require 13e
    #      — the control that demands a refusal — to be what goes red.
    saved_book_anchor_fn = ep._book_1_anchor
    flipped_local = ("f" if ep.CHURCH_V0.book_anchor[0] != "f" else "0") \
        + ep.CHURCH_V0.book_anchor[1:]
    watched_m10, calls_m10 = _watched_observer_profile(book_anchor=flipped_local)
    try:
        # Shape-only, as it was: any 64 hex string satisfies the preflight.
        ep._book_1_anchor = lambda: flipped_local
        settled_m10 = ep.settle_eq(watched_m10, ep.church(3), ep.church(3),
                                   5000, 5000, ep.fresh_env())
        chk("M10. with a shape-only anchor preflight, a foreign anchor settles "
            "EQUAL with two receipts — control 13e is what catches it",
            settled_m10.verdict == ep.EQUAL
            and settled_m10.lhs is not None and settled_m10.rhs is not None
            and len(calls_m10) == 2,
            f"{settled_m10.verdict}, observer ran {len(calls_m10)} time(s)")
    finally:
        ep._book_1_anchor = saved_book_anchor_fn
    watched_m10b, calls_m10b = _watched_observer_profile(
        book_anchor=flipped_local)
    settled_m10b = ep.settle_eq(watched_m10b, ep.church(3), ep.church(3),
                                5000, 5000, ep.fresh_env())
    chk("M10b. and with the binding restored it is refused, observer unrun",
        settled_m10b.verdict == ep.REFUSED and calls_m10b == [])

    chk("M7b. and with the real digest they differ again",
        ep.profile_commitment(ep.EqualityProfile(**{
            **ep.CHURCH_V0.__dict__,
            "observe": lambda term, env: ep._materialize(
                env, ("lit", ep.MARKER_X_ATOM))}))
        != ep.profile_commitment(ep.CHURCH_V0))


if __name__ == "__main__":
    raise SystemExit(main())
