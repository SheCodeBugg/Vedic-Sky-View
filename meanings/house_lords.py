# meanings/house_lords.py

"""
House lordship by Ascendant.
Used to interpret how planets act as functional benefics or malefics for that chart.
"""

HOUSE_LORDS = {
    "Aries": {
        1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury",
        7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
    },
    "Taurus": {
        1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury", 6: "Venus",
        7: "Mars", 8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter", 12: "Mars"
    },
    "Gemini": {
        1: "Mercury", 2: "Moon", 3: "Sun", 4: "Mercury", 5: "Venus", 6: "Mars",
        7: "Jupiter", 8: "Saturn", 9: "Saturn", 10: "Jupiter", 11: "Mars", 12: "Venus"
    },
    "Cancer": {
        1: "Moon", 2: "Sun", 3: "Mercury", 4: "Venus", 5: "Mars", 6: "Jupiter",
        7: "Saturn", 8: "Saturn", 9: "Jupiter", 10: "Mars", 11: "Venus", 12: "Mercury"
    },
    # ... You’ll continue this pattern for all 12 ascendants later.
}
