# Builds the `regions` dimension from ONS population data. Only the 4
# nation-level rows are used (England, Scotland, Wales, Northern Ireland) —
# the finer 9-English-region breakdown in regions_uk.json isn't used here,
# since Google Trends' regional snapshots only reach nation-level
# granularity (see the plan for why: the England sub-region export kept
# failing with a Google Trends server error).
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.transform_ons

import pandas as pd

from src.utils.io import RAW_DIR, load_json, save_processed
from src.utils.mappings import REGION_ID_MAP, resolve_region_id
from src.utils.validate import assert_no_nulls


class DimRegionsBuilder:

    def __init__(self):

        self.population_path = RAW_DIR / "ons" / "population_estimates_uk.json"

    def select_year(self, population_by_year) -> str:
        return max(population_by_year, key=int)

    def build_staging(self):

        data = load_json(self.population_path)
        rows = []

        for geography in data["geographies"]:

            region_name = geography["name"]

            if region_name not in REGION_ID_MAP:
                continue

            year = self.select_year(geography["population_by_year"])

            rows.append({
                "ons_code": geography["code"],
                "region_name": region_name,
                "population": geography["population_by_year"][year],
                "year": year,
            })

        return pd.DataFrame(rows)

    def build_dimension(self, staging_df):

        rows = [
            {
                "region_id": resolve_region_id(row.region_name),
                "region_name": row.region_name,
                "population": row.population,
            }
            for row in staging_df.itertuples()
        ]

        return pd.DataFrame(rows).sort_values("region_id").reset_index(drop=True)

    def validate(self, regions_df):

        assert_no_nulls(regions_df, ["region_name", "population"], "regions")

        if len(regions_df) != len(REGION_ID_MAP):
            raise ValueError(
                f"regions expected {len(REGION_ID_MAP)} rows, got {len(regions_df)}"
            )

    def save_staging(self, staging_df):

        return save_processed(staging_df, "geography", "ons_population_staging.csv")

    def save_dimension(self, regions_df):

        return save_processed(regions_df, "dimensions", "regions.csv")


builder = DimRegionsBuilder()

if __name__ == "__main__":

    staging_df = builder.build_staging()
    builder.save_staging(staging_df)

    regions_df = builder.build_dimension(staging_df)
    builder.validate(regions_df)
    output_path = builder.save_dimension(regions_df)

    print(f"Wrote {len(regions_df)} regions to {output_path}")
