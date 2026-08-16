import requests
import json
from pathlib import Path
import time
import random


class Gdelt:

    def fetch_gdelt(self, keyword):
        
        MAX_ENTRIES = 5
        URL = "https://api.gdeltproject.org/api/v2/doc/doc"
        HEADERS = {
            "User-Agent": "peptides-uk-interest-analysis/1.0"
        }
        
        params = {
            "query": f'"{keyword}"',
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "sort": "HybridRel",
        }


        for attempt in range(MAX_ENTRIES):
            response = requests.get(
                URL,
                params=params,
                headers=HEADERS,
                timeout=30,
            )

            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

    
            wait_seconds = 60 * (2 ** attempt)
            wait_seconds += random.uniform(0, 5)

            print(
                f"Waiting {wait_seconds:.1f} seconds "
                f"before retrying..."
            )

            time.sleep(wait_seconds)

        raise RuntimeError(
            f"GDELT continued returning HTTP 429 for {keyword} "
            f"after {MAX_ENTRIES} attempts."
        )
                
    def save_raw(self, data, keyword):

        path = Path(
            f"data/raw/gdelt/{keyword}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


KEYWORDS = [
        "BPC-157",
        "TB-500",
        "retatrutide",
        "semaglutide",
        "ipamorelin",
        "GHK-Cu",
        "epitalon",
        "tesamorelin",
        "CJC-1295"  
    ]

gdelt = Gdelt()

if __name__ == "__main__":

    for keyword in KEYWORDS:
        try:
            data = gdelt.fetch_gdelt(keyword)
            gdelt.save_raw(data,keyword)
            print(f"Retrieved {keyword}")
            
        except requests.RequestException as error:
            print(f"Request failed for {keyword}: {error}")
        finally:
            time.sleep(6)