#!/usr/bin/env python3
"""Shared scaffolding for the Σ-GLYPH probes.

Extracted after the fact, because three probes carried identical copies of it.
The helpers are the same code the probes ran with; the measurements below did not
move when they were factored out, and each probe prints its own numbers so that
can be checked rather than believed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "impl"))

from sigma_glyph import Store, c1, eval_hash, sha, term_bytes, term_hash  # noqa: E402,F401

LIMITS = {"max_node_depth": 500_000, "max_materialized_nodes": 200_000_000,
          "max_store_fetches": 500_000_000}

V = lambda name: ("var", name)                       # noqa: E731
L = lambda name, body: ("lam", name, body)           # noqa: E731
A = lambda fn, arg: ("lapp", fn, arg)                # noqa: E731


def put(store, term):
    """Store a term tree, returning the hash of its root."""
    if term[0] == "thunk":
        return term[1]
    if term[0] == "app":
        put(store, term[1])
        put(store, term[2])
    return store.put(term_bytes(term))


def compile_store(store, lam):
    """Compile a closed lambda term through Profile C1 and store it."""
    return "thunk", put(store, c1(lam))


def node(store, fn, *args):
    """Apply, storing every intermediate so the graph is shared by hash."""
    term = fn
    for arg in args:
        term = ("app", term, arg)
        put(store, term)
        term = ("thunk", term_hash(term))
    return term


def church_booleans(store):
    return (compile_store(store, L("a", L("b", V("a")))),
            compile_store(store, L("a", L("b", V("b")))))


def forced(store, term):
    """Drive a boolean-valued term to a normal form."""
    return node(store, term, ("lit", sha(b"I")), ("lit", sha(b"I")))
