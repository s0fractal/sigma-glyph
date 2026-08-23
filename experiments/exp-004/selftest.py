#!/usr/bin/env python3
"""Do the controls fail when the thing they control is broken?

A harness that reports CONTROLS PASS proves nothing until removing what it checks
makes it fail. One perturbation per control, each required to produce *its own*
control's complaint — a perturbation that breaks everything attributes nothing.

  A  commutation allocates a fifth agent, so a rule grows the net by more than
     its price                         -> `peak <= initial + 2 x interactions`
  B  a schedule leaves a redex unreduced and reports having normalised
                                       -> the interaction-count agreement
  C  `delta` under-reports commutation as neutral
                                       -> the reordering bound
  D  the parallel schedule caps on rounds instead of interactions
                                       -> the budget-in-interactions check
  E  a schedule's observation reaches the record incomplete
                                       -> receipt completeness
  F  the allocation model understates what a commutation allocates
                                       -> the model-predicts-the-measured-size check
  G  a starting net differs from the one that was frozen
                                       -> the corpus pin
  H  the batch schedule truncates a round it cannot afford
                                       -> the whole-round-or-refuse check
  I  reserved-then-released is taken across rounds rather than per round
                                       -> the identity with what a round destroys

D, E, F, H and I guard defects this harness actually had.

The parallel schedule really did cap on rounds; the record really did carry one
schedule's interaction count for all four; the transient really was computed from
a formula that did not match its description; the allocation profile really was
checked only through its difference, so `5` and `3` passed where the reducer does
`4` and `2`; the batch schedule really did truncate its last round; and
reserved-then-released really was assembled from maxima of different rounds.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corpus  # noqa: E402
import measure  # noqa: E402
from nets import Net  # noqa: E402

# One net that does not normalise, so the budget path is exercised.
WANTED = ("dup-tree-3", "dup-tree-5", "race-3-4", "race-3-16", "random-3-12")
SMALL = [(n, m) for n, m in corpus.CORPUS if n in WANTED]
BUDGET = 200
PER_RULE_BOUND = "the per-rule bound"

ORIGINAL = {"interact": Net.interact, "delta": Net.delta,
            "dup_tree": corpus.dup_tree}


@contextlib.contextmanager
def swapped(container, key, value):
    """Put the perturbation in place and take it out again, so no control is
    left broken for the next one — the whole point is one defect at a time."""
    keep = container[key]
    container[key] = value
    try:
        yield
    finally:
        container[key] = keep


@contextlib.contextmanager
def patched(target, name, value):
    """The same, for a class attribute rather than a dict entry."""
    keep = getattr(target, name)
    setattr(target, name, value)
    try:
        yield
    finally:
        setattr(target, name, keep)


def run() -> tuple[int, str]:
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
        code = measure.main(SMALL, BUDGET)
    return code, captured.getvalue()


def expect(label: str, wanted: str, unwanted: tuple[str, ...] = ()) -> list[str]:
    code, errors = run()
    problems = []
    if code == 0:
        problems.append(f"{label}: the run passed with the perturbation in place")
    if wanted not in errors:
        problems.append(f"{label}: expected a complaint about {wanted!r}; got:\n"
                        f"{errors[:700]}")
    problems += [f"{label}: also complained about {other!r}, so the failure is not "
                 "attributable to the control under test"
                 for other in unwanted if other in errors]
    if not problems:
        print(f"OK   {label}")
    return problems


def leaky_interact(self, a, b):
    change = ORIGINAL["interact"](self, a, b)
    if change > 0:
        self.new_node("E", {})            # one extra agent per commutation
    return change


def forgetful(net, order, budget=BUDGET):
    """Stops with a redex still on the table and reports having normalised. The
    count it gives is honest about what it did — the control has to notice the
    missing interaction, not a doctored number."""
    run = measure.Run(net)
    size = net.size()
    while run.interactions < budget:
        pairs = net.active_pairs()
        if not pairs or (run.interactions > 3 and len(pairs) == 1):
            break
        a, b = min(pairs, key=lambda p: (order(net.delta(*p)), p))
        allocated = run.fire(a, b)
        run.transient = max(run.transient, size + allocated)
        size = net.size()
        run.peak = max(run.peak, size)
    return run.close()


def blind_delta(self, a, b):
    change = ORIGINAL["delta"](self, a, b)
    return 0 if change > 0 else change


def rounds_capped(net, budget=BUDGET):
    """The defect the first version of this harness shipped: `budget` counted
    rounds, so the parallel schedule did several times the work of the others and
    the comparison between them was meaningless."""
    return measure.rounds(net, budget * 1000, True)


def incomplete(net, budget=BUDGET):
    result = measure.rounds(net, budget, True)
    return {k: v for k, v in result.items() if k != "rounds"}


def truncating_batch(net, budget=BUDGET):
    """The prefix variant wearing the batch schedule's name."""
    return measure.rounds(net, budget, False)


def cross_round(net, budget=BUDGET):
    """`max(envelope) - max(kept)` — literally the formula that was shipped, not
    a doctored number: `transient_peak` is the largest envelope of any round and
    `peak` the largest size after any round, and nothing says they are the same
    round."""
    result = measure.rounds(net, budget, True)
    return dict(result, handed_back=result["transient_peak"] - result["peak"])


def fatter_tree(depth: int):
    net = ORIGINAL["dup_tree"](depth)
    net.new_node("E", {})
    return net


def main() -> int:
    code, errors = run()
    if code != 0:
        print("FAIL the unperturbed harness does not pass, so nothing below means "
              f"anything:\n{errors[:700]}", file=sys.stderr)
        return 1
    print("OK   unperturbed: the controls pass")

    problems = []
    independent = ("no observation recorded", "stopped on the budget")

    with patched(Net, "interact", leaky_interact):
        problems += expect("A  a rule allocating more than its price",
                           PER_RULE_BOUND, independent)

    with swapped(measure.SCHEDULES, "grow-first",
                 lambda net, budget=BUDGET: forgetful(net, lambda d: -d, budget)):
        problems += expect("B  a schedule losing an interaction",
                           "interaction counts differ",
                           independent + (PER_RULE_BOUND,))

    with patched(Net, "delta", blind_delta):
        problems += expect("C  a price under-reporting growth",
                           "where reordering one fixed multiset allows at most",
                           independent)

    with swapped(measure.SCHEDULES, "parallel-round", rounds_capped):
        problems += expect("D  a schedule capped on rounds, not interactions",
                           "the cap is not being applied in interactions")

    with swapped(measure.SCHEDULES, "parallel-round", incomplete):
        problems += expect("E  an observation reaching the record incomplete",
                           "the record omits", (PER_RULE_BOUND,))

    # 5 and 3 describe the same net change as 4 and 2 and a different widest
    # point, so a control that reads only the difference lets this through.
    with swapped(measure.ALLOCATES, "growing", 5), \
            swapped(measure.FREES, "growing", 3):
        problems += expect("F  a profile with the right difference and the wrong "
                           "widest point", "ALLOCATES/FREES misstate a rule",
                           independent)

    with swapped(measure.SCHEDULES, "parallel-round", truncating_batch):
        problems += expect("H  a batch schedule truncating a round",
                           "partial rounds", independent)

    with swapped(measure.SCHEDULES, "parallel-round", cross_round):
        problems += expect("I  reserved-then-released taken across rounds",
                           "this figure spans different rounds", independent)

    corpus.CORPUS[:] = [(n, (lambda d=int(n[-1]): fatter_tree(d))
                         if n.startswith("dup-tree") else m)
                        for n, m in corpus.CORPUS]
    SMALL[:] = [(n, m) for n, m in corpus.CORPUS if n in WANTED]
    problems += expect("G  a starting net that is not the one frozen",
                       "the corpus is not the one that was frozen", independent)

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nEXP-004 SELFTEST: every control failed for its own reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
