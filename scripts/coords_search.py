#!/usr/bin/env python3
import math
import time
import requests
import yaml

# --- Coordinate datum conversion: GCJ-02 (Amap/高德) -> WGS-84 (OSM/Leaflet) ---
# The Amap REST API returns coordinates in GCJ-02, China's mandatory obfuscated
# datum. Leaflet's OpenStreetMap tiles are WGS-84, so Amap points land a few
# hundred metres off (the well-known "China GPS offset"). Every coordinate that
# enters the system from Amap must be shifted back to WGS-84 before use. The
# offset is only defined inside China's borders, so ``out_of_china`` leaves
# foreign points (Japan, Singapore, …) untouched — matching the encoder, which
# never offset them in the first place. This is the standard reverse transform
# (a.k.a. eviltransform / coordtransform), accurate to ~1 m.
_GCJ_A = 6378245.0                      # semi-major axis (Krasovsky 1940)
_GCJ_EE = 0.00669342162296594323        # eccentricity squared


def out_of_china(lng, lat):
    """True when (lng, lat) is outside the region where Amap applies GCJ-02.

    The classic crude bounding box (lng 73.66-135.05, lat 3.86-53.55) also
    swallows the Indochina peninsula (Thailand / Laos / northern Malaysia).
    Amap serves those overseas POIs already in WGS-84, so offsetting them would
    push points ~130-270 m off. China's land stays north of ~21 deg N once west
    of ~108 deg E (Yunnan); Hainan and Guangdong sit east of that, so excluding
    the south-west corner drops Indochina without touching Chinese territory.
    """
    if not (73.66 < lng < 135.05 and 3.86 < lat < 53.55):
        return True
    return lat < 21.0 and lng < 108.0


def _transform_lat(lng, lat):
    ret = (-100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat
           + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi)
            + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi)
            + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng, lat):
    ret = (300.0 + lng + 2.0 * lat + 0.1 * lng * lng
           + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng)))
    ret += (20.0 * math.sin(6.0 * lng * math.pi)
            + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi)
            + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi)
            + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(lng, lat):
    """Shift a GCJ-02 (lng, lat) back to WGS-84; no-op outside China."""
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _GCJ_EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_GCJ_A * (1 - _GCJ_EE)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_GCJ_A / sqrtmagic * math.cos(radlat) * math.pi)
    return lng * 2 - (lng + dlng), lat * 2 - (lat + dlat)


def get_coordinates(keyword, api_key, retries=4, timeout=10):
    """
    Fetch coordinates for a given keyword using Amap API.

    :param keyword: The name of the location (e.g., city, station, airport).
    :param api_key: Your Amap API key.
    :param retries: Number of attempts on network/transport errors.
    :param timeout: Per-request timeout in seconds.
    :return: A tuple of (latitude, longitude) or None if not found.
    """
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keyword,
        "key": api_key,
        "city": "",  # Optional: specify a city for more accurate results
        "output": "JSON"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and data.get('pois'):
                    location = data['pois'][0]['location']
                    lon, lat = map(float, location.split(','))
                    # Amap returns GCJ-02; shift to WGS-84 for the OSM basemap.
                    lon, lat = gcj02_to_wgs84(lon, lat)
                    return lat, lon
                # A valid 200 response with no match is not retryable.
                return None
            print(f"  Amap API returned HTTP {response.status_code} for "
                  f"'{keyword}' (attempt {attempt + 1}/{retries})")
        except requests.RequestException as exc:
            print(f"  Network error geocoding '{keyword}' "
                  f"(attempt {attempt + 1}/{retries}): {exc}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s, ...
    return None


# Example usage
if __name__ == "__main__":
    with open('./scripts/configs.yaml', 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)
    API_KEY = conf['amap_api']
    keyword = "宁波站"
    coords = get_coordinates(keyword, API_KEY)
    if coords:
        print(f"Coordinates of {keyword}: {coords}")
    else:
        print(f"Coordinates for {keyword} not found.")
