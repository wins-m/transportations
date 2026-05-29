#!/usr/bin/env python3
import time
import requests
import yaml


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
