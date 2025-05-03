#!venv/bin/python
from bs4 import BeautifulSoup
import json
import re


def main():
    update_map_html(coords='./configs/locCoords.json',
                    segs='./configs/travelSegments.json',
                    tamp='./templates/map_heat16_ds.html',
                    tgt='./incoming.html')


def update_map_html(coords, segs, tamp, tgt):
    """Update the HTML template with new JSON data."""

    print(
        f"Updating HTML template '{tamp}' with JSON data from '{coords}' and '{segs}'")

    # Load JSON data
    with open(coords, "r", encoding="utf-8") as json_file:
        loc_js = json.load(json_file)
    with open(segs, "r", encoding="utf-8") as json_file:
        seg_js = json.load(json_file)

    # Read HTML
    with open(tamp, "r", encoding="utf-8") as html_file:
        soup = BeautifulSoup(html_file, "html.parser")

    # Find the <script> with 'const locCoords'
    for body in soup.find_all('body'):
        for script in body.find_all("script"):
            assert script.string and "const locCoords" in script.string
            assert script.string and "const travelSegments" in script.string

            # Pattern to match full multi-line JS const block
            for pattern, js_replacement in zip([r"const\s+locCoords\s*=\s*\{.*?\};",
                                                r"const\s+travelSegments\s*=\s*\[.*?\];"],
                                               [f"const locCoords = {loc_js};".replace("], ", "],\n\t\t\t"),
                                                f"const travelSegments = {seg_js};".replace("{'type'", "\n\t\t\t{'type'").replace('nan', "'-'")]):
                pattern = re.compile(pattern, re.DOTALL)
                # Replace the JS variable with updated JSON
                script.string = pattern.sub(js_replacement, script.string)

    # Save modified HTML
    with open(tgt, "w", encoding="utf-8") as out_file:
        out_file.write(str(soup))

    print(f"Updated HTML with new JSON data, saved as '{tgt}'")


if __name__ == "__main__":
    main()
