import pandas as pd
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "full_hyderabad_dataset.csv"
)


# ==================================================
# LOAD DATA
# ==================================================

print("Loading processed dataset...")

df = pd.read_csv(DATA_FILE)

print(
    "Rows:",
    len(df)
)


# ==================================================
# CHECK REQUIRED COLUMNS
# ==================================================

required_columns = [
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count"
]


missing = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing:

    print()
    print("ERROR: Missing columns:")

    for column in missing:
        print(" -", column)

    print()
    print("Available columns:")
    print(
        df.columns.tolist()
    )

    raise SystemExit(1)


# ==================================================
# NORMALIZATION
# ==================================================

def percentile_score(series):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    if series.nunique() <= 1:

        return pd.Series(
            0.5,
            index=series.index
        )

    return series.rank(
        pct=True,
        method="average"
    )


# ==================================================
# 1. CRIME
# PRIORITY = 40%
#
# Higher crime = lower safety
# ==================================================

crime_percentile = percentile_score(
    df["crime_rate_per_10k"]
)

crime_safety_score = (
    1 - crime_percentile
)


# ==================================================
# 2. CCTV
# PRIORITY = 30%
# ==================================================

cctv_score = percentile_score(
    df["cctv_count"]
)


# ==================================================
# 3. POLICE
# PRIORITY = 20%
#
# IMPORTANT:
# Uses the existing police_coverage_score.
#
# We are NOT using:
# police_area_distance.csv
# ==================================================

police_score = percentile_score(
    df["police_coverage_score"]
)


# ==================================================
# 4. PUBLIC PLACES
# PRIORITY = 10%
# ==================================================

public_place_score = percentile_score(
    df["amenity_count"]
)


# ==================================================
# WEIGHTS
# ==================================================

CRIME_WEIGHT = 0.40
CCTV_WEIGHT = 0.30
POLICE_WEIGHT = 0.20
PUBLIC_PLACE_WEIGHT = 0.10


# ==================================================
# FINAL SAFETY SCORE
# ==================================================

df["safety_score"] = (

    100
    *
    (
        CRIME_WEIGHT
        * crime_safety_score

        +

        CCTV_WEIGHT
        * cctv_score

        +

        POLICE_WEIGHT
        * police_score

        +

        PUBLIC_PLACE_WEIGHT
        * public_place_score
    )

).clip(
    0,
    100
).round(2)


# ==================================================
# SAVE COMPONENT SCORES
# ==================================================

df["crime_safety_score"] = (
    crime_safety_score.round(4)
)

df["cctv_safety_score"] = (
    cctv_score.round(4)
)

df["police_safety_score"] = (
    police_score.round(4)
)

df["public_place_safety_score"] = (
    public_place_score.round(4)
)


# ==================================================
# RISK LEVEL
# ==================================================

def get_risk_level(score):

    if score < 35:
        return "HIGH"

    elif score < 60:
        return "MEDIUM"

    else:
        return "LOW"


df["risk_level"] = (
    df["safety_score"]
    .apply(get_risk_level)
)


# ==================================================
# SAVE
# ==================================================

df.to_csv(
    DATA_FILE,
    index=False
)


# ==================================================
# REPORT
# ==================================================

print()
print("======================================")
print("SAFETY INDEX CREATED")
print("======================================")

print()
print("FINAL PRIORITIES:")

print("Crime Risk      : 40%")
print("CCTV            : 30%")
print("Police          : 20%")
print("Public Places   : 10%")


print()
print("Safety score statistics:")

print(
    df["safety_score"].describe()
)


print()
print("Risk distribution:")

print(
    df["risk_level"].value_counts()
)


# ==================================================
# LOWEST AREAS
# ==================================================

print()
print("Lowest scoring areas:")

lowest_columns = [
    "area",
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count",
    "safety_score",
    "risk_level"
]

print(
    df[
        lowest_columns
    ]
    .sort_values(
        "safety_score"
    )
    .head(10)
    .to_string(
        index=False
    )
)


# ==================================================
# HIGHEST AREAS
# ==================================================

print()
print("Highest scoring areas:")

print(
    df[
        lowest_columns
    ]
    .sort_values(
        "safety_score",
        ascending=False
    )
    .head(10)
    .to_string(
        index=False
    )
)


# ==================================================
# SAVE MESSAGE
# ==================================================

print()
print("Saved to:")

print(DATA_FILE)


print()
print("======================================")
print("READY FOR MODEL TRAINING")
print("======================================")