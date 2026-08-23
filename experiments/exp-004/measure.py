#!/usr/bin/env python3
"""Reduce every net under four schedules and record what differs.

The schedules are not attempts at optimality. `shrink-first` and `grow-first`
are greedy, so they bracket the achievable peaks without reaching the true best
and worst; the numbers are therefore a *lower bound* on the spread, which is the
safe direction for the claim being tested.

Two things are checked rather than reported, because interaction nets already
settle them: the interaction count must be identical under every schedule
(strong confluence gives uniform normalisation), and so must the normal form. A
failure of either is a defect in this harness, not a discovery, and the run says
so and exits non-zero.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from corpus import CAP, CORPUS, SIZE_CAP  # noqa: E402


def tally() -> dict[str, int]:
    return {"growing": 0, "neutral": 0, "shrinking": 0}


def kind(change: int) -> str:
    return "growing" if change > 0 else ("shrinking" if change < 0 else "neutral")


def sequential(net, order):
    """`order` ranks an active pair by its size delta. Peak is observed after
    every single interaction, which is what a sequential machine holds."""
    peak = size = net.size()
    rules = tally()
    steps = 0
    while steps < CAP:
        pairs = net.active_pairs()
        if not pairs:
            break
        a, b = min(pairs, key=lambda p: (order(net.delta(*p)), p))
        rules[kind(net.delta(a, b))] += 1
        net.interact(a, b)
        # Read from the net, not accumulated from delta(): a rule that allocates
        # more than its price claims must show up here rather than cancel out.
        size = net.size()
        peak = max(peak, size)
        steps += 1
        if size > SIZE_CAP:
            return {"interactions": steps, "peak": peak, "final": size,
                    "rules": rules, "normal": False, "stopped": "size"}
    return {"interactions": steps, "peak": peak, "final": net.size(), "rules": rules,
            "normal": steps < CAP, "stopped": None if steps < CAP else "steps"}


def parallel(net):
    """Every active pair fires in one step. Two peaks are recorded: at step
    boundaries, and the worst an implementation could hold *inside* a step if it
    allocates everything before freeing anything — which is the honest bound for
    a machine that really runs the pairs at the same time."""
    boundary = inside = size = net.size()
    rules = tally()
    steps = interactions = 0
    while steps < CAP:
        pairs = net.active_pairs()
        if not pairs:
            break
        inside = max(inside, size + 2 * sum(1 for p in pairs if net.delta(*p) > 0))
        for a, b in pairs:
            if a in net.symbol and b in net.symbol:
                rules[kind(net.delta(a, b))] += 1
                net.interact(a, b)
        size = net.size()
        boundary = max(boundary, size)
        interactions += len(pairs)
        steps += 1
        if size > SIZE_CAP:
            return {"interactions": interactions, "peak": boundary,
                    "peak_inside": inside, "final": size, "steps": steps,
                    "rules": rules, "normal": False, "stopped": "size"}
    return {"interactions": interactions, "peak": boundary, "peak_inside": inside,
            "final": net.size(), "steps": steps, "rules": rules,
            "normal": steps < CAP, "stopped": None if steps < CAP else "steps"}


SCHEDULES = {
    "sequential":   lambda net: sequential(net, lambda d: 0),
    "shrink-first": lambda net: sequential(net, lambda d: d),
    "grow-first":   lambda net: sequential(net, lambda d: -d),
    "parallel":     parallel,
}


def main(corpus=CORPUS) -> int:
    rows, problems = [], []
    for name, make in corpus:
        start = make().size()
        runs = {}
        signatures = {}
        for schedule, run in SCHEDULES.items():
            net = make()
            result = run(net)
            result["initial"] = start
            runs[schedule] = result
            if result["normal"]:
                signatures[schedule] = net.signature()

        terminating = all(r["normal"] for r in runs.values())
        if terminating:
            counts = {s: r["interactions"] for s, r in runs.items()}
            if len(set(counts.values())) != 1:
                problems.append(f"{name}: interaction counts differ {counts} — "
                                "uniform normalisation is a theorem, so this is a "
                                "harness defect, not a result")
            if len(set(signatures.values())) != 1:
                problems.append(f"{name}: normal forms differ between schedules — "
                                "confluence is a theorem, so this is a harness defect")
            shapes = {s: tuple(sorted(r["rules"].items())) for s, r in runs.items()}
            if len(set(shapes.values())) != 1:
                problems.append(f"{name}: the multiset of interactions differs "
                                f"between schedules {shapes} — uniform normalisation "
                                "says only their order may differ")

        # The bound itself, checked on every row rather than argued: no rule adds
        # more than two agents, so this cannot fail unless the reducer is wrong.
        for schedule, result in runs.items():
            if result["peak"] > start + 2 * result["interactions"]:
                problems.append(f"{name}/{schedule}: peak {result['peak']} exceeds "
                                f"initial + 2 x interactions — the per-rule bound "
                                "is violated, which is impossible for these rules")

        peaks = {s: r["peak"] for s, r in runs.items()}
        rules = runs["sequential"]["rules"]
        spread = max(peaks.values()) - min(peaks.values())
        # If only the order may differ, the reachable peaks are the prefix sums of
        # one fixed multiset of +2/0/-2 steps, so no schedule can be further from
        # another than twice the smaller of the two signed counts.
        reordering_bound = 2 * min(rules["growing"], rules["shrinking"])
        if terminating and spread > reordering_bound:
            problems.append(f"{name}: schedules differ by {spread} where reordering "
                            f"one fixed multiset allows at most {reordering_bound} — "
                            "either the multiset is not fixed or the harness is wrong")
        rows.append({"net": name, "initial": start, "terminating": terminating,
                     "interactions": runs["sequential"]["interactions"],
                     "rules": rules, "reordering_bound": reordering_bound,
                     "peaks": peaks,
                     "peak_inside_parallel": runs["parallel"]["peak_inside"],
                     "parallel_steps": runs["parallel"]["steps"],
                     "spread": spread,
                     "ratio": round(max(peaks.values()) / max(min(peaks.values()), 1), 4)})
        flag = "" if terminating else "  (did not normalise within the cap)"
        print(f"{name:16} start {start:5}  int {runs['sequential']['interactions']:6}  "
              f"peaks seq {peaks['sequential']:6} shrink {peaks['shrink-first']:6} "
              f"grow {peaks['grow-first']:6} par {peaks['parallel']:6} "
              f"(inside {runs['parallel']['peak_inside']:6})  "
              f"spread {rows[-1]['spread']:6} x{rows[-1]['ratio']}  "
              f"bound {reordering_bound:6}{flag}")

    if corpus is CORPUS:
        (HERE / "results.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nCONTROLS PASS: on every net that normalised, all four schedules agreed on\n"
          "  the interaction count, the multiset of rules and the normal form; no peak\n"
          "  exceeded initial + 2 x interactions; and no spread exceeded what reordering\n"
          "  that one fixed multiset permits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
