import pandas as pd
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

# preprocessing.py is inside:
# C:\safetyroute\ml\
#
# parent       -> C:\safetyroute\ml
# parent.parent -> C:\safetyroute

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"

PROCESSED_DATA.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# LOAD DATASETS
# ==================================================

print("Loading final datasets...")

areas = pd.read_csv(
    RAW_DATA / "areas.csv"
)

crime = pd.read_csv(
    RAW_DATA / "crime_rates.csv"
)

cctv = pd.read_csv(
    RAW_DATA / "cctv.csv"
)

police = pd.read_csv(
    RAW_DATA / "police_stations.csv"
)

amenities = pd.read_csv(
    RAW_DATA / "amenities.csv"
)


print()
print("Datasets loaded successfully.")

print("Areas:", len(areas))
print("Crime records:", len(crime))
print("CCTV records:", len(cctv))
print("Police records:", len(police))
print("Amenities:", len(amenities))


# ==================================================
# CLEAN AREA NAMES
# ==================================================

print()
print("Cleaning area names...")


for df in [
    areas,
    crime,
    cctv,
    police
]:

    if "area" in df.columns:

        df["area"] = (
            df["area"]
            .astype(str)
            .str.strip()
        )


# ==================================================
# POLICE FEATURE
# ==================================================

print()
print("Processing police stations...")


# The current police_stations.csv contains:
#
# area
# police_station
#
# It does NOT contain:
# latitude
# longitude
# station status
#
# Therefore we cannot calculate actual
# police-station distance yet.
#
# For now we create a temporary
# police coverage score.


police["police_station"] = (
    police["police_station"]
    .astype(str)
    .str.strip()
)


# Count how many areas are associated
# with each police station.

station_area_count = (
    police[
        "police_station"
    ]
    .value_counts()
)


# Map station name -> number of areas

police["station_area_count"] = (
    police["police_station"]
    .map(station_area_count)
)


# Create temporary coverage score.
#
# This is only a proxy until we connect
# the Hyderabad police GIS API.

police["police_coverage_score"] = (
    police["station_area_count"]
    .rank(
        method="average",
        pct=True,
        ascending=False
    )
)


# Keep one record per area.

police_features = (
    police[
        [
            "area",
            "police_station",
            "police_coverage_score"
        ]
    ]
    .drop_duplicates(
        subset=["area"]
    )
    .copy()
)


# ==================================================
# CCTV FEATURE
# ==================================================

print()
print("Processing CCTV...")


cctv_features = cctv[
    [
        "area",
        "cctv_count"
    ]
].copy()


cctv_features["cctv_count"] = (
    pd.to_numeric(
        cctv_features["cctv_count"],
        errors="coerce"
    )
    .fillna(0)
)


# ==================================================
# CRIME FEATURE
# ==================================================

print()
print("Processing crime data...")


crime_features = crime[
    [
        "area",
        "crime_rate_per_10k"
    ]
].copy()


crime_features["crime_rate_per_10k"] = (
    pd.to_numeric(
        crime_features["crime_rate_per_10k"],
        errors="coerce"
    )
)


# ==================================================
# PUBLIC PLACES / AMENITIES
# ==================================================

print()
print("Processing public places...")


# Get area coordinates.

area_coordinates = areas[
    [
        "area",
        "centroid_lat",
        "centroid_lon"
    ]
].copy()


# Convert coordinates to numbers.

area_coordinates["centroid_lat"] = (
    pd.to_numeric(
        area_coordinates["centroid_lat"],
        errors="coerce"
    )
)

area_coordinates["centroid_lon"] = (
    pd.to_numeric(
        area_coordinates["centroid_lon"],
        errors="coerce"
    )
)


# Remove invalid area coordinates.

area_coordinates = (
    area_coordinates
    .dropna(
        subset=[
            "centroid_lat",
            "centroid_lon"
        ]
    )
)


# Convert amenity coordinates.

amenities["latitude"] = (
    pd.to_numeric(
        amenities["latitude"],
        errors="coerce"
    )
)

amenities["longitude"] = (
    pd.to_numeric(
        amenities["longitude"],
        errors="coerce"
    )
)


# Remove amenities with invalid coordinates.

amenities = (
    amenities
    .dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )
)


# ==================================================
# FIND NEAREST AREA
# ==================================================

def nearest_area(
    latitude,
    longitude
):

    distances = (

        (
            area_coordinates["centroid_lat"]
            - latitude
        ) ** 2

        +

        (
            area_coordinates["centroid_lon"]
            - longitude
        ) ** 2

    )


    index = distances.idxmin()


    return area_coordinates.loc[
        index,
        "area"
    ]


# Assign every public place to
# its nearest Hyderabad area.

print(
    "Assigning public places to areas..."
)


amenities["area"] = amenities.apply(

    lambda row:
        nearest_area(
            row["latitude"],
            row["longitude"]
        ),

    axis=1

)


# Count public places per area.

amenity_features = (

    amenities

    .groupby("area")

    .size()

    .reset_index(
        name="amenity_count"
    )

)


# ==================================================
# BUILD MASTER DATASET
# ==================================================

print()
print("Building final master dataset...")


master = areas[
    [
        "area",
        "centroid_lat",
        "centroid_lon"
    ]
].copy()


# --------------------------------------------------
# Add crime
# --------------------------------------------------

master = master.merge(

    crime_features,

    on="area",

    how="left"

)


# --------------------------------------------------
# Add CCTV
# --------------------------------------------------

master = master.merge(

    cctv_features,

    on="area",

    how="left"

)


# --------------------------------------------------
# Add police
# --------------------------------------------------

master = master.merge(

    police_features,

    on="area",

    how="left"

)


# --------------------------------------------------
# Add public places
# --------------------------------------------------

master = master.merge(

    amenity_features,

    on="area",

    how="left"

)


# ==================================================
# FILL MISSING VALUES
# ==================================================

print()
print("Cleaning numeric features...")


numeric_columns = [

    "crime_rate_per_10k",

    "cctv_count",

    "police_coverage_score",

    "amenity_count"

]


for column in numeric_columns:

    master[column] = (

        pd.to_numeric(

            master[column],

            errors="coerce"

        )

        .fillna(0)

    )


# ==================================================
# REMOVE DUPLICATE AREAS
# ==================================================

master = (
    master
    .drop_duplicates(
        subset=["area"]
    )
    .reset_index(
        drop=True
    )
)


# ==================================================
# SAVE PROCESSED DATASET
# ==================================================

output_file = (

    PROCESSED_DATA

    / "full_hyderabad_dataset.csv"

)


master.to_csv(

    output_file,

    index=False

)


# ==================================================
# REPORT
# ==================================================

print()
print("======================================")
print("PREPROCESSING COMPLETE")
print("======================================")


print()
print("Rows:", len(master))


print()
print("Final columns:")


for column in master.columns:

    print(
        " -",
        column
    )


print()
print("Missing values:")

print(
    master[
        numeric_columns
    ]
    .isnull()
    .sum()
)


print()
print("Final feature statistics:")

print(
    master[
        numeric_columns
    ]
    .describe()
)


print()
print("Saved to:")

print(
    output_file
)


print()
print("======================================")
print("READY FOR SAFETY INDEX")
print("======================================")