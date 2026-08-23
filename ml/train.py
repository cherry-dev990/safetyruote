import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import joblib


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

MODEL_DIR = (
    PROJECT_ROOT
    / "models"
)

MODEL_FILE = (
    MODEL_DIR
    / "safety_model.pkl"
)


# Create models directory if needed

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# LOAD DATA
# ==================================================

print("Loading dataset...")

df = pd.read_csv(
    DATA_FILE
)

print(
    "Rows:",
    len(df)
)


# ==================================================
# FEATURES
# ==================================================

FEATURES = [
    "crime_rate_per_10k",
    "cctv_count",
    "police_coverage_score",
    "amenity_count"
]

TARGET = "safety_score"


# ==================================================
# CHECK COLUMNS
# ==================================================

missing = [
    column
    for column in FEATURES + [TARGET]
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
# PREPARE DATA
# ==================================================

X = df[
    FEATURES
].copy()

y = df[
    TARGET
].copy()


X = X.apply(
    pd.to_numeric,
    errors="coerce"
)

y = pd.to_numeric(
    y,
    errors="coerce"
)


valid_rows = (
    X.notna().all(axis=1)
    &
    y.notna()
)


X = X[
    valid_rows
]

y = y[
    valid_rows
]


print(
    "Valid rows:",
    len(X)
)


# ==================================================
# TRAIN / TEST SPLIT
# ==================================================

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )
)


print()
print(
    "Training rows:",
    len(X_train)
)

print(
    "Testing rows:",
    len(X_test)
)


# ==================================================
# RANDOM FOREST
# ==================================================

print()
print(
    "Training Random Forest..."
)


model = RandomForestRegressor(

    n_estimators=300,

    max_depth=None,

    min_samples_split=2,

    min_samples_leaf=1,

    random_state=42,

    n_jobs=-1

)


model.fit(
    X_train,
    y_train
)


# ==================================================
# PREDICTION
# ==================================================

y_pred = model.predict(
    X_test
)


# ==================================================
# METRICS
# ==================================================

mae = mean_absolute_error(
    y_test,
    y_pred
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred
    )
)

r2 = r2_score(
    y_test,
    y_pred
)


print()
print(
    "======================================"
)

print(
    "MODEL PERFORMANCE"
)

print(
    "======================================"
)

print(
    f"MAE  : {mae:.2f}"
)

print(
    f"RMSE : {rmse:.2f}"
)

print(
    f"R²   : {r2:.4f}"
)


# ==================================================
# FEATURE IMPORTANCE
# ==================================================

importance = pd.DataFrame({

    "feature":
        FEATURES,

    "importance":
        model.feature_importances_

})


importance = (
    importance
    .sort_values(
        "importance",
        ascending=False
    )
)


print()
print(
    "======================================"
)

print(
    "FEATURE IMPORTANCE"
)

print(
    "======================================"
)

print(
    importance.to_string(
        index=False
    )
)


# ==================================================
# SAVE MODEL
# ==================================================

joblib.dump(
    model,
    MODEL_FILE
)


print()
print(
    "Model saved to:"
)

print(
    MODEL_FILE
)


print()
print(
    "======================================"
)

print(
    "MODEL TRAINING COMPLETE"
)

print(
    "======================================"
)