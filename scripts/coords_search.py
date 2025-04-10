#!/opt/homebrew/Caskroom/miniforge/base/bin/python
import requests

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
    API_KEY = "f5f19b61c04c94bb526e361bfa112afb"  # Replace with your Amap API key
    keyword = "宁波站"
    coords = get_coordinates(keyword, API_KEY)
    if coords:
        print(f"Coordinates of {keyword}: {coords}")
    else:
        print(f"Coordinates for {keyword} not found.")