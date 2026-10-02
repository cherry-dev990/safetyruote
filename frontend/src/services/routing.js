const VALHALLA_URL =
  "https://valhalla1.openstreetmap.de/route";

// ==================================================
// GET ROUTES
// ==================================================

export async function getRoutes(
  start,
  destination,
  mode = "walking"
) {

  // Normalize travel mode
  const normalizedMode =
    mode === "vehicle" || mode === "driving"
      ? "driving"
      : "walking";

  const [startLat, startLng] = start;
  const [destLat, destLng] = destination;

  // ==================================================
  // TRAVEL MODE
  // ==================================================

  const costing =
    normalizedMode === "walking"
      ? "pedestrian"
      : "auto";

  // ==================================================
  // VALHALLA REQUEST
  // ==================================================

  const requestBody = {
    locations: [
      {
        lat: startLat,
        lon: startLng
      },
      {
        lat: destLat,
        lon: destLng
      }
    ],

    costing: costing,

    units: "kilometers",

    alternates: 2,

    directions_options: {
      units: "kilometers"
    }
  };

  console.log(
    "======================================"
  );

  console.log(
    "ROUTING REQUEST"
  );

  console.log({
    mode,
    normalizedMode,
    costing,
    start,
    destination
  });

  console.log(
    "======================================"
  );

  // ==================================================
  // SEND REQUEST
  // ==================================================

  let response;

  try {

    response = await fetch(
      VALHALLA_URL,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify(
          requestBody
        )
      }
    );

  } catch (error) {

    console.error(
      "Routing network error:",
      error
    );

    throw new Error(
      "Unable to connect to the routing server."
    );
  }

  // ==================================================
  // HTTP ERROR
  // ==================================================

  if (!response.ok) {

    const errorText =
      await response.text();

    console.error(
      "Valhalla HTTP error:",
      response.status,
      errorText
    );

    throw new Error(
      `Routing server error (${response.status})`
    );
  }

  // ==================================================
  // PARSE RESPONSE
  // ==================================================

  let data;

  try {

    data =
      await response.json();

  } catch (error) {

    console.error(
      "Invalid routing JSON:",
      error
    );

    throw new Error(
      "Invalid response from routing server."
    );
  }

  console.log(
    "Valhalla response:",
    data
  );

  // ==================================================
  // PRIMARY ROUTE CHECK
  // ==================================================

  if (
    !data.trip ||
    !data.trip.legs ||
    data.trip.legs.length === 0
  ) {

    throw new Error(
      data.error ||
      data.message ||
      "No route could be found between these locations."
    );
  }

  // ==================================================
  // PRIMARY + ALTERNATE ROUTES
  // ==================================================

  const alternateTrips =
    Array.isArray(data.alternates)

      ? data.alternates.map(
          (alternate) =>
            alternate.trip ||
            alternate
        )

      : [];

  const rawRoutes = [
    data.trip,
    ...alternateTrips
  ];

  // ==================================================
  // VALID ROUTES
  // ==================================================

  const validRoutes =
    rawRoutes.filter(
      (trip) => {

        return (
          trip &&
          Array.isArray(
            trip.legs
          ) &&
          trip.legs.length > 0 &&
          trip.summary
        );

      }
    );

  // ==================================================
  // CONVERT ROUTES
  // ==================================================

  const routes =
    validRoutes
      .slice(0, 3)
      .map(
        (trip, index) => {

          const summary =
            trip.summary;

          // ------------------------------------------
          // Combine all route legs
          // ------------------------------------------

          const routeCoordinates = [];

          for (
            const leg of trip.legs
          ) {

            if (!leg.shape) {
              continue;
            }

            const legCoordinates =
              decodePolyline(
                leg.shape
              );

            if (
              routeCoordinates.length === 0
            ) {

              routeCoordinates.push(
                ...legCoordinates
              );

            } else {

              routeCoordinates.push(
                ...legCoordinates.slice(1)
              );

            }
          }

          if (
            routeCoordinates.length === 0
          ) {

            return null;
          }

          // ------------------------------------------
          // IMPORTANT:
          // Valhalla summary.time = seconds
          // Convert seconds -> minutes
          // ------------------------------------------

          const durationMinutes =
            Number(summary.time) / 60;

          const distanceKm =
            Number(summary.length);

          return {

            id:
              `route-${index + 1}`,

            coordinates:
              routeCoordinates,

            distanceKm:
              distanceKm,

            durationMinutes:
              durationMinutes,

            mode:
              normalizedMode,

            routeNumber:
              index + 1
          };

        }
      )
      .filter(Boolean);

  // ==================================================
  // SAFETY CHECK
  // ==================================================

  if (
    routes.length === 0
  ) {

    throw new Error(
      "The routing server did not return a usable route."
    );
  }

  // ==================================================
  // DEBUG
  // ==================================================

  console.log(
    `Found ${routes.length} ${normalizedMode} route(s)`
  );

  routes.forEach(
    (route) => {

      console.log(
        route.id,
        "|",
        route.distanceKm.toFixed(2),
        "km |",
        route.durationMinutes.toFixed(1),
        "min |",
        route.mode
      );

    }
  );

  return routes;
}


// ==================================================
// POLYLINE DECODER
// ==================================================

function decodePolyline(
  encoded
) {

  let index = 0;

  let lat = 0;

  let lng = 0;

  const coordinates = [];

  while (
    index < encoded.length
  ) {

    let shift = 0;

    let result = 0;

    let byte;

    // ----------------------------------------------
    // LATITUDE
    // ----------------------------------------------

    do {

      byte =
        encoded.charCodeAt(
          index++
        ) - 63;

      result |=
        (byte & 0x1f)
        << shift;

      shift += 5;

    } while (
      byte >= 0x20
    );

    const deltaLat =
      (result & 1)
        ? ~(result >> 1)
        : result >> 1;

    lat += deltaLat;

    // ----------------------------------------------
    // LONGITUDE
    // ----------------------------------------------

    shift = 0;

    result = 0;

    do {

      byte =
        encoded.charCodeAt(
          index++
        ) - 63;

      result |=
        (byte & 0x1f)
        << shift;

      shift += 5;

    } while (
      byte >= 0x20
    );

    const deltaLng =
      (result & 1)
        ? ~(result >> 1)
        : result >> 1;

    lng += deltaLng;

    coordinates.push([
      lat / 1e6,
      lng / 1e6
    ]);
  }

  return coordinates;
}