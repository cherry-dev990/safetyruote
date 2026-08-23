import requests
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DYNAMIC_DIR = (
    PROJECT_ROOT
    / "data"
    / "dynamic"
)

BACKUP_DIR = (
    DYNAMIC_DIR
    / "backup"
)

DATASET_FILE = (
    DYNAMIC_DIR
    / "latest_hyderabad_dataset.csv"
)

RAW_CCTV_FILE = (
    DYNAMIC_DIR
    / "cctv_api_raw.csv"
)


DYNAMIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)

BACKUP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CCTV ARCGIS API
# ============================================================

API_URL = (
    "https://services6.arcgis.com/"
    "JDWzamIuD1Wgrxfk/"
    "ArcGIS/rest/services/"
    "Public_Crime___Infrastructure_Mapping_WFL1/"
    "FeatureServer/1/query"
)


PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json"
}


# ============================================================
# FETCH CCTV DATA
# ============================================================

print(
    "Fetching CCTV data..."
)

response = requests.get(
    API_URL,
    params=PARAMS,
    timeout=30
)

response.raise_for_status()

data = response.json()


if "features" not in data:

    raise RuntimeError(
        "CCTV API did not return feature records."
    )


features = data["features"]

print(
    "CCTV records received:",
    len(features)
)


if not features:

    raise RuntimeError(
        "CCTV API returned zero records."
    )


# ============================================================
# CONVERT FEATURES
# ============================================================

records = []

for feature in features:

    attributes = feature.get(
        "attributes",
        {}
    )

    geometry = feature.get(
        "geometry",
        {}
    )

    attributes["longitude"] = geometry.get(
        "x"
    )

    attributes["latitude"] = geometry.get(
        "y"
    )

    records.append(
        attributes
    )


cctv_df = pd.DataFrame(
    records
)


# ============================================================
# SAVE RAW DATA
# ============================================================

cctv_df.to_csv(
    RAW_CCTV_FILE,
    index=False
)

print()
print(
    "Raw CCTV data saved:"
)

print(
    RAW_CCTV_FILE
)


# ============================================================
# VALIDATE COORDINATES
# ============================================================

cctv_df["latitude"] = pd.to_numeric(
    cctv_df["latitude"],
    errors="coerce"
)

cctv_df["longitude"] = pd.to_numeric(
    cctv_df["longitude"],
    errors="coerce"
)

cctv_df = cctv_df.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
)


# ============================================================
# HYDERABAD BOUNDING BOX
#
# Approximate Hyderabad-area filter.
# ============================================================

HYD_MIN_LAT = 17.20
HYD_MAX_LAT = 17.60

HYD_MIN_LON = 78.20
HYD_MAX_LON = 78.70


cctv_df = cctv_df[
    (
        cctv_df["latitude"]
        >= HYD_MIN_LAT
    )
    &
    (
        cctv_df["latitude"]
        <= HYD_MAX_LAT
    )
    &
    (
        cctv_df["longitude"]
        >= HYD_MIN_LON
    )
    &
    (
        cctv_df["longitude"]
        <= HYD_MAX_LON
    )
].copy()


print()
print(
    "CCTV records inside Hyderabad bounds:",
    len(cctv_df)
)


# ============================================================
# LOAD 312-AREA DATASET
# ============================================================

if not DATASET_FILE.exists():

    raise FileNotFoundError(
        f"Dataset not found: {DATASET_FILE}"
    )


df = pd.read_csv(
    DATASET_FILE
)


required_columns = [
    "area",
    "cctv_count"
]


missing = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing:

    raise RuntimeError(
        "Dataset missing columns: "
        + ", ".join(missing)
    )


# ============================================================
# CHECK AREA_NAME FIELD
# ============================================================

if "Area_Name" not in cctv_df.columns:

    raise RuntimeError(
        "The CCTV API does not contain Area_Name. "
        "Automatic area aggregation cannot be performed safely."
    )


# ============================================================
# NORMALIZE AREA NAMES
# ============================================================

cctv_df["Area_Name"] = (
    cctv_df["Area_Name"]
    .astype(str)
    .str.strip()
    .str.lower()
)


df["_area_key"] = (
    df["area"]
    .astype(str)
    .str.strip()
    .str.lower()
)


# ============================================================
# COUNT CCTV BY AREA
# ============================================================

cctv_counts = (
    cctv_df
    .groupby(
        "Area_Name"
    )
    .size()
    .reset_index(
        name="new_cctv_count"
    )
)


# ============================================================
# UPDATE ONLY EXACT AREA MATCHES
# ============================================================

merged = df.merge(
    cctv_counts,
    left_on="_area_key",
    right_on="Area_Name",
    how="left"
)


matched = (
    merged["new_cctv_count"]
    .notna()
    .sum()
)


print()
print(
    "Exact area matches:",
    matched,
    "/",
    len(df)
)


# ============================================================
# SAFETY RULE
#
# Do NOT replace unmatched areas with zero.
# Keep their previous validated CCTV count.
# ============================================================

matched_mask = (
    merged["new_cctv_count"]
    .notna()
)


merged.loc[
    matched_mask,
    "cctv_count"
] = merged.loc[
    matched_mask,
    "new_cctv_count"
]


merged["cctv_count"] = (
    pd.to_numeric(
        merged["cctv_count"],
        errors="coerce"
    )
    .fillna(0)
    .clip(lower=0)
)


# ============================================================
# CLEAN COLUMNS
# ============================================================

merged = merged.drop(
    columns=[
        "_area_key",
        "Area_Name",
        "new_cctv_count"
    ],
    errors="ignore"
)


# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup_file = (
    BACKUP_DIR
    /
    f"dataset_before_cctv_{timestamp}.csv"
)


shutil.copy2(
    DATASET_FILE,
    backup_file
)


# ============================================================
# SAVE UPDATED DATASET
# ============================================================

merged.to_csv(
    DATASET_FILE,
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
    "CCTV FEATURE UPDATED"
)

print(
    "======================================"
)

print(
    "CCTV records:",
    len(cctv_df)
)

print(
    "Area matches:",
    matched
)

print(
    "Dataset rows:",
    len(merged)
)

print()
print(
    "CCTV statistics:"
)

print(
    merged[
        "cctv_count"
    ].describe()
)

print()
print(
    "Updated dataset:"
)

print(
    DATASET_FILE
)

print()
print(
    "Backup:"
)

print(
    backup_file
)

print()
print(
    "CCTV update complete."
)