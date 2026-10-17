# Probes behind the redesign review (2026-10-17)

Each probe takes the repository root as its first argument:
`python3 experiments/resume-probes/<probe>.py . [N]`.

- **`probe_sigma.py`** has three checks:
  - it reproduces B04: a cold thunk and the materialized `APPLY(I,K)` share a
    term_hash, with size 1 against 3;
  - it checks, over 20,114 (state, budget) pairs, that the action `step5` takes
    does not depend on the remaining budget. The budget only decides whether the
    action is affordable;
  - it runs 400 random terms looking for state cycles.
- **`cycle_search.py N`** runs every SKI term with at most N leaves for up to 300
  actions and looks for a repeated machine state.
  - N=7: 323,175 terms, 0 cycles.
  - N=8: 3,137,844 terms, 0 cycles.
- **`turing.py`** tests Turing's fixed point `A A I`, with `A` compiled by `c1`.
  The term grows and never cycles.
- **`turing_search.py N`** searches for a combinator `T` with
  `T x y ->> y (x x y)` exactly. Such a `T` would make `T T I` periodic.

These are measurements, not proofs. Finding no cycle up to 8 leaves does not show
that Sigma has no cycles.
