import pandas as pd
import re
from pathlib import Path
from difflib import SequenceMatcher


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"

ORIGINAL_FILE = (
    RAW_DATA / "police_stations.csv"
)

TGRAC_FILE = (
    RAW_DATA / "police_stations_clean.csv"
)

OUTPUT_FILE = (
    RAW_DATA / "police_station_matches.csv"
)


# ==================================================
# LOAD
# ==================================================

print("Loading police station datasets...")

original = pd.read_csv(
    ORIGINAL_FILE
)

tgrac = pd.read_csv(
    TGRAC_FILE
)


print(
    "Original records:",
    len(original)
)

print(
    "TGRAC records:",
    len(tgrac)
)


# ==================================================
# NORMALIZE NAMES
# ==================================================

def normalize_name(name):

    if pd.isna(name):
        return ""

    name = str(name).upper()

    # Replace common separators
    name = name.replace("_", " ")
    name = name.replace("&", " AND ")
    name = name.replace("/", " ")

    # Remove punctuation
    name = re.sub(
        r"[^A-Z0-9 ]",
        " ",
        name
    )

    # Normalize whitespace
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    # Remove common police terminology
    replacements = [
        " POLICE STATION ",
        " POLICE PS ",
        " PS ",
        " POLICE ",
    ]

    for value in replacements:

        name = name.replace(
            value,
            " "
        )

    return name.strip()


original["normalized_station"] = (
    original["police_station"]
    .apply(normalize_name)
)

tgrac["normalized_station"] = (
    tgrac["police_property"]
    .apply(normalize_name)
)


# ==================================================
# MATCH FUNCTION
# ==================================================

def similarity(
    name1,
    name2
):

    if not name1 or not name2:
        return 0

    return SequenceMatcher(
        None,
        name1,
        name2
    ).ratio()


# ==================================================
# MATCH
# ==================================================

print()
print(
    "Matching station names..."
)


results = []


for _, original_row in original.iterrows():

    original_area = (
        original_row["area"]
    )

    original_station = (
        original_row["police_station"]
    )

    original_name = (
        original_row["normalized_station"]
    )


    best_score = 0

    best_row = None


    for _, tgrac_row in tgrac.iterrows():

        tgrac_name = (
            tgrac_row[
                "normalized_station"
            ]
        )


        score = similarity(
            original_name,
            tgrac_name
        )


        if score > best_score:

            best_score = score

            best_row = tgrac_row


    if best_row is not None:

        matched_station = (
            best_row[
                "police_property"
            ]
        )

        latitude = (
            best_row[
                "latitude"
            ]
        )

        longitude = (
            best_row[
                "longitude"
            ]
        )

    else:

        matched_station = None

        latitude = None

        longitude = None


    # ------------------------------------------------
    # MATCH STATUS
    # ------------------------------------------------

    if best_score >= 0.85:

        status = "HIGH"

    elif best_score >= 0.65:

        status = "MEDIUM"

    elif best_score >= 0.50:

        status = "LOW"

    else:

        status = "UNMATCHED"


    results.append({

        "area":
            original_area,

        "original_police_station":
            original_station,

        "matched_tgrac_station":
            matched_station,

        "match_score":
            round(
                best_score,
                3
            ),

        "match_status":
            status,

        "latitude":
            latitude,

        "longitude":
            longitude

    })


# ==================================================
# DATAFRAME
# ==================================================

matches = pd.DataFrame(
    results
)


# ==================================================
# SAVE
# ==================================================

matches.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==================================================
# REPORT
# ==================================================

print()
print(
    "======================================"
)

print(
    "POLICE STATION MATCHING COMPLETE"
)

print(
    "======================================"
)


print()
print(
    "Match status:"
)

print(
    matches[
        "match_status"
    ]
    .value_counts()
)


print()
print(
    "Low-confidence matches:"
)


low_matches = matches[
    matches[
        "match_status"
    ].isin(
        [
            "LOW",
            "UNMATCHED"
        ]
    )
]


if low_matches.empty:

    print(
        "None"
    )

else:

    print(
        low_matches[
            [
                "area",
                "original_police_station",
                "matched_tgrac_station",
                "match_score",
                "match_status"
            ]
        ]
        .to_string(
            index=False
        )
    )


print()
print(
    "Sample matches:"
)


print(
    matches[
        [
            "area",
            "original_police_station",
            "matched_tgrac_station",
            "match_score",
            "match_status"
        ]
    ]
    .head(30)
    .to_string(
        index=False
    )
)


print()
print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)