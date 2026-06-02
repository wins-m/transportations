#!/usr/bin/env python3
"""Generate location & route configs from the trip spreadsheet (``*.xlsx``)."""
import os
import re
import json
import yaml
import pandas as pd
from coords_search import get_coordinates, get_coordinates_osm
from calc import cal_duration

# Map the spreadsheet's 类型 (category) onto the three coordinate buckets used
# everywhere downstream. Single source of truth — keep this the only copy.
TRANS = {
    '铁路': 'Railway',
    '公路': 'Other',    # highway
    '水路': 'Other',    # waterway
    '飞机': 'Airline',
    '自行车': 'Other',
    '其他': 'Other',
}


def main():
    convert_coords_and_segments(src='./data/transport_record.xlsx',
                                tgt_coords='./configs/locCoords',
                                tgt_segs='./configs/travelSegments')


def convert_coords_and_segments(src, tgt_coords, tgt_segs):
    """Convert coordinates and travel segments from Excel to JSON files."""

    # Check if the file exists
    if not os.path.exists(src):
        print(f"File {src} does not exist.")
        return
    # Load the Excel file. The last 4 rows are footer/summary rows, and the
    # sheet is newest-first, so reverse it to get chronological order.
    df = pd.read_excel(src, header=0, sheet_name='Sheet1',
                       skipfooter=4).iloc[::-1]

    # Preprocess spot coordinates
    spots = {}
    for _, sr in df.iterrows():
        spots.update(cache_coords(sr=sr))

    # Generate string of locations
    tgt = filename_check(tgt_coords, 'json', fu=True)
    gen_loc_coords(spots, tgt)

    # Generate string of travel segments
    tgt = filename_check(tgt_segs, 'json', fu=True)
    gen_travel_segments(df, tgt)


def gen_loc_coords(dic, tgt):
    print(f"Generate location coordinates to {tgt}.json ({len(dic)} locations)")
    json_dump(data=dic, tgt=tgt)


def filename_check(tgt, suf, fu=False):
    if fu:
        return tgt
    while os.path.exists(tgt + f'.{suf}'):
        tgt += '.1'
    return tgt


def gen_travel_segments(df, tgt):
    print(f"Generate travel segments to {tgt}.json")
    res = []
    for _, a in df.iterrows():
        if a.count() <= 4:
            continue
        kind = _decide_trans_kind(a['类型'])
        res.append({
            'type': kind,
            'date': a['日期'].strftime('%Y-%m-%d') if a['日期'] is not None else '-',
            'from': _mod2(_mod1(a['乘坐区间'].split('-')[0], kind, a['始发站']), kind=kind),
            'to': _mod2(_mod1(a['乘坐区间'].split('-')[-1], kind, a['终到站']), kind=kind),
            'vehicle': a['车次'],
            'time': a['时间'] if a['时间'] is not None else '-',
            'duration': cal_duration(a['时间'], False) if a['时间'] is not None else '-',
            'distance': str(a['区间里程']) + ' km' if a['区间里程'] is not None else '-',
            'seat': a['座位号'],
            'price': a['票价'],
            'note': a['备注'] if a['备注'] is not None else '',
        })
    print(f"  -> {len(res)} segments")
    json_dump(data=res, tgt=tgt)


def json_dump(data, tgt):
    # Save the JSON string to the file
    with open(tgt + '.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _decide_trans_kind(kind):
    if kind not in TRANS:
        raise ValueError(f"Unknown transportation type: {kind}")
    return TRANS[kind]


def _mod2(x, kind=None):
    if kind == 'Airline':
        return x.split('T')[0]
    else:
        return x  # .replace('机场', '').replace('航站楼', '')


def _mod1(x, kind, ref):
    """modify location keyword for Amap API"""
    x = x.strip()
    if kind == 'Railway':
        if bool(re.search(r'[a-zA-Z]', x)):
            if x.split(' ')[-1] != 'Station':
                x += ' Station'
        elif x[-1] != '站':
            x = x + '站'
    elif kind == 'Airline':
        if 'T' in x:
            if ref not in x:
                x = ref + 'T' + x.split('T')[-1]
            if x[-3:] != '航站楼':
                x += '航站楼'
            if '机场T' not in x:
                x = x.replace('T', '机场T')
        else:
            if x in ref:
                x = ref
            if x[-2:] != '机场':
                x += '机场'
    elif kind != 'Other':
        raise ValueError(f"Unknown transportation type: {kind}")
    return x


# Loaded once, lazily, on the first geocode miss.
_API_KEY = _UNSET = object()   # _UNSET = not yet looked up; None = unavailable
_MANUAL = None                 # hand-pinned WGS-84 overrides (highest priority)
MANUAL_SRC = './configs/coords/manual.yaml'


def cache_coords(sr: pd.Series) -> dict:
    """generate coordinates of start and end locations.

    Resolution order per location, highest priority first:
      1. ``configs/coords/manual.yaml`` — hand-pinned WGS-84, used verbatim.
      2. the per-category ``configs/coords/{kind}.yaml`` geocode cache.
      3. geocode a fresh miss: Amap first (China, GCJ-02 -> WGS-84), then fall
         back to OpenStreetMap/Nominatim (worldwide, native WGS-84).
    """

    global _API_KEY, _MANUAL

    if _MANUAL is None:
        _MANUAL = _load_manual()

    kind = _decide_trans_kind(sr['类型'])
    src_coords = f'./configs/coords/{kind.lower()}.yaml'

    # Load the existing coordinates from the YAML file
    if os.path.exists(src_coords):
        with open(src_coords, 'r', encoding='utf-8') as f:
            head = yaml.safe_load(f) or {}
    else:
        head = {}

    # Check if the coordinates for the locations already exist
    chg_flag = 0
    # Result locations
    locs = {}
    for x0, ref in zip(sr['乘坐区间'].split('-'), [sr['始发站'], sr['终到站']]):
        _ = _mod1(x0, kind, ref)
        x2 = _mod2(_, kind=kind)

        if x2 in _MANUAL:                 # 1. manual override wins, used as-is
            locs[x2] = _MANUAL[x2]
        elif x2 in head:                  # 2. per-category geocode cache
            locs[x2] = head[x2]
        else:                             # 3. geocode: Amap, then OSM fallback
            res = _geocode(x2)
            if res is None:
                print(f"Coordinates for {x2} not found (Amap + OSM).")
                continue
            lat, lon = res
            print(f"Find coordinates of {x2}: {lat}, {lon}")
            chg_flag = 1
            head[x2] = [lat, lon]
            locs[x2] = [lat, lon]

    if chg_flag:
        with open(src_coords, 'w', encoding='utf-8') as f:
            yaml.safe_dump(head, f, allow_unicode=True)

    return locs


def _geocode(keyword):
    """Resolve a keyword to (lat, lon) WGS-84: Amap first, then OSM fallback."""
    global _API_KEY
    if _API_KEY is _UNSET:
        _API_KEY = load_api_keys()        # may be None if no key configured
    res = get_coordinates(keyword, _API_KEY) if _API_KEY else None
    if res is None:                       # foreign / Amap miss -> OpenStreetMap
        res = get_coordinates_osm(keyword)
    return res


def _load_manual(src=MANUAL_SRC):
    if os.path.exists(src):
        with open(src, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def load_api_keys(src='./scripts/configs.yaml'):
    """Return the Amap API key, or ``None`` if it isn't configured.

    Amap is optional now: a missing key just means new China places are geocoded
    via the OpenStreetMap fallback instead. Returning None (rather than raising)
    lets the pipeline run key-free."""
    if not os.path.exists(src):
        print(f"Note: Amap key file '{src}' not found — new locations will be "
              f"geocoded via OpenStreetMap only. For better China coverage, add "
              f"it:\n    amap_api: <your-amap-api-key>   (it is gitignored)")
        return None
    with open(src, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f) or {}
    if 'amap_api' not in conf:
        print(f"Note: 'amap_api' key missing from '{src}' — using OpenStreetMap "
              f"fallback for new locations.")
        return None
    return conf['amap_api']


if __name__ == '__main__':
    main()
