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
- For each row, `cache_coords()` resolves the origin/terminal in priority order: **(1)
  `configs/coords/manual.yaml`** — hand-pinned WGS-84 overrides, used verbatim and never geocoded
  or shifted; **(2)** the per-bucket geocode cache, where `_decide_trans_kind` maps `类型` into one
  of three buckets — `Railway` (铁路), `Airline` (飞机), `Other` (公路/水路/自行车/其他) — cached in
  **`configs/coords/{railway,airline,other}.yaml`**; **(3)** a fresh geocode for a cache miss, via
  `_geocode`: the **Amap (高德) REST API** first (`coords_search.py::get_coordinates`), then an
  **OpenStreetMap / Nominatim** fallback (`get_coordinates_osm`) for anything Amap can't resolve
  (mostly foreign places). The result is written back to the bucket YAML. Places neither API can
  resolve are printed and skipped.
- **Amap's foreign-miss trap.** For a foreign keyword it can't place, Amap doesn't return an empty
  result — it returns a bogus point **in Beijing**, so a bare `None` check can't catch it. `_geocode`
  therefore cross-checks: any Amap answer inside the Beijing municipality box (`_BEIJING_BOX`) is
  verified against OSM, and if OSM puts the place >80 km away (i.e. it's actually abroad) the OSM
  result is used instead. Genuine Beijing places pass because OSM agrees with Amap on them. If both
  agree it's foreign but OSM can't verify, it warns to pin the point in `manual.yaml`.
- **Datum: Amap returns GCJ-02, the map (and OSM/Nominatim) render WGS-84.** `get_coordinates`
  shifts every Amap result back to WGS-84 via `gcj02_to_wgs84` before returning it, so the
  OSM/Leaflet basemap lines up (raw GCJ-02 lands a few hundred metres off — the "China GPS offset").
  The shift only applies inside China; `out_of_china` leaves foreign points untouched — its box also
  excludes the Indochina peninsula **and Hong Kong/Macau** (lat 22.0–22.58, lng 113.40–114.55, with
  Shenzhen just north of it), all of which Amap already serves in WGS-84. `get_coordinates_osm` and
  `manual.yaml` are native WGS-84 and are never shifted. **Caveat:** Google Maps' road layer inside
  mainland China is *also* GCJ-02-shifted, so coordinates copied from it are not clean WGS-84 — use
  OpenStreetMap (same datum as the basemap) or Google's satellite layer instead.
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

- **Amap API key is optional.** `load_api_keys` reads `conf['amap_api']` from `./scripts/configs.yaml`,
  which is **gitignored** (`**/configs.yaml`) and not in the repo. If it's missing, `load_api_keys`
  returns `None` (no longer raises) and new locations are geocoded via the OpenStreetMap fallback
  only — so the pipeline runs key-free, just with weaker Chinese place-name matching. If every place
  is already cached, no geocoding happens at all.
- **Coordinate stores, by priority.** `configs/coords/manual.yaml` holds hand-pinned WGS-84 overrides
  (highest priority, used verbatim, never geocoded/shifted — the place to fix any point exactly).
  `configs/coords/{railway,airline,other}.yaml` are the per-category geocode caches (append-only via
  the APIs). `configs/locCoords.json` is the regenerated, flattened map of every place in the current
  dataset. Don't hand-edit `locCoords.json`; fix `manual.yaml`, the YAML cache, or the spreadsheet.
- **`templates/map_heat16_ds.html` is the only live template** — the current default that produced
  `index.html`. All other variants (the earlier `map_heat{12,13,15}_ds.html`, `map_ds.html`,
  `map_detail_ds.html`, `fullmap_ds.html`, `map_with_arrows.html`, and the legacy standalone
  `map.html` prototype with hardcoded coords) are **archived under `templates/archive/`** and are not
  part of the pipeline. Point `--tamp` at one only if reviving it.
- **`README.md` and `python3 scripts/main.py --help` are the authoritative CLI references** — both
  cover the current `--src/--tgt_coords/--tgt_segs/--tamp/--tgt` flags.
- Commits in this repo are dated snapshots (e.g. `update 20260508`); follow that style.
