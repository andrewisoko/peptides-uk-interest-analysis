# Step 4 load for dim_dates -- same shape as load_dim_peptides.py, just a
# different processed CSV and table name.
#
# Run from the repo root: python -m src.load.load_dim_dates

import pandas as pd
from psycopg2.extras import execute_values

from src.load.db import get_connection
from src.utils.io import PROCESSED_DIR
from src.utils.validate import assert_no_nulls

TABLE = "dim_dates"
COLUMNS = ["date_id", "date", "month", "quarter", "year"]


def extract():

    path = PROCESSED_DIR / "dimensions" / "dates.csv"
    return pd.read_csv(path)


def validate(df):

    assert_no_nulls(df, ["date_id", "date", "month", "quarter", "year"], TABLE)


def load(conn, df):

    # CASCADE is required because fact_search_interest references this
    # table by FK -- Postgres refuses a plain TRUNCATE while that reference
    # exists, even if the fact table is empty. The cascaded fact rows are
    # always reloaded afterwards by src/load/run_all.py.
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
