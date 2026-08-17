# Shared I/O helpers for Step 3. Paths are relative to the repo root, matching
# the convention already used by the Step 2 extract scripts (e.g.
# data/raw/gdelt/gdelt_api.py's `Path(f"data/raw/gdelt/{keyword}.json")`) —
# run every transform script from the project root.

import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def load_json(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_google_trends_csv(path):

    # Google Trends exports start with "Category: All categories" then a
    # blank line before the real header row, e.g.:
    #   Category: All categories
    #
    #   Week,BPC-157: (United Kingdom),Peptides: (United Kingdom)
    return pd.read_csv(path, skiprows=2)


def save_processed(df, subfolder, filename):

    output_path = PROCESSED_DIR / subfolder / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    return output_path
