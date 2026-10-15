# The global atmospheric river transport network

ARTN Atlas: an interactive browser explorer for atmospheric river transport networks (ARTNs): hubs, highways and basins as defined in Braun et al. (2026), *Earth Syst. Dynam.* 17, 695–716.

Everything is computed in the visitor's browser from a compact copy of the AR catalog: the transport matrix, the ε threshold, node strength, divergence, PageRank, edge betweenness (exact Brandes in a Web Worker, checked against `networkx`) and Infomap basins (official WebAssembly build). The site is a set of static files, so it needs no server code.

## Folder layout

```
site/
  index.html          the app (single file)
  data/               compact catalog, about 13 MB in total
    meta.json
    tracks.u32.gz  month.u16.gz  ivt.u16.gz
    cell_<centroid|head>_r<1|2|3>.u16.gz
    regimes.json      monthly ENSO / NAO / blocking phases
tools/
  prep_web_data.py    builds site/data from PIKART_hex.pkl (or the slim .npz)
  prep_regimes.py     builds site/data/regimes.json from the index tables
.github/workflows/
  pages.yml           publishes site/ to GitHub Pages on every push to main
```

## Run it locally

Browsers block `fetch()` for pages opened straight from disk, so serve the folder:

```bash
cd site
python3 -m http.server 8000
# then open http://localhost:8000
```

## Rebuild the data (for example for PIKART v1.1)

```bash
pip install numpy pandas h3
python3 tools/prep_web_data.py /path/to/PIKART_hex.pkl site/data --label "PIKART v1.0 · ERA5"
```

The input needs `time`, `trackid`, `mean_ivt` (magnitude) and `hex_idx_<centroid|head>_res<1|2|3>` columns.

Climate regimes (ONI.txt, NAO_2023.txt, BlockIndex.txt in one folder):

```bash
python3 tools/prep_regimes.py /path/to/indices site/data --y0 1940 --y1 2023
```

ENSO phases follow `classify_sustained_phases` in `Fig4_ARHighways_conditional.py`, including its reading of ONI.txt (the first row, 1950, is skipped there).

With a season or regime filter the app by default picks the AR count threshold whose edge count is closest to the unfiltered network of the same window at ε ("Match edge count"). For ENSO over 1951–2023 this gives 3 (El Niño), 9 (neutral) and 4 (La Niña) ARs, against 3, 9 and 3 in the paper.

## Credits and licence

- Method: Braun et al. (2026), Earth Syst. Dynam. 17, 695–716, https://doi.org/10.5194/esd-17-695-2026
- Data: PIKART v1.0, Vallejo-Bernal et al. (2025), https://doi.org/10.1029/2024JD041869
- Colour maps: Crameri, F., Shephard, G. E. and Heron, P. J. (2020), The misuse of colour in science communication, Nat. Commun. 11, 5444, https://www.fabiocrameri.ch/colourmaps/
- Code: MIT licence (see LICENSE). Derived data in `site/data`: CC BY 4.0.
- Libraries loaded from CDNs: d3 (ISC), topojson-client (ISC), h3-js (Apache-2.0), @mapequation/infomap (GPL-3.0), world-atlas land outlines (Natural Earth, public domain).

`logo/` holds the three logo drafts; `logoB.svg` is used in the header and takes its colours from the page theme.

## Put it online

`site/` can be copied as-is to any static host. With the included workflow, GitHub Pages republishes it automatically after every push to `main` (Settings → Pages → Source: GitHub Actions).
