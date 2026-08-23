import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

POLICE_UPDATER = (
    PROJECT_ROOT
    / "ml"
    / "update_police_data.py"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="SafeRoute API",
    description="AI-powered safety-aware navigation",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",

    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]


PRODUCTION_ORIGIN = os.getenv(
    "SAFEROUTE_FRONTEND_URL"
)


ALLOWED_ORIGINS = LOCAL_ORIGINS.copy()


if PRODUCTION_ORIGIN:

    PRODUCTION_ORIGIN = (
        PRODUCTION_ORIGIN
        .strip()
        .rstrip("/")
    )

    if PRODUCTION_ORIGIN not in ALLOWED_ORIGINS:

        ALLOWED_ORIGINS.append(
            PRODUCTION_ORIGIN
        )


app.add_middleware(
    CORSMiddleware,

    allow_origins=ALLOWED_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class RouteRequest(BaseModel):

    coordinates: List[List[float]]

    # Current hour, 0-23
    hour: Optional[int] = 14


# ============================================================
# POLICE DATA UPDATE
# ============================================================

def update_police_data():

    print("=" * 60)
    print("UPDATING POLICE DATA")
    print("=" * 60)

    if not POLICE_UPDATER.exists():

        print(
            "WARNING: Police updater not found:"
        )

        print(POLICE_UPDATER)

        print(
            "Continuing with the existing dataset."
        )

        return False


    try:

        result = subprocess.run(
            [
                sys.executable,
                str(POLICE_UPDATER)
            ],

            cwd=str(PROJECT_ROOT),

            capture_output=True,

            text=True,

            timeout=60
        )


        if result.returncode == 0:

            print(
                "Police data updated successfully."
            )

            if result.stdout:

                print(result.stdout)

            return True


        print(
            "WARNING: Police data update failed."
        )

        if result.stderr:

            print(result.stderr)

        print(
            "Continuing with the last validated dataset."
        )

        return False


    except subprocess.TimeoutExpired:

        print(
            "WARNING: Police data update timed out."
        )

        print(
            "Continuing with the last validated dataset."
        )

        return False


    except Exception as error:

        print(
            "WARNING: Could not update police data:"
        )

        print(error)

        print(
            "Continuing with the last validated dataset."
        )

        return False


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    print("=" * 60)
    print("STARTING SAFEROUTE API")
    print("=" * 60)

    print(
        "Allowed frontend origins:",
        ALLOWED_ORIGINS
    )

    print(
        "Using latest validated safety dataset."
    )

    print(
        "Police data refresh is available separately."
    )

    print("=" * 60)
    print("SAFEROUTE API STARTUP COMPLETE")
    print("=" * 60)


# ============================================================
# LOAD SAFETY ENGINE
# ============================================================

from backend.app.services.route_safety import analyze_route


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "SafeRoute API",
        "status": "running"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# ADMIN - UPDATE POLICE DATA
# ============================================================

@app.post("/admin/update-police-data")
def refresh_police_data():

    success = update_police_data()

    if success:

        return {
            "success": True,
            "message": "Police data updated successfully."
        }


    raise HTTPException(
        status_code=500,
        detail="Police data update failed."
    )


# ============================================================
# ROUTE SAFETY
# ============================================================

@app.post("/safety/analyze-route")
def analyze_route_endpoint(
    request: RouteRequest
):

    try:

        # ----------------------------------------------------
        # Validate coordinates
        # ----------------------------------------------------

        if not request.coordinates:

            raise HTTPException(
                status_code=400,
                detail="Route coordinates are required."
            )


        for coordinate in request.coordinates:

            if len(coordinate) != 2:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Each coordinate must contain "
                        "[latitude, longitude]."
                    )
                )


        # ----------------------------------------------------
        # Validate hour
        # ----------------------------------------------------

        if request.hour < 0 or request.hour > 23:

            raise HTTPException(
                status_code=400,
                detail="Hour must be between 0 and 23."
            )


        # ----------------------------------------------------
        # RUN SAFETY ENGINE
        # ----------------------------------------------------

        result = analyze_route(
            request.coordinates,
            hour=request.hour
        )


        return {
            "success": True,
            "route": result
        }


    except HTTPException:

        raise


    except Exception as error:

        print(
            "Route analysis error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )