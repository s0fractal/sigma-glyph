# Receipt atom — demo transcript

**Goal:** one self-verifying verdict-receipt, proven by a hand-off to a *different*
model that re-derives the verdict from bytes alone (zero trust in the producer).
Target: the real pain of the v0.6.6 §0 gate, where deepseek/gemini had to **trust**
a pasted `gov-replay 20/20` transcript they could not re-run.

## The atom (two files + committed input)

- `verify_receipt.py` — mint + verify. Reuses `tools/anchor_governance.py`'s JCS
  `canon` + Ed25519, and its `replay` command as the deterministic computation.
  No new crypto, no new schema family: a receipt is a warrant-style `{body, sig}`
  envelope whose body **names a computation + content-addressed inputs + the
  claimed result**.
- `receipt.json` — one instance. Claim: *the governance vectors replay ALL PASS
  (20/20)*. Signed by a demo producer key.
- `inputs/governance_vectors.json` — the input, committed by SHA-256 in the body.

**Identity ≠ truth (the load-bearing design choice):** the signature proves *who*
produced the receipt; `VERIFIED` is **not** gated on it. `VERIFIED` means the fact
was **re-derived** from the bytes. Trust in the producer *for the fact* = 0.

## Run 1 — producer self-verify

```
ok   producer signature (identity only)
ok   input governance_vectors.json hash == committed
ok   re-derived: 'GOVERNANCE-REPLAY: ALL PASS (20/20)'
VERIFIED — the fact was re-derived from the bytes; trust in the producer for it = 0.
```

## Run 2 — negative control (flip one input byte)

```
ok   producer signature (identity only)
FAIL input governance_vectors.json hash == committed
FAIL re-derived: 'GOVERNANCE-REPLAY: ALL PASS (20/20)'
FAILED — the claim did not reproduce.
```

Content-addressing catches the tamper; the fact does not reproduce. Good.

## Run 3 — SECOND NODE (codex), read-only sandbox → **FAILED** (reported, not hidden)

Codex was handed only the bytes and the instruction "do not trust the producer;
run the verifier." Under a **read-only** sandbox it printed:

```
ok   input governance_vectors.json hash == committed
FAIL re-derived: 'GOVERNANCE-REPLAY: ALL PASS (20/20)'
SECOND-NODE: FAILED
```

The input **hash matched** — but the computation could not re-run: `replay`
materializes stores in `/tmp`, and the read-only sandbox blocked the writes. This
is a real property, not a receipt bug: **an execution-bound receipt cannot be
verified by a node that may read but not compute.**

## Run 4 — SECOND NODE (codex), execution allowed → **VERIFIED**

Same bytes, same blind instruction, sandbox permitting execution. Codex, verbatim:

> **VERIFIED**
> Running the verifier RE-DERIVED the fact from the delivered bytes; I did not have
> to trust the receipt's producer.
> "GOVERNANCE-REPLAY: ALL PASS (20/20)"
> **SECOND-NODE: VERIFIED**

A genuinely different model re-derived the exact fact that was load-bearing trust
at the §0 gate — from bytes alone, producer-trust = 0.

## Findings

1. **Mechanism holds.** The second node (codex) independently re-derived the
   verdict; the trust it would otherwise have given the producer collapsed to zero
   for that fact. This is the atom working.
2. **Nodes must compute, not just read (Run 3).** The receipt names a computation
   that must *run* (with scratch space). A read-only node verifies only the
   content-address, never the fact. A "second node" on this kind of network must be
   an **executor**, not a chat surface — which is consistent with the goal of a
   substrate *hybridized with computation*, but it is a hard boundary worth naming.
3. **What this does NOT prove (honest bound).** Codex re-verified because it was
   *asked* to, not because it had a real need for this fact. Mechanism ≠ need. This
   demo delivers the seed and the cheapest falsification test — **not** adoption,
   not a network.

## Termination

Atom built, second node demonstrated, one honest limit surfaced. No v2, no
protocol, no jurisdictions, no generalization. Stop.
