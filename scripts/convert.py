#!venv/bin/python
"""
from *.xlsx generate loc & route configs

"""
import os
import re
import json
import yaml
import pandas as pd
from coords_search import get_coordinates
from calc import cal_duration


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
    # Load the Excel file
    df = pd.read_excel(src, header=0, sheet_name='Sheet1',
                       skipfooter=4).iloc[::-1]

    # Preprocess spot oordinates
    spots = {}
    for _, sr in df.iterrows():
        left = cache_coords(sr=sr)
        spots.update(left)

    # Generate string of locations
    tgt = filename_check(tgt_coords, 'json', fu=True)
    gen_loc_coords(spots, tgt)

    # Generate string of travel segments
    tgt = filename_check(tgt_segs, 'json', fu=True)
    gen_travel_segments(df, tgt)


def gen_loc_coords(dic, tgt):
    print(f"Generate location coordinates to {tgt}.json")
    json_dump(data=dic, tgt=tgt)


def filename_check(tgt, suf, fu=False):
    if fu:
        return tgt
    while os.path.exists(tgt + f'.{suf}'):
        tgt += '.1'
    return tgt


def gen_travel_segments(df, tgt):
    TRANS = {
        '铁路': 'Railway',
        '公路': 'Other',  # 'highway',
        '水路': 'Other',  # 'waterway',
        '飞机': 'Airline',
        '自行车': 'Other',
        '其他': 'Other',
    }
    print(f"Generate travel segments to {tgt}.json")
    res = []
    for _, a in df.iterrows():
        if a.count() <= 4:
            continue
        kind = _decide_trans_kind(a['类型'])
        res.append({
            'type': TRANS[a['类型']],
            'date': a['日期'].strftime('%Y-%m-%d') if a['日期'] is not None else '-',
            'from': _mod2(_mod1(a['乘坐区间'].split('-')[0], kind, a['始发站']), kind=1),
            'to': _mod2(_mod1(a['乘坐区间'].split('-')[-1], kind, a['终到站']), kind=1),
            'vehicle': a['车次'],
            'time': a['时间'] if a['时间'] is not None else '-',
            'duration': cal_duration(a['时间'], False) if a['时间'] is not None else '-',
            'distance': str(a['区间里程']) + ' km' if a['区间里程'] is not None else '-',
            'seat': a['座位号'],
            'price': a['票价'],
            'note': a['备注'] if a['备注'] is not None else '',
        })
    json_dump(data=res, tgt=tgt)


def json_dump(data, tgt):
    # Save the JSON string to the file
    with open(tgt + '.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # print(f"JSON saved to {tgt}.json")


def _decide_trans_kind(kind):
    TRANS = {
        '铁路': 'Railway',
        '公路': 'Other',  # 'highway',
        '水路': 'Other',  # 'waterway',
        '飞机': 'Airline',
        '自行车': 'Other',
        '其他': 'Other',
    }
    if kind in TRANS:
        kind = TRANS[kind]
    else:
        raise ValueError(f"Unknown transportation type: {kind}")
    return kind


def _mod2(x, kind=0):
    if kind == 1:
        return x.split('T')[0]
    else:
        return x.replace('机场', '').replace('航站楼', '')


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
    elif kind == 'waterway':
        pass
        # x = x.replace('港', '')
    elif kind == 'highway':
        if bool(re.search(r'[a-zA-Z]', x)):
            pass
        elif x[-5:] != '汽车客运站':
            x = x + '汽车客运站'
    elif kind != 'Other':
        raise ValueError(f"Unknown transportation type: {kind}")
    return x


def __coords_correction(head, kind, ref):
    res = {}
    for x in head:
        res[_mod1(x, kind, ref)] = head[x]
    head = res


def cache_coords(sr: pd.Series) -> dict:
    """generate coordinates of start and end locations"""

    kind = _decide_trans_kind(sr['类型'])
    src_coords = f'./configs/coords/{kind.lower()}.yaml'

    # Load the existing coordinates from the YAML file
    if os.path.exists(src_coords):
        head = yaml.safe_load(open(src_coords, 'r', encoding='utf-8'))
    else:
        head = {}

    # Check if the coordinates for the locations already exist
    chg_flag = 0
    # Rusult locations
    locs = {}
    for x0, ref in zip(sr['乘坐区间'].split('-'), [sr['始发站'], sr['终到站']]):
        x1 = _mod1(x0, kind, ref)
        x2 = _mod2(x1, kind=1)

        if x1 not in head:
            # TODO: Replace with your Amap API key
            API_KEY = load_api_keys()
            res = get_coordinates(x1, API_KEY)
            if res is None:
                print(f"Coordinates for {x1} not found.")
                continue
            else:
                lat, lon = res
                print(f"Find coordinates of {x1}: {lat}, {lon}")
                chg_flag = 1
                head[x1] = [lat, lon]
                locs[x2] = [lat, lon]
        else:
            locs[x2] = head[x1]

    if chg_flag:
        with open(src_coords, 'w', encoding='utf-8') as f:
            yaml.safe_dump(head, f, allow_unicode=True)

    return locs


def load_api_keys(src='./scripts/config.yaml'):
    with open(src, 'r') as f:
        conf = yanl.safe_load(f)
    return conf['amap_api']


if __name__ == '__main__':
    main()
