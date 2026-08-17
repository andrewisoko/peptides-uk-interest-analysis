# Shared validation helpers for Step 3's "Validate" stage. Each check raises
# ValueError with enough detail (row count + offending values) to debug —
# they never silently pass on bad data.

import pandas as pd

from src.utils.dates import MAX_DATE, MIN_DATE


def assert_no_nulls(df, columns, table_name):

    for column in columns:

        null_count = df[column].isna().sum()

        if null_count > 0:
            raise ValueError(
                f"{table_name}.{column} has {null_count} null value(s), expected none"
            )


def assert_fk_exists(df, fk_col, dim_df, dim_pk, table_name):

    non_null_values = df[fk_col].dropna()
    valid_ids = set(dim_df[dim_pk])
    invalid_ids = sorted(set(non_null_values) - valid_ids)

    if invalid_ids:
        raise ValueError(
            f"{table_name}.{fk_col} has {len(invalid_ids)} value(s) with no "
            f"matching {dim_pk}: {invalid_ids[:10]}"
        )


def assert_date_bounds(df, date_col, table_name, min_date=MIN_DATE, max_date=MAX_DATE):

    dates = pd.to_datetime(df[date_col]).dt.date
    out_of_bounds = df[(dates < min_date) | (dates > max_date)]

    if not out_of_bounds.empty:
        raise ValueError(
            f"{table_name}.{date_col} has {len(out_of_bounds)} row(s) "
            f"outside {min_date}..{max_date}"
        )


def assert_valid_ids(df, id_col, valid_ids, table_name):

    non_null_values = df[id_col].dropna()
    invalid_ids = sorted(set(non_null_values) - set(valid_ids))

    if invalid_ids:
        raise ValueError(
            f"{table_name}.{id_col} has {len(invalid_ids)} invalid id(s): "
            f"{invalid_ids[:10]}"
        )
