#!/usr/bin/env python3
"""The nets to be measured. Fixed here, before any measurement is recorded.

Four families, chosen for what each one can show and not for what it will say:

- `dup-tree`   pure growth: a duplicator meets the root of a constructor tree
               and every commutation adds two agents. No shrinking interaction
               exists, so every schedule must have the same peak. This family is
               a control on H1: if it shows a spread, the harness is wrong.
- `erase-tree` pure zero: erasure against a binary agent replaces two agents
               with two. Size never moves.
- `race`       growth and shrinking available at once. The two components are
               independent, which is deliberate: it isolates ordering from
               everything else, so any spread is attributable to order alone.
- `random`     the same question without a construction behind it, from fixed
               seeds, including nets that do not terminate.
"""

from __future__ import annotations

import random

from nets import Net

CAP = 200_000


def constructor_tree(net: Net, depth: int) -> int:
    """Returns the wire at the root's principal port. Leaves are left free."""
    if depth == 0:
        wire = net.new_var()
        net.free[f"leaf{len(net.free)}"] = wire
        return wire
    left, right = constructor_tree(net, depth - 1), constructor_tree(net, depth - 1)
    root = net.new_var()
    net.new_node("G", {0: root, 1: left, 2: right})
    return root


def dup_tree(depth: int) -> Net:
    net = Net()
    root = constructor_tree(net, depth)
    net.new_node("D1", {0: root})
    return net


def erase_tree(depth: int) -> Net:
    net = Net()
    net.new_node("E", {0: constructor_tree(net, depth)})
    return net


def annihilation_ladder(net: Net, pairs: int) -> None:
    """`pairs` constructor pairs facing each other: every one is a shrinking
    interaction that is available immediately and depends on nothing."""
    for i in range(pairs):
        wire = net.new_var()
        for side in ("a", "b"):
            nid = net.new_node("G", {0: wire})
            net.free[f"lad{i}{side}1"] = net.var[(nid, 1)]
            net.free[f"lad{i}{side}2"] = net.var[(nid, 2)]


def race(depth: int, pairs: int) -> Net:
    net = dup_tree(depth)
    annihilation_ladder(net, pairs)
    return net


def random_net(seed: int, agents: int) -> Net:
    rng = random.Random(seed)
    net = Net()
    symbols = ["G", "D1", "D2", "E"]
    for _ in range(agents):
        net.new_node(rng.choice(symbols), {})
    ports = list(net.var)
    rng.shuffle(ports)
    freed = 0
    while len(ports) >= 2:
        left, right = ports.pop(), ports.pop()
        net.union(net.var[left], net.var[right])
    for port in ports:
        net.free[f"f{freed}"] = net.var[port]
        freed += 1
    # Any wire nothing else reaches is an interface, so the net stays well formed.
    seen: dict[int, int] = {}
    for wire in net.var.values():
        seen[net.find(wire)] = seen.get(net.find(wire), 0) + 1
    for wire, count in seen.items():
        if count == 1 and wire not in {net.find(w) for w in net.free.values()}:
            net.free[f"f{freed}"] = wire
            freed += 1
    return net


CORPUS = (
    [(f"dup-tree-{d}", lambda d=d: dup_tree(d)) for d in (3, 5, 7, 9)]
    + [(f"erase-tree-{d}", lambda d=d: erase_tree(d)) for d in (3, 6, 9)]
    + [(f"race-{d}-{k}", lambda d=d, k=k: race(d, k))
       for d, k in ((3, 4), (3, 16), (5, 16), (5, 64), (7, 64), (7, 256))]
    + [(f"random-{s}-{n}", lambda s=s, n=n: random_net(s, n))
       for s in (1, 2, 3, 5, 8, 13, 21, 34) for n in (12, 48)]
)
