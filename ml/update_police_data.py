import requests
import pandas as pd
import shutil
import math
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DYNAMIC_DIR = PROJECT_ROOT / "data" / "dynamic"
BACKUP_DIR = DYNAMIC_DIR / "backup"

DATASET_FILE = (
    DYNAMIC_DIR / "latest_hyderabad_dataset.csv"
)

RAW_POLICE_FILE = (
    DYNAMIC_DIR / "police_api_raw.csv"
)

CLEAN_POLICE_FILE = (
    DYNAMIC_DIR / "police_stations_dynamic.csv"
)

POLICE_AREA_FILE = (
    DYNAMIC_DIR / "police_area_dynamic.csv"
)

DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# TGRAC POLICE API
# ============================================================

API_URL = (
    "https://tgrac.telangana.gov.in/"
    "arcgis/rest/services/"
    "PoliceProperties_Folder/"
    "Police_Properties2/"
    "MapServer/1/query"
)

PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json"
}


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    radius = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


# ============================================================
# FETCH POLICE DATA
# ============================================================

print("Fetching Hyderabad police data...")

response = requests.get(
    API_URL,
    params=PARAMS,
    timeout=30
)

response.raise_for_status()

data = response.json()

if "features" not in data:
    raise RuntimeError(
        "Police API did not return feature records."
    )

features = data["features"]

print(
    "Records received:",
    len(features)
)

if not features:
    raise RuntimeError(
        "Police API returned zero records."
    )


# ============================================================
# CONVERT API RESPONSE
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

    attributes["latitude"] = geometry.get("y")
    attributes["longitude"] = geometry.get("x")

    records.append(attributes)


raw_df = pd.DataFrame(records)


# ============================================================
# SAVE RAW DATA
# ============================================================

raw_df.to_csv(
    RAW_POLICE_FILE,
    index=False
)

print()
print(
    "Raw police API data saved:"
)

print(
    RAW_POLICE_FILE
)


# ============================================================
# FIND PROPERTY NAME FIELD
# ============================================================

name_column = None

for column in [
    "Name_of_the_Property",
    "name",
    "NAME",
    "Name"
]:

    if column in raw_df.columns:

        name_column = column
        break


if name_column is None:

    raise RuntimeError(
        "Police property name field not found."
    )


# ============================================================
# CLEAN COORDINATES
# ============================================================

clean = raw_df[
    [
        name_column,
        "latitude",
        "longitude"
    ]
].copy()


clean = clean.rename(
    columns={
        name_column:
            "police_property"
    }
)


clean["latitude"] = pd.to_numeric(
    clean["latitude"],
    errors="coerce"
)

clean["longitude"] = pd.to_numeric(
    clean["longitude"],
    errors="coerce"
)


clean = clean.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
)


# ============================================================
# HYDERABAD BOUNDARY
# ============================================================

clean = clean[
    (clean["latitude"] >= 17.20)
    &
    (clean["latitude"] <= 17.60)
    &
    (clean["longitude"] >= 78.20)
    &
    (clean["longitude"] <= 78.70)
].copy()


# ============================================================
# SELECT POLICE STATION RECORDS
# ============================================================

name_lower = (
    clean["police_property"]
    .astype(str)
    .str.lower()
)


# Keep records that clearly represent police stations.

station_mask = (
    name_lower.str.contains(
        r"\bps\b|police station|police_station",
        regex=True,
        na=False
    )
)


clean = clean[
    station_mask
].copy()


# ============================================================
# REMOVE CLEARLY NON-STATION PROPERTIES
# ============================================================

exclude_words = [
    "open land",
    "stadium",
    "command control",
    "quarters",
    "barrack",
    "barracks"
]


for word in exclude_words:

    clean = clean[
        ~clean["police_property"]
        .astype(str)
        .str.lower()
        .str.contains(
            word,
            regex=False,
            na=False
        )
    ]


# Remove duplicate coordinates.

clean = clean.drop_duplicates(
    subset=[
        "latitude",
        "longitude"
    ]
).reset_index(
    drop=True
)


# ============================================================
# SAVE CLEAN POLICE DATA
# ============================================================

clean.to_csv(
    CLEAN_POLICE_FILE,
    index=False
)


print()
print(
    "======================================"
)

print(
    "CLEAN POLICE DATA CREATED"
)

print(
    "======================================"
)

print(
    "Raw records:",
    len(raw_df)
)

print(
    "Actual police-station candidates:",
    len(clean)
)

print()
print(
    "Saved to:"
)

print(
    CLEAN_POLICE_FILE
)


# ============================================================
# LOAD CURRENT DATASET
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
    "centroid_lat",
    "centroid_lon",
    "police_coverage_score"
]


missing = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing:

    raise RuntimeError(
        "Dataset missing required columns: "
        + ", ".join(missing)
    )


# ============================================================
# VALIDATE AREA COORDINATES
# ============================================================

df["centroid_lat"] = pd.to_numeric(
    df["centroid_lat"],
    errors="coerce"
)

df["centroid_lon"] = pd.to_numeric(
    df["centroid_lon"],
    errors="coerce"
)


if df[
    [
        "centroid_lat",
        "centroid_lon"
    ]
].isna().any().any():

    raise RuntimeError(
        "Some areas have missing centroid coordinates."
    )


# ============================================================
# POLICE STATION RECORDS
# ============================================================

station_records = clean[
    [
        "police_property",
        "latitude",
        "longitude"
    ]
].to_dict(
    "records"
)


if not station_records:

    raise RuntimeError(
        "No valid police stations available."
    )


# ============================================================
# CALCULATE NEAREST POLICE STATION
# ============================================================

print()
print(
    "Calculating nearest current police station..."
)


nearest_names = []
nearest_distances = []
police_scores = []


for _, area in df.iterrows():

    area_lat = float(
        area["centroid_lat"]
    )

    area_lon = float(
        area["centroid_lon"]
    )

    nearest_station = None
    nearest_distance = float("inf")


    for station in station_records:

        distance = haversine_distance(
            area_lat,
            area_lon,
            float(station["latitude"]),
            float(station["longitude"])
        )

        if distance < nearest_distance:

            nearest_distance = distance
            nearest_station = station


    # ========================================================
    # DISTANCE TO POLICE SCORE
    #
    # 0 km  -> 1.0
    # 1 km  -> 0.667
    # 2 km  -> 0.500
    # 5 km  -> 0.286
    # 10 km -> 0.167
    # 20 km -> 0.091
    # ========================================================

    score = (
        1.0
        /
        (
            1.0
            +
            nearest_distance / 2.0
        )
    )


    score = max(
        0.0,
        min(
            1.0,
            score
        )
    )


    nearest_names.append(
        nearest_station[
            "police_property"
        ]
    )

    nearest_distances.append(
        nearest_distance
    )

    police_scores.append(
        score
    )


# ============================================================
# UPDATE POLICE FEATURE
# ============================================================

df[
    "nearest_police_station"
] = nearest_names

df[
    "nearest_police_distance_km"
] = nearest_distances

df[
    "police_coverage_score"
] = police_scores


# ============================================================
# POLICE AREA DATASET
# ============================================================

police_area_df = df[
    [
        "area",
        "nearest_police_station",
        "nearest_police_distance_km",
        "police_coverage_score"
    ]
].copy()


police_area_df[
    "nearest_police_distance_km"
] = (
    police_area_df[
        "nearest_police_distance_km"
    ].round(3)
)


police_area_df[
    "police_coverage_score"
] = (
    police_area_df[
        "police_coverage_score"
    ].round(4)
)


police_area_df.to_csv(
    POLICE_AREA_FILE,
    index=False
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
    f"dataset_before_police_{timestamp}.csv"
)


shutil.copy2(
    DATASET_FILE,
    backup_file
)


# ============================================================
# SAVE UPDATED DATASET
# ============================================================

df.to_csv(
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
    "POLICE FEATURE UPDATED"
)

print(
    "======================================"
)

print(
    "Actual police-station candidates:",
    len(clean)
)

print(
    "Areas processed:",
    len(df)
)

print()
print(
    "Police coverage statistics:"
)

print(
    df[
        "police_coverage_score"
    ].describe()
)

print()
print(
    "Nearest police examples:"
)

examples = [
    "Banjara Hills",
    "Ameerpet",
    "Madhuranagar",
    "Jubilee Hills",
    "Miyapur"
]

print(
    police_area_df[
        police_area_df["area"].isin(
            examples
        )
    ].to_string(
        index=False
    )
)

print()
print(
    "Updated:"
)

print(
    DATASET_FILE
)

print()
print(
    "Police area data:"
)

print(
    POLICE_AREA_FILE
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
    "Police API update complete."
)