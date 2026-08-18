# Step 4 load for dim_peptides -- the single worked example for this stage.
# It's the simplest table to start from: one processed CSV, no FK columns of
# its own, nothing to combine across sources.
#
# The pattern below (extract -> validate -> connect -> truncate+load) is what
# every other loader in this project should follow:
#   1. dim_regions, dim_sources, dim_dates -- same shape as this file, just a
#      different processed CSV and table name.
#   2. fact_search_interest, fact_events -- the harder step up: each combines
#      two processed CSVs (search_interest_google_trends.csv +
#      search_interest_wikipedia.csv; events_gdelt.csv + events_pubmed.csv)
#      into one table, and needs assert_fk_exists() against the dimension
#      tables (peptide_id, region_id, source_id/date_id) before loading,
#      the same way src/transform/*.py validates FKs before saving to
#      processed/.
#
# Run from the repo root: python -m src.load.load_dim_peptides

import pandas as pd
from psycopg2.extras import execute_values

from src.load.db import get_connection
from src.utils.io import PROCESSED_DIR
from src.utils.validate import assert_no_nulls

TABLE = "dim_peptides"
COLUMNS = ["peptide_id", "peptide_name", "primary_usage", "price_range", "approved"]


# ----------------------------------------------------------------------
# EXTRACT -- read the already-clean, already-validated processed CSV
# ----------------------------------------------------------------------

def extract():

    path = PROCESSED_DIR / "dimensions" / "peptides.csv"
    return pd.read_csv(path)


# ----------------------------------------------------------------------
# VALIDATE -- re-check the columns this loader actually depends on. The
# processed CSV was already validated in Step 3, but re-checking here
# means this loader still fails loudly if run against a stale/edited file.
# ----------------------------------------------------------------------

def validate(df):

    assert_no_nulls(df, ["peptide_id", "peptide_name", "primary_usage"], TABLE)


# ----------------------------------------------------------------------
# LOAD -- TRUNCATE then bulk INSERT, so re-running this script is safe and
# never produces duplicate rows or primary-key errors. CASCADE is required
# because fact_search_interest/fact_events reference this table by FK --
# Postgres refuses a plain TRUNCATE while that reference exists, even if
# the fact tables are empty. The cascaded fact rows are always reloaded
# afterwards by src/load/run_all.py.
# ----------------------------------------------------------------------

def load(conn, df):

    rows = [tuple(row) for row in df[COLUMNS].itertuples(index=False)]

    with conn.cursor() as cur:

        cur.execute(f"TRUNCATE TABLE {TABLE} CASCADE")
        execute_values(
            cur,
            f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}) VALUES %s",
            rows,
        )

    conn.commit()

    return len(rows)


def run():

    df = extract()
    validate(df)

    conn = get_connection()

    try:
        row_count = load(conn, df)
    finally:
        conn.close()

    return row_count


if __name__ == "__main__":

    row_count = run()
    print(f"Loaded {row_count} rows into {TABLE}")
