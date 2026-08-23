#!/usr/bin/env python3
"""Do the controls fail when the thing they control is broken?

A harness that reports CONTROLS PASS proves nothing until removing what it checks
makes it fail. Three perturbations, each aimed at one control:

  A  commutation allocates a fifth agent, so a rule grows the net by more than
     its price   -> the `peak <= initial + 2 x interactions` check must fire;
  B  a schedule quietly drops an available active pair and stops
     -> the interaction-count and normal-form checks must fire;
  C  `delta` under-reports commutation as neutral, so the predicted reordering
     bound collapses to zero while the peaks still spread
     -> the reordering check must fire.

Each perturbation must produce *its own* control's complaint. A perturbation that
fails everything proves as little as one that fails nothing.
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

SMALL = [(n, m) for n, m in corpus.CORPUS if n in
         ("dup-tree-3", "dup-tree-5", "race-3-4", "race-3-16", "race-5-16")]

ORIGINAL_INTERACT = Net.interact
ORIGINAL_DELTA = Net.delta


def run() -> tuple[int, str]:
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
        code = measure.main(SMALL)
    return code, captured.getvalue()


def leaky_interact(self, a, b):
    change = ORIGINAL_INTERACT(self, a, b)
    if change > 0:                     # one extra agent per commutation
        self.new_node("E", {})
    return change


def forgetful_sequential(net, order):
    """Stops with a redex still on the table and reports having normalised —
    the count it gives is honest about what it did, which is the point: the
    control has to notice the missing interaction, not a doctored number."""
    peak = size = net.size()
    rules = measure.tally()
    steps = 0
    while True:
        pairs = net.active_pairs()
        if not pairs or (steps > 3 and len(pairs) == 1):
            break
        a, b = min(pairs, key=lambda p: (order(net.delta(*p)), p))
        rules[measure.kind(net.delta(a, b))] += 1
        net.interact(a, b)
        size = net.size()
        peak = max(peak, size)
        steps += 1
    return {"interactions": steps, "peak": peak, "final": net.size(),
            "rules": rules, "normal": True, "stopped": None}


def blind_delta(self, a, b):
    change = ORIGINAL_DELTA(self, a, b)
    return 0 if change > 0 else change


def expect(label: str, wanted: str, unwanted: tuple[str, ...]) -> list[str]:
    code, errors = run()
    problems = []
    if code == 0:
        problems.append(f"{label}: the run passed with the perturbation in place")
    if wanted not in errors:
        problems.append(f"{label}: expected a complaint about {wanted!r}; got:\n"
                        f"{errors[:600]}")
    for other in unwanted:
        if other in errors:
            problems.append(f"{label}: also complained about {other!r}, so the "
                            "failure is not attributable to the control under test")
    if not problems:
        print(f"OK   {label}")
    return problems


def main() -> int:
    problems = []

    code, errors = run()
    if code != 0:
        print("FAIL the unperturbed harness does not pass, so nothing below means "
              f"anything:\n{errors[:600]}", file=sys.stderr)
        return 1
    print("OK   unperturbed: the controls pass")

    Net.interact = leaky_interact
    problems += expect("A  a rule that allocates more than its price is caught",
                       "the per-rule bound", ())
    Net.interact = ORIGINAL_INTERACT

    original = measure.SCHEDULES["grow-first"]
    measure.SCHEDULES["grow-first"] = lambda net: forgetful_sequential(net, lambda d: -d)
    problems += expect("B  a schedule that loses an interaction is caught",
                       "interaction counts differ", ("the per-rule bound",))
    measure.SCHEDULES["grow-first"] = original

    Net.delta = blind_delta
    problems += expect("C  a price that under-reports growth is caught",
                       "where reordering one fixed multiset allows at most",
                       ("interaction counts differ",))
    Net.delta = ORIGINAL_DELTA

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nEXP-004 SELFTEST: every control failed for its own reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
