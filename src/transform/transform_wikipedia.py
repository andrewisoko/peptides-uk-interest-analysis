# Step 3 transform for Wikipedia: daily en.wikipedia pageviews per peptide,
# aggregated to the project's weekly grain and folded into the same
# `search_interest` fact table Google Trends uses (both are "Popularity
# growth data" per the project scope).
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.transform_wikipedia

import pandas as pd

from src.utils.dates import date_id_for, to_week_start
from src.utils.io import RAW_DIR, load_json, save_processed
from src.utils.mappings import (
    PEPTIDE_ID_MAP,
    RAW_FILENAME_CASING,
    resolve_peptide_id,
    resolve_source_id,
)
from src.utils.validate import assert_date_bounds, assert_no_nulls, assert_valid_ids


class WikipediaTransformer:

    def __init__(self):

        self.raw_dir = RAW_DIR / "wikipedia"
        self.source_id = resolve_source_id("Wikipedia")

    # ------------------------------------------------------------------
    # PARSE -- read one peptide's daily pageviews JSON into a flat table
    # ------------------------------------------------------------------

    def parse(self, peptide_name):

        filename_casing = RAW_FILENAME_CASING[peptide_name]
        path = self.raw_dir / f"{filename_casing}_pageviews.json"
        data = load_json(path)

        rows = [
            {"date": item["timestamp"][:8], "views": item["views"]}
            for item in data["items"]
        ]

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # CLEAN -- collapse daily views into weekly totals at the project grain
    # ------------------------------------------------------------------

    def clean(self, df):

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.date.apply(to_week_start)

        weekly = df.groupby("date", as_index=False)["views"].sum()

        return weekly.rename(columns={"views": "weekly_views"})

    # ------------------------------------------------------------------
    # STANDARDISE -- attach FK columns and turn raw views into a 0-100 index
    # ------------------------------------------------------------------

    def standardise(self, df, peptide_name):

        df = df.copy()

        df["date_id"] = df["date"].apply(date_id_for)
        df["peptide_id"] = resolve_peptide_id(peptide_name)
        df["region_id"] = None
        df["source_id"] = self.source_id

        # Wikipedia pageviews have no shared "anchor" term the way Google
        # Trends' queries do (see transform_google_trends.py), so each
        # peptide is normalised only against its OWN peak week. Scores are
        # comparable week-to-week within a peptide, not across peptides.
        peak_views = df["weekly_views"].max()
        df["interest_score"] = (
            df["weekly_views"] / peak_views * 100 if peak_views > 0 else 0.0
        )

        return df

    # ------------------------------------------------------------------
    # INTEGRATE -- union every peptide into the final search_interest shape
    # ------------------------------------------------------------------

    def integrate(self, frames):

        columns = ["date_id", "peptide_id", "region_id", "source_id", "interest_score"]

        return pd.concat(frames, ignore_index=True)[columns]

    # ------------------------------------------------------------------
    # VALIDATE
    # ------------------------------------------------------------------

    def validate(self, df):

        assert_no_nulls(
            df, ["date_id", "peptide_id", "source_id", "interest_score"],
            "search_interest_wikipedia",
        )

        dates = pd.to_datetime(df["date_id"], format="%Y%m%d")
        assert_date_bounds(df.assign(_date=dates), "_date", "search_interest_wikipedia")

        assert_valid_ids(df, "peptide_id", PEPTIDE_ID_MAP.values(), "search_interest_wikipedia")

        out_of_range = df[(df["interest_score"] < 0) | (df["interest_score"] > 100)]

        if not out_of_range.empty:
            raise ValueError(
                f"search_interest_wikipedia.interest_score has "
                f"{len(out_of_range)} value(s) outside 0-100"
            )

    # ------------------------------------------------------------------
    # RUN -- orchestrates the whole class
    # ------------------------------------------------------------------

    def run(self):

        frames = []

        for peptide_name in PEPTIDE_ID_MAP:

            df = self.clean(self.parse(peptide_name))
            df = self.standardise(df, peptide_name)
            frames.append(df)

        combined_df = self.integrate(frames)

        self.validate(combined_df)

        output_path = save_processed(
            combined_df, "search_interest", "search_interest_wikipedia.csv"
        )

        return combined_df, output_path


transformer = WikipediaTransformer()

if __name__ == "__main__":

    combined_df, output_path = transformer.run()
    print(f"Wrote {len(combined_df)} rows to {output_path}")
