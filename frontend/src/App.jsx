import { useEffect, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
  useMapEvents,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import L from "leaflet";

import { getRoutes } from "./services/routing";
import { analyzeRouteSafety } from "./services/safety";

import "./App.css";


// ============================================================
// LEAFLET ICON FIX
// ============================================================

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",

  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",

  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});


// ============================================================
// MAP CONTROLLER
// ============================================================

function MapController({ location }) {
  const map = useMap();

  useEffect(() => {
    if (location) {
      map.setView(location, 15);
    }
  }, [location, map]);

  return null;
}


// ============================================================
// MAP CLICK HANDLER
// ============================================================

function DestinationSelector({
  location,
  travelMode,
  setDestination,
  calculateRoutes,
}) {
  useMapEvents({
    click: async (event) => {
      const destination = [
        event.latlng.lat,
        event.latlng.lng,
      ];

      setDestination(destination);

      if (!location) {
        return;
      }

      await calculateRoutes(
        location,
        destination,
        travelMode
      );
    },
  });

  return null;
}


// ============================================================
// MAIN APP
// ============================================================

function App() {

  // ----------------------------------------------------------
  // LOCATION
  // ----------------------------------------------------------

  const [location, setLocation] =
    useState(null);

  const [destination, setDestination] =
    useState(null);


  // ----------------------------------------------------------
  // ROUTES
  // ----------------------------------------------------------

  const [routes, setRoutes] =
    useState([]);

  const [selectedRoute, setSelectedRoute] =
    useState(null);


  // ----------------------------------------------------------
  // TRAVEL MODE
  // ----------------------------------------------------------

  const [travelMode, setTravelMode] =
    useState("walking");


  // ----------------------------------------------------------
  // ROUTING STATE
  // ----------------------------------------------------------

  const [routing, setRouting] =
    useState(false);

  const [routeError, setRouteError] =
    useState(null);


  // ----------------------------------------------------------
  // SAFETY STATE
  // ----------------------------------------------------------

  const [routeSafety, setRouteSafety] =
    useState({});

  const [safetyLoading, setSafetyLoading] =
    useState(false);

  const [safetyError, setSafetyError] =
    useState(null);


  // ----------------------------------------------------------
  // LOCATION STATE
  // ----------------------------------------------------------

  const [locationLoading, setLocationLoading] =
    useState(true);

  const [locationError, setLocationError] =
    useState(null);


  // ==========================================================
  // GET CURRENT LOCATION
  // ==========================================================

  useEffect(() => {

    if (!navigator.geolocation) {

      setLocationError(
        "Geolocation is not supported by this browser."
      );

      setLocationLoading(false);

      return;
    }


    navigator.geolocation.getCurrentPosition(

      (position) => {

        setLocation([
          position.coords.latitude,
          position.coords.longitude,
        ]);

        setLocationLoading(false);
      },

      (error) => {

        console.error(
          "Location error:",
          error
        );

        setLocationError(
          "Unable to get your location. Please allow location access."
        );

        setLocationLoading(false);
      },

      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }

    );

  }, []);


  // ==========================================================
  // CALCULATE ROUTES + SAFETY
  // ==========================================================

  async function calculateRoutes(
    start,
    end,
    mode
  ) {

    try {

      // ------------------------------------------------------
      // RESET
      // ------------------------------------------------------

      setRouting(true);

      setRouteError(null);

      setSafetyError(null);

      setRoutes([]);

      setSelectedRoute(null);

      setRouteSafety({});


      // ------------------------------------------------------
      // GET REAL ROUTES
      // ------------------------------------------------------

      console.log(
        "======================================"
      );

      console.log(
        "GETTING ROUTES"
      );

      console.log(
        "Start:",
        start
      );

      console.log(
        "Destination:",
        end
      );

      console.log(
        "Mode:",
        mode
      );

      console.log(
        "======================================"
      );


      const results =
        await getRoutes(
          start,
          end,
          mode
        );


      console.log(
        "Routes received:",
        results
      );


      setRoutes(results);


      setRouting(false);


      // ------------------------------------------------------
      // SAFETY ANALYSIS
      // ------------------------------------------------------

      if (
        !results ||
        results.length === 0
      ) {

        return;
      }


      setSafetyLoading(true);


      const safetyResults = {};

      let safetyFailures = 0;


      // ------------------------------------------------------
      // ANALYZE EVERY ROUTE
      // ------------------------------------------------------

      for (
        const route of results
      ) {

        try {

          console.log(
            "======================================"
          );

          console.log(
            "ANALYZING ROUTE SAFETY"
          );

          console.log(
            "Route:",
            route.id
          );

          console.log(
            "Points:",
            route.coordinates.length
          );

          console.log(
            "======================================"
          );


          const safety =
            await analyzeRouteSafety(
              route.coordinates
            );


          console.log(
            "SAFETY RESULT:",
            route.id,
            safety
          );


          safetyResults[
            route.id
          ] = safety;


        } catch (error) {

          safetyFailures++;

          console.error(
            "Safety analysis failed:",
            route.id,
            error
          );

        }

      }


      // ------------------------------------------------------
      // STORE RESULTS
      // ------------------------------------------------------

      setRouteSafety(
        safetyResults
      );


      // ------------------------------------------------------
      // SHOW ERROR ONLY IF ALL FAILED
      // ------------------------------------------------------

      if (
        safetyFailures === results.length
      ) {

        setSafetyError(
          "Unable to analyze route safety."
        );

      } else if (
        safetyFailures > 0
      ) {

        setSafetyError(
          `${safetyFailures} route safety analysis failed.`
        );

      }


    } catch (error) {

      console.error(
        "ROUTING ERROR:",
        error
      );


      setRouteError(
        error.message ||
        "Unable to find routes."
      );


    } finally {

      setRouting(false);

      setSafetyLoading(false);

    }

  }


  // ==========================================================
  // CHANGE TRAVEL MODE
  // ==========================================================

  async function changeTravelMode(
    mode
  ) {

    setTravelMode(mode);


    if (
      location &&
      destination
    ) {

      await calculateRoutes(
        location,
        destination,
        mode
      );

    }

  }


  // ==========================================================
  // CLEAR DESTINATION
  // ==========================================================

  function clearDestination() {

    setDestination(null);

    setRoutes([]);

    setSelectedRoute(null);

    setRouteSafety({});

    setRouteError(null);

    setSafetyError(null);

  }


  // ==========================================================
  // SAFETY COLOR
  // ==========================================================

  function getSafetyColor(
    score
  ) {

    if (
      score >= 70
    ) {

      return "#15803d";
    }


    if (
      score >= 40
    ) {

      return "#d97706";
    }


    return "#dc2626";
  }


  // ==========================================================
  // MAP CENTER
  // ==========================================================

  const defaultLocation = [
    17.3850,
    78.4867,
  ];

  const mapCenter =
    location ||
    defaultLocation;


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="app">


      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="header">

        <div>

          <h1>
            SafeRoute
          </h1>

          <p>
            AI-Powered Safety Navigation
          </p>

        </div>

      </header>


      {/* =====================================================
          STATUS
      ===================================================== */}

      <div className="location-status">

        {locationLoading && (

          <span>
            ðŸ“ Detecting your location...
          </span>

        )}


        {!locationLoading &&
          location &&
          !destination && (

          <span className="success">
            ðŸ“ Location detected â€”
            click anywhere on the map
            to select destination
          </span>

        )}


        {routing && (

          <span>
            ðŸ›£ï¸ Finding real road route...
          </span>

        )}


        {safetyLoading && (

          <span>
            ðŸ¤– AI analyzing route safety...
          </span>

        )}


        {!routing &&
          !safetyLoading &&
          routes.length > 0 && (

          <span className="success">

            âœ… {routes.length} route
            {routes.length !== 1
              ? "s"
              : ""} found

          </span>

        )}


        {locationError && (

          <span className="error">
            âš ï¸ {locationError}
          </span>

        )}

      </div>


      {/* =====================================================
          MAP
      ===================================================== */}

      <main className="map-container">

        <MapContainer

          center={mapCenter}

          zoom={
            location
              ? 15
              : 12
          }

          className="map"

        >

          <TileLayer

            attribution=
              '&copy; OpenStreetMap contributors'

            url=
              "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

          />


          <MapController
            location={location}
          />


          <DestinationSelector

            location={location}

            travelMode={travelMode}

            setDestination={
              setDestination
            }

            calculateRoutes={
              calculateRoutes
            }

          />


          {/* =================================================
              CURRENT LOCATION
          ================================================= */}

          {location && (

            <Marker
              position={location}
            >

              <Popup>

                <strong>
                  ðŸ“ Your Location
                </strong>

              </Popup>

            </Marker>

          )}


          {/* =================================================
              DESTINATION
          ================================================= */}

          {destination && (

            <Marker
              position={destination}
            >

              <Popup>

                <strong>
                  ðŸŽ¯ Destination
                </strong>

              </Popup>

            </Marker>

          )}


          {/* =================================================
              ROUTES
          ================================================= */}

          {routes.map(
            (
              route,
              index
            ) => (

              <Polyline

                key={
                  route.id
                }

                positions={
                  route.coordinates
                }

                pathOptions={{

                  color:

                    selectedRoute?.id ===
                    route.id

                      ? "#0f172a"

                      : index === 0

                        ? "#0ea5e9"

                        : index === 1

                          ? "#14b8a6"

                          : "#64748b",

                  weight:

                    selectedRoute?.id ===
                    route.id

                      ? 8
                      : 5,

                  opacity:

                    selectedRoute?.id ===
                    route.id

                      ? 1
                      : 0.65,

                }}


                eventHandlers={{

                  click: () => {

                    setSelectedRoute(
                      route
                    );

                  },

                }}

              />

            )

          )}

        </MapContainer>


        {/* =====================================================
            TRAVEL MODE
        ===================================================== */}

        <div className="mode-card">

          <strong>
            Travel Mode
          </strong>


          <div className="mode-buttons">

            <button

              className={
                travelMode === "walking"
                  ? "active"
                  : ""
              }

              onClick={() =>
                changeTravelMode(
                  "walking"
                )
              }

            >

              ðŸš¶ Walking

            </button>


            <button

              className={
                travelMode === "driving"
                  ? "active"
                  : ""
              }

              onClick={() =>
                changeTravelMode(
                  "driving"
                )
              }

            >

              ðŸš— Vehicle

            </button>

          </div>

        </div>


        {/* =====================================================
            DESTINATION
        ===================================================== */}

        {destination && (

          <div className="destination-card">

            <strong>
              ðŸŽ¯ Destination
            </strong>

            <div>

              {destination[0].toFixed(5)}

              ,

              {" "}

              {destination[1].toFixed(5)}

            </div>


            <button
              onClick={
                clearDestination
              }
            >

              Clear

            </button>

          </div>

        )}


        {/* =====================================================
            ROUTING LOADING
        ===================================================== */}

        {routing && (

          <div className="route-card">

            ðŸ›£ï¸ Finding route...

          </div>

        )}


        {/* =====================================================
            ROUTING ERROR
        ===================================================== */}

        {routeError && (

          <div className="route-error">

            âš ï¸ {routeError}

          </div>

        )}


        {/* =====================================================
            SAFETY ERROR
        ===================================================== */}

        {safetyError && (

          <div className="route-error">

            âš ï¸ {safetyError}

          </div>

        )}


        {/* =====================================================
            SAFETY ANALYSIS LOADING
        ===================================================== */}

        {safetyLoading && (

          <div className="route-card">

            ðŸ¤– Analyzing safety of route
            {routes.length > 1
              ? "s"
              : ""}...

          </div>

        )}


        {/* =====================================================
            ROUTE RESULTS
        ===================================================== */}

        {routes.length > 0 && (

          <div className="routes-card">

            <div className="routes-header">

              <strong>
                Available Routes
              </strong>

              <span>
                AI Safety Analysis
              </span>

            </div>


            {routes.map(
              (
                route,
                index
              ) => {

                const safety =
                  routeSafety[
                    route.id
                  ];


                return (

                  <div

                    key={
                      route.id
                    }

                    className={
                      "route-option " +
                      (
                        selectedRoute?.id ===
                        route.id
                          ? "selected"
                          : ""
                      )
                    }

                    onClick={() =>
                      setSelectedRoute(
                        route
                      )
                    }

                  >

                    {/* -------------------------------------
                        ROUTE LABEL
                    ------------------------------------- */}

                    <div className="route-title">

                      {index === 0
                        ? "âš¡ Route"
                        : index === 1
                          ? "âš–ï¸ Alternative"
                          : "ðŸ›¡ï¸ Alternative"
                      }

                    </div>


                    {/* -------------------------------------
                        DISTANCE + TIME
                    ------------------------------------- */}

                    <div className="route-time">

                      {Number(
                        route.distanceKm
                      ).toFixed(2)}

                      {" "}
                      km

                      {" â€¢ "}

                      {Math.round(
                        route.durationMinutes
                      )}

                      {" "}
                      min

                    </div>


                    {/* -------------------------------------
                        SAFETY
                    ------------------------------------- */}

                    {safety ? (

                      <>

                        <div

                          className="route-safety"

                          style={{
                            color:
                              getSafetyColor(
                                Number(
                                  safety.safety_score
                                )
                              ),
                          }}

                        >

                          ðŸ›¡ï¸ Safety:

                          {" "}

                          <strong>

                            {Number(
                              safety.safety_score
                            ).toFixed(2)}

                            %

                          </strong>

                          {" â€¢ "}

                          <strong>

                            {safety.risk_level}

                          </strong>

                        </div>


                        <div className="route-details">

                          Average:

                          {" "}

                          {Number(
                            safety.average_score
                          ).toFixed(2)}

                          %

                          {" | "}

                          Worst:

                          {" "}

                          {Number(
                            safety.minimum_score
                          ).toFixed(2)}

                          %

                        </div>


                        {safety.dangerous_segments &&
                          safety.dangerous_segments.length > 0 && (

                          <div className="danger-warning">

                            Risk: <strong>High</strong>

                          </div>

                        )}

                      </>

                    ) : (

                      <div className="safety-pending">

                        {safetyLoading
                          ? "ðŸ¤– Analyzing safety..."
                          : "Safety data unavailable"}

                      </div>

                    )}

                  </div>

                );

              }

            )}

          </div>

        )}

      </main>

    </div>

  );
}


export default App;
