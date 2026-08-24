# Implementing Book I without reading our code

*Non-normative. [`book-1-truth.md`](book-1-truth.md) governs; this page only
shows that it is enough.*

The paper accompanying this repository says the single most valuable missing
datum is an implementation of Book I by someone who has not read the reference
code. It also gave a reason — that §5.1 sends you to `impl/sigma_glyph.py` for
the genesis atoms, so you would have to read it.

**That reason is wrong, and this page is the demonstration.**
[`tools/spec_audit.py`](../tools/spec_audit.py) accounts for all fifteen 64-hex
constants the Book prints, on every CI run and in either language, by one of two
routes that need no implementation:

- **ten** are re-derived from a construction the Book itself states — the genesis
  axioms, the reason hashes, `FALSE`, the Canonical Invalid Object, and every
  vector that prints its bytes;
- the rest are **proved by recomputation from the normative suite's own store**,
  which maps a hash to the bytes that produce it, and **bound to the record of
  the test that names them** — not merely found somewhere in the file.

Nothing printed is unaccounted for. The distinction in that last line is not
pedantry: an earlier version of this audit asked only whether a digest appeared
anywhere in the suite, and stayed green when two tests' hashes were swapped.

## The one convention the text leaves to inference, and how to settle it

`SHA-256("I")` means the hash of the ASCII bytes of `I` — one byte, `0x49`, no
quotes, no terminator. The Book does not spell that out, and it does not have to:
§5.3 prints three hashes of longer strings, so you can confirm your reading
before you rely on it.

```python
import hashlib
assert hashlib.sha256(b"Invalid Object").hexdigest() == \
    "7cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8"
```

If that passes, your convention is the Book's, and §5.1 is fully determined.

## Deriving the genesis atoms yourself

§5.1 states the construction — `CanonicalBytes = 0001 + SHA-256("X")` — and §2
states that `NodeHash = SHA-256(CanonicalBytes)`. That is the whole recipe:

```python
import hashlib
for glyph in ("I", "K", "S"):
    atom = hashlib.sha256(glyph.encode()).digest()
    canonical = bytes([0x00, 0x01]) + atom          # LITERAL, F_ATOM
    print(glyph, hashlib.sha256(canonical).hexdigest())
```

Compare against the NodeHash column of §5.1. If your three lines match, you have
the genesis set with no store, no download and no reference implementation. TV-1
in §7 prints `SHA-256("I")` in full as a second check.

FALSE follows the same way: `0206 ‖ H(K) ‖ H(I)`, hashed, is §5.2's value. So
does TV-3, whose bytes §7 prints outright.

## What you actually need to read

| For | Read |
| --- | --- |
| node layout, opcodes, flag values | §1.1, §1.2, §2 |
| reduction rules and their order | §3.1, §3.2, §3.3 |
| what an action costs, and the memory bound | §3.4 |
| resolution, and the two ways it fails | §3.5 |
| what is a canonical failure and what is not | §3.6, §4.2 |
| deserialization | §4.1 |
| genesis constants and reason hashes | §5 |
| the λ→SKI profile, if you want one | §6 |
| the vectors your implementation must pass | §7 and `tests/spec_conformance/vectors.json` |

Nothing on that list requires our code.

## The honest caveats

**The normative text is Ukrainian.** [`book-1-truth.en.md`](book-1-truth.en.md)
is a complete English rendering, marked informative, and — unlike the normative
file — **it is not anchored**, so it carries no integrity guarantee of its own.
What it does carry is a checked relationship: `spec_audit.py` requires the two
files to contain the same 64-hex hashes in the same order, the same RFC 2119
keywords in the same order, and the same code blocks once translated words are
set aside. If they ever drift, CI fails. That is weaker than an anchor and much
stronger than a promise.

**§7 says the oracle wins.** In a discrepancy between the prose and
`tests/spec_conformance/vectors.json`, the Book designates `impl/sigma_glyph.py`
as the arbiter. A precedence rule is only ever exercised when a discrepancy
exists, and `spec_audit.py` checks whether one does: every hash the §7 prose
claims must appear in the vector suite, and the suite must be pinned to the exact
bytes of the Book that ships. Today no discrepancy exists.

The audit also compares what §7 *says* against what the suite recorded: every
stated budget, spend, outcome and normal form must match the records filed under
that test. Four claims are declared undecided — a statement quantified over every
budget, a claim about what the compiler emits rather than about an evaluation, and
a note recording how v0.4.x behaved — and the run fails if an undeclared one
appears, or if a declaration stops applying. One claim does not yet have a machine-readable filing — TV-12's second
half, `eval(H(I), n) = ⟨I⟩` at 0 ATP, is recorded by `EV-GENESIS-BARE`, whose note
does not name TV-12. The audit carries that as a named exception which fails the
run if it ever stops reproducing, so the exception cannot outlive the defect.

§7 remains a sentence telling an implementer their disagreement with the
specification is settled by code they cannot see, and changing it — like filing
that vector — is an edit to anchored bytes. See
[`proposals/ADR-008-specification-is-the-arbiter.md`](../proposals/ADR-008-specification-is-the-arbiter.md).

**Three implementations already agree, and that is weaker evidence than it
looks.** The Python oracle, `warrant-go` and the Rust implementation were written
from the same specification text by the same author with model assistance. They
are good evidence about coding slips and specification ambiguity; they are weak
evidence about specification *error*, because three implementations of a wrong
sentence agree perfectly.

## If you do implement it

The useful outcome is not a green suite. It is the list of places where you had
to guess — every one of those is a defect in the Book, and it is worth more to us
than a passing vector. Open an issue with the sentence you had to interpret.

## Check the check

```sh
python3 tools/spec_audit.py            # the Book is self-contained
python3 tests/spec_audit_selftest.py   # and the audit fails when it is not
```

The second command matters more than the first. It breaks the Book in **twenty**
ways — a genesis hash its construction does not produce, an axiom whose
construction is replaced by "see the reference implementation", a prose hash no
record of its own test carries, two tests' hashes swapped while both remain in the
suite, a price restated in prose while the record keeps the old one, a constant
printed that nothing accounts for, a rule changed in translation, a suite
generated against different bytes, and a recorded exception that has stopped
reproducing — and requires the audit to fail for each, with its own reason.

Eleven of those twenty exist because external review reproduced the gap first, in
two rounds. The audit's first version was described in wider terms than it
checked; its second still let a whole test's filing vanish, ignored budgets no
record used, read a note about a superseded version as a claim about this one, and
let an exception outlive the evidence it named.

The audit therefore reports two numbers rather than one: claims **decided**, and
claims **explicitly left undecided**, each with the reason. A claim that is
neither is an error. That accounting, rather than a stronger sentence, is what
keeps the description from outrunning the check.
