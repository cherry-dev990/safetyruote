import requests
import pandas as pd
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"

OUTPUT_FILE = (
    RAW_DATA / "police_stations_clean.csv"
)


# ==================================================
# TGRAC API
# ==================================================

API_URL = (
    "https://tgrac.telangana.gov.in/"
    "arcgis/rest/services/"
    "PoliceProperties_Folder/"
    "Police_Properties2/"
    "MapServer/1/query"
)


# ==================================================
# DOWNLOAD
# ==================================================

print("Fetching Hyderabad police data...")


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json"
}


response = requests.get(
    API_URL,
    params=params,
    timeout=30
)


response.raise_for_status()

data = response.json()


if "error" in data:

    raise RuntimeError(
        data["error"]
    )


features = data.get(
    "features",
    []
)


print(
    "Records received:",
    len(features)
)


# ==================================================
# CONVERT
# ==================================================

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


    name = str(
        attributes.get(
            "Name_of_the_Property",
            ""
        )
    ).strip()


    latitude = geometry.get(
        "y"
    )

    longitude = geometry.get(
        "x"
    )


    records.append({

        "object_id":
            attributes.get(
                "OBJECTID"
            ),

        "district":
            attributes.get(
                "District_Name"
            ),

        "police_property":
            name,

        "mandal":
            attributes.get(
                "Mandal_Name"
            ),

        "ward":
            attributes.get(
                "Ward"
            ),

        "zone":
            attributes.get(
                "Zone"
            ),

        "latitude":
            latitude,

        "longitude":
            longitude

    })


df = pd.DataFrame(
    records
)


# ==================================================
# CLEAN
# ==================================================

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)


df = df.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
)


# ==================================================
# NORMALIZE NAME
# ==================================================

df["name_upper"] = (
    df["police_property"]
    .str.upper()
    .str.replace(
        "\r",
        " ",
        regex=False
    )
    .str.replace(
        "\n",
        " ",
        regex=False
    )
    .str.strip()
)


# ==================================================
# IDENTIFY POLICE STATIONS
# ==================================================

# We accept names containing PS.
#
# Examples:
#
# Banjara Hills PS
# Golconda PS
# Habeebnagar_PS
# Humayun_nagar_PS_&_ACP...
#
# We deliberately do NOT automatically accept:
#
# Police Quarters
# Open Land
# Stadium
# Command Control
# etc.


df["is_police_station"] = (
    df["name_upper"]
    .str.contains(
        r"\bPS\b|_PS| PS_|_PS_",
        regex=True,
        na=False
    )
)


# Remove obvious non-station properties.

exclude_words = (
    "OPEN LAND",
    "QUARTERS",
    "STADIUM",
    "COMMAND CONTROL",
    "OUT POST",
    "OUTPOST"
)


for word in exclude_words:

    df.loc[
        df["name_upper"].str.contains(
            word,
            regex=False,
            na=False
        ),
        "is_police_station"
    ] = False


clean = df[
    df["is_police_station"]
].copy()


# ==================================================
# REMOVE DUPLICATES
# ==================================================

clean = (
    clean
    .drop_duplicates(
        subset=[
            "police_property",
            "latitude",
            "longitude"
        ]
    )
    .reset_index(
        drop=True
    )
)


# ==================================================
# REMOVE HELPER COLUMN
# ==================================================

clean = clean[
    [
        "object_id",
        "district",
        "police_property",
        "mandal",
        "ward",
        "zone",
        "latitude",
        "longitude"
    ]
]


# ==================================================
# SAVE
# ==================================================

clean.to_csv(
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
    "CLEAN POLICE DATA CREATED"
)

print(
    "======================================"
)

print(
    "Raw records:",
    len(df)
)

print(
    "Actual police-station candidates:",
    len(clean)
)

print()

print(
    clean[
        [
            "police_property",
            "latitude",
            "longitude"
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