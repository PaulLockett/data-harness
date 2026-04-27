"""dh caps — pretty-print Capabilities snapshot. Subcommand of run.py.

`uv run dh caps` is the canonical install smoke test — it prints the
typed Capabilities snapshot for the current host (regime, CPU/RAM/GPU,
network, scratch dir, declared profile overrides). If this prints a
sensible block, the installation is alive.

`uv run dh caps --dry-run-resolve <skill-path>` walks the skill's
declared `floor.json` against the live Capabilities + walks each
required model primitive through `models.resolve` WITHOUT consuming
compute, reporting `(picked, fits, reason)` per primitive — useful
for verifying a fixture would run on this host before paying the cost.
"""
from __future__ import annotations

import json
import sys

import capabilities as _caps_mod


def _format(c: "_caps_mod.Capabilities") -> str:
    cpu_extra = ""
    if c.cpu_apple_p_cores or c.cpu_apple_e_cores:
        cpu_extra = f"  P={c.cpu_apple_p_cores} E={c.cpu_apple_e_cores}"
    lines = [
        "data-harness Capabilities",
        f"  regime              {c.regime}",
        f"  cpu                 {c.cpu_logical} logical / {c.cpu_physical} physical ({c.arch}, {c.os}){cpu_extra}",
        f"  cpu_load_1m         {c.cpu_load_1m:.2f}",
        f"  ram                 {c.ram_available_bytes / 1e9:.1f} GB available / {c.ram_total_bytes / 1e9:.1f} GB total",
        f"  has_gpu             {c.has_gpu}",
    ]
    for g in c.gpus:
        lines.append(
            f"    gpu               {g.name}  "
            f"free={g.free_vram_bytes/1e9:.1f} GB / total={g.total_vram_bytes/1e9:.1f} GB "
            f"({g.backend.value})"
        )
    if c.network:
        bw = c.network.measured_bandwidth_MBps
        bw_str = f"{bw:.1f} MB/s" if bw else "unmeasured"
        lines.append(f"  network             online={c.network.online}  egress_allowed={c.network.egress_allowed}  bandwidth={bw_str}")
    lines.append(f"  in_container        {c.in_container}")
    lines.append(f"  in_ci               {c.in_ci}")
    lines.append(f"  on_battery          {c.on_battery}")
    lines.append(f"  is_shared           {c.is_shared}")
    lines.append(f"  is_offline          {c.is_offline}")
    if c.scratch_mount:
        lines.append(f"  scratch_dir         {c.scratch_mount.path} (free={c.scratch_mount.free_bytes/1e9:.1f} GB)")
    lines.append(f"  hf_cache_size       {(c.hf_cache_size_bytes or 0) / 1e9:.2f} GB")
    if c.declared:
        keys = [k for k in c.declared.keys() if not k.startswith("_")][:8]
        lines.append(f"  declared_profile    keys: {keys}")
    return "\n".join(lines)


def main(argv: list) -> int:
    if argv and argv[0] == "--dry-run-resolve":
        if len(argv) < 2:
            print("usage: dh caps --dry-run-resolve <skill-path>", file=sys.stderr); return 2
        from models import dry_run_resolve
        rows = dry_run_resolve(argv[1:])
        print(json.dumps(rows, indent=2))
        return 0
    if argv and argv[0] == "--json":
        try:
            from daemon import _caps_to_dict
        except Exception as e:
            print(f"failed to import daemon: {e}", file=sys.stderr); return 1
        c = _caps_mod.detect()
        print(json.dumps(_caps_to_dict(c), indent=2, default=str))
        return 0
    c = _caps_mod.detect()
    print(_format(c))
    return 0
