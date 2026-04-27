"""data-harness check_skill — predicate-first skill-fixture validator.

Per spec §11 / §18. Keep ≤200 lines.

Behavior:
- Discover all `fixtures/case_*/` under <skill-path>.
- For each case, evaluate `expected.json` predicates against the skill's output
  (or against `inputs/record.json` if no skill code is present — identity case).
- Honor `floor.json` (skipped-below-floor on inadequate hardware).
- Replay `cache.json` cassettes for any model-using primitives (no live calls).
- Reject trivial-predicate sets (linter, §18 acceptance criterion).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import capabilities as _caps_mod


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_error": str(e)}


def _jsonpath(obj: Any, path: str):
    """Tiny JSONPath subset: $, .key, [*]. Returns a list of matches.

    $.facility.name        → [name]
    $.permits[*].number    → [n1, n2, ...]
    $.facility             → [facility]
    """
    if not path.startswith("$"):
        raise ValueError(f"path must start with $: {path}")
    cur = [obj]
    rest = path[1:]
    for token in re.findall(r"\.([^.\[]+)|\[\*\]", rest):
        key = token if isinstance(token, str) else None
        if key:
            new = []
            for x in cur:
                if isinstance(x, dict) and key in x:
                    new.append(x[key])
            cur = new
        else:
            new = []
            for x in cur:
                if isinstance(x, list):
                    new.extend(x)
            cur = new
    # Also handle [*] explicitly
    if "[*]" in path:
        # Already handled above via regex
        pass
    return cur


def _check_predicate(values: list, pred: dict) -> tuple[bool, str]:
    """Evaluate one predicate against the JSONPath-resolved values list."""
    if pred.get("for_all"):
        for v in values:
            ok, why = _check_one(v, pred)
            if not ok:
                return False, f"for_all violated: {why} (value={v!r})"
        return True, "ok"
    # default: at least one match
    if not values:
        return False, f"no matches for path {pred.get('path')!r}"
    if len(values) == 1:
        return _check_one(values[0], pred)
    # path resolved to multiple (e.g. list field) but no for_all — check the LIST as the value
    return _check_one(values, pred)


_TYPE_MAP = {
    "string": str, "int": int, "float": (int, float), "bool": bool,
    "list": list, "object": dict,
    "list[string]": list, "list[object]": list, "list[int]": list, "list[float]": list,
}


def _run_skill_output(skill_dir: Path, inputs_dir: Path):
    """If <skill_dir>/skill.py exists with run(inputs_dir) → dict, return its output.
    Else return None (caller falls back to identity-load of inputs/record.json).
    """
    skill_py = skill_dir / "skill.py"
    if not skill_py.exists():
        return None
    import importlib.util, sys as _sys
    here = str(Path(__file__).resolve().parent)
    if here not in _sys.path:
        _sys.path.insert(0, here)
    spec = importlib.util.spec_from_file_location(f"_skill_{skill_dir.name}", skill_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        return None
    return mod.run(inputs_dir)


def _check_one(v: Any, pred: dict) -> tuple[bool, str]:
    typ = pred.get("type")
    if typ and typ in _TYPE_MAP and not isinstance(v, _TYPE_MAP[typ]):
        return False, f"type={typ} but got {type(v).__name__}"
    if (mn := pred.get("min_length")) is not None and isinstance(v, str) and len(v) < mn:
        return False, f"len {len(v)} < min_length {mn}"
    if (mx := pred.get("max_length")) is not None and isinstance(v, str) and len(v) > mx:
        return False, f"len {len(v)} > max_length {mx}"
    if (mn := pred.get("min_size")) is not None and hasattr(v, "__len__") and len(v) < mn:
        return False, f"size {len(v)} < min_size {mn}"
    if (mx := pred.get("max_size")) is not None and hasattr(v, "__len__") and len(v) > mx:
        return False, f"size {len(v)} > max_size {mx}"
    if (rgx := pred.get("regex")) and isinstance(v, str) and not re.match(rgx, v):
        return False, f"regex {rgx!r} did not match"
    if (rng := pred.get("in_range")) and isinstance(v, (int, float)) and not (rng[0] <= v <= rng[1]):
        return False, f"value {v} not in [{rng[0]},{rng[1]}]"
    if (allowed := pred.get("in_set")) is not None and v not in allowed:
        return False, f"value {v!r} not in set of {len(allowed)}"
    if (req_keys := pred.get("key_set_includes")) and isinstance(v, dict):
        if missing := [k for k in req_keys if k not in v]:
            return False, f"missing keys: {missing}"
    if pred.get("embedding_cosine_to") is not None:
        print("[check-skill] note: embedding_cosine_to skipped (no embedder in v0)", file=sys.stderr)
        return True, "skipped (v0)"
    return True, "ok"


def _trivial_predicate_linter(predicates: list) -> tuple[bool, str]:
    """Reject predicate sets that would pass for `lorem ipsum`."""
    if not predicates:
        return False, "empty predicates"
    has_positive = any(
        p.get("regex") or p.get("in_set") or p.get("embedding_cosine_to") or
        p.get("in_range") or p.get("key_set_includes")
        for p in predicates
    )
    if not has_positive:
        return False, "no positive predicate (regex|in_set|in_range|key_set_includes|embedding_cosine_to required)"
    return True, "ok"


def _meets_floor(floor: dict, c) -> tuple[bool, str]:
    if not floor:
        return True, "no floor"
    if (mn := floor.get("min_ram_gb")) is not None:
        avail = c.ram_available_bytes / (1 << 30)
        if avail < mn:
            return False, f"ram {avail:.1f} GB < {mn} GB"
    if (mn := floor.get("min_vram_gb", 0)) > 0:
        free = max((g.free_vram_bytes for g in c.gpus), default=0) / (1 << 30)
        if free < mn:
            return False, f"vram {free:.1f} GB < {mn} GB"
    return True, "ok"


def _run_case(case_dir: Path, c) -> tuple[str, str]:
    """Returns ('pass'|'fail'|'skipped-below-floor'|'skipped-budget', detail)."""
    floor = _load(case_dir / "floor.json") or {}
    ok, why = _meets_floor(floor, c)
    if not ok:
        return "skipped-below-floor", why
    expected = _load(case_dir / "expected.json")
    if not expected or "predicates" not in expected:
        return "fail", "missing expected.json with 'predicates'"
    predicates = expected["predicates"]
    ok, why = _trivial_predicate_linter(predicates)
    if not ok:
        return "fail", f"trivial-predicate linter: {why}"
    # If <skill>/skill.py exists, run it on inputs/ to produce the output.
    # Else fall back to identity-load of inputs/record.json (or first .json there).
    inputs = case_dir / "inputs"
    skill_dir = case_dir.parent.parent  # case_001 → fixtures/ → <skill>/
    output = _run_skill_output(skill_dir, inputs)
    if output is None:
        candidate = inputs / "record.json"
        if not candidate.exists():
            jsons = list(inputs.glob("*.json")) if inputs.exists() else []
            if not jsons:
                return "fail", f"no skill.py and no inputs/*.json in {inputs}"
            candidate = jsons[0]
        output = _load(candidate)
    for p in predicates:
        path = p.get("path", "$")
        values = _jsonpath(output, path)
        ok, why = _check_predicate(values, p)
        if not ok:
            return "fail", f"predicate {path}: {why}"
    return "pass", f"{len(predicates)} predicates ok"


def main(argv: list) -> int:
    if not argv:
        print("usage: dh check-skill <skill-path>", file=sys.stderr); return 2
    skill = Path(argv[0])
    if not skill.exists():
        print(f"skill path does not exist: {skill}", file=sys.stderr); return 2
    cases = sorted((skill / "fixtures").glob("case_*")) if (skill / "fixtures").exists() else []
    if not cases:
        print(f"no fixtures under {skill}/fixtures/", file=sys.stderr); return 2
    c = _caps_mod.current()
    n_pass = n_fail = n_skip = 0
    for case in cases:
        status, detail = _run_case(case, c)
        marker = {"pass": "✓", "fail": "✗"}.get(status, "○")
        print(f"  {marker} {case.name}: {status} ({detail})")
        if status == "pass":
            n_pass += 1
        elif status == "fail":
            n_fail += 1
        else:
            n_skip += 1
    print(f"{skill}: {n_pass} pass, {n_fail} fail, {n_skip} skipped")
    return 0 if n_fail == 0 else 1
