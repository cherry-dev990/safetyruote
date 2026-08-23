const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function analyzeRouteSafety(coordinates) {
  if (!coordinates || coordinates.length === 0) {
    throw new Error("No route coordinates available.");
  }

  // Current local hour
  const hour = new Date().getHours();

  console.log("=================================");
  console.log("SAFEROUTE SAFETY ANALYSIS");
  console.log("API URL:", API_URL);
  console.log("Route points:", coordinates.length);
  console.log("Current hour:", hour);
  console.log("=================================");

  const response = await fetch(
    `${API_URL}/safety/analyze-route`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        coordinates: coordinates,
        hour: hour,
      }),
    }
  );

  const responseText = await response.text();

  console.log(
    "Safety API status:",
    response.status
  );

  if (!response.ok) {
    throw new Error(
      `Safety API ${response.status}: ${responseText}`
    );
  }

  let data;

  try {
    data = JSON.parse(responseText);
  } catch {
    throw new Error(
      "Safety API returned invalid JSON."
    );
  }

  if (!data.success) {
    throw new Error(
      data.detail ||
      "Safety analysis failed."
    );
  }

  console.log(
    "Safety result:",
    data.route
  );

  return data.route;
}