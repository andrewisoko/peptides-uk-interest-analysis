# Builds the `dates` dimension: one row per Sunday-anchored week from
# 2023-01-01 to 2026-12-31 (the project's scope). Every fact table joins to
# this via date_id instead of storing raw dates, per the data dictionary.
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.build_dim_dates

from src.utils.dates import build_date_dimension
from src.utils.io import save_processed


class DimDatesBuilder:


    def build(self):

        return build_date_dimension()


    def save(self, dates_df):
        return save_processed(dates_df, "dimensions", "dates.csv")


builder = DimDatesBuilder()

if __name__ == "__main__":

    dates_df = builder.build()
    output_path = builder.save(dates_df)

    print(f"Wrote {len(dates_df)} weeks to {output_path}")
