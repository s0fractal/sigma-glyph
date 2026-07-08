# Two jurisdictions, one node

The first *live* exercise of Book III: everything before this ran as pure
functions over pinned vectors; this builds two real warrant stores, moves
records between them over the dumbest possible transport (copying files), and
derives each jurisdiction's sovereign view with the reference oracle.

```sh
python3 examples/two-jurisdictions/demo.py            # temp dirs, self-cleaning
python3 examples/two-jurisdictions/demo.py --keep out # inspect the stores after
```

Requires the `cryptography` package (records are actually Ed25519-signed).

## What it demonstrates

| Beat | Book III claim exercised |
| --- | --- |
| Kyiv and Lviv select different assertions for the same node | §1: waves are per-jurisdiction, per-policy derived coordinates |
| Copying Kyiv's records into Lviv's store changes nothing | §2: assertions embed their jurisdiction root — replay resistance is live, not prose |
| Two epoch-tied Lviv assertions | §4: ConflictSet — clients MUST NOT merge; automation treats the node as unannotated |
| The conflict makes `APPLY(I, node)` derive to absent | §5: absent-poisoning of structural derivation |
| Divergence printed as two ViewIDs + set roots | §6: disagreement is named mechanically, never argued |
| `tools/warrant_verify.py` passes on both stores | the records are real Warrant-format artifacts, not demo mocks |

A detail worth noticing in step 7: after gossip, Lviv's store reports **two
roots** — Kyiv's genesis arrived with its records and sits there as an
unadopted root, which is exactly Warrant §9's model of two jurisdictions
sharing a blob store.

## Honest scope

- Node ids are synthetic hex64 (the oracle's own vector convention); a
  production annotator would use Book I NodeHashes.
- The candidate extraction takes every well-formed `accept` at face value;
  a settlement-grade pipeline would first run threshold/key-state checks via
  the warrant CLI (Warrant §5.1/§9). Wiring that stage in is the natural next
  iteration of this demo.
- Gossip cadence, peering, and discovery remain an implementation profile by
  design (Book III non-goals).
