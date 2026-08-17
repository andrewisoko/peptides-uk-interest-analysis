# Shared ID lookups for Step 3. Every transform script imports these instead of
# re-deriving IDs, so the same peptide/region/source always gets the same id
# everywhere (this is what the data dictionary's FK checks depend on).

PEPTIDE_KEYWORDS = [
    "BPC-157",
    "TB-500",
    "Retatrutide",
    "Semaglutide",
    "Ipamorelin",
    "GHK-Cu",
    "Epitalon",
    "Tesamorelin",
    "CJC-1295",
]

PEPTIDE_ID_MAP = {
    name: index + 1
    for index, name in enumerate(PEPTIDE_KEYWORDS)
}

REGION_ORDER = ["England", "Scotland", "Wales", "Northern Ireland"]

REGION_ID_MAP = {
    name: index + 1
    for index, name in enumerate(REGION_ORDER)
}

# ONS geography codes for the 4 nation-level rows in
# data/raw/ons/population_estimates_uk.json
REGION_ONS_CODE_MAP = {
    "England": "E92000001",
    "Scotland": "S92000003",
    "Wales": "W92000004",
    "Northern Ireland": "N92000002",
}

SOURCE_ORDER = ["Google Trends", "PubMed", "GDELT", "Wikipedia", "ONS"]

SOURCE_ID_MAP = {
    name: index + 1
    for index, name in enumerate(SOURCE_ORDER)
}

# Authored reliability judgment (1-10), documented rather than sourced from
# any of the 5 raw datasets since none of them self-report reliability.
SOURCE_RELIABILITY = {
    "Google Trends": 7,
    "PubMed": 9,
    "GDELT": 5,
    "Wikipedia": 6,
    "ONS": 10,
}

_NORMALISED_PEPTIDE_MAP = {
    name.strip().upper(): peptide_id
    for name, peptide_id in PEPTIDE_ID_MAP.items()
}

_NORMALISED_REGION_MAP = {
    name.strip().upper(): region_id
    for name, region_id in REGION_ID_MAP.items()
}

_NORMALISED_SOURCE_MAP = {
    name.strip().upper(): source_id
    for name, source_id in SOURCE_ID_MAP.items()
}


def resolve_peptide_id(raw_name):

    key = raw_name.strip().upper()

    if key not in _NORMALISED_PEPTIDE_MAP:
        raise KeyError(f"Unrecognised peptide name: {raw_name!r}")

    return _NORMALISED_PEPTIDE_MAP[key]


def resolve_region_id(raw_name):

    key = raw_name.strip().upper()

    if key not in _NORMALISED_REGION_MAP:
        raise KeyError(f"Unrecognised region name: {raw_name!r}")

    return _NORMALISED_REGION_MAP[key]


# The Step 2 GDELT/PubMed/Wikipedia extract scripts all share one KEYWORDS
# list that mixes casing (e.g. "retatrutide", "GHK-Cu") -- this maps each
# canonical PEPTIDE_KEYWORDS name to the exact casing used in the raw
# filenames on disk for those 3 sources, so Step 3 transforms can find the
# right file without renaming raw data.
RAW_FILENAME_CASING = {
    "BPC-157": "BPC-157",
    "TB-500": "TB-500",
    "Retatrutide": "retatrutide",
    "Semaglutide": "semaglutide",
    "Ipamorelin": "ipamorelin",
    "GHK-Cu": "GHK-Cu",
    "Epitalon": "epitalon",
    "Tesamorelin": "tesamorelin",
    "CJC-1295": "CJC-1295",
}


def resolve_source_id(raw_name):

    key = raw_name.strip().upper()

    if key not in _NORMALISED_SOURCE_MAP:
        raise KeyError(f"Unrecognised source name: {raw_name!r}")

    return _NORMALISED_SOURCE_MAP[key]
