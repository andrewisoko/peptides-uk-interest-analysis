# Step 3 transform for PubMed: publication summaries per peptide, aggregated
# to one row per peptide/week in the shared `events` fact table (see
# transform_gdelt.py for why GDELT and PubMed share one table -- `category`
# is what tells a PubMed-derived row apart from a GDELT-derived one).
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.transform_pubmed

import pandas as pd

from src.utils.dates import MAX_DATE, MIN_DATE, to_week_start
from src.utils.io import RAW_DIR, load_json, save_processed
from src.utils.mappings import PEPTIDE_ID_MAP, RAW_FILENAME_CASING, resolve_peptide_id
from src.utils.validate import assert_date_bounds, assert_no_nulls, assert_valid_ids


class PubmedTransformer:

    def __init__(self):

        self.raw_dir = RAW_DIR / "pubmed"

        # Matches the data dictionary's own example value for events.category
        # -- kept as one fixed, authored label since PubMed summaries don't
        # self-classify a publication's research category.
        self.CATEGORY = "Clinical research"

    # ------------------------------------------------------------------
    # PARSE -- read one peptide's publication summaries into a flat table
    # ------------------------------------------------------------------

    def parse(self, peptide_name):

        filename_casing = RAW_FILENAME_CASING[peptide_name]
        path = self.raw_dir / f"{filename_casing}_summary.json"
        data = load_json(path)

        result = data["result"]

        rows = [
            {
                "pubdate": result[uid]["sortpubdate"],
                "journal": result[uid]["fulljournalname"],
                "title": result[uid]["title"],
            }
            for uid in result["uids"]
        ]

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # CLEAN -- turn PubMed's sortpubdate string into a week-start date
    # ------------------------------------------------------------------

    def clean(self, df):

        df = df.copy()

        # sortpubdate looks like "2026/08/11 00:00".
        df["week"] = pd.to_datetime(df["pubdate"]).dt.date.apply(to_week_start)

        # parse() fetched with datetype=pdat bounded to 2023-2026, but
        # sortpubdate reflects a different date facet (e.g. an earlier epub
        # date) that can occasionally fall just outside that window -- drop
        # the rare row(s) rather than let a single record violate the
        # project's 2023-2026 scope during aggregation.
        in_scope = (df["week"] >= MIN_DATE) & (df["week"] <= MAX_DATE)

        return df[in_scope].drop(columns=["pubdate"])

    # ------------------------------------------------------------------
    # STANDARDISE -- attach FK columns
    # ------------------------------------------------------------------

    def standardise(self, df, peptide_name):

        df = df.copy()

        df["peptide_id"] = resolve_peptide_id(peptide_name)
        # PubMed gives no UK-region signal for a publication, so every
        # PubMed event is left unattributed (region_id is nullable for
        # exactly this reason -- same as the GDELT transform).
        df["region_id"] = None
        df["category"] = self.CATEGORY

        return df

    # ------------------------------------------------------------------
    # INTEGRATE -- collapse every peptide's publications into one row per
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
            source_count=("journal", "nunique"),
            # combined preserves each file's original esearch order (PubMed's
            # default relevance sort), so "first" means "most relevant
            # publication that week" rather than an arbitrary pick.
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
            "events_pubmed",
        )

        assert_date_bounds(df, "event_date", "events_pubmed")
        assert_valid_ids(df, "peptide_id", PEPTIDE_ID_MAP.values(), "events_pubmed")

        self.validate_source_specific(df)

    def validate_source_specific(self, df):

        invalid_counts = df[
            (df["related_article_count"] < 1) | (df["source_count"] < 1)
        ]

        if not invalid_counts.empty:
            raise ValueError(
                f"events_pubmed has {len(invalid_counts)} row(s) with "
                f"related_article_count/source_count below 1"
            )

        impossible_counts = df[df["source_count"] > df["related_article_count"]]

        if not impossible_counts.empty:
            raise ValueError(
                f"events_pubmed has {len(impossible_counts)} row(s) where "
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

        output_path = save_processed(combined_df, "events", "events_pubmed.csv")

        return combined_df, output_path


transformer = PubmedTransformer()

if __name__ == "__main__":

    combined_df, output_path = transformer.run()
    print(f"Wrote {len(combined_df)} rows to {output_path}")
