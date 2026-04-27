"""tess — read TESS light-curve FITS files, build a validated canonical record.

Contract: run(inputs_dir: Path) -> dict.

Inputs (capture-time):
    inputs_dir/_provenance.json   target spec + capture metadata (see SKILL.md)
    inputs_dir/lightcurves/*.fits one or more SPOC light-curve FITS files

Output: a canonical Light-Curve record with target identity, per-file stats, and
a validation rollup that asserts every FITS file's TICID matches the searched
target. The validated boolean is true iff TICID and OBJECT both agree with the
declared target. expected.json predicates assert that rollup is true for_all.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _native(x: Any) -> Any:
    """Cast numpy scalars / NaN to plain Python for JSON-friendliness."""
    if x is None:
        return None
    if isinstance(x, (bytes, bytearray)):
        return x.decode("utf-8", errors="replace")
    try:
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return None
        if hasattr(x, "item"):
            return x.item()
        return f if not float(x).is_integer() else int(x)
    except (TypeError, ValueError):
        pass
    if hasattr(x, "item"):
        try:
            return x.item()
        except Exception:
            pass
    return x


def _hdr(hdr, key: str, default=None) -> Any:
    v = hdr.get(key, default)
    return _native(v) if v is not None else default


def _parse_one(fits_path: Path) -> dict:
    from astropy.io import fits
    import numpy as np

    raw = fits_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]

    with fits.open(str(fits_path)) as hdul:
        prim = hdul[0].header
        lc = hdul[1].data
        cols = list(hdul[1].columns.names)

        tic_id_in_header = str(_hdr(prim, "TICID", "")).strip()
        object_in_header = str(_hdr(prim, "OBJECT", "")).strip()
        sector = _hdr(prim, "SECTOR")
        camera = _hdr(prim, "CAMERA")
        ccd = _hdr(prim, "CCD")
        tessmag = _hdr(prim, "TESSMAG")
        teff = _hdr(prim, "TEFF")
        radius = _hdr(prim, "RADIUS")
        ra_obj = _hdr(prim, "RA_OBJ")
        dec_obj = _hdr(prim, "DEC_OBJ")

        n_cadences = int(len(lc))
        flux_col = "PDCSAP_FLUX" if "PDCSAP_FLUX" in cols else "SAP_FLUX"
        flux = np.asarray(lc[flux_col], dtype=float)
        time_arr = np.asarray(lc["TIME"], dtype=float)
        finite_flux = flux[np.isfinite(flux)]
        finite_time = time_arr[np.isfinite(time_arr)]

        flux_median = float(np.median(finite_flux)) if finite_flux.size else None
        flux_min = float(finite_flux.min()) if finite_flux.size else None
        flux_max = float(finite_flux.max()) if finite_flux.size else None
        time_min = float(finite_time.min()) if finite_time.size else None
        time_max = float(finite_time.max()) if finite_time.size else None
        n_finite_flux = int(finite_flux.size)

    return {
        "filename": fits_path.name,
        "file_path": f"lightcurves/{fits_path.name}",
        "size_bytes": len(raw),
        "sha256_prefix": sha,
        "sector": sector,
        "camera": camera,
        "ccd": ccd,
        "n_cadences": n_cadences,
        "n_finite_flux": n_finite_flux,
        "time_min_bjd": time_min,
        "time_max_bjd": time_max,
        "flux_column": flux_col,
        "pdcsap_flux_median": flux_median,
        "pdcsap_flux_min": flux_min,
        "pdcsap_flux_max": flux_max,
        "tic_id_in_header": tic_id_in_header,
        "object_in_header": object_in_header,
        "_target_block": {
            "tic_id": tic_id_in_header,
            "object_name": object_in_header,
            "tess_mag": tessmag,
            "teff": teff,
            "radius": radius,
            "ra_deg": ra_obj,
            "dec_deg": dec_obj,
            "camera": camera,
            "ccd": ccd,
        },
    }


def run(inputs_dir: Path) -> dict:
    inputs_dir = Path(inputs_dir)
    prov = json.loads((inputs_dir / "_provenance.json").read_text())
    target_tic = str(prov["target_tic"])
    target_aliases = list(prov.get("target_aliases", [])) + [target_tic, f"TIC {target_tic}"]
    target_aliases = sorted(set(a.strip() for a in target_aliases if a))
    url_map = prov.get("lightcurve_urls", {})

    fits_paths = sorted((inputs_dir / "lightcurves").glob("*.fits"))
    if not fits_paths:
        raise RuntimeError(f"no FITS files under {inputs_dir / 'lightcurves'}")

    parsed = [_parse_one(p) for p in fits_paths]

    target_block = parsed[0].pop("_target_block")
    for p in parsed[1:]:
        p.pop("_target_block", None)

    lightcurves = []
    for p in parsed:
        tic_match = p["tic_id_in_header"] == target_tic
        obj_match = any(a.lower() in p["object_in_header"].lower() for a in target_aliases if a)
        validated = bool(tic_match and obj_match and p["n_cadences"] > 100)
        p_out = dict(p)
        p_out["url"] = url_map.get(p["filename"], "")
        p_out["tic_id_match"] = tic_match
        p_out["object_name_match"] = obj_match
        p_out["validated"] = validated
        lightcurves.append(p_out)

    all_validated = all(lc["validated"] for lc in lightcurves)

    return {
        "target": target_block,
        "lightcurves": lightcurves,
        "captured_from": prov.get("captured_from", ""),
        "captured_at_utc": prov.get("captured_at_utc", ""),
        "capture_method": prov.get("capture_method", ""),
        "validation": {
            "all_validated": all_validated,
            "n_lightcurves": len(lightcurves),
            "target_identifiers": target_aliases,
        },
    }
