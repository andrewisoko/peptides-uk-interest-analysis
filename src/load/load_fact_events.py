# Step 4 load for fact_events -- combines the two processed CSVs that share
# this table's grain (events_gdelt.csv + events_pubmed.csv, already told
# apart by the `category` column -- see src/transform/transform_gdelt.py)
# and checks their foreign keys against the dimension CSVs before loading.
#
# Run from the repo root: python -m src.load.load_fact_events

import pandas as pd
from psycopg2.extras import execute_values

from src.load.db import get_connection
from src.utils.io import PROCESSED_DIR
from src.utils.validate import assert_fk_exists, assert_no_nulls

TABLE = "fact_events"
COLUMNS = [
    "event_date",
    "related_article_count",
    "source_count",
    "category",
    "title",
    "region_id",
    "peptide_id",
]


# ----------------------------------------------------------------------
# EXTRACT -- read and combine both processed CSVs at this table's grain
# ----------------------------------------------------------------------

def extract():

    gdelt = pd.read_csv(PROCESSED_DIR / "events" / "events_gdelt.csv")
    pubmed = pd.read_csv(PROCESSED_DIR / "events" / "events_pubmed.csv")

    return pd.concat([gdelt, pubmed], ignore_index=True)


# ----------------------------------------------------------------------
# VALIDATE -- re-check nulls and foreign keys against the dimension CSVs.
# region_id is nullable (fact_events has no UK-region breakdown for every
# row), so it's excluded from the null check; assert_fk_exists tolerates
# nulls itself.
# ----------------------------------------------------------------------

def validate(df):

    assert_no_nulls(
        df,
        ["event_date", "related_article_count", "source_count", "category", "title", "peptide_id"],
        TABLE,
    )

    peptides = pd.read_csv(PROCESSED_DIR / "dimensions" / "peptides.csv")
    regions = pd.read_csv(PROCESSED_DIR / "dimensions" / "regions.csv")

    assert_fk_exists(df, "peptide_id", peptides, "peptide_id", TABLE)
    assert_fk_exists(df, "region_id", regions, "region_id", TABLE)


# ----------------------------------------------------------------------
# LOAD -- TRUNCATE then bulk INSERT. region_id can be NaN (float) when
# absent; convert those to None so psycopg2 writes SQL NULL instead of
# erroring on a float against an INTEGER column.
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
