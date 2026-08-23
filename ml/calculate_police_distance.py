import pandas as pd
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"

AREAS_FILE = RAW_DATA / "areas.csv"

POLICE_FILE = (
    RAW_DATA / "police_stations_clean.csv"
)

OUTPUT_FILE = (
    RAW_DATA / "police_area_distance.csv"
)


# ==================================================
# LOAD DATA
# ==================================================

print("Loading areas...")

areas = pd.read_csv(
    AREAS_FILE
)

print(
    "Areas:",
    len(areas)
)


print()
print("Loading clean police candidates...")

police = pd.read_csv(
    POLICE_FILE
)

print(
    "Police candidates:",
    len(police)
)


# ==================================================
# CLEAN COORDINATES
# ==================================================

areas["centroid_lat"] = pd.to_numeric(
    areas["centroid_lat"],
    errors="coerce"
)

areas["centroid_lon"] = pd.to_numeric(
    areas["centroid_lon"],
    errors="coerce"
)

police["latitude"] = pd.to_numeric(
    police["latitude"],
    errors="coerce"
)

police["longitude"] = pd.to_numeric(
    police["longitude"],
    errors="coerce"
)


areas = areas.dropna(
    subset=[
        "centroid_lat",
        "centroid_lon"
    ]
)

police = police.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
)


# ==================================================
# HAVERSINE DISTANCE
# ==================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth_radius = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)

    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return earth_radius * c


# ==================================================
# FIND NEAREST CANDIDATE
# ==================================================

print()
print(
    "Calculating nearest police candidate..."
)


results = []


for _, area in areas.iterrows():

    area_name = area["area"]

    area_lat = area["centroid_lat"]

    area_lon = area["centroid_lon"]


    best_station = None

    best_distance = float("inf")


    for _, station in police.iterrows():

        distance = haversine_km(

            area_lat,
            area_lon,

            station["latitude"],
            station["longitude"]

        )


        if distance < best_distance:

            best_distance = distance

            best_station = station


    results.append({

        "area":
            area_name,

        "centroid_lat":
            area_lat,

        "centroid_lon":
            area_lon,

        "nearest_police_station":
            best_station[
                "police_property"
            ],

        "nearest_police_distance_km":
            round(
                best_distance,
                3
            ),

        "police_latitude":
            best_station[
                "latitude"
            ],

        "police_longitude":
            best_station[
                "longitude"
            ]

    })


result_df = pd.DataFrame(
    results
)


# ==================================================
# POLICE PROXIMITY SCORE
# ==================================================

# 0 km = score near 1
# Increasing distance = lower score
#
# This is a temporary mathematical
# transformation. We can calibrate it
# after inspecting the distances.

result_df[
    "police_proximity_score"
] = (

    1
    /
    (
        1
        +
        result_df[
            "nearest_police_distance_km"
        ]
    )

).round(4)


# ==================================================
# SAVE
# ==================================================

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==================================================
# SHOW IMPORTANT AREAS
# ==================================================

print()
print(
    "======================================"
)

print(
    "NEAREST POLICE RESULTS"
)

print(
    "======================================"
)


important_areas = [

    "Gachibowli",
    "Kondapur",
    "Kukatpally",
    "Miyapur",
    "Manikonda",
    "Hitech City",
    "Madhapur",
    "Nallagandla",
    "Madinaguda",
    "Narsingi",
    "Ameerpet",
    "Banjara Hills",
    "Jubilee Hills"

]


available = result_df[
    result_df["area"].isin(
        important_areas
    )
]


print(
    available[
        [
            "area",
            "nearest_police_station",
            "nearest_police_distance_km",
            "police_proximity_score"
        ]
    ]
    .sort_values(
        "area"
    )
    .to_string(
        index=False
    )
)


# ==================================================
# DISTANCE STATISTICS
# ==================================================

print()
print(
    "======================================"
)

print(
    "DISTANCE STATISTICS"
)

print(
    "======================================"
)


print(
    result_df[
        "nearest_police_distance_km"
    ].describe()
)


print()
print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)