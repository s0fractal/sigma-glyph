#!/usr/bin/env python3
"""Does the verifier decide *before* the stranger's term costs it anything?

`eval` is total, so a stranger's computation always terminates. That is the
guarantee, and it is not the same as being affordable: a 32-bit budget permits up
to 4,294,967,295 priced actions, and because `size <= atp + 1` the budget the
stranger chooses is also their licence over the verifier's memory. Whoever supplies
the term must not get to decide how much the verifier spends finding that out.

So the admission decision has to hold three properties, and each is checked here
rather than described:

  1. it refuses above the limit and admits at it;
  2. it refuses **before** the store is touched — a term whose bytes would be
     fetched must not be fetched to learn that the budget was never acceptable;
  3. the refusal is not a result. It is not a DISSONANCE, it is not a
     ResourceFault, and a caller cannot mistake it for what the term evaluates to.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))

import sigma_glyph as sg  # noqa: E402


class ExplodingStore(dict):
    """Any read is a failure of property 2."""

    def __contains__(self, key):
        raise AssertionError("the store was consulted before admission")

    def __getitem__(self, key):
        raise AssertionError("the store was consulted before admission")

    def get(self, key, default=None):
        raise AssertionError("the store was consulted before admission")


def main() -> int:
    problems = []
    policy = dict(sg.DEFAULT_LIMITS, max_atp=1000)

    # 1. the boundary, both sides of it
    try:
        sg.admit(1000, policy)
    except sg.AdmissionRefused:
        problems.append("a budget exactly at the limit was refused; the limit is "
                        "a maximum, not a strict bound")
    try:
        sg.admit(1001, policy)
        problems.append("a budget above the limit was admitted")
    except sg.AdmissionRefused as refusal:
        if (refusal.claimed, refusal.allowed) != (1001, 1000):
            problems.append(f"the refusal reports {refusal.claimed}/{refusal.allowed} "
                            "rather than what was claimed and what is allowed")

    # 2. nothing is touched first
    try:
        sg.eval_hash(sg.I_H, 10 ** 9, ExplodingStore(), policy)
        problems.append("an over-budget evaluation ran to completion")
    except sg.AdmissionRefused:
        pass
    except AssertionError as touched:
        problems.append(f"refused only after work: {touched}")

    # 3. a refusal is not a result, and not the fault type used during evaluation
    if issubclass(sg.AdmissionRefused, sg.ResourceFault):
        problems.append("AdmissionRefused is a ResourceFault, so a caller "
                        "handling in-flight limit breaches silently swallows a "
                        "decision that was made before the run began")
    refused = sg.AdmissionRefused(2, 1)
    if isinstance(refused, tuple) or hasattr(refused, "hex"):
        problems.append("a refusal looks like a term")

    # 4. and the oracle keeps answering for any budget the Book permits
    term, spent = sg.eval_hash(sg.I_H, 2 ** 32 - 1, {})
    if spent != 0:
        problems.append(f"the default limits refused or charged for a bare "
                        f"intrinsic at the maximum budget (spent {spent})")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("ATP-ADMISSION: refused above the limit, admitted at it, decided before "
          "the store was read, distinct from every canonical outcome, and absent "
          "by default so the oracle still answers for any budget the Book permits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
