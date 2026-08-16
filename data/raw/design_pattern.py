import requests
import json
import time 
import random

# IMPORTANT some classes might contain more or less functions based on the necessities but conceptually they all follow this pattern

class DataSource:
    
    def fetch_data(self):
        
        HEADERS = { "User-Agent":"peptides-uk-interest-analysis/1.0"}
        URL = "API_ENDPOINT"
        MAX_RETRIES = 5

        # RETRY STRATEGY
        for attempt in range(MAX_RETRIES):
            
            response = requests.get(URL, timeout=30)
            
            if response.status_code != 429:
                response.raise_for_status()
                return response.json()
            
           # 60, 120, 240, 480, 960 seconds
            wait_seconds = 60 * (2 ** attempt)
            wait_seconds += random.uniform(0,5)
            
            time.sleep(wait_seconds)
        
        raise RuntimeError(
            "continued returning HTTP 429"
        )   
       

    def save_raw(self, data, output_path):
        
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


dt = DataSource()
if __name__ == "__main__":
    
    try:
        data = dt.fetch_data()
        dt.save_raw(data)
        print("data retrieved")
        
    except requests.RequestException as error:
        print("request failed")
    finally:
        time.sleep(6)


