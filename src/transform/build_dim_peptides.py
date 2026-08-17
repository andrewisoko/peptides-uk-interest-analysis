# Builds the `peptides` dimension. peptide_id/peptide_name come straight
# from PEPTIDE_ID_MAP, but primary_usage/price_range/approved aren't present
# in ANY of the 5 raw sources — no source gives clinical usage, pricing, or
# approval status, so these are legitimately manually-authored reference
# data, not something a parser can derive.
#
# To make that manual step evidence-backed rather than a cold guess, this
# script mines each peptide's already-collected PubMed article titles for
# its most common significant words and prints them as a research aid before
# you fill in PEPTIDE_MANUAL_INFO below.
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.build_dim_peptides

import re
from collections import Counter

import pandas as pd

from src.utils.io import RAW_DIR, load_json, save_processed
from src.utils.mappings import PEPTIDE_ID_MAP

# TODO: fill these in yourself, using the printed PubMed title hints (and
# your own research) as a starting point. Leave a field as None if you
# genuinely can't find a reliable value — price_range/approved are allowed
# to be null, but primary_usage should end up filled in for every peptide.
# price_range is left null for every peptide: none of the 5 raw sources give
# pricing, and this project has no reliable/verifiable source for it, so
# fabricating a number would be worse than leaving the (nullable) field blank.
# approved reflects whether the peptide has an approved pharmaceutical
# product in a major regulatory jurisdiction (MHRA/FDA/EMA) as of this
# project's data window (2023-2026) -- re-verify before reuse, since several
# of these (Retatrutide especially) are active late-stage trial candidates
# whose status can change.
PEPTIDE_MANUAL_INFO = {
    "BPC-157": {
        "primary_usage": "gastric/tissue injury repair, studied mainly in animal models",
        "price_range": None,
        "approved": False,
    },
    "TB-500": {
        "primary_usage": "tissue repair and wound healing, studied mainly in animal models",
        "price_range": None,
        "approved": False,
    },
    "Retatrutide": {
        "primary_usage": "triple hormone-receptor agonist studied for obesity and type 2 diabetes weight loss",
        "price_range": None,
        "approved": False,
    },
    "Semaglutide": {
        "primary_usage": "GLP-1 receptor agonist for type 2 diabetes and chronic weight management",
        "price_range": None,
        "approved": True,
    },
    "Ipamorelin": {
        "primary_usage": "growth hormone secretagogue studied for GH release and body composition",
        "price_range": None,
        "approved": False,
    },
    "GHK-Cu": {
        "primary_usage": "copper-binding peptide studied for skin repair, collagen production and wound healing",
        "price_range": None,
        "approved": False,
    },
    "Epitalon": {
        "primary_usage": "synthetic tetrapeptide studied for telomerase activation and cellular ageing",
        "price_range": None,
        "approved": False,
    },
    "Tesamorelin": {
        "primary_usage": "GHRH analogue studied for reducing visceral fat; approved in the US (Egrifta) for HIV-associated lipodystrophy but not MHRA-approved in the UK",
        "price_range": None,
        "approved": False,
    },
    "CJC-1295": {
        "primary_usage": "GHRH analogue studied for sustained growth hormone/IGF-1 elevation",
        "price_range": None,
        "approved": False,
    },
}

_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "after", "before", "study",
    "studies", "review", "case", "effect", "effects", "using", "based",
    "analysis", "clinical", "patient", "patients", "human", "humans", "trial",
    "results", "role", "novel", "new", "use", "used", "associated", "among",
    "between", "following", "report", "reports", "systematic", "meta",
    "literature", "current", "potential", "future", "randomized", "controlled",
    "double", "blind", "placebo", "group", "groups", "data", "model", "models",
}


class DimPeptidesBuilder:

    def __init__(self):

        self.pubmed_dir = RAW_DIR / "pubmed"
        self.top_n_hints = 15

    def research_primary_usage_hints(self, peptide_name):

        summary_path = self.pubmed_dir / f"{peptide_name}_summary.json"

        if not summary_path.exists():
            return []

        summary = load_json(summary_path)
        titles = [
            summary["result"][uid]["title"]
            for uid in summary["result"]["uids"]
            if "title" in summary["result"][uid]
        ]

        name_tokens = {
            token.lower()
            for token in re.split(r"[^A-Za-z]+", peptide_name)
            if token
        }

        words = Counter()

        for title in titles:
            for token in re.split(r"[^A-Za-z]+", title.lower()):
                if len(token) < 4:
                    continue
                if token in _STOPWORDS or token in name_tokens:
                    continue
                words[token] += 1

        return [word for word, _count in words.most_common(self.top_n_hints)]

    def build(self):

        rows = []

        for peptide_name, peptide_id in PEPTIDE_ID_MAP.items():

            manual_info = PEPTIDE_MANUAL_INFO[peptide_name]

            rows.append({
                "peptide_id": peptide_id,
                "peptide_name": peptide_name,
                "primary_usage": manual_info["primary_usage"],
                "price_range": manual_info["price_range"],
                "approved": manual_info["approved"],
            })

        return pd.DataFrame(rows).sort_values("peptide_id").reset_index(drop=True)

    def save(self, peptides_df):

        return save_processed(peptides_df, "dimensions", "peptides.csv")


builder = DimPeptidesBuilder()

if __name__ == "__main__":

    print("PubMed title research hints (use these to fill in primary_usage above):\n")

    for peptide_name in PEPTIDE_ID_MAP:
        hints = builder.research_primary_usage_hints(peptide_name)
        print(f"  {peptide_name}: {', '.join(hints) if hints else '(no titles found)'}")

    peptides_df = builder.build()
    output_path = builder.save(peptides_df)

    missing_usage = peptides_df[peptides_df["primary_usage"].isna()]["peptide_name"].tolist()

    print(f"\nWrote {len(peptides_df)} peptides to {output_path}")

    if missing_usage:
        print(
            f"Still missing primary_usage for: {missing_usage} "
            f"- fill in PEPTIDE_MANUAL_INFO and re-run before combining tables."
        )
