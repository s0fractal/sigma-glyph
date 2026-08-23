#!/usr/bin/env python3
"""Reduce every net under several schedules and record what differs.

Check-only by default. `--record` rewrites `results.json`, and only after every
control has passed: a receipt written beside a failure is worse than none, since
it looks exactly like a receipt written beside a success.

Every schedule is given the same budget **in interactions**. An earlier version
capped the parallel schedule on rounds and wrote one schedule's count into the
record for all four, which made a comparison at "equal work" impossible to check
and, as it turned out, false.

Two properties are checked rather than reported, because interaction nets already
settle them: on a net that reaches a normal form, every schedule performs the
same multiset of interactions and reaches the same normal form. A failure of
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

# The allocation profile, declared here and then measured against the reducer
# rather than inferred from it. Every rule builds its whole right-hand side
# before any agent of its left-hand side is freed, so a commutation holds six
# agents at its widest and an erasure four.
#
# Checking only `ALLOCATES - FREES` would be vacuous: `5` and `3` describe the
# same net change as `4` and `2` and a very different widest point. The reducer
# counts agents created and destroyed, and each interaction is compared against
# both numbers separately.
ALLOCATES = {"growing": 4, "neutral": 2, "shrinking": 0}
FREES = {"growing": 2, "neutral": 2, "shrinking": 2}

KINDS = ("growing", "neutral", "shrinking")


def tally() -> dict[str, int]:
    return dict.fromkeys(KINDS, 0)


def kind(change: int) -> str:
    if change > 0:
        return "growing"
    return "shrinking" if change < 0 else "neutral"


class Run:
    """One schedule reducing one net, with the allocation profile under test."""

    def __init__(self, net) -> None:
        self.net = net
        self.rules = tally()
        self.peak = self.transient = net.size()
        self.interactions = self.rounds = 0
        self.handed_back = 0
        self.max_round_freed = 0
        self.partial_rounds = 0
        self.model_errors: list[str] = []
        self.stopped: str | None = None
        self.pending = 0          # size of a round refused for want of budget

    def fire(self, a, b) -> int:
        """Perform one interaction and return what it actually allocated."""
        shape = kind(self.net.delta(a, b))
        before = (self.net.allocated, self.net.freed)
        self.net.interact(a, b)
        allocated = self.net.allocated - before[0]
        freed = self.net.freed - before[1]
        if (allocated, freed) != (ALLOCATES[shape], FREES[shape]):
            self.model_errors.append(
                f"a {shape} rule allocated {allocated} and freed {freed}; the "
                f"profile declares {ALLOCATES[shape]} and {FREES[shape]}")
        self.rules[shape] += 1
        self.interactions += 1
        return allocated

    def close(self) -> dict:
        return {"interactions": self.interactions, "rounds": self.rounds,
                "peak": self.peak, "transient_peak": self.transient,
                "handed_back": self.handed_back,
                "max_round_freed": self.max_round_freed,
                "partial_rounds": self.partial_rounds, "final": self.net.size(),
                "rules": self.rules, "stopped": self.stopped,
                "pending_round": self.pending, "model_errors": self.model_errors,
                "normal": self.stopped is None}


def sequential(net, order, budget=CAP):
    """One interaction at a time. `order` ranks an active pair by its size delta.

    The peak is read from the net after every interaction, never accumulated from
    `delta()`: a rule that allocates more than its price claims has to show up
    here rather than cancel out against its own accounting.
    """
    run = Run(net)
    size = net.size()
    while run.interactions < budget:
        pairs = net.active_pairs()
        if not pairs:
            break
        a, b = min(pairs, key=lambda p: (order(net.delta(*p)), p))
        allocated = run.fire(a, b)
        run.transient = max(run.transient, size + allocated)
        size = net.size()
        run.peak = max(run.peak, size)
        if size > SIZE_CAP:
            run.stopped = "size"
            break
    else:
        run.stopped = "budget"
    return run.close()


def rounds(net, budget, whole_rounds: bool):
    """Every active pair in a round fires together.

    Two granularities, because they answer different questions and conflating
    them was a defect:

    - `whole_rounds=True` runs a round or refuses it, which is the batch machine
      the architectural conclusion is about. Choosing *part* of a round is
      already the arbitration that conclusion says a batch machine avoids.
    - `whole_rounds=False` truncates the last round to a prefix. That is a
      legitimate schedule — the pairs in a round are pairwise disjoint, so any
      prefix is a set of interactions that could have been chosen — and it is
      used only where every schedule must stop at exactly the same count.
    """
    run = Run(net)
    size = net.size()
    while run.interactions < budget:
        pairs = net.active_pairs()
        if not pairs:
            break
        room = budget - run.interactions
        if len(pairs) > room:
            if whole_rounds:
                run.pending = len(pairs)
                run.stopped = "budget"
                return run.close()
            pairs = pairs[:room]
            run.partial_rounds += 1
        was_freed = net.freed
        allocated = sum(run.fire(a, b) for a, b in pairs)
        envelope = size + allocated
        run.transient = max(run.transient, envelope)
        size = net.size()
        # Per round, not maxima of different rounds: what a round reserves and
        # hands straight back is a property of that round alone, and it has an
        # exact identity — it is precisely the agents the round destroys.
        run.handed_back = max(run.handed_back, envelope - size)
        run.max_round_freed = max(run.max_round_freed, net.freed - was_freed)
        run.peak = max(run.peak, size)
        run.rounds += 1
        if size > SIZE_CAP:
            run.stopped = "size"
            break
    else:
        run.stopped = "budget"
    return run.close()


SCHEDULES = {
    "sequential":     lambda net, budget=CAP: sequential(net, lambda d: 0, budget),
    "shrink-first":   lambda net, budget=CAP: sequential(net, lambda d: d, budget),
    "grow-first":     lambda net, budget=CAP: sequential(net, lambda d: -d, budget),
    "parallel-round": lambda net, budget=CAP: rounds(net, budget, True),
}
# Exact equal work needs a schedule that can stop mid-round; the batch machine
# cannot, by definition. So the fair comparison uses the prefix variant.
EQUAL_WORK = dict(SCHEDULES, **{
    "parallel-round": lambda net, budget=CAP: rounds(net, budget, False)})

FIELDS = ("interactions", "rounds", "peak", "transient_peak", "handed_back",
          "max_round_freed", "partial_rounds", "final", "rules", "stopped",
          "pending_round", "normal")


def check_receipt(name: str, runs: dict) -> list[str]:
    """Every schedule's own observation must reach the record. An earlier version
    wrote one schedule's interaction count and let three others go unrecorded,
    which is how a false claim about equal work survived review."""
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
    """A schedule that stops on the budget must have spent it — exactly, or, for
    a round-granular one, to within the round it could not afford. Capping the
    parallel schedule on rounds instead of interactions was the defect this
    control exists to catch."""
    problems = []
    for schedule, result in runs.items():
        if result["stopped"] != "budget":
            continue
        spent, refused = result["interactions"], result["pending_round"]
        if spent + refused < budget or spent > budget:
            problems.append(
                f"{name}/{schedule}: stopped on the budget having spent {spent} "
                f"with a refused round of {refused}, which does not account for "
                f"{budget} — the cap is not being applied in interactions")
    return problems


def check_allocation_model(name: str, start: int, runs: dict) -> list[str]:
    """The declared profile against the reducer's own counters, per interaction,
    and then the final size it forces."""
    problems = []
    for schedule, result in runs.items():
        for error in dict.fromkeys(result["model_errors"]):
            problems.append(f"{name}/{schedule}: {error} — ALLOCATES/FREES "
                            "misstate a rule")
        predicted = start + sum((ALLOCATES[k] - FREES[k]) * result["rules"][k]
                                for k in KINDS)
        if predicted != result["final"]:
            problems.append(f"{name}/{schedule}: the allocation model predicts a "
                            f"final size of {predicted}, the net has "
                            f"{result['final']}")
        if result["transient_peak"] < result["peak"]:
            problems.append(f"{name}/{schedule}: transient {result['transient_peak']} "
                            f"below the peak {result['peak']}, which is impossible")
    return problems


def check_batch(name: str, runs: dict) -> list[str]:
    """Two things the batch machine's claim rests on.

    It must never run part of a round: choosing a subset *is* the arbitration the
    architectural conclusion says round granularity avoids. And what a round
    reserves and hands straight back is exactly the agents it destroys — an
    identity, so comparing the arithmetic against the reducer's own free counter
    catches a figure assembled from maxima of different rounds."""
    problems = []
    batch = runs.get("parallel-round")
    if batch is None:
        return problems
    if batch["partial_rounds"]:
        problems.append(f"{name}/parallel-round: ran {batch['partial_rounds']} "
                        "partial rounds — a batch machine runs a round or refuses "
                        "it, and choosing part of one is the arbitration this "
                        "granularity exists to avoid")
    if batch["rounds"] and batch["handed_back"] != batch["max_round_freed"]:
        problems.append(f"{name}/parallel-round: reserved-then-released is "
                        f"{batch['handed_back']} but the worst round destroyed "
                        f"{batch['max_round_freed']} agents; they are the same "
                        "quantity, so this figure spans different rounds")
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
            "interactions — the per-rule bound is violated, which is impossible "
            "for these rules"
            for schedule, result in runs.items()
            if result["peak"] > start + 2 * result["interactions"]]


def measure_net(name: str, make, budget: int) -> tuple[dict, list[str]]:
    start = make().size()
    runs, signatures = {}, {}
    for schedule, run in SCHEDULES.items():
        net = make()
        runs[schedule] = run(net, budget)
        if runs[schedule]["normal"]:
            signatures[schedule] = net.signature()

    # An incomplete record cannot be analysed, and a control that reads past a
    # missing field crashes instead of reporting — which is a silent control.
    incomplete = check_receipt(name, runs)
    if incomplete:
        return {"net": name, "initial": start, "unanalysable": True}, incomplete

    problems = check_budget(name, runs, budget)
    problems += check_allocation_model(name, start, runs)
    problems += check_bound(name, start, runs) + check_batch(name, runs)
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
    fair = {s: run(make(), same_work) for s, run in EQUAL_WORK.items()}
    problems += [p.replace(name, f"{name} at equal work", 1)
                 for p in check_budget(name, fair, same_work)]
    if any(r["interactions"] != same_work for r in fair.values()):
        problems.append(f"{name}: the equal-work run did not stop every schedule at "
                        f"{same_work} interactions, so its peaks compare different "
                        "amounts of work")

    batch = runs["parallel-round"]
    row = {"net": name, "initial": start, "terminating": terminating,
           "schedules": runs, "reordering_bound": reordering_bound,
           "peaks": peaks, "spread": spread,
           "ratio": round(max(peaks.values()) / max(min(peaks.values()), 1), 4),
           "equal_work": {"interactions": same_work,
                          "peaks": {s: r["peak"] for s, r in fair.items()},
                          "transients": {s: r["transient_peak"] for s, r in fair.items()}},
           "batch": {"envelope": batch["transient_peak"], "kept": batch["peak"],
                     "handed_back_worst_round": batch["handed_back"],
                     "refused_round": batch["pending_round"]}}
    return row, problems


def report(row: dict) -> str:
    if row.get("unanalysable"):
        return f"{row['net']:16} start {row['initial']:5}  record incomplete"
    peaks, fair = row["peaks"], row["equal_work"]
    counts = {s: r["interactions"] for s, r in row["schedules"].items()}
    return (f"{row['net']:16} start {row['initial']:5}  "
            f"int {min(counts.values()):7}-{max(counts.values()):<9} "
            + " ".join(f"{s[:4]} {peaks[s]:6}" for s in SCHEDULES) +
            f"  spread {row['spread']:6}  bound {row['reordering_bound']:6}  "
            f"| equal work {fair['interactions']:7}: " +
            " ".join(f"{fair['peaks'][s]:6}" for s in EQUAL_WORK) +
            ("" if row["terminating"] else "  (did not normalise)"))


def main(corpus=CORPUS, budget=CAP, record=False) -> int:
    rows, problems = [], []
    pinned, drift = fingerprint(corpus)
    problems += drift
    for name, make in corpus:
        row, trouble = measure_net(name, make, budget)
        rows.append(row)
        problems += trouble
        print(report(row))

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        print("results.json left untouched: a receipt beside a failure is worse "
              "than no receipt", file=sys.stderr)
        return 1

    if record:
        (HERE / "results.json").write_text(json.dumps(
            # Major.minor, not the patch level: the numbers do not depend on it,
            # and a receipt that no other machine can reproduce byte for byte
            # cannot be compared against a replay, which is what makes it a
            # receipt rather than a note.
            {"python": ".".join(platform.python_version_tuple()[:2]),
             "budget_interactions": budget,
             "size_cap": SIZE_CAP, "corpus_digest": pinned, "nets": rows},
            indent=2, sort_keys=True) + "\n")
        print("\nrecorded results.json")
    print("\nCONTROLS PASS: every schedule's own observation is recorded; each spent\n"
          "  the budget in interactions; every rule allocated and freed exactly what\n"
          "  the profile declares; no peak exceeds initial + 2 x interactions; the\n"
          "  starting nets match their pinned structure; and on every net that\n"
          "  normalised the schedules agreed on the interaction count, the multiset of\n"
          "  rules and the normal-form signature, with no spread beyond what\n"
          "  reordering that one fixed multiset permits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(record="--record" in sys.argv))
