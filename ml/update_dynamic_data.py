import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "full_hyderabad_dataset.csv"
)

DYNAMIC_DIR = (
    PROJECT_ROOT
    / "data"
    / "dynamic"
)

BACKUP_DIR = (
    DYNAMIC_DIR
    / "backup"
)

OUTPUT_FILE = (
    DYNAMIC_DIR
    / "latest_hyderabad_dataset.csv"
)


# ============================================================
# REQUIRED MODEL FEATURES
# ============================================================

FEATURES = [
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count",
]


# ============================================================
# CREATE DIRECTORIES
# ============================================================

DYNAMIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)

BACKUP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD CURRENT VALIDATED DATA
# ============================================================

print("Loading current validated dataset...")

df = pd.read_csv(
    SOURCE_FILE
)

print(
    f"Areas loaded: {len(df)}"
)


# ============================================================
# VALIDATE
# ============================================================

required_columns = [
    "area"
] + FEATURES


missing = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing:

    raise RuntimeError(
        "Missing required columns: "
        + ", ".join(missing)
    )


# ============================================================
# NUMERIC VALIDATION
# ============================================================

for column in FEATURES:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


invalid_rows = df[
    df[FEATURES]
    .isna()
    .any(axis=1)
]


if not invalid_rows.empty:

    print()
    print(
        "WARNING:"
    )

    print(
        f"{len(invalid_rows)} rows contain "
        "missing/invalid feature values."
    )

    print(
        "Keeping the last validated values."
    )

    # Restore invalid values from original source
    original = pd.read_csv(
        SOURCE_FILE
    )

    for column in FEATURES:

        df.loc[
            invalid_rows.index,
            column
        ] = pd.to_numeric(
            original.loc[
                invalid_rows.index,
                column
            ],
            errors="coerce"
        )


# ============================================================
# SAFETY CHECKS
# ============================================================

# Crime cannot be negative
df["crime_rate_per_10k"] = (
    df["crime_rate_per_10k"]
    .clip(lower=0)
)


# CCTV cannot be negative
df["cctv_count"] = (
    df["cctv_count"]
    .clip(lower=0)
)


# Police score should be 0-1
df["police_coverage_score"] = (
    df["police_coverage_score"]
    .clip(
        lower=0,
        upper=1
    )
)


# Public places cannot be negative
df["amenity_count"] = (
    df["amenity_count"]
    .clip(lower=0)
)


# ============================================================
# BACKUP PREVIOUS DYNAMIC DATA
# ============================================================

if OUTPUT_FILE.exists():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        BACKUP_DIR
        /
        f"latest_hyderabad_dataset_{timestamp}.csv"
    )

    shutil.copy2(
        OUTPUT_FILE,
        backup_file
    )

    print()
    print(
        "Previous dynamic dataset backed up:"
    )

    print(
        backup_file
    )


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# REPORT
# ============================================================

print()
print(
    "======================================"
)

print(
    "DYNAMIC DATASET CREATED"
)

print(
    "======================================"
)

print()
print(
    "Source:"
)

print(
    SOURCE_FILE
)

print()
print(
    "Output:"
)

print(
    OUTPUT_FILE
)

print()
print(
    "Rows:",
    len(df)
)

print()
print(
    "Model features:"
)

for feature in FEATURES:

    print(
        " -",
        feature
    )

print()
print(
    "======================================"
)

print(
    "DATA VALIDATION COMPLETE"
)

print(
    "======================================"
)