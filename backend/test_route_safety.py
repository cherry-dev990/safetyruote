from app.services.route_safety import analyze_route


route = [

    [17.3850, 78.4867],

    [17.3870, 78.4880],

    [17.3900, 78.4900],

    [17.3930, 78.4920],

    [17.3960, 78.4950],

]


print()
print("=" * 65)
print("SAFEROUTE AI - ROUTE SAFETY TEST")
print("=" * 65)


# ============================================================
# DAY
# ============================================================

print()
print("DAY ANALYSIS — 14:00")
print("-" * 65)


day_result = analyze_route(
    route,
    hour=14
)


print(
    "Safety Score:",
    day_result["safety_score"]
)

print(
    "Risk:",
    day_result["risk_level"]
)

print(
    "Average:",
    day_result["average_score"]
)

print(
    "Worst:",
    day_result["minimum_score"]
)

print(
    "Danger Section Average:",
    day_result["danger_section_average"]
)

print(
    "Points:",
    day_result["points_analyzed"]
)


# ============================================================
# NIGHT
# ============================================================

print()
print("NIGHT ANALYSIS — 22:00")
print("-" * 65)


night_result = analyze_route(
    route,
    hour=22
)


print(
    "Safety Score:",
    night_result["safety_score"]
)

print(
    "Risk:",
    night_result["risk_level"]
)

print(
    "Average:",
    night_result["average_score"]
)

print(
    "Worst:",
    night_result["minimum_score"]
)

print(
    "Danger Section Average:",
    night_result["danger_section_average"]
)


# ============================================================
# COMPARISON
# ============================================================

print()
print("=" * 65)
print("DAY vs NIGHT")
print("=" * 65)


print(
    f"14:00 → "
    f"{day_result['safety_score']}%"
)


print(
    f"22:00 → "
    f"{night_result['safety_score']}%"
)


print()
print("=" * 65)
print("ROUTE SEGMENTS")
print("=" * 65)


for i, point in enumerate(
    night_result["point_scores"],
    start=1
):

    print(

        f"Segment {i:02d} | "

        f"Safety: "
        f"{point['safety_score']:>6.2f}% | "

        f"Risk: "
        f"{point['risk_level']}"

    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)