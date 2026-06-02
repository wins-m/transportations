# transportations

A personal travel-history visualizer. A spreadsheet of trips
(`data/transport_record.xlsx`) is geocoded and transformed into JSON, then
injected into a Leaflet map template. The committed `index.html` is the
published artifact — a self-contained interactive map with route lines,
station popups, a legend, a year/type filter, a travel-stats panel, and an
optional heatmap layer.

The source spreadsheet and all place names are in **Chinese**.

## Setup

```sh
pip install -r scripts/requirements.txt
```

New (uncached) locations are geocoded in this order: a hand-pinned
**`configs/coords/manual.yaml`** override → the **Amap (高德)** API (best for
China) → an **OpenStreetMap / Nominatim** fallback (worldwide, for places Amap
can't find). An Amap key is *optional* — add it to `scripts/configs.yaml`
(gitignored) for better Chinese coverage:

```yaml
amap_api: <your-amap-api-key>
```

Without it, new places fall back to OpenStreetMap. If every place is already
cached in `configs/coords/*.yaml`, no geocoding happens at all.

### Coordinate datums

Amap returns **GCJ-02** (China's offset datum); the pipeline shifts those to
**WGS-84** so they line up with the OpenStreetMap basemap (the correction
applies inside China only — foreign points, incl. Hong Kong/Macau, are left
as-is). OpenStreetMap and `manual.yaml` are already WGS-84.

To **pin a point exactly** (domestic or foreign), add it to
`configs/coords/manual.yaml` — it overrides everything and is used verbatim.
Look the coordinate up on **OpenStreetMap** (same datum as the map). Note that
Google Maps' road layer *inside mainland China* is also GCJ-02-shifted (~500 m
off), so use OSM or Google's satellite layer for Chinese points.

## Usage

Run the full pipeline from the **repo root** (paths default relative to it):

```sh
python3 scripts/main.py
```

```
usage: main.py [-h] [--src SRC] [--tgt_coords TGT_COORDS] [--tgt_segs TGT_SEGS]
               [--tamp TAMP] [--tgt TGT]

options:
  --src SRC               source spreadsheet   (default: ./data/transport_record.xlsx)
  --tgt_coords TGT_COORDS location coords out  (default: ./configs/locCoords)
  --tgt_segs TGT_SEGS     travel segments out  (default: ./configs/travelSegments)
  --tamp TAMP             HTML template         (default: ./templates/map_heat16_ds.html)
  --tgt TGT               output HTML           (default: ./incoming.html)
```

The scripts' shebangs are normalized to `#!/usr/bin/env python3`, but invoking
them explicitly with `python3` (or an activated venv) is recommended.

## Publish

Review the generated `./incoming.html` (gitignored), then promote it to the
tracked artifact and commit:

```sh
mv incoming.html index.html
git commit -am "update $(date +%Y%m%d)" && git push
```

## Layout

- `data/transport_record.xlsx` — source trip log (`Sheet1`).
- `scripts/` — the pipeline: `main.py` → `convert.py` (xlsx → JSON +
  geocoding via `coords_search.py`, durations via `calc.py`) → `update.py`
  (injects JSON into the template).
- `configs/coords/{railway,airline,other}.yaml` — append-only geocode caches
  (source of truth). `configs/locCoords.json` + `configs/travelSegments.json`
  are the regenerated datasets — don't hand-edit them.
- `templates/map_heat16_ds.html` — the live (default) map template. Older
  variants and the legacy `map.html` prototype are archived under
  `templates/archive/` and are not part of the pipeline.
- `index.html` — the published, self-contained map.

See `CLAUDE.md` for the detailed pipeline architecture and gotchas.
