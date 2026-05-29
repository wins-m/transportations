# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal travel-history visualizer. A spreadsheet of trips (`data/transport_record.xlsx`)
is geocoded and transformed into JSON, then injected into a Leaflet map template. The committed
`index.html` is the published artifact — a self-contained interactive map (route lines, popups,
legend/control panel, grouping by year & type, heatmap layers).

The source spreadsheet and all place names are in **Chinese**. The relevant `Sheet1` columns are:
`类型` (category), `乘坐区间` (segment as `"start-end"`), `始发站`/`终到站` (origin/terminal station),
`日期` (date), `车次` (vehicle no.), `时间` (time range), `区间里程` (distance), `座位号` (seat),
`票价` (price), `备注` (note).

## Commands

```sh
pip install -r scripts/requirements.txt   # pandas, numpy, openpyxl, PyYAML, requests, beautifulsoup4

# Full pipeline: xlsx -> configs JSON -> incoming.html (defaults shown in main.py --help)
python3 scripts/main.py

# Helpers (standalone)
python3 scripts/calc.py                          # uses cal_duration() over the spreadsheet
python3 scripts/coords_search.py                 # one-off Amap geocode lookup (edit keyword in file)
```

After running `main.py`, review the generated `./incoming.html`, then publish:

```sh
mv incoming.html index.html
git commit -am "update <date>" && git push
```

`incoming.html` is gitignored; `index.html` is the tracked, published output.

There is no test suite, linter, or build config. The scripts' shebangs are `#!/usr/bin/env python3`,
but invoking them explicitly with `python3` (or an activated venv) is still recommended. The default
`--src`, `--tamp`, etc. paths are relative to the **repo root**, so run from there.

## Pipeline architecture

`scripts/main.py` runs two stages in order:

### 1. `convert_coords_and_segments` (`scripts/convert.py`)
- Reads the Excel via `pd.read_excel(..., sheet_name='Sheet1', skipfooter=4).iloc[::-1]` — the last
  4 rows are dropped and **row order is reversed** (spreadsheet is newest-first; output is
  chronological).
- For each row, `cache_coords()` geocodes the origin/terminal. `_decide_trans_kind` maps `类型`
  into one of three buckets — `Railway` (铁路), `Airline` (飞机), `Other` (公路/水路/自行车/其他) —
  and coordinates are cached per-bucket in **`configs/coords/{railway,airline,other}.yaml`**. A
  location absent from its YAML cache is looked up via the **Amap (高德) geocoding REST API**
  (`scripts/coords_search.py::get_coordinates`) and written back to the YAML. Locations the API
  can't resolve are printed and skipped.
- `_mod1`/`_mod2` normalize raw place strings into Amap-friendly keywords (appending `站` / `机场` /
  `航站楼`, handling airport `T<n>` terminals, English `Station` suffixes). The normalized name
  becomes the key used everywhere downstream, so route endpoints must match `locCoords` keys exactly.
- Outputs: `configs/locCoords.json` (name → `[lat, lon]`) and `configs/travelSegments.json` (one
  object per trip: `type/date/from/to/vehicle/time/duration/distance/seat/price/note`, where
  `duration` is derived by `calc.cal_duration`). Rows with `<= 4` populated fields are skipped.

### 2. `update_map_html` (`scripts/update.py`)
- Parses the template HTML with BeautifulSoup, locates the single `<script>` that defines both
  `const locCoords` and `const travelSegments`, and **regex-replaces those two JS literal blocks**
  with the freshly generated JSON. Writes the result to `incoming.html`. Default template is
  `templates/map_heat16_ds.html`.

**Key consequence:** any template you point `--tamp` at must already contain `const locCoords = {…};`
and `const travelSegments = […];` (in one `<script>`) for the replacement to work. The map's
behavior/UI lives entirely in that template's JS — editing visuals means editing the template (or
`index.html`), not the Python. The default template renders route lines, station popups, a legend,
a year/type filter, a travel-stats panel (bottom-left), and an optional heatmap toggle (the
`leaflet.heat` plugin is loaded from a CDN and degrades gracefully if unavailable).

## Conventions & gotchas

- **Amap API key required for new locations.** `cache_coords` reads `conf['amap_api']` from
  `./scripts/configs.yaml`, which is **gitignored** (`**/configs.yaml`) and not in the repo. Geocoding
  (and therefore a clean `main.py` run that encounters an uncached place) needs this file. If every
  place is already in the `configs/coords/*.yaml` caches, no API call — and no key — is needed.
- **Two coordinate stores, different roles.** `configs/coords/*.yaml` are the per-category geocode
  caches (the source of truth, append-only via the API). `configs/locCoords.json` is the regenerated,
  flattened map of every place used in the current dataset. Don't hand-edit `locCoords.json`; fix the
  YAML cache or the spreadsheet.
- **`templates/map.html` is a legacy standalone prototype** with hardcoded coordinates and routes; it
  is not part of the pipeline. The `*_ds.html` templates are the real ones (richer variants:
  detail/heat/full), and `map_heat16_ds.html` is the current default that produced `index.html`.
- **`README.md` and `python3 scripts/main.py --help` are the authoritative CLI references** — both
  cover the current `--src/--tgt_coords/--tgt_segs/--tamp/--tgt` flags.
- Commits in this repo are dated snapshots (e.g. `update 20260508`); follow that style.
