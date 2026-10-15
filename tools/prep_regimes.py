"""Turn monthly climate-index tables into regime labels for the ARTN Atlas.

Usage
-----
    python prep_regimes.py  path/to/indices  site/data  --y0 1940 --y1 2023

Reads ONI.txt, NAO_2023.txt and BlockIndex.txt (rows: year + 12 monthly values,
-99.9 = missing) and writes regimes.json with one label per month from y0-01 to
y1-12: "+" positive phase, "-" negative phase, "0" neutral, "." no index value.

ENSO follows the classification in Fig4_ARHighways_conditional.py
(classify_sustained_phases): 3-month rolling mean of ONI, z-scored over the
record, |z| > 0.5, and a month counts once the run has lasted 5 months.
NAO and the blocking index use the same z-score and threshold month by month.
"""
import argparse, json
from pathlib import Path
import numpy as np


def read_table(path, skip_first=False, complete_rows=False):
    vals = {}
    lines = Path(path).read_text().splitlines()
    if skip_first:
        lines = lines[1:]   # mirrors read_csv(..., skiprows=1) in the Fig. 4 script, which drops 1950 from the headerless ONI.txt
    for line in lines:
        parts = line.split()
        if not parts or not parts[0].lstrip("-").isdigit():
            continue                                  # header lines such as "Year x1 x2 ..."
        if complete_rows and any(float(v) <= -99 for v in parts[1:13]):
            continue                                  # the Fig. 4 script drops rows that contain -99.90
        year = int(parts[0])
        for m, v in enumerate(parts[1:13]):
            x = float(v)
            if x > -99:
                vals[(year, m)] = x
    return vals


def sustained(cond, min_periods):
    """Mirror of classify_sustained_phases: True from the min_periods-th month of a run on."""
    out = np.zeros(len(cond), bool); run = 0
    for i, c in enumerate(cond):
        run = run + 1 if c else 0
        out[i] = run >= min_periods
    return out


def labels(vals, y0, y1, rolling, thresh, min_periods):
    keys = sorted(vals)
    series = np.array([vals[k] for k in keys])
    if rolling > 1:   # pandas rolling(window, min_periods=window).mean(), labelled at the window end
        series = np.array([np.nan] * (rolling - 1) + list(np.convolve(series, np.ones(rolling) / rolling, "valid")))
    z = (series - np.nanmean(series)) / np.nanstd(series)
    pos = sustained(np.nan_to_num(z, nan=0) > thresh, min_periods)
    neg = sustained(np.nan_to_num(z, nan=0) < -thresh, min_periods)
    lab = {k: ("." if np.isnan(z[i]) else "+" if pos[i] else "-" if neg[i] else "0") for i, k in enumerate(keys)}
    s = "".join(lab.get((y, m), ".") for y in range(y0, y1 + 1) for m in range(12))
    covered = [k[0] for k in keys]
    return s, [max(y0, min(covered)), min(y1, max(covered))]


INDICES = [
    dict(key="enso", file="ONI.txt", name="ENSO (ONI)", pos="El Niño", neg="La Niña", rolling=3, thresh=0.5, min_periods=5, skip_first=True, complete_rows=True,
         method="ONI, 3-month mean, z-score beyond ±0.5 for at least 5 months (as in Braun et al. 2026, Fig. 4)"),
    dict(key="nao", file="NAO_2023.txt", name="NAO", pos="NAO+", neg="NAO−", rolling=1, thresh=0.5, min_periods=1,
         method="Monthly NAO index, z-score beyond ±0.5"),
    dict(key="block", file="BlockIndex.txt", name="Blocking index", pos="Blocked", neg="Unblocked", rolling=1, thresh=0.5, min_periods=1,
         method="Monthly blocking index, z-score beyond ±0.5"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("indir"); ap.add_argument("out")
    ap.add_argument("--y0", type=int, default=1940); ap.add_argument("--y1", type=int, default=2023)
    a = ap.parse_args()
    res = []
    for spec in INDICES:
        p = Path(a.indir) / spec["file"]
        if not p.exists():
            print("missing", p); continue
        s, cov = labels(read_table(p, spec.get("skip_first", False), spec.get("complete_rows", False)), a.y0, a.y1, spec["rolling"], spec["thresh"], spec["min_periods"])
        res.append(dict(key=spec["key"], name=spec["name"], pos=spec["pos"], neg=spec["neg"], method=spec["method"],
                        coverage=cov, labels=s))
        print(spec["name"], cov, {c: s.count(c) for c in "+0-."})
    Path(a.out, "regimes.json").write_text(json.dumps(dict(y0=a.y0, y1=a.y1, indices=res)))


if __name__ == "__main__":
    main()
