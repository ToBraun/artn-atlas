"""Convert a hex-gridded AR catalog (ARnetwork's PIKART_hex.pkl) into the compact
binary files the ARTN Atlas web app loads.

Usage
-----
    python prep_web_data.py PIKART_hex.pkl  web/data  --label "PIKART v1.0 · ERA5"
    python prep_web_data.py pikart_slim.npz web/data  --label "PIKART v1.0 · ERA5"

Output (all little-endian, gzip-compressed)
-------------------------------------------
    meta.json                 catalog label, time range, counts, file list
    tracks.u32.gz             start offset of every track in the point arrays (n_tracks + 1)
    month.u16.gz              month index of every point, (year - y0) * 12 + month - 1
    ivt.u16.gz                mean IVT magnitude of every point times ivt_scale (meta.json), rounded
    cell_<loc>_r<res>.u16.gz  H3 cell of every point, as index into the sorted list
                              of all H3 cells at that resolution

Points are sorted by (trackid, time), so consecutive points of one track are the
AR transport events (origin -> destination) used by ARnet_sub.origins_and_destinations.
"""
import argparse, gzip, json, sys
from pathlib import Path
import numpy as np
import h3

LOCATORS = ("centroid", "head")
RESOLUTIONS = (1, 2, 3)


def load(path):
    path = Path(path)
    if path.suffix == ".npz":
        z = np.load(path)
        time = z["time"].astype("datetime64[h]")
        cols = {k: z[k] for k in z.files}
        to_str = lambda a: np.array([format(int(x), "x") for x in a])
        hexcols = {k: to_str(v) for k, v in cols.items() if k.startswith("hex_idx_")}
        return time, cols["trackid"], cols["mean_ivt"], hexcols
    import pandas as pd
    d = pd.read_pickle(path)
    d = d.sort_values(["trackid", "time"], kind="stable").reset_index(drop=True)
    hexcols = {c: d[c].astype(str).values for c in d.columns if c.startswith("hex_idx_")}
    return d["time"].values.astype("datetime64[h]"), d["trackid"].values, d["mean_ivt"].values, hexcols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--label", default="PIKART v1.0 · ERA5")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    time, trackid, ivt, hexcols = load(a.src)
    order = np.lexsort((time, trackid))          # (trackid, time)
    time, trackid, ivt = time[order], trackid[order], ivt[order]
    hexcols = {k: v[order] for k, v in hexcols.items()}

    years = time.astype("datetime64[Y]").astype(int) + 1970
    months = time.astype("datetime64[M]").astype(int) % 12
    y0, y1 = int(years.min()), int(years.max())
    month_idx = ((years - y0) * 12 + months).astype("<u2")
    starts = np.flatnonzero(np.r_[True, trackid[1:] != trackid[:-1]])
    offsets = np.r_[starts, len(time)].astype("<u4")

    def save(name, arr):
        with gzip.open(out / name, "wb", compresslevel=9) as f:
            f.write(np.ascontiguousarray(arr).tobytes())

    save("tracks.u32.gz", offsets)
    save("month.u16.gz", month_idx)
    IVT_SCALE = 50   # store IVT in steps of 0.02 kg m-1 s-1 so class thresholds and edge means match the float catalogue
    assert np.nanmax(ivt) * IVT_SCALE < 65535
    save("ivt.u16.gz", np.clip(np.rint(ivt * IVT_SCALE), 0, 65535).astype("<u2"))

    files = {}
    for res in RESOLUTIONS:
        all_cells = sorted(c for r0 in h3.get_res0_cells() for c in h3.cell_to_children(r0, res))
        lookup = {c: i for i, c in enumerate(all_cells)}
        for loc in LOCATORS:
            col = f"hex_idx_{loc}_res{res}"
            if col not in hexcols:
                print(f"skipping {col}: not in catalog", file=sys.stderr); continue
            idx = np.array([lookup[h] for h in hexcols[col]], dtype="<u2")
            name = f"cell_{loc}_r{res}.u16.gz"; save(name, idx); files[f"{loc}_r{res}"] = name

    meta = dict(label=a.label, y0=y0, y1=y1, n_points=int(len(time)), n_tracks=int(len(starts)),
                locators=list(LOCATORS), resolutions=list(RESOLUTIONS), cells=files,
                tracks="tracks.u32.gz", month="month.u16.gz", ivt="ivt.u16.gz", ivt_scale=IVT_SCALE)
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
