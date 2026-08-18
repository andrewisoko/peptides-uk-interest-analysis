# Runs every Step 4 loader in one go, in the order FK constraints require:
# dimensions first (dim_peptides, dim_regions, dim_sources, dim_dates), then
# the fact tables that reference them (fact_search_interest, fact_events).
#
# Run from the repo root: python -m src.load.run_all

from src.load.load_dim_dates import TABLE as DIM_DATES_TABLE
from src.load.load_dim_dates import run as run_dim_dates
from src.load.load_dim_peptides import TABLE as DIM_PEPTIDES_TABLE
from src.load.load_dim_peptides import run as run_dim_peptides
from src.load.load_dim_regions import TABLE as DIM_REGIONS_TABLE
from src.load.load_dim_regions import run as run_dim_regions
from src.load.load_dim_sources import TABLE as DIM_SOURCES_TABLE
from src.load.load_dim_sources import run as run_dim_sources
from src.load.load_fact_events import TABLE as FACT_EVENTS_TABLE
from src.load.load_fact_events import run as run_fact_events
from src.load.load_fact_search_interest import TABLE as FACT_SEARCH_INTEREST_TABLE
from src.load.load_fact_search_interest import run as run_fact_search_interest

STEPS = [
    (DIM_PEPTIDES_TABLE, run_dim_peptides),
    (DIM_REGIONS_TABLE, run_dim_regions),
    (DIM_SOURCES_TABLE, run_dim_sources),
    (DIM_DATES_TABLE, run_dim_dates),
    (FACT_SEARCH_INTEREST_TABLE, run_fact_search_interest),
    (FACT_EVENTS_TABLE, run_fact_events),
]


if __name__ == "__main__":

    for table, run in STEPS:

        row_count = run()
        print(f"Loaded {row_count} rows into {table}")
