# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal travel-history visualizer. A spreadsheet of trips (`data/transport_record.xlsx`)
is processed into JSON config and rendered onto an interactive Leaflet map. The committed
`index.html` is the published artifact (a self-contained map served e.g. via GitHub Pages).

The source spreadsheet and all place names use **Chinese column headers and labels**. Key
columns in the record: `出发地` (from), `到达地` (to), `日期` (date), `方式` (transport type),
`备注` (note).

## Commands

All scripts assume they are run **from the repo root** — default paths are relative (`./data/...`,
`./configs/...`). `scripts/` has no package entry beyond an empty `__init__.py`; the scripts
import each other by bare module name, so run them from inside `scripts/` OR rely on the default
invocation below.

```sh
pip install -r scripts/requirements.txt   # pandas, openpyxl, pyyaml

# Full pipeline: xlsx -> configs JSON -> incoming.html
./scripts/main.py                          # uses defaults; see flags with --help

# Helpers (standalone, run from repo root)
python3 scripts/calc.py                    # total trip distance (haversine over segments)
python3 scripts/coords_search.py <place>   # look up [lat, lon] via OSM Nominatim
```

After running `main.py`, review the generated `./incoming.html`, then publish:

```sh
mv incoming.html index.html
git commit -am "update <date>" && git push
```

`incoming.html` is gitignored; `index.html` is the tracked output.

There is no test suite, linter, or build config in this repo.

## Pipeline architecture

`scripts/main.py` orchestrates four steps (see `convert.py` and `update.py`):

1. **`load_transport_record(src)`** — reads the Excel file into a pandas DataFrame, stripping
   column names.
2. **`generate_location_coordinates(records, tgt_coords)`** — collects every unique place from
   `出发地`/`到达地` and merges them into `configs/locCoords.json`. This file is **append-only /
   preserved across runs**: existing coordinates are kept, and any new place is added with a
   `[null, null]` placeholder. The function prints which places still need coordinates.
3. **`generate_travel_segments(records, tgt_segs)`** — rewrites `configs/travelSegments.json` as a
   flat list of `{from, to, date, type, note}` objects (one per spreadsheet row).
4. **`update_html(...)`** — loads both JSON files, **drops any location whose coordinate is null**,
   then injects the data into the template by string-replacing the `/*LOC_COORDS*/` and
   `/*TRAVEL_SEGMENTS*/` placeholders in `templates/map.html`. The rendered file is written to
   `incoming.html`.

The critical consequence: **a trip will silently not render until its endpoints have real
coordinates in `locCoords.json`.** The normal loop is: run `main.py`, read the "needs coordinates"
output, fill the `[null, null]` entries (manually or with `coords_search.py`), and re-run.

## Conventions & gotchas

- **Template injection is comment-placeholder based.** Any template used with `update.py` must
  contain the literal tokens `/*LOC_COORDS*/` and `/*TRAVEL_SEGMENTS*/`. `templates/map.html` is
  the default minimal template. The other `templates/*_ds.html` files are richer variants
  (control panel, group-by-year/type, popups, heatmaps) used to produce the current `index.html`;
  switch templates with `--tamp`.
- **`configs/coords/*.yaml` are NOT part of the pipeline.** They are manually maintained reference
  coordinate banks grouped by transport category (`铁路` railway, `airline`, `other`). No script
  imports `yaml` — `pyyaml` in requirements is currently unused by code. Treat these as a lookup
  resource, not pipeline input.
- **Data hygiene matters in `方式` (type) values.** The source data contains inconsistencies such as
  trailing spaces (`"飞机 "`) and synonyms (`驾车` vs `自驾`). Anything that groups or colors by type
  should normalize these.
- **Known bug:** `scripts/main.py` declares the `--tgt` argument (and `parser.parse_args()`) twice,
  which makes argparse raise `ArgumentError` and the script fails on launch. Fix the duplicate
  before relying on `main.py`.
