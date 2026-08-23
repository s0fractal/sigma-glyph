#!/usr/bin/env python3
"""Lafont's interaction combinators, small enough to read in one sitting.

Agents: `G` (constructor γ) and `D<label>` (duplicator δ), both binary — one
principal port and two auxiliary — and `E` (eraser ε), principal port only.
Labels on duplicators are HVM's device, not Lafont's: two duplicators with the
same label annihilate, with different labels they commute, which is what makes
sharing observable.

Wires are union-find variables rather than port-to-port links. That is not a
performance choice: it makes the degenerate cases — an agent wired to itself, an
active pair whose auxiliary ports already face each other — collapse correctly
instead of needing four special cases each.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def arity(symbol: str) -> int:
    return 0 if symbol == "E" else 2


def annihilates(a: str, b: str) -> bool:
    """Same symbol, same label. `D1` and `D2` commute; that is the point of labels."""
    return a == b


@dataclass
class Net:
    symbol: dict[int, str] = field(default_factory=dict)
    var: dict[tuple[int, int], int] = field(default_factory=dict)
    up: dict[int, int] = field(default_factory=dict)          # union-find over wires
    free: dict[str, int] = field(default_factory=dict)        # interface name -> wire
    allocated: int = 0                                        # agents ever created
    freed: int = 0                                            # agents ever deleted
    owner: dict[int, int] = field(default_factory=dict)       # wire -> agent whose principal is on it
    mate: dict[int, int] = field(default_factory=dict)        # the active pairs, maintained as they arise
    _node: int = 0
    _var: int = 0

    # -- wires ---------------------------------------------------------------

    def new_var(self) -> int:
        self._var += 1
        self.up[self._var] = self._var
        return self._var

    def find(self, v: int) -> int:
        root = v
        while self.up[root] != root:
            root = self.up[root]
        while self.up[v] != root:
            self.up[v], v = root, self.up[v]
        return root

    def union(self, u: int, v: int) -> None:
        """Merging two wires can put two principal ports on the same wire, which
        is how an annihilation hands the next active pair to its neighbours."""
        u, v = self.find(u), self.find(v)
        if u == v:
            return
        holder, other = self._holder(u), self._holder(v)
        self.up[v] = u
        if holder is not None and other is not None:
            self.mate[holder], self.mate[other] = other, holder
        chosen = holder if holder is not None else other
        if chosen is not None:
            self.owner[u] = chosen

    def _holder(self, wire: int) -> int | None:
        """The live agent whose principal port sits on `wire`, if any. Entries go
        stale when agents are deleted, so they are validated on the way out."""
        nid = self.owner.get(wire)
        if nid is None:
            return None
        if nid in self.symbol and self.find(self.var[(nid, 0)]) == wire:
            return nid
        del self.owner[wire]
        return None

    # -- agents --------------------------------------------------------------

    def new_node(self, symbol: str, wires: dict[int, int]) -> int:
        self._node += 1
        self.allocated += 1
        nid = self._node
        self.symbol[nid] = symbol
        for slot in range(arity(symbol) + 1):
            self.var[(nid, slot)] = wires[slot] if slot in wires else self.new_var()
        principal = self.find(self.var[(nid, 0)])
        facing = self._holder(principal)
        if facing is not None:
            self.mate[facing], self.mate[nid] = nid, facing
        else:
            self.owner[principal] = nid
        return nid

    def delete(self, nid: int) -> None:
        self.freed += 1
        partner = self.mate.pop(nid, None)
        if partner is not None:
            self.mate.pop(partner, None)
        for slot in range(arity(self.symbol[nid]) + 1):
            del self.var[(nid, slot)]
        del self.symbol[nid]

    def structure(self) -> str:
        """The net written out exactly, for pinning.

        Not the colour-refinement signature: that is invariant under renaming and
        therefore not injective, so two different starting nets could share one.
        This is the literal layout — symbols, every port's wire root, and the
        interface — which is what "the corpus did not change" has to mean.
        """
        agents = ";".join(
            f"{nid}:{self.symbol[nid]}:" +
            ",".join(str(self.find(self.var[(nid, slot)]))
                     for slot in range(arity(self.symbol[nid]) + 1))
            for nid in sorted(self.symbol))
        interface = ";".join(f"{name}={self.find(wire)}"
                             for name, wire in sorted(self.free.items()))
        return f"agents[{agents}]free[{interface}]"

    def size(self) -> int:
        """Memory, counted as agents. Wires are not counted: an interaction
        changes the wire count by a bounded amount too, and counting both only
        scales the same quantity."""
        return len(self.symbol)

    # -- reduction -----------------------------------------------------------

    def active_pairs(self) -> list[tuple[int, int]]:
        """Agents facing each other principal to principal. They are pairwise
        disjoint by construction — an agent has one principal port — which is
        why a whole set of them can fire in one parallel step.

        Maintained as agents are created and wires merged rather than rescanned:
        a rescan is linear in the whole net, which turns a non-terminating net
        into a harness that never finishes rather than one that reports."""
        return sorted({tuple(sorted((a, b))) for a, b in self.mate.items()
                       if a in self.symbol and b in self.symbol})

    def delta(self, a: int, b: int) -> int:
        """Net-size change of the interaction, before performing it."""
        sa, sb = self.symbol[a], self.symbol[b]
        if sa == "E" and sb == "E":
            return -2
        if sa == "E" or sb == "E":
            return 0                       # the eraser is copied onto both aux ports
        return -2 if annihilates(sa, sb) else +2

    def interact(self, a: int, b: int) -> int:
        sa, sb = self.symbol[a], self.symbol[b]
        change = self.delta(a, b)

        if sa == "E" and sb == "E":
            self.delete(a)
            self.delete(b)
        elif sa == "E" or sb == "E":
            eraser, agent = (a, b) if sa == "E" else (b, a)
            below = [self.find(self.var[(agent, 1)]), self.find(self.var[(agent, 2)])]
            self.delete(eraser)
            self.delete(agent)
            for wire in below:
                self.new_node("E", {0: wire})
        elif annihilates(sa, sb):
            self.union(self.var[(a, 1)], self.var[(b, 1)])
            self.union(self.var[(a, 2)], self.var[(b, 2)])
            self.delete(a)
            self.delete(b)
        else:
            a1, a2 = self.find(self.var[(a, 1)]), self.find(self.var[(a, 2)])
            b1, b2 = self.find(self.var[(b, 1)]), self.find(self.var[(b, 2)])
            self.delete(a)
            self.delete(b)
            w = [self.new_var() for _ in range(4)]
            self.new_node(sb, {0: a1, 1: w[0], 2: w[1]})
            self.new_node(sb, {0: a2, 1: w[2], 2: w[3]})
            self.new_node(sa, {0: b1, 1: w[0], 2: w[2]})
            self.new_node(sa, {0: b2, 1: w[1], 2: w[3]})
        return change

    # -- identity ------------------------------------------------------------

    def signature(self) -> str:
        """Colour refinement over the port structure.

        Equal nets give equal signatures, so a mismatch is a real difference and
        never a false alarm. The converse does not hold: this is a necessary
        condition for two nets to be the same and not a proof of isomorphism, and
        nothing here treats it as one.

        The colours are `blake2b` rather than Python's `hash`, which is seeded
        per process. With `hash` the signature was stable inside one run — so the
        comparisons between schedules were still sound — and different on the
        next run, which made every result unreproducible from its own record.
        """
        colour = {nid: self.symbol[nid] for nid in self.symbol}
        ends: dict[int, list[tuple[int, int]]] = {}
        for port, wire in self.var.items():
            ends.setdefault(self.find(wire), []).append(port)
        names = {self.find(w): n for n, w in self.free.items()}

        for _ in range(min(len(colour) + 1, 64)):
            fresh = {}
            for nid in colour:
                around = []
                for slot in range(arity(self.symbol[nid]) + 1):
                    wire = self.find(self.var[(nid, slot)])
                    other = sorted(colour.get(p[0], "?") + f".{p[1]}"
                                   for p in ends[wire] if p != (nid, slot))
                    around.append(f"{slot}[{names.get(wire, '')}|{','.join(other)}]")
                blob = repr((colour[nid], tuple(around))).encode()
                fresh[nid] = hashlib.blake2b(blob, digest_size=8).hexdigest()
            if fresh == colour:
                break
            colour = fresh

        interface = sorted(f"{n}={colour.get(p[0], 'wire')}"
                           for n, w in self.free.items()
                           for p in ends.get(self.find(w), []))
        return "|".join(sorted(colour.values())) + "//" + "|".join(interface)
