import os
import math
import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        ".."
    )
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "dynamic",
    "latest_hyderabad_dataset.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "safety_model.pkl"
)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading safety dataset...")

df = pd.read_csv(DATA_PATH)

print(
    f"Loaded {len(df)} Hyderabad areas."
)


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading safety model...")

model = joblib.load(MODEL_PATH)

print("Safety model loaded.")


# ============================================================
# MODEL FEATURES
#
# New model:
#
# Crime          40%
# CCTV           30%
# Police         20%
# Public Places  10%
# ============================================================

FEATURE_COLUMNS = [
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count",
]


# ============================================================
# VALIDATE FEATURES
# ============================================================

missing_columns = [
    column
    for column in FEATURE_COLUMNS
    if column not in df.columns
]

if missing_columns:

    raise RuntimeError(
        "Missing ML features: "
        + ", ".join(missing_columns)
    )


# ============================================================
# PRE-CALCULATE ML SCORE FOR EVERY AREA
# ============================================================

print("Calculating area safety scores...")

area_features = df[
    FEATURE_COLUMNS
].copy()

area_features = area_features.apply(
    pd.to_numeric,
    errors="coerce"
)

if area_features.isna().any().any():

    raise RuntimeError(
        "ML dataset contains invalid or missing "
        "values in model features."
    )


df["base_safety_score"] = model.predict(
    area_features
)

df["base_safety_score"] = (
    df["base_safety_score"]
    .clip(0, 100)
)


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Distance between two GPS coordinates.
    Returns kilometers.
    """

    radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


# ============================================================
# FIND NEAREST AREAS
# ============================================================

def find_nearest_areas(
    latitude,
    longitude,
    count=3
):
    """
    Fast nearest-area lookup.
    """

    lat = float(latitude)
    lon = float(longitude)

    lat_km = 111.0

    lon_km = (
        111.0
        *
        math.cos(
            math.radians(lat)
        )
    )

    lat_diff = (
        df["centroid_lat"] - lat
    ) * lat_km

    lon_diff = (
        df["centroid_lon"] - lon
    ) * lon_km

    distances = (
        lat_diff ** 2
        +
        lon_diff ** 2
    ) ** 0.5

    nearest_indices = (
        distances
        .nsmallest(count)
        .index
    )

    results = []

    for index in nearest_indices:

        area = df.loc[index]

        results.append(
            (
                float(
                    distances.loc[index]
                ),
                area
            )
        )

    return results


# ============================================================
# TIME OF DAY
# ============================================================

def is_night(hour):
    """
    Night period:
    20:00 -> 05:00
    """

    return (
        hour >= 20
        or
        hour < 5
    )


# ============================================================
# NIGHT SAFETY ADJUSTMENT
# ============================================================

def calculate_time_adjustment(
    area,
    hour
):
    """
    Deterministic night adjustment.

    At night:
    - Better CCTV improves safety.
    - Lower crime improves safety.

    The trained Random Forest remains unchanged.
    """

    if not is_night(hour):

        return 0.0


    # --------------------------------------------------------
    # CCTV
    # --------------------------------------------------------

    cctv_values = df[
        "cctv_count"
    ]

    cctv_min = cctv_values.min()

    cctv_max = cctv_values.max()

    cctv_range = (
        cctv_max - cctv_min
    )


    if cctv_range > 0:

        cctv_ratio = (

            (
                float(
                    area[
                        "cctv_count"
                    ]
                )
                - cctv_min
            )
            /
            cctv_range

        )

    else:

        cctv_ratio = 0.5


    # --------------------------------------------------------
    # CRIME
    # --------------------------------------------------------

    crime_values = df[
        "crime_rate_per_10k"
    ]

    crime_min = crime_values.min()

    crime_max = crime_values.max()

    crime_range = (
        crime_max - crime_min
    )


    if crime_range > 0:

        crime_ratio = (

            (
                float(
                    area[
                        "crime_rate_per_10k"
                    ]
                )
                - crime_min
            )
            /
            crime_range

        )

    else:

        crime_ratio = 0.5


    # --------------------------------------------------------
    # NIGHT EFFECTS
    # --------------------------------------------------------

    cctv_effect = (
        (cctv_ratio - 0.5)
        * 5
    )

    crime_effect = (
        (0.5 - crime_ratio)
        * 7
    )


    return (
        cctv_effect
        +
        crime_effect
    )


# ============================================================
# POINT SAFETY
# ============================================================

def calculate_point_safety(
    latitude,
    longitude,
    hour=14
):
    """
    Calculate safety at one route point using
    the three nearest safety areas.
    """

    nearest = find_nearest_areas(
        latitude,
        longitude,
        count=3
    )

    if not nearest:

        raise ValueError(
            "No nearby safety areas found."
        )


    weighted_score = 0.0

    total_weight = 0.0

    contributing_areas = []


    for distance, area in nearest:

        weight = 1 / max(
            distance,
            0.05
        )


        base_score = float(
            area[
                "base_safety_score"
            ]
        )


        time_adjustment = (
            calculate_time_adjustment(
                area,
                hour
            )
        )


        adjusted_score = (
            base_score
            +
            time_adjustment
        )


        adjusted_score = max(
            0,
            min(
                100,
                adjusted_score
            )
        )


        weighted_score += (
            adjusted_score
            *
            weight
        )

        total_weight += weight


        contributing_areas.append({

            "area":
                str(
                    area["area"]
                ),

            "distance_km":
                round(
                    distance,
                    3
                ),

            "base_score":
                round(
                    base_score,
                    2
                ),

            "time_adjustment":
                round(
                    time_adjustment,
                    2
                ),

            "adjusted_score":
                round(
                    adjusted_score,
                    2
                )

        })


    final_score = (
        weighted_score
        /
        total_weight
    )


    final_score = max(
        0,
        min(
            100,
            final_score
        )
    )


    if final_score >= 70:

        risk = "LOW"

    elif final_score >= 40:

        risk = "MEDIUM"

    else:

        risk = "HIGH"


    return {

        "latitude":
            round(
                latitude,
                6
            ),

        "longitude":
            round(
                longitude,
                6
            ),

        "safety_score":
            round(
                final_score,
                2
            ),

        "risk_level":
            risk,

        "nearest_areas":
            contributing_areas

    }


# ============================================================
# ROUTE SAMPLING
# ============================================================

def sample_route(
    coordinates,
    max_points=20
):
    """
    Reduce very large route geometry
    to manageable safety-analysis points.
    """

    if not coordinates:

        return []


    if len(coordinates) <= max_points:

        return coordinates


    indexes = []

    total = len(coordinates)


    for i in range(
        max_points
    ):

        index = round(

            i
            *
            (total - 1)
            /
            (max_points - 1)

        )

        indexes.append(
            index
        )


    return [
        coordinates[i]
        for i in indexes
    ]


# ============================================================
# ROUTE DISTANCE
# ============================================================

def calculate_route_distance(
    coordinates
):
    """
    Calculate approximate route distance.
    """

    total = 0.0


    for i in range(
        1,
        len(coordinates)
    ):

        lat1, lon1 = coordinates[
            i - 1
        ]

        lat2, lon2 = coordinates[
            i
        ]


        total += haversine_distance(

            float(lat1),
            float(lon1),

            float(lat2),
            float(lon2)

        )


    return total


# ============================================================
# ROUTE SAFETY
# ============================================================

def analyze_route(
    coordinates,
    hour=14
):
    """
    Analyze an actual route.

    Route
       ↓
    Sample points
       ↓
    Find nearest safety areas
       ↓
    ML score
       ↓
    Night adjustment
       ↓
    Segment scores
       ↓
    Route score
    """

    if not coordinates:

        raise ValueError(
            "Route contains no coordinates."
        )


    sampled = sample_route(
        coordinates,
        max_points=10
    )


    point_scores = []


    for coordinate in sampled:

        latitude = float(
            coordinate[0]
        )

        longitude = float(
            coordinate[1]
        )


        result = calculate_point_safety(

            latitude,
            longitude,

            hour

        )


        point_scores.append(
            result
        )


    if not point_scores:

        raise ValueError(
            "No route points could be analyzed."
        )


    scores = [

        point["safety_score"]

        for point in point_scores

    ]


    # ========================================================
    # ROUTE STATISTICS
    # ========================================================

    average_score = (
        sum(scores)
        /
        len(scores)
    )


    minimum_score = min(
        scores
    )


    # --------------------------------------------------------
    # Low-score segments
    # --------------------------------------------------------

    sorted_scores = sorted(
        scores
    )


    bottom_count = max(
        1,
        math.ceil(
            len(sorted_scores)
            * 0.25
        )
    )


    danger_average = (

        sum(
            sorted_scores[
                :bottom_count
            ]
        )
        /
        bottom_count

    )


    # --------------------------------------------------------
    # Final route score
    #
    # 50% overall route
    # 30% dangerous sections
    # 20% worst section
    # --------------------------------------------------------

    route_score = (

        average_score
        * 0.50

        +

        danger_average
        * 0.30

        +

        minimum_score
        * 0.20

    )


    route_score = max(
        0,
        min(
            100,
            route_score
        )
    )


    # ========================================================
    # ROUTE RISK
    # ========================================================

    if route_score >= 70:

        risk_level = "LOW"

    elif route_score >= 40:

        risk_level = "MEDIUM"

    else:

        risk_level = "HIGH"


    # ========================================================
    # RISK EXPLANATIONS
    # ========================================================

    def get_risk_reasons(area):

        reasons = []

        crime_threshold = df[
            "crime_rate_per_10k"
        ].quantile(0.75)

        if float(
            area["crime_rate_per_10k"]
        ) >= crime_threshold:

            reasons.append({
                "factor": "crime",
                "message": "High crime risk",
                "value": round(
                    float(
                        area["crime_rate_per_10k"]
                    ),
                    2
                )
            })

        cctv_threshold = df[
            "cctv_count"
        ].quantile(0.25)

        if float(
            area["cctv_count"]
        ) <= cctv_threshold:

            reasons.append({
                "factor": "cctv",
                "message": "Low CCTV coverage",
                "value": int(
                    area["cctv_count"]
                )
            })

        police_threshold = df[
            "police_coverage_score"
        ].quantile(0.25)

        if float(
            area["police_coverage_score"]
        ) <= police_threshold:

            reasons.append({
                "factor": "police",
                "message": "Low police coverage",
                "value": round(
                    float(
                        area["police_coverage_score"]
                    ),
                    3
                )
            })

        amenity_threshold = df[
            "amenity_count"
        ].quantile(0.25)

        if float(
            area["amenity_count"]
        ) <= amenity_threshold:

            reasons.append({
                "factor": "public_places",
                "message": "Low availability of public places",
                "value": int(
                    area["amenity_count"]
                )
            })

        return reasons


    # ========================================================
    # DANGEROUS SEGMENTS
    # ========================================================

    dangerous_segments = []

    for point in point_scores:

        if point["safety_score"] >= 40:
            continue

        area_name = None
        area_record = None

        nearest_areas = point.get(
            "nearest_areas",
            []
        )

        if nearest_areas:

            area_name = nearest_areas[0].get(
                "area"
            )

            matches = df[
                df["area"].astype(str)
                == str(area_name)
            ]

            if not matches.empty:
                area_record = matches.iloc[0]

        reasons = []

        if area_record is not None:
            reasons = get_risk_reasons(
                area_record
            )

        if not reasons:
            reasons.append({
                "factor": "overall",
                "message": "Overall safety score is low",
                "value": round(
                    float(point["safety_score"]),
                    2
                )
            })

        dangerous_segments.append({

            "latitude":
                point["latitude"],

            "longitude":
                point["longitude"],

            "safety_score":
                point["safety_score"],

            "risk_level":
                "HIGH",

            "area":
                area_name,

            "reasons":
                reasons

        })


    # ========================================================
    # SAFEST / MOST DANGEROUS
    # ========================================================

    safest_point = max(

        point_scores,

        key=lambda x:
            x["safety_score"]

    )


    dangerous_point = min(

        point_scores,

        key=lambda x:
            x["safety_score"]

    )


    # ========================================================
    # ROUTE DISTANCE
    # ========================================================

    route_distance = (
        calculate_route_distance(
            coordinates
        )
    )


    # ========================================================
    # RESULT
    # ========================================================

    return {

        "safety_score":
            round(
                route_score,
                2
            ),

        "risk_level":
            risk_level,

        "average_score":
            round(
                average_score,
                2
            ),

        "minimum_score":
            round(
                minimum_score,
                2
            ),

        "danger_section_average":
            round(
                danger_average,
                2
            ),

        "route_distance_km":
            round(
                route_distance,
                3
            ),

        "analysis_hour":
            hour,

        "points_analyzed":
            len(point_scores),

        "safest_point":
            safest_point,

        "most_dangerous_point":
            dangerous_point,

        "dangerous_segments":
            dangerous_segments,

        "point_scores":
            point_scores

    }