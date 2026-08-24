# Implementing Book I without reading our code

*Non-normative. [`book-1-truth.md`](book-1-truth.md) governs; this page only
shows that it is enough.*

The paper accompanying this repository says the single most valuable missing
datum is an implementation of Book I by someone who has not read the reference
code. It also gave a reason — that §5.1 sends you to `impl/sigma_glyph.py` for
the genesis atoms, so you would have to read it.

**That reason is wrong, and this page is the demonstration.** Every constant the
Book prints is re-derivable from the Book, in either language, and
[`tools/spec_audit.py`](../tools/spec_audit.py) re-derives all of them on every
CI run.

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

It remains a sentence that tells an implementer their disagreement with the
specification is settled by code they cannot see, and changing it is a normative
edit — see [`proposals/ADR-008-specification-is-the-arbiter.md`](../proposals/ADR-008-specification-is-the-arbiter.md).

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

The second command matters more than the first. It breaks the Book in nine ways —
a genesis hash its construction does not produce, an axiom whose construction is
replaced by "see the reference implementation", a prose hash no vector carries, a
rule changed in translation, a suite generated against different bytes — and
requires the audit to fail for each, with its own reason. An audit that cannot be
made to fail is not an audit.
