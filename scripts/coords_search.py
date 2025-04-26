#!venv/bin/python
import requests
import yaml


def get_coordinates(keyword, api_key):
    """
    Fetch coordinates for a given keyword using Amap API.

    :param keyword: The name of the location (e.g., city, station, airport).
    :param api_key: Your Amap API key.
    :return: A tuple of (latitude, longitude) or None if not found.
    """
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keyword,
        "key": api_key,
        "city": "",  # Optional: specify a city for more accurate results
        "output": "JSON"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1' and data['pois']:
            location = data['pois'][0]['location']
            lon, lat = map(float, location.split(','))
            return lat, lon
    return None

# Example usage
if __name__ == "__main__":
    API_KEY = ""  # Replace with your Amap API key
    with open('./scripts/configs.yaml', 'r') as f:
        conf = yaml.safe_load(f)
    API_KEY = conf['amap_api']
    keyword = "宁波站"
    coords = get_coordinates(keyword, API_KEY)
    if coords:
        print(f"Coordinates of {keyword}: {coords}")
    else:
        print(f"Coordinates for {keyword} not found.")
