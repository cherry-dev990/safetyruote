import joblib
import pandas as pd

from pathlib import Path


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent

MODEL_FILE = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "safety_model.pkl"
)

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "full_hyderabad_dataset.csv"
)


# ==================================================
# FEATURES
# ==================================================

FEATURES = [

    "police_coverage_score",

    "crime_rate_per_10k",

    "cctv_count",

    "amenity_count"

]


# ==================================================
# LOAD MODEL + DATA
# ==================================================

model = joblib.load(
    MODEL_FILE
)

area_data = pd.read_csv(
    DATA_FILE
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


# ==================================================
# PREDICT FROM FEATURES
# ==================================================

def predict_safety(

    police_coverage_score,

    crime_rate,

    cctv,

    amenities

):

    features = {

        "police_coverage_score":
            police_coverage_score,

        "crime_rate_per_10k":
            crime_rate,

        "cctv_count":
            cctv,

        "amenity_count":
            amenities

    }


    input_data = pd.DataFrame(

        [features],

        columns=FEATURES

    )


    prediction = float(
        model.predict(
            input_data
        )[0]
    )


    score = max(
        0,
        min(
            100,
            prediction
        )
    )


    return {

        "safety_score":
            round(score, 2),

        "risk_level":
            get_risk_level(score)

    }


# ==================================================
# PREDICT FROM AREA
# ==================================================

def predict_area(area_name):

    area_name = (
        area_name
        .strip()
    )


    matches = area_data[

        area_data["area"]
        .astype(str)
        .str.strip()
        .str.lower()

        ==

        area_name.lower()

    ]


    if matches.empty:

        return {

            "error":
                f"Area '{area_name}' not found"

        }


    row = matches.iloc[0]


    result = predict_safety(

        police_coverage_score=
            row["police_coverage_score"],

        crime_rate=
            row["crime_rate_per_10k"],

        cctv=
            row["cctv_count"],

        amenities=
            row["amenity_count"]

    )


    result.update({

        "area":
            row["area"],

        "latitude":
            row["centroid_lat"],

        "longitude":
            row["centroid_lon"]

    })


    return result


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    test_areas = [

        "Gachibowli",

        "Ghatkesar",

        "Masab Tank",

        "Nallagandla",

        "Narsingi"

    ]


    print()
    print("======================================")
    print("AREA SAFETY TEST")
    print("======================================")


    for area in test_areas:

        print()

        result = predict_area(
            area
        )

        print(
            result
        )