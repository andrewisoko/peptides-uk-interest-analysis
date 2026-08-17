# Builds the `sources` dimension from the fixed SOURCE_ID_MAP /
# SOURCE_RELIABILITY defined in src/utils/mappings.py. None of the 5 raw
# datasets self-report a reliability score, so this is an authored judgment
# call rather than a parsed value — documented here rather than left blank.
#
# Run from the repo root: .venv/Scripts/python.exe -m src.transform.build_dim_sources

import pandas as pd

from src.utils.io import save_processed
from src.utils.mappings import SOURCE_ID_MAP, SOURCE_RELIABILITY


class DimSourcesBuilder:

    def build(self):

        rows = [
            {
                "source_id": source_id,
                "source_name": source_name,
                "reliability": SOURCE_RELIABILITY[source_name],
            }
            for source_name, source_id in SOURCE_ID_MAP.items()
        ]

        return pd.DataFrame(rows).sort_values("source_id").reset_index(drop=True)

    def save(self, sources_df):

        return save_processed(sources_df, "dimensions", "sources.csv")


builder = DimSourcesBuilder()

if __name__ == "__main__":

    sources_df = builder.build()
    output_path = builder.save(sources_df)

    print(f"Wrote {len(sources_df)} sources to {output_path}")
