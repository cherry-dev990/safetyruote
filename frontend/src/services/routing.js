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

  const [startLat, startLng] = start;

  const [destLat, destLng] = destination;


  // ==================================================
  // TRAVEL MODE
  // ==================================================

  const costing =
    mode === "walking"
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

    // Ask Valhalla for alternatives
    alternates: 2,

    directions_options: {
      units: "kilometers"
    }

  };


  console.log(
    "Routing request:",
    {
      mode,
      start,
      destination
    }
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
      "Network error:",
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
      "Invalid JSON response:",
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
  // CHECK PRIMARY ROUTE
  // ==================================================

  if (
    !data.trip ||
    !data.trip.legs ||
    data.trip.legs.length === 0
  ) {

    console.error(
      "No route response:",
      data
    );

    throw new Error(
      data.error ||
      data.message ||
      "No road route could be found between these locations."
    );

  }


  // ==================================================
  // PRIMARY + ALTERNATE ROUTES
  // ==================================================

  const alternateTrips =
  Array.isArray(data.alternates)
    ? data.alternates.map(
        (alternate) =>
          alternate.trip || alternate
      )
    : [];


const rawRoutes = [
  data.trip,
  ...alternateTrips
];


  // ==================================================
  // REMOVE INVALID ROUTES
  // ==================================================
const validRoutes =
  rawRoutes.filter(
    (trip) => {

      const valid =
        trip &&
        Array.isArray(trip.legs) &&
        trip.legs.length > 0 &&
        trip.summary;

      if (!valid) {

        console.warn(
          "Ignoring invalid Valhalla route:",
          trip
        );

      }

      return valid;

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


          // ==========================================
          // DECODE ALL LEGS
          // ==========================================

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

              // Avoid duplicating the
              // connecting point.

              routeCoordinates.push(
                ...legCoordinates.slice(1)
              );

            }

          }


          // ==========================================
          // MAKE SURE ROUTE HAS GEOMETRY
          // ==========================================

          if (
            routeCoordinates.length === 0
          ) {

            return null;

          }


          return {

            id:
              `route-${index + 1}`,

            coordinates:
              routeCoordinates,

            distanceKm:
              Number(
                summary.length
              ),

            durationMinutes:
              Number(
                summary.time
              ) / 60,

            mode:
              mode,

            routeNumber:
              index + 1

          };

        }
      )
      .filter(
        Boolean
      );


  // ==================================================
  // ROUTE CHECK
  // ==================================================

  if (
    routes.length === 0
  ) {

    throw new Error(
      "The routing server did not return a usable route."
    );

  }


  console.log(
    `Found ${routes.length} route(s)`
  );


  routes.forEach(
    (route) => {

      console.log(
        route.id,
        "|",
        route.coordinates.length,
        "points |",
        route.distanceKm,
        "km |",
        route.durationMinutes.toFixed(1),
        "min"
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

    // ==============================================
    // LATITUDE
    // ==============================================

    let shift = 0;

    let result = 0;

    let byte;


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


    // ==============================================
    // LONGITUDE
    // ==============================================

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


    // ==============================================
    // ADD COORDINATE
    // ==============================================

    coordinates.push([

      lat / 1e6,

      lng / 1e6

    ]);

  }


  return coordinates;
}