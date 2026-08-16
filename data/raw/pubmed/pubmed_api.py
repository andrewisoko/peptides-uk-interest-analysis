import requests
import json
from pathlib import Path
import time
import random


class Pubmed():

    def __init__(self):

        self.MAX_RETRIES = 5
        self.BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.HEADERS = {
            "User-Agent": "peptides-uk-interest-analysis/1.0"
        }
        # project scope is the last 3 years (see orchestrator.md)
        self.MIN_DATE = "2023/01/01"
        self.MAX_DATE = "2026/12/31"
        self.SUMMARY_CHUNK_SIZE = 200

    def _get(self, url, params=None):

        for attempt in range(self.MAX_RETRIES):

            response = requests.get(
                url,
                headers=self.HEADERS,
                params=params,
                timeout=30
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
            f"PubMed continued returning HTTP 429 "
            f"after {self.MAX_RETRIES} attempts"
        )

    def fetch_search(self, keyword):

        params = {
            "db": "pubmed",
            "term": keyword,
            "retmax": 500,
            "retmode": "json",
            "datetype": "pdat",
            "mindate": self.MIN_DATE,
            "maxdate": self.MAX_DATE,
        }

        return self._get(self.BASE_URL + "esearch.fcgi", params)

    def fetch_summaries(self, idlist):

        if not idlist:
            return {"result": {"uids": []}}

        merged = {"result": {"uids": []}}

        for start in range(0, len(idlist), self.SUMMARY_CHUNK_SIZE):

            chunk = idlist[start:start + self.SUMMARY_CHUNK_SIZE]

            params = {
                "db": "pubmed",
                "id": ",".join(chunk),
                "retmode": "json",
            }

            for attempt in range(self.MAX_RETRIES):

                response = requests.post(
                    self.BASE_URL + "esummary.fcgi",
                    headers=self.HEADERS,
                    data=params,
                    timeout=30
                )

                if response.status_code != 429:
                    response.raise_for_status()
                    chunk_data = response.json()
                    break

                wait_seconds = 60 * (2 ** attempt)
                wait_seconds += random.uniform(0, 5)

                print(
                    f"Waiting {wait_seconds:.1f} seconds "
                    f"before retrying..."
                )

                time.sleep(wait_seconds)

            else:
                raise RuntimeError(
                    f"PubMed continued returning HTTP 429 "
                    f"after {self.MAX_RETRIES} attempts"
                )

            merged["result"]["uids"].extend(chunk_data["result"]["uids"])
            merged["result"].update(
                {
                    uid: chunk_data["result"][uid]
                    for uid in chunk_data["result"]["uids"]
                }
            )

        return merged

    def save_raw(self, data, filename):

        path = Path(f"data/raw/pubmed/{filename}")

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
pubmed = Pubmed()

if __name__ == "__main__":

    for keyword in KEYWORDS:
        try:
            search_data = pubmed.fetch_search(keyword)
            pubmed.save_raw(search_data, f"{keyword}_search.json")

            idlist = search_data.get("esearchresult", {}).get("idlist", [])
            summary_data = pubmed.fetch_summaries(idlist)
            pubmed.save_raw(summary_data, f"{keyword}_summary.json")

            print(f"Retrieved {keyword}")

        except requests.RequestException as error:
            print(f"Request failed for {keyword}: {error}")
        finally:
            time.sleep(6)
