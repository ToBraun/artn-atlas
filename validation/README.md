# Validation of the ARTN Atlas against the ARnetlab code

Run on 16 Oct 2026. The report with all results is the doc "ARTN Atlas: scientific validation".

- `refnet.py` builds reference networks with `ARnet_sub.py` / `NETanalysis_sub.py` from `artn_scripts/ARnetlab`
  (copy both next to it, plus `h3shim.py`, which maps the h3 v3 names those modules use onto h3 v4).
  Only `origins_and_destinations` is replaced by a vectorised copy with the same rule.
- `browser.py` runs `site/index.html` headless (Playwright) and exports networks, PageRank, betweenness and Infomap
  results by H3 cell.
- `compare1.py` construction, node measures, IVT classes, betweenness · `compare2.py` time window, seasons, ENSO ·
  `compare3.py` Infomap basins · `compare4.py` Infomap link flows and flow ratios · `pr_check*.py` PageRank
  convergence · `hist_check*.py` highway-latitude trends vs scipy · `shots.py` + `sbs.py` paper/app figure pairs.
- `results/` holds the JSON outputs, `figures/` the side-by-side images.
