# Step 3 transform for GDELT: relevance-ranked news articles per peptide,
# aggregated to one row per peptide/week in the shared `events` fact table
# (GDELT + PubMed both feed `events`, since both are "Cause growth data" per
# the project scope; `category` is what tells the two apart downstream --
# events has no source_id column of its own).
#
# Note: unlike PubMed's search (which is date-bounded server-side) GDELT's
# free "doc" API only returns its top 250 most-relevant hits with no date
# filter, so validate() enforces the project's 2023-2026 window itself.
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.transform_gdelt

import pandas as pd

from src.utils.dates import to_week_start
from src.utils.io import RAW_DIR, load_json, save_processed
from src.utils.mappings import PEPTIDE_ID_MAP, RAW_FILENAME_CASING, resolve_peptide_id
from src.utils.validate import assert_date_bounds, assert_no_nulls, assert_valid_ids


class GdeltTransformer:

    def __init__(self):

        self.raw_dir = RAW_DIR / "gdelt"

        # None of GDELT's fields self-classify an article's topic, so every
        # GDELT-derived event row gets this fixed, authored category -- it's
        # what lets an `events` row be told apart from a PubMed-derived one.
        self.CATEGORY = "News/Media"

    # ------------------------------------------------------------------
    # PARSE -- read one peptide's article list into a flat table
    # ------------------------------------------------------------------

    def parse(self, peptide_name):

        filename_casing = RAW_FILENAME_CASING[peptide_name]
        path = self.raw_dir / f"{filename_casing}.json"
        data = load_json(path)

        rows = [
            {
                "seendate": article["seendate"],
                "title": article["title"],
                "domain": article["domain"],
            }
            for article in data["articles"]
        ]

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # CLEAN -- turn GDELT's seendate string into a week-start date
    # ------------------------------------------------------------------

    def clean(self, df):

        df = df.copy()

        # seendate looks like "20260609T133000Z".
        df["week"] = (
            pd.to_datetime(df["seendate"], format="%Y%m%dT%H%M%SZ")
            .dt.date.apply(to_week_start)
        )

        return df.drop(columns=["seendate"])

    # ------------------------------------------------------------------
    # STANDARDISE -- attach FK columns
    # ------------------------------------------------------------------

    def standardise(self, df, peptide_name):

        df = df.copy()

        df["peptide_id"] = resolve_peptide_id(peptide_name)
        # GDELT's sourcecountry is the publishing outlet's country, not a UK
        # nation -- there's no signal here to tie an article to one of the 4
        # region rows, so every GDELT event is left unattributed (region_id
        # is a nullable FK for exactly this reason).
        df["region_id"] = None
        df["category"] = self.CATEGORY

        return df

    # ------------------------------------------------------------------
    # INTEGRATE -- collapse every peptide's articles into one row per
    # peptide/week, matching the `events` table's aggregate grain
    # ------------------------------------------------------------------

    def integrate(self, frames):

        combined = pd.concat(frames, ignore_index=True)

        grouped = combined.groupby(
            ["peptide_id", "week", "region_id", "category"],
            as_index=False,
            dropna=False,
        ).agg(
            related_article_count=("title", "size"),
            source_count=("domain", "nunique"),
            # combined preserves each file's original relevance order (GDELT
            # sorts by HybridRel), so "first" here means "most relevant
            # article that week" rather than an arbitrary pick.
            title=("title", "first"),
        )

        grouped = grouped.rename(columns={"week": "event_date"})

        return grouped[
            ["event_date", "related_article_count", "source_count",
             "category", "title", "region_id", "peptide_id"]
        ]

    # ------------------------------------------------------------------
    # VALIDATE
    # ------------------------------------------------------------------

    def validate(self, df):

        assert_no_nulls(
            df,
            ["event_date", "related_article_count", "source_count", "category",
             "title", "peptide_id"],
            "events_gdelt",
        )

        assert_date_bounds(df, "event_date", "events_gdelt")
        assert_valid_ids(df, "peptide_id", PEPTIDE_ID_MAP.values(), "events_gdelt")

        self.validate_source_specific(df)

    def validate_source_specific(self, df):

        invalid_counts = df[
            (df["related_article_count"] < 1) | (df["source_count"] < 1)
        ]

        if not invalid_counts.empty:
            raise ValueError(
                f"events_gdelt has {len(invalid_counts)} row(s) with "
                f"related_article_count/source_count below 1"
            )

        # source_count is distinct domains within the same articles that
        # were counted for related_article_count, so it can never exceed it.
        impossible_counts = df[df["source_count"] > df["related_article_count"]]

        if not impossible_counts.empty:
            raise ValueError(
                f"events_gdelt has {len(impossible_counts)} row(s) where "
                f"source_count exceeds related_article_count"
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

        output_path = save_processed(combined_df, "events", "events_gdelt.csv")

        return combined_df, output_path


transformer = GdeltTransformer()

if __name__ == "__main__":

    combined_df, output_path = transformer.run()
    print(f"Wrote {len(combined_df)} rows to {output_path}")
