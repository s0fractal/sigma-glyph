#!/usr/bin/env python3
"""The WASM profile's load path: identity first, execution second.

Sigma-Glyph names a term by the hash of itself, and a verifier who wants to run
*that* term must be told the hash out of band. WASM has no such rule, so this
profile adds one: the expected digest is pinned in `artifact.json`, the bytes are
compared against it, and only a matching module is handed to Wasmtime.

Without this the two sides are not comparable — one would be judged on an
identity check the other was never given. With it, the remaining difference is
where the check lives: normative in Book I, a profile wrapper here. That belongs
in the trusted-computing-base metrics, not in a kill criterion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import wasmtime

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / "artifact.json").read_text())


class ArtifactMismatch(Exception):
    pass


def configured_engine() -> wasmtime.Engine:
    config = wasmtime.Config()
    config.consume_fuel = True
    config.wasm_simd = False
    config.wasm_relaxed_simd = False
    config.wasm_threads = False
    config.wasm_reference_types = False
    config.wasm_bulk_memory = False
    config.cranelift_opt_level = "speed"
    return wasmtime.Engine(config)


def load_verified(engine: wasmtime.Engine, raw: bytes | None = None,
                  expected: str | None = None) -> wasmtime.Module:
    """Refuse before executing anything if the bytes are not the pinned artifact."""
    raw = (HERE / PIN["file"]).read_bytes() if raw is None else raw
    expected = expected or PIN["sha256"]
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise ArtifactMismatch(f"artifact is {digest[:16]}…, expected {expected[:16]}…")
    module = wasmtime.Module(engine, raw)
    if module.imports:
        raise ArtifactMismatch("the module declares imports")
    return module
