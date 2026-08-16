import requests
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import time
import random


class Wikipedia():

    def __init__(self):

        self.MAX_RETRIES = 5
        self.BASE_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        self.PROJECT = "en.wikipedia"
        self.ACCESS = "all-access"
        self.AGENT = "user"
        self.GRANULARITY = "daily"
        self.START_DATE = "2023010100"
        # Wikimedia's API etiquette policy requires a descriptive
        # User-Agent with a contact method, or requests may be throttled.
        self.HEADERS = {
            "User-Agent": (
                "peptides-uk-interest-analysis/1.0 "
                "(andrewisoko1998@gmail.com)"
            )
        }

    def _end_date(self):

        return datetime.now(timezone.utc).strftime("%Y%m%d00")

    def fetch_pageviews(self, page):

        # MediaWiki article titles always capitalise the first letter;
        # the REST pageviews API is case-sensitive and does not do this
        # normalisation itself, so a lowercase title silently resolves to
        # an (almost always empty) different page.
        title = page[0].upper() + page[1:]

        url = "/".join([
            self.BASE_URL,
            self.PROJECT,
            self.ACCESS,
            self.AGENT,
            quote(title, safe=""),
            self.GRANULARITY,
            self.START_DATE,
            self._end_date(),
        ])

        for attempt in range(self.MAX_RETRIES):

            response = requests.get(
                url,
                headers=self.HEADERS,
                timeout=30,
            )

            if response.status_code == 404:
                print(f"No Wikipedia page found for {page}")
                return None

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
            f"Wikipedia continued returning HTTP 429 for {page} "
            f"after {self.MAX_RETRIES} attempts."
        )

    def save_raw(self, data, page):

        output = Path(
            f"data/raw/wikipedia/{page}_pageviews.json"
        )
        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return data


PAGES = [
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
wikipedia = Wikipedia()

if __name__ == "__main__":

    for page in PAGES:
        try:
            data = wikipedia.fetch_pageviews(page)
            if data is not None:
                wikipedia.save_raw(data, page)
                print(f"Retrieved {page}")
        except requests.RequestException as error:
            print(f"Request failed for {page}: {error}")
        finally:
            time.sleep(6)
