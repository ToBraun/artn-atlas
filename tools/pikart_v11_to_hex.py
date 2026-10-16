# Copyright (C) 2026 by
# Tobias Braun
"""
Regrid the PIKART V1.1 Lagrangian AR catalogue (ERA5, 0.5 deg, 6-hourly, one
NetCDF file per year) onto H3 hexagons, as was done for PIKART_hex.pkl (v1.0).

Writes to OUT_DIR
    PIKART_V1.1_ERA5_hex.pkl    full catalogue + hex columns (same layout as PIKART_hex.pkl)
    PIKART_V1.1_ERA5_slim.npz   only what the ARTN Atlas needs (prep_web_data.py reads it;
                                plain numpy, so no pandas pickle-version issues off the HPC)

Usage on the HPC
    python pikart_v11_to_hex.py --inspect     # print the layout of one yearly file and stop
    python pikart_v11_to_hex.py               # full run
Paths can be overridden with PIKART_DIR / ARNET_OUT.
"""
import os, sys, glob, argparse
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import h3

# ------------------------------------------------------------------ PATHS
IN_DIR   = Path(os.environ.get("PIKART_DIR", "/p/projects/climxtreme/data/PIKART/ERA5/0p5deg_6hr/PIKART_V1.1_lagrangian"))
OUT_DIR  = Path(os.environ.get("ARNET_OUT",  "/p/projects/climxtreme/braun/ARnet"))
PATTERN  = "PIKART_V1.1_lagrangian_ERA5_0p5deg_6hr_*.nc"
OUT_PKL  = OUT_DIR / "PIKART_V1.1_ERA5_hex.pkl"
OUT_NPZ  = OUT_DIR / "PIKART_V1.1_ERA5_slim.npz"

# ------------------------------------------------------------------ PARAMETERS
LOCATORS    = ["centroid", "head", "core"]
RESOLUTIONS = range(0, 5)        # 0-4 as in PIKART_hex.pkl (v1.0); the Atlas uses 1-3
WEB_RES     = (1, 2, 3)
DROP_PREFIX = ("insu_", "conti_")
DROP_COLS   = {"contour_lon", "contour_lat", "axis_lon", "axis_lat"}

# h3 v3 and v4 have different function names; the cells are identical
if hasattr(h3, "latlng_to_cell"):
    to_cell, to_latlng = h3.latlng_to_cell, h3.cell_to_latlng
else:
    from h3 import h3 as _h3
    to_cell, to_latlng = _h3.geo_to_h3, _h3.h3_to_geo


def locator_cols(loc):
    return f"{loc}_lon", f"{loc}_lat"


# ------------------------------------------------------------------ LOAD
# V1.1 Lagrangian files are gridded: (time, trackid[, coordinate|component]), NaN where a track is not active.
# coordinate = (lat, lon) [degrees_north, degrees_east]; component = (magnitude, zonal, meridional).
POINT_VARS = {"centroid": "centroid", "head": "head", "tail": "tail", "core_loc": "core", "lf_loc": "lf"}
VECTOR_VARS = {"mean_ivt": ("mean_ivt", "mean_ivtu", "mean_ivtv"), "core_ivt": ("core_ivt", "core_ivtu", "core_ivtv")}
SKIP = {"footprints", "contour", "axis"}


def load_year(f):
    """One yearly file -> DataFrame with one row per active (time, trackid), column names as in PIKART_hex.pkl v1.0."""
    ds = xr.open_dataset(f)
    if ds["centroid"].dims != ("time", "trackid", "coordinate"):
        sys.exit(f"{f.name}: unexpected layout {ds['centroid'].dims}")
    cen = ds["centroid"].values
    t, k = np.nonzero(np.isfinite(cen).all(-1))                 # active AR steps
    out = {"time": ds["time"].values[t], "trackid": ds["trackid"].values[k].astype(np.int64)}
    for v in ds.data_vars:
        if v in SKIP or v.startswith(DROP_PREFIX):
            continue
        x, dims = ds[v], ds[v].dims
        if v in POINT_VARS:
            a = x.values[t, k]
            out[POINT_VARS[v] + "_lat"], out[POINT_VARS[v] + "_lon"] = a[:, 0], a[:, 1]
        elif v in VECTOR_VARS:
            a = x.values[t, k]
            for i, name in enumerate(VECTOR_VARS[v]): out[name] = a[:, i]
        elif dims == ("time", "trackid"):
            a = x.values[t, k]
            out[v] = np.char.decode(a, "utf-8") if a.dtype.kind == "S" else a
        elif dims == ("trackid",):
            out[v] = x.values[k]
        # anything else (land masks, ...) is not per AR step and is left out
    ds.close()
    return pd.DataFrame(out)


def load_all(files):
    parts, prev = [], None
    for f in tqdm(files, desc="reading"):
        d = load_year(f)
        d["src_year"] = int(f.stem.split("_")[-1])
        # track IDs must be unique across files; a shared ID is only fine if it is the same
        # AR continuing across New Year (last step of one file, first step of the next)
        if prev is not None:
            shared = np.intersect1d(prev["trackid"].unique(), d["trackid"].unique())
            if len(shared):
                last = prev[prev.trackid.isin(shared)].groupby("trackid").time.max()
                first = d[d.trackid.isin(shared)].groupby("trackid").time.min()
                gap = (first - last.reindex(first.index))
                bad = gap[(gap <= pd.Timedelta(0)) | (gap > pd.Timedelta("24h"))]
                if len(bad) > 0.1 * len(shared):
                    sys.exit(f"{f.name}: {len(bad)} of {len(shared)} track IDs shared with the previous year are not "
                             f"continuations (e.g. {list(bad.index[:5])}). IDs seem to restart per file.")
                if len(bad):
                    print(f"  WARNING {f.name}: {len(bad)} shared IDs with gap <=0 or >24 h across New Year: {bad.head().to_dict()}")
                print(f"  {len(shared)} tracks continue from {prev.src_year.iat[0]} into {d.src_year.iat[0]}")
        parts.append(d); prev = d
    return pd.concat(parts, ignore_index=True)


# ------------------------------------------------------------------ CHECKS
def check(cat):
    need = ["time", "trackid", "mean_ivt"] + [c for l in LOCATORS for c in locator_cols(l)]
    miss = [c for c in need if c not in cat.columns]
    if miss:
        sys.exit(f"Missing columns {miss}.\nAvailable: {list(cat.columns)}\n"
                 "If they are only renamed, add a rename mapping after loading.")
    cat["time"] = pd.to_datetime(cat["time"])
    n0 = len(cat)
    cat.drop_duplicates(["trackid", "time"], inplace=True)
    if len(cat) < n0:
        print(f"  dropped {n0 - len(cat)} duplicate (trackid, time) rows (overlap between files?)")
    cat.sort_values(["trackid", "time"], kind="stable", inplace=True, ignore_index=True)

    for l in LOCATORS:
        x, y = locator_cols(l)
        nan = int(cat[[x, y]].isna().any(axis=1).sum())
        print(f"  {l:8s} lon [{cat[x].min():.2f}, {cat[x].max():.2f}]  lat [{cat[y].min():.2f}, {cat[y].max():.2f}]  NaN rows: {nan}")
        if nan and l in ("centroid", "head"):
            sys.exit(f"{nan} rows without {l} position. Dropping them would join non-consecutive steps "
                     "into false transport links, so this needs a decision first.")
    dt = cat.groupby("trackid").time.diff().dropna()
    print("  time steps within tracks (v1.0: 6 h, ~3 % 12 h):")
    print((dt.value_counts(normalize=True).head(5) * 100).round(2).to_string())
    print(f"  {cat.trackid.nunique():,} tracks, {len(cat):,} AR time steps, "
          f"{cat.time.min()} to {cat.time.max()}, hours {sorted(cat.time.dt.hour.unique())}")
    print(f"  mean_ivt [{cat.mean_ivt.min():.1f}, {cat.mean_ivt.max():.1f}] kg m-1 s-1")
    return cat


# ------------------------------------------------------------------ REGRID
def regrid(cat):
    """Hex index and hex-centre coordinates per locator and resolution.
    Vectorised over unique positions (positions sit on the 0.5 deg grid, so there are few)."""
    for loc in LOCATORS:
        x, y = locator_cols(loc)
        lon = ((cat[x].to_numpy(float) + 180) % 360) - 180      # [0, 360) -> [-180, 180)
        lat = cat[y].to_numpy(float)
        pts, inv = np.unique(np.c_[lat, lon], axis=0, return_inverse=True)
        inv = inv.ravel()
        for res in tqdm(RESOLUTIONS, desc=loc):
            cells = np.array([to_cell(a, b, res) for a, b in pts], dtype=object)
            cen = np.array([to_latlng(c) for c in cells])
            cat[f"hex_idx_{loc}_res{res}"] = cells[inv]
            cat[f"hex_{loc}_lat_res{res}"] = cen[inv, 0]
            cat[f"hex_{loc}_lon_res{res}"] = cen[inv, 1]
    return cat


def slim(cat):
    out = dict(time=cat.time.values.astype("datetime64[h]").astype(np.int64),
               trackid=cat.trackid.to_numpy(np.int64),
               mean_ivt=cat.mean_ivt.to_numpy(np.float32))
    for loc in LOCATORS:
        for res in WEB_RES:
            out[f"hex_idx_{loc}_res{res}"] = np.array([int(c, 16) for c in cat[f"hex_idx_{loc}_res{res}"]], dtype=np.uint64)
    return out


# ------------------------------------------------------------------ INSPECT
def inspect(files):
    """Everything needed to write the loader: variables, coordinate order, and whether track IDs
    continue across New Year (compares the last step of year 1 with the first step of year 2)."""
    ds = xr.open_dataset(files[0])
    print(ds.attrs.get("comment", ""), "\n")
    for v in ds.variables:
        x = ds[v]
        print(f"{v:22s} {str(x.dims):42s} {str(x.dtype):9s} {x.attrs.get('long_name', '')} [{x.attrs.get('units', '')}]")
        extra = {k: x.attrs[k] for k in x.attrs if k not in ("long_name", "units")}
        if extra: print(f"{'':22s} {extra}")
    for d in ("coordinate", "component"):
        if d in ds.variables: print(d, ds[d].values)
    c = ds["centroid"].isel(time=slice(0, 200)).values           # (time, trackid, coordinate)
    ok = np.isfinite(c).all(-1)
    t, k = np.nonzero(ok)
    print("\nfirst 5 AR steps (time, trackid, centroid[0], centroid[1]):")
    for i in np.lexsort((t, k))[:5]:
        print(" ", ds.time.values[t[i]], int(ds.trackid.values[k[i]]), c[t[i], k[i]])
    print("per track: steps", np.bincount(k).max(), "max;  any track with gaps in time?",
          any(np.ptp(np.nonzero(ok[:, j])[0]) + 1 != ok[:, j].sum() for j in np.unique(k)))
    for var in ("mean_ivt", "ivt"):
        if var in ds: print(var, ds[var].dims, "sample:", np.asarray(ds[var].isel(time=slice(0, 200)).values)[ok][:5])
    if len(files) > 1:
        ds2 = xr.open_dataset(files[1])
        a_ = ds["centroid"].isel(time=-1).values; b_ = ds2["centroid"].isel(time=0).values
        ia = np.flatnonzero(np.isfinite(a_).all(-1)); ib = np.flatnonzero(np.isfinite(b_).all(-1))
        print(f"\nNew Year: {ds.time.values[-1]} has {len(ia)} ARs, {ds2.time.values[0]} has {len(ib)} ARs")
        print("  IDs at end of year 1   :", ds.trackid.values[ia][:15], a_[ia][:3].tolist())
        print("  IDs at start of year 2 :", ds2.trackid.values[ib][:15], b_[ib][:3].tolist())
        print("  trackid range year 1 / year 2:", int(ds.trackid.min()), int(ds.trackid.max()), "/", int(ds2.trackid.min()), int(ds2.trackid.max()))


# ------------------------------------------------------------------ MAIN
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--years", help="e.g. 1940-1942 for a test run")
    a = ap.parse_args()

    files = sorted(Path(p) for p in glob.glob(str(IN_DIR / PATTERN)))
    if a.years:
        y0, y1 = map(int, a.years.split("-"))
        files = [f for f in files if y0 <= int(f.stem.split("_")[-1]) <= y1]
    if not files:
        sys.exit(f"No files matching {IN_DIR / PATTERN}")
    print(f"{len(files)} files: {files[0].name} ... {files[-1].name}")

    if a.inspect:
        inspect(files); sys.exit()

    cat = check(load_all(files))
    cat = regrid(cat)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cat.to_pickle(OUT_PKL)
    np.savez_compressed(OUT_NPZ, **slim(cat))
    print(f"wrote {OUT_PKL} ({OUT_PKL.stat().st_size / 1e6:.0f} MB) and {OUT_NPZ} ({OUT_NPZ.stat().st_size / 1e6:.0f} MB)")
