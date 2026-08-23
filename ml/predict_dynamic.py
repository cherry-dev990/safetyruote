import pandas as pd
import joblib
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_FILE = (
    PROJECT_ROOT
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
# MODEL FEATURES
# ==================================================

FEATURES = [
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count"
]


# ==================================================
# LOAD MODEL
# ==================================================

print("Loading safety model...")

model = joblib.load(
    MODEL_FILE
)

print(
    "Model loaded successfully."
)


# ==================================================
# LOAD CURRENT DATA
# ==================================================

print()
print("Loading latest dataset...")

df = pd.read_csv(
    DATA_FILE
)

print(
    "Areas available:",
    len(df)
)


# ==================================================
# FIND AREA
# ==================================================

area_name = input(
    "\nEnter Hyderabad area name: "
).strip()


matches = df[
    df["area"]
    .astype(str)
    .str.lower()
    .eq(area_name.lower())
]


if matches.empty:

    print()
    print(
        "Area not found."
    )

    print()
    print(
        "Example areas:"
    )

    print(
        df["area"]
        .head(20)
        .to_string(
            index=False
        )
    )

    raise SystemExit(1)


# ==================================================
# GET FEATURES
# ==================================================

row = matches.iloc[0]


input_data = pd.DataFrame(
    [[
        row["crime_rate_per_10k"],
        row["cctv_count"],
        row["police_coverage_score"],
        row["amenity_count"]
    ]],
    columns=FEATURES
)


# ==================================================
# PREDICT
# ==================================================

prediction = model.predict(
    input_data
)[0]


prediction = max(
    0,
    min(
        100,
        float(prediction)
    )
)


# ==================================================
# RISK LEVEL
# ==================================================

if prediction < 35:

    risk = "HIGH"

elif prediction < 60:

    risk = "MEDIUM"

else:

    risk = "LOW"


# ==================================================
# DISPLAY
# ==================================================

print()
print(
    "======================================"
)

print(
    "DYNAMIC SAFETY PREDICTION"
)

print(
    "======================================"
)

print(
    "Area:",
    row["area"]
)

print()

print(
    "Current features:"
)

print(
    "Crime rate / 10k :",
    row["crime_rate_per_10k"]
)

print(
    "CCTV count       :",
    row["cctv_count"]
)

print(
    "Police score     :",
    row["police_coverage_score"]
)

print(
    "Public places    :",
    row["amenity_count"]
)

print()

print(
    "Predicted safety:",
    f"{prediction:.2f}/100"
)

print(
    "Risk level:",
    risk
)

print(
    "======================================"
)