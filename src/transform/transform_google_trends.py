# Step 3 transform for Google Trends: national weekly time series +
# nation-level regional snapshots (baseline vs current). This is the first
# of the 5 source transforms.
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.transform_google_trends
#
# Fill in the stub methods below (parse_national, parse_regional,
# clean_national, clean_regional, standardise, integrate,
# validate_source_specific) -- everything else (I/O, orchestration, the
# shared FK/null/date-bound checks) is given so you can focus on the actual
# data-wrangling decisions.

import pandas as pd

from src.utils.dates import date_id_for, to_week_start
from src.utils.io import RAW_DIR, read_google_trends_csv, save_processed
from src.utils.mappings import (
    PEPTIDE_ID_MAP,
    REGION_ID_MAP,
    resolve_peptide_id,
    resolve_region_id,
    resolve_source_id,
)
from src.utils.validate import (
    assert_date_bounds,
    assert_no_nulls,
    assert_valid_ids,
)


class GoogleTrendsTransformer:

    def __init__(self):

        self.national_dir = RAW_DIR / "google_trends" / "national_timeseries"
        self.regional_dir = RAW_DIR / "google_trends" / "regional_snapshots"
        self.source_id = resolve_source_id("Google Trends")

        # A regional snapshot has no daily/weekly granularity -- its whole
        # window collapses to one representative date for date_id purposes.
        # These are the two windows' start dates (see the plan for why).
        self.BASELINE_DATE = pd.Timestamp("2023-01-01").date()
        self.CURRENT_DATE = pd.Timestamp("2026-05-15").date()

    # ------------------------------------------------------------------
    # PARSE
    # ------------------------------------------------------------------

    def parse_national(self, peptide_name):
        """
        Read data/raw/google_trends/national_timeseries/Peptides_{peptide_name}.csv
        via utils.io.read_google_trends_csv and return a DataFrame with
        exactly two columns: `week` (the raw date string from the CSV's
        first column) and `interest_score` (the peptide's OWN column --
        NOT the "Peptides: (...)" anchor column, drop that one).

        Hint: read_google_trends_csv gives you columns like
        ["Week", "BPC-157: (United Kingdom)", "Peptides: (United Kingdom)"].
        You want the 1st and 2nd columns, renamed to "week"/"interest_score".
        """
        path = self.national_dir / f"Peptides_{peptide_name}.csv"
        df = read_google_trends_csv(path)

        df = df.iloc[:, [0, 1]]
        df.columns = ["week", "interest_score"]

        return df

    def parse_regional(self, peptide_name):
        """
        Read both
        data/raw/google_trends/regional_snapshots/{peptide_name}_baseline.csv
        and .../{peptide_name}_current.csv, and return ONE DataFrame with
        4 (regions) x 2 (windows) = 8 rows, columns:
        `region` (e.g. "England"), `window` ("baseline" or "current"),
        `interest_score` (raw value straight from the CSV, e.g. "4%",
        "<1%", or blank -- don't clean it here, that's the next method).

        Hint: same anchor-column-drop rule as parse_national -- keep the
        Region column and the peptide's own column, drop "Peptides: (...)".
        """
        frames = []

        for window in ("baseline", "current"):

            path = self.regional_dir / f"{peptide_name}_{window}.csv"
            df = read_google_trends_csv(path)

            df = df.iloc[:, [0, 1]]
            df.columns = ["region", "interest_score"]
            df["window"] = window

            frames.append(df)

        return pd.concat(frames, ignore_index=True)[["region", "window", "interest_score"]]

    # ------------------------------------------------------------------
    # CLEAN
    # ------------------------------------------------------------------

    def clean_national(self, df):
        """
        Input: parse_national()'s output (week: raw date string,
        interest_score: usually a plain int like 0, 9, 10 -- but check the
        data yourself, some peptides (e.g. Ipamorelin, TB-500) have a few
        rows where Google Trends prints "<1" instead of a number for very
        low weeks. Same convention as the regional snapshots' "<1%": treat
        it as 0.5.
        Output: same columns, but `week` is a real `date` object floored to
        its week-start Sunday (use utils.dates.to_week_start), and
        `interest_score` is a float.

        Hint: pd.to_datetime(df["week"]).dt.date, then .apply(to_week_start).
        """
        df = df.copy()

        df["week"] = pd.to_datetime(df["week"]).dt.date.apply(to_week_start)

        # astype(str) first so this works whether pandas already read the
        # column as int64 (no "<1" rows) or object (mixed "<1"/int rows).
        df["interest_score"] = (
            df["interest_score"].astype(str).str.strip()
            .replace("<1", "0.5")
            .astype(float)
        )

        return df

    def clean_regional(self, df):
        """
        Input: parse_regional()'s output (interest_score as raw strings
        like "4%", "<1%", or blank).
        Output: same shape, but interest_score is a float 0-100, and a new
        `date` column replaces `window` (map "baseline" -> self.BASELINE_DATE,
        "current" -> self.CURRENT_DATE, then floor to week start).

        Hint for interest_score cleaning:
          - strip a trailing "%" and convert to float
          - "<1%" is Google's way of saying "some, but under 1%" -> use 0.5
          - blank/missing means "not enough data" -> use 0.0 (keeps every
            region/window/peptide combination present rather than dropping rows)
        """
        df = df.copy()

        def parse_percent(raw_value):

            value = str(raw_value).strip()

            if value == "" or value.lower() == "nan":
                return 0.0
            if value.startswith("<1"):
                return 0.5

            return float(value.rstrip("%"))

        df["interest_score"] = df["interest_score"].apply(parse_percent)

        window_to_date = {"baseline": self.BASELINE_DATE, "current": self.CURRENT_DATE}
        df["date"] = df["window"].map(window_to_date).apply(to_week_start)

        return df.drop(columns=["window"])

    # ------------------------------------------------------------------
    # STANDARDISE
    # ------------------------------------------------------------------

    def standardise(self, df, peptide_name, is_regional):
        """
        Add the FK columns every search_interest row needs:
        `date_id` (from the cleaned `date` column, via utils.dates.date_id_for),
        `peptide_id` (via resolve_peptide_id(peptide_name)),
        `source_id` (already computed once in __init__ as self.source_id),
        and, only if is_regional, `region_id` (via resolve_region_id on the
        `region` column) -- otherwise region_id should be None for every
        row (national rows aren't tied to a specific region).
        """
        df = df.copy()

        date_col = "date" if is_regional else "week"
        df["date_id"] = df[date_col].apply(date_id_for)
        df["peptide_id"] = resolve_peptide_id(peptide_name)
        df["source_id"] = self.source_id

        if is_regional:
            df["region_id"] = df["region"].apply(resolve_region_id)
        else:
            df["region_id"] = None

        return df

    # ------------------------------------------------------------------
    # INTEGRATE
    # ------------------------------------------------------------------

    def integrate(self, national_df, regional_df):
        """
        Union the standardised national and regional DataFrames into one,
        with exactly these columns in this order:
        date_id, peptide_id, region_id, source_id, interest_score
        (drop any leftover helper columns like `week`/`region`/`date`).
        """
        columns = ["date_id", "peptide_id", "region_id", "source_id", "interest_score"]

        return pd.concat(
            [national_df[columns], regional_df[columns]], ignore_index=True
        )

    # ------------------------------------------------------------------
    # VALIDATE -- the shared FK/null/date-bound checks are given; add the
    # two Google-Trends-specific checks yourself in validate_source_specific
    # ------------------------------------------------------------------

    def validate(self, df):

        assert_no_nulls(
            df, ["date_id", "peptide_id", "source_id", "interest_score"],
            "search_interest_google_trends",
        )

        dates = pd.to_datetime(df["date_id"], format="%Y%m%d")
        assert_date_bounds(df.assign(_date=dates), "_date", "search_interest_google_trends")

        assert_valid_ids(df, "peptide_id", PEPTIDE_ID_MAP.values(), "search_interest_google_trends")
        assert_valid_ids(df, "region_id", REGION_ID_MAP.values(), "search_interest_google_trends")

        self.validate_source_specific(df)

    def validate_source_specific(self, df):
        """
        TODO -- add two Google-Trends-specific checks, raising ValueError
        with a clear message if either fails:
        1. every interest_score is between 0 and 100 inclusive
        2. there are exactly 72 regional rows (4 regions x 9 peptides x 2
           windows) -- i.e. df[df["region_id"].notna()] has exactly 72 rows
        """
        out_of_range = df[(df["interest_score"] < 0) | (df["interest_score"] > 100)]

        if not out_of_range.empty:
            raise ValueError(
                f"search_interest_google_trends.interest_score has "
                f"{len(out_of_range)} value(s) outside 0-100"
            )

        regional_row_count = len(df[df["region_id"].notna()])

        if regional_row_count != 72:
            raise ValueError(
                f"search_interest_google_trends expected 72 regional rows "
                f"(4 regions x 9 peptides x 2 windows), got {regional_row_count}"
            )

    # ------------------------------------------------------------------
    # RUN -- orchestrates the whole class
    # ------------------------------------------------------------------

    def run(self):

        national_frames = []
        regional_frames = []

        for peptide_name in PEPTIDE_ID_MAP:

            national_df = self.clean_national(self.parse_national(peptide_name))
            national_df = self.standardise(national_df, peptide_name, is_regional=False)
            national_frames.append(national_df)

            regional_df = self.clean_regional(self.parse_regional(peptide_name))
            regional_df = self.standardise(regional_df, peptide_name, is_regional=True)
            regional_frames.append(regional_df)

        combined_df = self.integrate(
            pd.concat(national_frames, ignore_index=True),
            pd.concat(regional_frames, ignore_index=True),
        )

        self.validate(combined_df)

        output_path = save_processed(
            combined_df, "search_interest", "search_interest_google_trends.csv"
        )

        return combined_df, output_path


transformer = GoogleTrendsTransformer()

if __name__ == "__main__":

    combined_df, output_path = transformer.run()
    print(f"Wrote {len(combined_df)} rows to {output_path}")
