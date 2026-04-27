"""dh models — list / which / pull / clear local model weights.

Thin scaffolding around `models.RESOLVE_TABLE`: `list` shows every
primitive's resolve chain across all regimes, `which <primitive>`
prints the model that would resolve right now under the current
Capabilities. `pull` and `clear` are NotImplemented until the first
model-using skill lands real HF downloads (gated by
`helpers.should_download` against the live deadline + budget).
"""
from __future__ import annotations

import json
import sys

import capabilities as _caps_mod
from models import RESOLVE_TABLE


def main(argv: list) -> int:
    if not argv:
        print("usage: dh models {which|list|pull|clear} [args...]", file=sys.stderr); return 2
    op = argv[0]
    if op == "list":
        for prim, regimes in RESOLVE_TABLE.items():
            print(f"{prim}:")
            for regime, chain in regimes.items():
                print(f"  {regime}: {chain}")
        return 0
    if op == "which":
        if len(argv) < 2:
            print("usage: dh models which <primitive>", file=sys.stderr); return 2
        prim = argv[1]
        c = _caps_mod.detect()
        chain = RESOLVE_TABLE.get(prim, {}).get(c.regime, [])
        if not chain:
            print(f"no chain entry for primitive={prim} regime={c.regime}", file=sys.stderr); return 1
        print(json.dumps({"primitive": prim, "regime": c.regime, "chain": chain, "picked": chain[0]}, indent=2))
        return 0
    if op == "pull":
        print("dh models pull: not yet implemented. Use cassette replay (cache.json per fixture) for now.", file=sys.stderr)
        return 1
    if op == "clear":
        print("dh models clear: not yet implemented (no models pulled — green path is foundation-model-free).", file=sys.stderr)
        return 1
    print(f"unknown models op: {op}", file=sys.stderr); return 2
