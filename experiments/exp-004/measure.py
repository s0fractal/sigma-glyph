#!/usr/bin/env python3
"""Reduce every net under four schedules and record what differs.

Every schedule is given the same budget **in interactions**. The first version of
this harness capped the parallel schedule on *rounds* and wrote only the
sequential schedule's count into the receipt, which made a comparison at "equal
work" impossible to check and, as it turned out, false. Both are fixed here and
both are now guarded by controls that fail rather than report.

The schedules are not attempts at optimality. `shrink-first` and `grow-first` are
greedy, so they bracket the achievable peaks without reaching the true best and
worst; every spread reported is therefore a *lower* bound.

Two properties are checked rather than reported, because interaction nets already
settle them: on a net that reaches a normal form, every schedule performs the
same multiset of interactions, and reaches the same normal form. A failure of
either is a defect in this harness, not a discovery.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from corpus import CAP, CORPUS, SIZE_CAP, fingerprint  # noqa: E402

# The allocation model, stated once and then checked. Every rule builds its whole
# right-hand side before any agent of its left-hand side is freed, so a
# commutation holds six agents at its widest (four new beside the two it
# replaces) and an erasure four. `FREES` is the left-hand side in every case.
ALLOCATES = {"growing": 4, "neutral": 2, "shrinking": 0}
FREES = {"growing": 2, "neutral": 2, "shrinking": 2}

KINDS = ("growing", "neutral", "shrinking")


def tally() -> dict[str, int]:
    return dict.fromkeys(KINDS, 0)


def kind(change: int) -> str:
    if change > 0:
        return "growing"
    return "shrinking" if change < 0 else "neutral"


def observation(net, peak, transient, rules, interactions, rounds, stopped) -> dict:
    return {"interactions": interactions, "rounds": rounds, "peak": peak,
            "transient_peak": transient, "final": net.size(), "rules": rules,
            "stopped": stopped, "normal": stopped is None}


def sequential(net, order, budget=CAP):
    """One interaction at a time. `order` ranks an active pair by its size delta.

    The peak is read from the net after every interaction, never accumulated from
    `delta()`: a rule that allocates more than its price claims has to show up
    here rather than cancel out against its own accounting.
    """
    peak = transient = size = net.size()
    rules, done, stopped = tally(), 0, None
    while done < budget:
        pairs = net.active_pairs()
        if not pairs:
            break
        a, b = min(pairs, key=lambda p: (order(net.delta(*p)), p))
        shape = kind(net.delta(a, b))
        transient = max(transient, size + ALLOCATES[shape])
        rules[shape] += 1
        net.interact(a, b)
        size = net.size()
        peak = max(peak, size)
        done += 1
        if size > SIZE_CAP:
            stopped = "size"
            break
    else:
        stopped = "budget"
    return observation(net, peak, transient, rules, done, done, stopped)


def parallel(net, budget=CAP):
    """Every active pair in a round fires together.

    A round is truncated when the budget runs out. That is a legitimate state
    rather than a fudge: the pairs in a round are pairwise disjoint, so any
    prefix of them is a set of interactions that could have been chosen.
    """
    peak = transient = size = net.size()
    rules, done, rounds, stopped = tally(), 0, 0, None
    while done < budget:
        pairs = net.active_pairs()[: budget - done]
        if not pairs:
            break
        shapes = [kind(net.delta(a, b)) for a, b in pairs]
        transient = max(transient, size + sum(ALLOCATES[s] for s in shapes))
        for (a, b), shape in zip(pairs, shapes):
            rules[shape] += 1
            net.interact(a, b)
        size = net.size()
        peak = max(peak, size)
        done += len(pairs)
        rounds += 1
        if size > SIZE_CAP:
            stopped = "size"
            break
    else:
        stopped = "budget"
    return observation(net, peak, transient, rules, done, rounds, stopped)


SCHEDULES = {
    "sequential":   lambda net, budget=CAP: sequential(net, lambda d: 0, budget),
    "shrink-first": lambda net, budget=CAP: sequential(net, lambda d: d, budget),
    "grow-first":   lambda net, budget=CAP: sequential(net, lambda d: -d, budget),
    "parallel":     parallel,
}
FIELDS = ("interactions", "rounds", "peak", "transient_peak", "final", "rules",
          "stopped", "normal")


def check_receipt(name: str, runs: dict) -> list[str]:
    """Every schedule's own observation must reach the record. The first version
    of this file wrote one schedule's interaction count and let three others go
    unrecorded, which is how a false claim about equal work survived review."""
    problems = []
    for schedule in SCHEDULES:
        if schedule not in runs:
            problems.append(f"{name}: no observation recorded for {schedule}")
            continue
        missing = [f for f in FIELDS if f not in runs[schedule]]
        if missing:
            problems.append(f"{name}/{schedule}: the record omits {missing}")
    return problems


def check_budget(name: str, runs: dict, budget: int) -> list[str]:
    """A schedule that stops on the budget must have spent it exactly, in
    interactions. Capping the parallel schedule on rounds instead was the defect
    this control exists to catch."""
    return [f"{name}/{schedule}: stopped on the budget after "
            f"{result['interactions']} interactions, not {budget} — the cap is "
            "not being applied in interactions"
            for schedule, result in runs.items()
            if result["stopped"] == "budget" and result["interactions"] != budget]


def check_allocation_model(name: str, start: int, runs: dict) -> list[str]:
    """Ties the transient model to something observable. If every rule allocates
    `ALLOCATES` and frees `FREES`, the final size is forced; a transient formula
    that misstates either number contradicts a size that was measured."""
    problems = []
    for schedule, result in runs.items():
        predicted = start + sum((ALLOCATES[k] - FREES[k]) * result["rules"][k]
                                for k in KINDS)
        if predicted != result["final"]:
            problems.append(f"{name}/{schedule}: the allocation model predicts a "
                            f"final size of {predicted}, the net has "
                            f"{result['final']} — ALLOCATES/FREES misstate a rule")
        if result["transient_peak"] < result["peak"]:
            problems.append(f"{name}/{schedule}: transient {result['transient_peak']} "
                            f"below the peak {result['peak']}, which is impossible")
    return problems


def check_uniform(name: str, runs: dict, signatures: dict) -> list[str]:
    """Interaction nets are strongly confluent, so on a net that normalises only
    the *order* of interactions may differ between schedules."""
    problems = []
    counts = {s: r["interactions"] for s, r in runs.items()}
    if len(set(counts.values())) != 1:
        problems.append(f"{name}: interaction counts differ {counts} — uniform "
                        "normalisation is a theorem, so this is a harness defect")
    shapes = {s: tuple(sorted(r["rules"].items())) for s, r in runs.items()}
    if len(set(shapes.values())) != 1:
        problems.append(f"{name}: the multiset of interactions differs between "
                        f"schedules {shapes} — only their order may differ")
    if len(set(signatures.values())) != 1:
        problems.append(f"{name}: normal-form signatures differ between schedules, "
                        "and equal signatures are necessary for equal nets")
    return problems


def check_bound(name: str, start: int, runs: dict) -> list[str]:
    """No rule adds more than two agents, so this cannot fail unless the reducer
    is wrong."""
    return [f"{name}/{schedule}: peak {result['peak']} exceeds initial + 2 x "
            f"interactions — the per-rule bound is violated, which is impossible "
            "for these rules"
            for schedule, result in runs.items()
            if result["peak"] > start + 2 * result["interactions"]]


def equal_work(make, budget: int) -> dict:
    """Every schedule stopped at the same number of interactions. Without this,
    comparing peaks compares runs that did different amounts of work."""
    return {schedule: run(make(), budget) for schedule, run in SCHEDULES.items()}


def batch_reservation(runs: dict) -> dict:
    """What a round-granular machine must reserve, against what the round keeps.

    A parallel round of `k` pairs can be prepaid without arbitration: count `k`,
    reserve `3k` ATP and the round's allocation envelope, then run the whole round
    or refuse the whole round. The price of avoiding arbitration is the part of
    that envelope handed back immediately, which is what this measures."""
    result = runs["parallel"]
    envelope = result["transient_peak"]
    kept = result["peak"]
    return {"envelope": envelope, "kept": kept, "handed_back": envelope - kept,
            "atp_per_round_is_3k": True}


def measure_net(name: str, make, budget: int) -> tuple[dict, list[str]]:
    start = make().size()
    runs, signatures = {}, {}
    for schedule, run in SCHEDULES.items():
        net = make()
        runs[schedule] = run(net, budget)
        if runs[schedule]["normal"]:
            signatures[schedule] = net.signature()

    problems = check_receipt(name, runs) + check_budget(name, runs, budget)
    problems += check_allocation_model(name, start, runs) + check_bound(name, start, runs)
    terminating = all(r["normal"] for r in runs.values())
    if terminating:
        problems += check_uniform(name, runs, signatures)

    peaks = {s: r["peak"] for s, r in runs.items()}
    spread = max(peaks.values()) - min(peaks.values())
    rules = runs["sequential"]["rules"]
    reordering_bound = 2 * min(rules["growing"], rules["shrinking"])
    if terminating and spread > reordering_bound:
        problems.append(f"{name}: schedules differ by {spread} where reordering one "
                        f"fixed multiset allows at most {reordering_bound} — either "
                        "the multiset is not fixed or the harness is wrong")

    same_work = min(r["interactions"] for r in runs.values())
    fair = equal_work(make, same_work)
    row = {"net": name, "initial": start, "terminating": terminating,
           "schedules": runs, "reordering_bound": reordering_bound,
           "peaks": peaks, "spread": spread,
           "ratio": round(max(peaks.values()) / max(min(peaks.values()), 1), 4),
           "equal_work": {"interactions": same_work,
                          "peaks": {s: r["peak"] for s, r in fair.items()},
                          "transients": {s: r["transient_peak"] for s, r in fair.items()}},
           "batch": batch_reservation(runs)}
    problems += check_budget(f"{name} at equal work", fair, same_work)
    return row, problems


def report(row: dict) -> str:
    peaks, fair = row["peaks"], row["equal_work"]
    counts = {s: r["interactions"] for s, r in row["schedules"].items()}
    return (f"{row['net']:16} start {row['initial']:5}  "
            f"int {min(counts.values()):7}-{max(counts.values()):<9} "
            f"peaks " + " ".join(f"{s[:4]} {peaks[s]:6}" for s in SCHEDULES) +
            f"  spread {row['spread']:6}  bound {row['reordering_bound']:6}  "
            f"| equal work {fair['interactions']:7}: " +
            " ".join(f"{fair['peaks'][s]:6}" for s in SCHEDULES) +
            ("" if row["terminating"] else "  (did not normalise)"))


def main(corpus=CORPUS, budget=CAP) -> int:
    rows, problems = [], []
    pinned, drift = fingerprint(corpus)
    problems += drift
    for name, make in corpus:
        row, trouble = measure_net(name, make, budget)
        rows.append(row)
        problems += trouble
        print(report(row))

    if corpus is CORPUS:
        (HERE / "results.json").write_text(json.dumps(
            {"python": platform.python_version(), "budget_interactions": budget,
             "size_cap": SIZE_CAP, "corpus_digest": pinned, "nets": rows},
            indent=2, sort_keys=True) + "\n")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nCONTROLS PASS: every schedule's own observation is recorded; each spent\n"
          "  the budget in interactions; the allocation model predicts the sizes that\n"
          "  were measured; no peak exceeds initial + 2 x interactions; and on every\n"
          "  net that normalised the schedules agreed on the interaction count, the\n"
          "  multiset of rules and the normal-form signature, with no spread beyond\n"
          "  what reordering that one fixed multiset permits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
