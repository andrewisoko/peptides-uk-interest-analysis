# Step 4 load for fact_search_interest -- combines the two processed CSVs
# that share this table's grain (search_interest_google_trends.csv +
# search_interest_wikipedia.csv) and checks their foreign keys against the
# dimension CSVs before loading, the same way src/transform/*.py validates
# FKs before saving to processed/.
#
# Run from the repo root: python -m src.load.load_fact_search_interest

import pandas as pd
from psycopg2.extras import execute_values

from src.load.db import get_connection
from src.utils.io import PROCESSED_DIR
from src.utils.validate import assert_fk_exists, assert_no_nulls

TABLE = "fact_search_interest"
COLUMNS = ["date_id", "peptide_id", "region_id", "source_id", "interest_score"]


# ----------------------------------------------------------------------
# EXTRACT -- read and combine both processed CSVs at this table's grain
# ----------------------------------------------------------------------

def extract():

    google_trends = pd.read_csv(
        PROCESSED_DIR / "search_interest" / "search_interest_google_trends.csv"
    )
    wikipedia = pd.read_csv(
        PROCESSED_DIR / "search_interest" / "search_interest_wikipedia.csv"
    )

    return pd.concat([google_trends, wikipedia], ignore_index=True)


# ----------------------------------------------------------------------
# VALIDATE -- re-check nulls and foreign keys against the dimension CSVs.
# region_id is nullable (Wikipedia has no UK-region breakdown), so it's
# excluded from the null check; assert_fk_exists tolerates nulls itself.
# ----------------------------------------------------------------------

def validate(df):

    assert_no_nulls(df, ["date_id", "peptide_id", "source_id", "interest_score"], TABLE)

    peptides = pd.read_csv(PROCESSED_DIR / "dimensions" / "peptides.csv")
    regions = pd.read_csv(PROCESSED_DIR / "dimensions" / "regions.csv")
    sources = pd.read_csv(PROCESSED_DIR / "dimensions" / "sources.csv")
    dates = pd.read_csv(PROCESSED_DIR / "dimensions" / "dates.csv")

    assert_fk_exists(df, "peptide_id", peptides, "peptide_id", TABLE)
    assert_fk_exists(df, "region_id", regions, "region_id", TABLE)
    assert_fk_exists(df, "source_id", sources, "source_id", TABLE)
    assert_fk_exists(df, "date_id", dates, "date_id", TABLE)


# ----------------------------------------------------------------------
# LOAD -- TRUNCATE then bulk INSERT. region_id can be NaN (float) for
# national-only/Wikipedia rows; convert those to None so psycopg2 writes
# SQL NULL instead of erroring on a float against an INTEGER column.
# ----------------------------------------------------------------------

def load(conn, df):

    clean = df[COLUMNS].astype(object).where(pd.notnull(df[COLUMNS]), None)
    rows = [tuple(row) for row in clean.itertuples(index=False)]

    with conn.cursor() as cur:

        cur.execute(f"TRUNCATE TABLE {TABLE}")
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
