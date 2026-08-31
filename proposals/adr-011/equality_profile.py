#!/usr/bin/env python3
"""Receipted equality of admitted canonical data by normal-form address.

NON-NORMATIVE reference profile for ADR-011. Nothing here is anchored, nothing
here is a Book, and adopting the ADR would not adopt this file.

    An address settles equality only after an admitted profile has made the
    observation canonical.

The unconditional part is small and worth stating alone:

    Two evaluations that both exit `normal_form` with the same `result_hash`
    returned one canonically addressed result — modulo SHA-256 and the
    correctness of the implementations.

That says nothing about the terms that were evaluated. Carrying the conclusion
back to the inputs needs a PROFILE whose observation is proved, on its admitted
domain, to both reflect and preserve the equivalence being claimed. The two
directions are separate properties and neither is unconditional:

    reflection    same_address(observe(a), observe(b))  =>  a ~ b
    preservation  a ~ b  =>  same_address(observe(a), observe(b))

Why the distinction is not pedantry, on this evaluator, today:

    a = λf.λx.x        b = λf.λx.X          (X is the profile's own marker)
    Y = the literal sha("sigma-glyph/adr-011/church@v0/Y-probe"), a second
        observation point that is NOT a marker of this profile

    observe at (F, X): both -> e37391c4…   spends 12 and 15
    observe at (F, Y): a -> 2b0e3697…, b -> e37391c4…

(These are this profile's domain-separated markers. An earlier draft of this
docstring printed 8785b7dd…/8ee7e3ec…, which are genuine digests of the ad-hoc
`sha("F")/sha("X")` markers used by the CANDIDATE ADR — real numbers from the
wrong marker set, which is the exact defect MANIFESTO-CORRECTIONS.md raises as
C5 against AIE-0.1. Checked by `digest_problems()` in the selftest.)

One observation point cannot separate them. Reflection is a property of a
domain and a marker discipline, not of addressing.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "impl"))
import sigma_glyph as sg  # noqa: E402

EQUAL, UNEQUAL, UNSETTLED, REFUSED, FAULT = (
    "EQUAL", "UNEQUAL", "UNSETTLED", "REFUSED", "FAULT")

# Everything the oracle can raise instead of returning a Receipt. Catching only
# ResourceFault let an out-of-domain budget, a budget above a local `max_atp`
# and a malformed root escape as bare exceptions, past the REFUSED/FAULT surface
# this profile documents.


class Refused(Exception):
    """Admission declined. Not a Book I exit, not a DISSONANCE (Book I §3.6)."""


@dataclass(frozen=True)
class EqualityProfile:
    """What must be fixed BEFORE an address can settle anything."""

    profile_id: str
    admitted_domain: str          # prose: what may be submitted, and by what check
    equivalence_relation: str     # prose: which `~` is being claimed
    observe: Callable             # term -> observation term
    admit: Callable               # term -> None, or raise Refused
    marker_definition: dict       # exact bytes and NodeHashes; why they are safe
    budget_policy: str
    environment_policy: str
    book_anchor: str              # EXACTLY 64 hex: the Book I anchor itself
    book_context: str             # prose: which edition, adopted how, by what
    reflection: str               # the claim, domain-qualified, with its argument
    preservation: str
    not_established: tuple = field(default=())


@dataclass(frozen=True)
class SideReceipt:
    """One side's Book I Receipt, plus what Book I does not price."""

    root: str
    exit: str
    result_hash: str | None
    atp_spent: int


@dataclass(frozen=True)
class Settlement:
    verdict: str
    profile_id: str            # what the profile CALLS itself — not an identity
    profile_commitment: str | None  # what the profile IS; None only when the
                                    # profile could not be committed to, in
                                    # which case nothing was executed
    book_anchor: str           # EXACTLY 64 hex. This field held the prose
                               # "Book I document version 0.6.0, anchor
                               # e3e5d008…, adopted …", which is not an anchor
                               # and cannot be compared to one; the control
                               # over it only checked the string was non-empty
                               # and copied from the profile, so it was green
                               # on a value no verifier could use.
    book_context: str          # the prose, kept, where prose belongs
    lhs: SideReceipt | None
    rhs: SideReceipt | None
    detail: str = ""
    lhs_status: str = "ok"
    rhs_status: str = "ok"

    @property
    def spend_total(self) -> int | None:
        """The two spends added up.

        NOT a Book I Receipt. Book I prices one evaluation; this is arithmetic
        over two, and it prices neither the construction and materialization of
        the observation terms nor the CAS I/O that serves them.
        """
        if self.lhs is None or self.rhs is None:
            return None
        return self.lhs.atp_spent + self.rhs.atp_spent


# A fault outranks a refusal, so aggregating the two sides is a max over a fixed
# order and cannot depend on which side is examined first. The candidate returned
# whichever problem it met first walking lhs then rhs, so (REFUSED, FAULT) and
# (FAULT, REFUSED) gave different overall kinds for the same pair of facts.
_SEVERITY = {"ok": 0, REFUSED: 1, FAULT: 2}


def _book_1_anchor() -> str:
    """The Book I anchor, computed from the Book's bytes.

    A LITERAL node over the document: `NodeHash = SHA-256(0x00 0x01 ‖ atom)`
    where `atom = SHA-256(bytes)`. Written out here rather than imported so the
    profile does not depend on the benchmark, and recomputed independently again
    in the selftest so neither route is the other's oracle.
    """
    import hashlib
    book = Path(__file__).resolve().parents[2] / "spec/book-1-truth.md"
    atom = hashlib.sha256(book.read_bytes()).digest()
    return hashlib.sha256(bytes([0x00, 0x01]) + atom).hexdigest()


_HEX64 = frozenset("0123456789abcdef")


def _valid_anchor(value) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and set(value) <= _HEX64)


def settle_eq(profile: EqualityProfile, a, b, budget_a: int, budget_b: int,
              env) -> Settlement:
    """Settle `a ~ b` under `profile`, with a status and a receipt per side.

    **Every phase is per-side.** Admission, observation and evaluation each
    attach their problem to the side that caused it, and the other side runs
    anyway. Two earlier versions failed this: one wrapped both evaluations in a
    single `try`, discarding a completed side whenever the other declined; the
    next wrapped both ADMISSIONS in a single `try`, so refusing one term marked
    both sides `REFUSED` while the report claimed each side's status was kept.

    **Order independence.** Side problems aggregate by severity rather than by
    position, and both observations are materialized before either evaluation
    runs — otherwise the left side would evaluate against a smaller environment
    than the right, and under Book I §3.5 an extension can turn an
    `unresolved_reference` into a settled exit.

    That is as far as the framework goes. The two `observe()` calls still mutate
    one environment in sequence, so an observer that READ what the first one
    wrote could build a different root. **`church@v0` is order-independent
    because its observer depends only on the term and only adds a CAS-valid
    closure; `EqualityProfile.observe: Callable` guarantees nothing of the
    kind.** A pure, monotone observation is an obligation of each profile, not a
    property of this module — stated in `environment_policy`.

    It is not independent of swapping the terms while leaving the budgets in
    place: with `budget_a != budget_b` that is a different question.

    The candidate ADR gave the second side `atp - spent_left`, which is a
    different protocol with observably different answers — including
    `church(12)` reported UNEQUAL to itself at atp=600, and a verdict that flips
    with argument order at atp=100, 200 and 300.
    """
    # Phase 0: COMMIT TO THE PROFILE BEFORE EXECUTING IT.
    #
    # This ran last, while the Settlement was being built. A profile whose
    # source became unreadable between import and settlement therefore had its
    # admission run, both observers run, and the store mutated — and only then
    # raised, so the system executed a profile and afterwards discovered it
    # could not say which profile it had executed. Anything the observers wrote
    # was already there.
    #
    # It is computed once, here, and reused; recomputing it after execution
    # would also let a profile mutated mid-settlement report the wrong one.
    try:
        commitment = profile_commitment(profile)
    except Refused as refusal:
        return Settlement(verdict=REFUSED, profile_id=profile.profile_id,
                          profile_commitment=None,
                          book_anchor=profile.book_anchor,
                          book_context=profile.book_context, lhs=None, rhs=None,
                          detail=f"profile: {refusal}",
                          lhs_status=REFUSED, rhs_status=REFUSED)
    # The anchor must be the anchor of the Book this function actually runs.
    #
    # Checking only the SHAPE let a valid-but-foreign anchor through: a
    # one-digit mutation is still 64 hex, so a settlement claiming to be read
    # against some other Book I proceeded to EQUAL with two receipts, produced
    # by the local oracle the whole time. The claim and the execution were
    # unrelated, and nothing said so.
    #
    # `settle_eq` has no way to run a Book it is not linked against, so the only
    # honest options are to refuse or to take an engine bound to the claimed
    # anchor. This module refuses; injecting such an engine is not in scope here.
    local = _book_1_anchor()
    if not _valid_anchor(profile.book_anchor):
        return Settlement(verdict=REFUSED, profile_id=profile.profile_id,
                          profile_commitment=commitment,
                          book_anchor=profile.book_anchor,
                          book_context=profile.book_context, lhs=None, rhs=None,
                          detail="profile: book_anchor is not 64 hex "
                                 "characters, so a settlement could not say "
                                 "which Book I bytes it was read against",
                          lhs_status=REFUSED, rhs_status=REFUSED)
    if profile.book_anchor != local:
        return Settlement(verdict=REFUSED, profile_id=profile.profile_id,
                          profile_commitment=commitment,
                          book_anchor=profile.book_anchor,
                          book_context=profile.book_context, lhs=None, rhs=None,
                          detail=f"profile: book_anchor {profile.book_anchor} "
                                 f"is not the Book I this evaluator executes "
                                 f"({local}); refusing rather than settling "
                                 f"under one Book while claiming another",
                          lhs_status=REFUSED, rhs_status=REFUSED)

    sides = (("lhs", a, budget_a), ("rhs", b, budget_b))

    # Phase 1, per side: admission.
    problems = [_admit(profile, term) for _name, term, _budget in sides]

    # Phase 2, per side: observation. Both roots are built before any evaluation.
    roots = []
    for index, (_name, term, budget) in enumerate(sides):
        if problems[index] is not None:
            roots.append(None)
            continue
        root, problem = _prepare(profile, term, budget, env)
        roots.append(root)
        problems[index] = problem

    # Phase 3, per side: evaluation, against one prepared environment.
    receipts = []
    for index, (_name, _term, budget) in enumerate(sides):
        if problems[index] is not None:
            receipts.append(None)
            continue
        receipt, problem = _evaluate(roots[index], budget, env)
        receipts.append(receipt)
        problems[index] = problem

    left, right = receipts
    if any(problem is not None for problem in problems):
        kinds = [problem[0] if problem else "ok" for problem in problems]
        verdict = max(kinds, key=lambda kind: _SEVERITY[kind])
        detail = "; ".join(
            f"{name}: {problem[1]}" if problem else f"{name}: completed"
            for (name, _t, _b), problem in zip(sides, problems))
        return Settlement(verdict=verdict, profile_id=profile.profile_id,
                          profile_commitment=commitment,
                          book_anchor=profile.book_anchor,
                          book_context=profile.book_context,
                          lhs=left, rhs=right, detail=detail,
                          lhs_status=kinds[0], rhs_status=kinds[1])

    if left.exit != "normal_form" or right.exit != "normal_form":
        unfinished = [name for name, side in (("lhs", left), ("rhs", right))
                      if side.exit != "normal_form"]
        return Settlement(
            verdict=UNSETTLED, profile_id=profile.profile_id,
            profile_commitment=commitment, book_anchor=profile.book_anchor,
            book_context=profile.book_context, lhs=left, rhs=right,
            detail=f"did not reach a normal form: {', '.join(unfinished)}")

    verdict = EQUAL if left.result_hash == right.result_hash else UNEQUAL
    # Keyword arguments at every construction site. The positional form broke
    # twice while fields were being added, each time silently shifting a
    # receipt into a status slot in a MUTATION — the place least likely to be
    # read as wrong, because a mutation is expected to misbehave.
    return Settlement(verdict=verdict, profile_id=profile.profile_id,
                      profile_commitment=commitment,
                      book_anchor=profile.book_anchor,
                      book_context=profile.book_context, lhs=left, rhs=right)


def _admit(profile: EqualityProfile, term):
    """(None) if admitted, else (kind, why) for THIS side only."""
    try:
        profile.admit(term)
    except Refused as refusal:
        return (REFUSED, f"not admitted: {refusal}")
    except Exception as defect:                                   # noqa: BLE001
        return (FAULT, f"the profile's admit raised "
                       f"{type(defect).__name__}: {defect}")
    return None


def _prepare(profile: EqualityProfile, term, budget, env):
    """(root, None) or (None, (kind, why)). Boundaries kept apart.

    A blanket `except ValueError -> REFUSED` reported a bug in the profile's own
    observer as a well-formed refusal of the caller's input. These are different
    facts and they get different verdicts:

      * a budget outside `uint32`            -> REFUSED (the caller's input)
      * the observer refusing the term       -> REFUSED (the caller's input)
      * the observer raising anything else   -> FAULT   (the profile's defect)
      * a root that is not 32 bytes          -> FAULT   (the profile's defect)
    """
    if isinstance(budget, bool) or not isinstance(budget, int) \
            or not 0 <= budget <= 0xFFFFFFFF:
        return None, (REFUSED, f"budget {budget!r} is not a uint32")
    try:
        root = profile.observe(term, env)
    except Refused as refusal:
        return None, (REFUSED, f"the profile declined the term: {refusal}")
    except Exception as defect:                                   # noqa: BLE001
        return None, (FAULT, f"the profile's observer raised "
                             f"{type(defect).__name__}: {defect}")
    if not isinstance(root, (bytes, bytearray)) or len(root) != 32:
        return None, (FAULT, "the profile's observer produced a root that is "
                             "not a 32-byte NodeHash")
    return bytes(root), None


def _evaluate(root, budget, env):
    """(SideReceipt, None) or (None, (kind, why))."""
    try:
        receipt = sg.eval_receipt(root, budget, env)
    except sg.ResourceFault as fault:
        return None, (FAULT, f"local resource fault: {fault}")
    except sg.AdmissionRefused as refusal:
        return None, (REFUSED, f"the verifier declined to run it: {refusal}")
    except ValueError as unexpected:
        # The budget and the root were validated above, so this is not the
        # caller's input failing.
        return None, (FAULT, f"unexpected {type(unexpected).__name__} from the "
                             f"oracle after inputs were validated: {unexpected}")
    return SideReceipt(root=root.hex(), exit=receipt.exit,
                       result_hash=receipt.result_hash.hex(),
                       atp_spent=receipt.atp_spent), None


# --------------------------------------------------------------------------
# One profile. Narrow on purpose.
# --------------------------------------------------------------------------

MARKER_F_ATOM = sg.sha(b"sigma-glyph/adr-011/church@v0/F")
MARKER_X_ATOM = sg.sha(b"sigma-glyph/adr-011/church@v0/X")
MARKER_F_BYTES = sg.ser(sg.LITERAL, sg.F_ATOM, atom=MARKER_F_ATOM)
MARKER_X_BYTES = sg.ser(sg.LITERAL, sg.F_ATOM, atom=MARKER_X_ATOM)
MARKER_F = sg.node_hash(MARKER_F_BYTES)
MARKER_X = sg.node_hash(MARKER_X_BYTES)
assert MARKER_F != MARKER_X


def _materialize(env, term):
    """Put a symbolic term into the CAS and return its NodeHash."""
    if term[0] == "lit":
        env.put(sg.ser(sg.LITERAL, sg.F_ATOM, atom=term[1]))
        return sg.term_hash(term)
    if term[0] == "app":
        left, right = _materialize(env, term[1]), _materialize(env, term[2])
        env.put(sg.ser(sg.APPLY, sg.F_LEFT | sg.F_RIGHT, left=left, right=right))
        return sg.node_hash(sg.ser(sg.APPLY, sg.F_LEFT | sg.F_RIGHT,
                                   left=left, right=right))
    raise Refused(f"not a materializable term: {term!r}")


def _code_digest(fn) -> str:
    """A digest of the callable itself, not of the name it was given.

    SOURCE TEXT, not bytecode. The first version digested `co_code`, and CI
    caught it immediately: the same profile committed to
    98d3432c… on CPython 3.14 and f2592195… on 3.12, because bytecode is not
    stable across interpreter versions. A commitment that changes when nothing
    about the profile changed is not a commitment — it cannot tell "a different
    profile" from "a different Python".

    Two components, and both are needed. The callable's own source separates
    two different lambdas defined in one file; the module's source separates
    two files AND catches edits to the helpers a callable delegates to, which
    its own source text does not show.
    """
    import hashlib
    import inspect
    module_file = getattr(sys.modules.get(getattr(fn, "__module__", None)),
                          "__file__", None)
    try:
        module_source = Path(module_file).read_bytes() if module_file else None
        own_source = inspect.getsource(fn).encode()
    except (OSError, TypeError):
        module_source = own_source = None
    if module_source is None or own_source is None:
        # Fail closed. Degrading to a partial digest would still return a hex
        # string, and every caller would keep treating it as a commitment while
        # it had stopped covering what it claims to cover. A callable defined at
        # a REPL cannot be committed to; say so.
        raise Refused(
            f"cannot commit to {getattr(fn, '__qualname__', fn)!r}: its source "
            f"is not readable, so a commitment could not cover either the "
            f"callable or the helpers it calls")
    digest = hashlib.sha256(b"sigma-glyph/adr-011/code-digest@v0")
    for part in (getattr(fn, "__qualname__", "").encode(), own_source,
                 module_source):
        digest.update(b"\x00" + hashlib.sha256(part).digest())
    return digest.hexdigest()


def profile_commitment(profile: "EqualityProfile") -> str:
    """What the settlement is actually under — beyond the chosen `profile_id`.

    `profile_id` is a string the profile picks for itself. Two profiles can
    carry the same one and behave differently: an observer that returns the
    marker `X` for every term makes `church(5)` and `church(7)` settle EQUAL,
    and the settlement still says `sigma-glyph/adr-011/church@v0`. A receipt
    that names a profile without identifying it is a receipt under an unknown
    profile.

    So the commitment covers every field that changes what a settlement means:
    the prose contract, the markers, the Book I edition, and digests of `observe`
    and `admit` themselves.

    **PORTABLE SETTLEMENT IS BLOCKED, and this function does not unblock it.**
    This digest identifies a profile to *another run of this Python module* —
    on CPython 3.12 and 3.14, the two versions it is verified
    on. It commits to source text rather than bytecode, but
    `inspect.getsource` and `repr` carry no cross-version
    canonicality contract that this ADR establishes, so the
    claim is those two versions and no more. It is not a content-addressed
    profile descriptor: a Go or Rust implementation of the same profile
    computes a different commitment, because it commits to this file's bytes. Comparing settlements across
    implementations needs a descriptor that is itself canonical bytes in the
    store, with the admission and observation expressed in something both
    implementations execute. No such descriptor exists in Book I today and this
    ADR does not propose one. Until it does, a settlement is portable evidence
    only alongside the module that produced it.
    """
    import hashlib
    digest = hashlib.sha256(b"sigma-glyph/adr-011/profile-commitment@v0")
    for name in ("profile_id", "admitted_domain", "equivalence_relation",
                 "budget_policy", "environment_policy", "book_anchor",
                 "reflection", "preservation"):
        digest.update(b"\x00" + repr(getattr(profile, name)).encode())
    digest.update(b"\x00" + repr(sorted(profile.marker_definition.items())).encode())
    digest.update(b"\x00" + repr(profile.not_established).encode())
    for fn in (profile.observe, profile.admit):
        digest.update(b"\x00" + bytes.fromhex(_code_digest(fn)))
    return digest.hexdigest()


def _mentions_marker(term) -> bool:
    """Does this term contain either marker?

    The counterexample above is exactly a term that mentions a marker. Freshness
    here means: the markers are fixed by the profile id BEFORE any term is
    submitted, and a submitted term that names one is refused at admission.
    A profile that derived fresh markers per settlement instead would have to
    commit to the terms first; that ordering is the same requirement seen from
    the other side, and this profile takes the simpler branch.
    """
    if term[0] == "lit":
        return term[1] in (MARKER_F_ATOM, MARKER_X_ATOM)
    if term[0] in ("app", "lapp"):
        return _mentions_marker(term[1]) or _mentions_marker(term[2])
    if term[0] == "lam":
        return _mentions_marker(term[2])
    return False


# The grammar this profile reads, as arities. A term is a tuple whose head is
# one of these and whose length is EXACTLY the arity — no trailing fields.
_ARITY = {"var": 2, "lit": 2, "lam": 3, "lapp": 3, "app": 3}


def _is_node(term, head) -> bool:
    """`term` is exactly a `head` node: right tag, right length, tuple.

    The checks here indexed the positions they wanted and ignored everything
    else, so both of these were accepted as written-out numerals and settled
    EQUAL against `church(0)`:

        ("lam", "f", ("lam", "x", ("var", "x")), "EXTRA")
        ("lam", "f", ("lam", "x", ("var", "x"), "EXTRA"))

    Neither is a term of the grammar the profile declares it admits. Reading a
    tuple by index accepts every superset of the shape you asked for.
    """
    return (isinstance(term, tuple) and len(term) == _ARITY.get(head, -1)
            and term[0] == head)


def _is_binder_name(name) -> bool:
    """Binder names are strings. Stated, because `f_name == x_name` compares
    whatever is in the slot, and an unstated type makes that comparison mean
    whatever the caller put there."""
    return isinstance(name, str)


def _is_well_formed(term) -> bool:
    """Closed structural check over the whole term, exact arity everywhere."""
    if not isinstance(term, tuple) or not term:
        return False
    head = term[0]
    if head not in _ARITY or len(term) != _ARITY[head]:
        return False
    if head == "var":
        return _is_binder_name(term[1])
    if head == "lit":
        return isinstance(term[1], bytes) and len(term[1]) == 32
    if head == "lam":
        return _is_binder_name(term[1]) and _is_well_formed(term[2])
    return _is_well_formed(term[1]) and _is_well_formed(term[2])


def _is_church_literal(term) -> bool:
    """`λf.λx. f(f(...(x)))` written out. A SYNTACTIC check, deliberately.

    This is not an admission test for "Church-natural computations". It admits
    numerals as written and nothing else — not `PLUS 7 5`, not anything whose
    Church-ness is a fact about what it computes. **No mechanical admission of
    computed Church naturals exists here**, and substituting a syntactic
    heuristic for that semantic precondition is precisely the move this ADR was
    corrected for. A caller wanting `7+5` settled must either supply the numeral
    or extend the profile with an admission it can actually justify.
    """
    if not _is_node(term, "lam"):
        return False
    f_name, inner = term[1], term[2]
    if not _is_node(inner, "lam"):
        return False
    x_name, body = inner[1], inner[2]
    if not (_is_binder_name(f_name) and _is_binder_name(x_name)):
        return False
    if f_name == x_name:
        # `λf.λf.f(f)` walked the spine and matched, because both binders were
        # read by NAME. Under shadowing the inner binder wins, so the term
        # denotes `λa.λb.b(b)` — its observation agrees with no numeral. That is
        # over-acceptance OUTSIDE the domain reflection and preservation rest
        # on, which is the one direction this profile must not fail in.
        #
        # This also refuses terms that shadow and still denote a numeral, e.g.
        # `λx.λx.x`, which is church(0). Refusing an admissible term costs a
        # caller a settlement; admitting an inadmissible one costs the claim.
        return False
    while _is_node(body, "lapp"):
        if body[1] != ("var", f_name):
            return False
        body = body[2]
    return _is_node(body, "var") and body == ("var", x_name)


def _admit_church(term):
    if not _is_well_formed(term):
        raise Refused("not a term of this profile's grammar: every node must "
                      "be a tuple of exactly its arity (var/lit 2, "
                      "lam/lapp/app 3) with a string binder name")
    if _mentions_marker(term):
        raise Refused("the term names a profile marker; observation at that "
                      "point cannot distinguish it from a numeral")
    if not _is_church_literal(term):
        raise Refused("not a written-out Church numeral; this profile admits "
                      "no computed expressions (see _is_church_literal)")


def _observe_church(term, env):
    """O(n) = n F X, materialized into `env`."""
    return _materialize(env, ("app", ("app", sg.c1(term),
                                      ("lit", MARKER_F_ATOM)),
                              ("lit", MARKER_X_ATOM)))


CHURCH_V0 = EqualityProfile(
    profile_id="sigma-glyph/adr-011/church@v0",
    admitted_domain=(
        "Church numerals WRITTEN OUT as λf.λx.fⁿ(x), checked syntactically, "
        "with DISTINCT binders and containing neither marker. Computed "
        "expressions are NOT admitted: no mechanical admission of "
        "'Church-natural computations' exists here. The binder-distinctness "
        "requirement also refuses some terms that do denote numerals, such as "
        "λx.λx.x = church(0); refusing an admissible term costs a caller a "
        "settlement, admitting an inadmissible one costs the claim."),
    equivalence_relation="equality of the natural number a numeral denotes",
    observe=_observe_church,
    admit=_admit_church,
    marker_definition={
        "F_atom": MARKER_F_ATOM.hex(), "F_node": MARKER_F.hex(),
        "X_atom": MARKER_X_ATOM.hex(), "X_node": MARKER_X.hex(),
        "distinct": True,
        "freshness": ("domain-separated from the profile id and fixed before "
                      "any term is submitted; a term naming either is refused"),
    },
    budget_policy=("each side carries its own explicit budget; neither is "
                   "derived from the other's spend"),
    environment_policy=(
        "Both sides resolve against the same content environment, and both "
        "observations are materialized before either evaluation runs (Book I "
        "§3.5: extending an environment can turn an unresolved_reference into "
        "a settled exit, so the order of the sides could otherwise change "
        "UNSETTLED). "
        "OBLIGATION OF THIS PROFILE, not a guarantee of settle_eq: `observe` is "
        "pure in the term and monotone in the environment — it reads nothing "
        "from `env` and only adds a CAS-valid closure, so the second "
        "observation cannot depend on what the first one wrote. A profile whose "
        "observer reads the environment must argue order-independence for "
        "itself; `EqualityProfile.observe: Callable` does not supply it."),
    book_anchor=_book_1_anchor(),
    book_context=("Book I document version 0.6.0, adopted as part of "
                  "anchor-set release v0.7.0 (Receipt with exit; §3.4, §3.6)"),
    reflection=(
        "On the admitted domain: two written-out numerals whose observations "
        "share an address denote the same natural. Argument: c1 compiles "
        "λf.λx.fⁿ(x) so that applying it to two inert literals reduces to the "
        "constructor spine Fⁿ(X), which is injective in n; the markers are "
        "inert, so nothing else can produce that spine."),
    preservation=(
        "On the admitted domain: equal naturals observe to the same address, "
        "because the spine depends only on n."),
    not_established=(
        "equality of arbitrary SKI terms",
        "equality of higher-order terms (η/extensionality is not decided here)",
        "admission of computed Church-natural expressions",
        "any asymptotic bound for terms outside the admitted domain",
    ),
)


def fresh_env():
    env = sg.Store()
    for genesis in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
        env.put(genesis)
    return env


def church(n: int):
    body = ("var", "x")
    for _ in range(n):
        body = ("lapp", ("var", "f"), body)
    return ("lam", "f", ("lam", "x", body))
