from tabulate import tabulate

# Define Vedic aspects (Drishti) per planet
VEDIC_DRISHTI = {
    'Sun': [3, 6, 10, 11],
    'Moon': [7],
    'Mars': [4, 7, 8],
    'Mercury': [7],
    'Jupiter': [5, 7, 9],
    'Venus': [7],
    'Saturn': [3, 7, 10],
    'Rahu': [5, 9],
    'Ketu': [5, 9]
}

def calculate_vedic_aspects(natal_planets):
    """
    Calculate Vedic aspects based on planetary houses.
    natal_planets: dict of planets -> {'house': int (1-12), 'rasi': str, 'degrees': float}

    """
    # Build housess mapping: house -> list of planets
    houses = {i: [] for i in range(1, 13)}
    for planet, data in natal_planets.items():
        house_num = data['house']
        houses[house_num].append(planet)

    aspects = []

    for planet, drishti_houses in VEDIC_DRISHTI.items():
        if planet not in natal_planets:
            continue

        current_house = natal_planets[planet]['house']
        affected_houses = []

        for distance in drishti_houses:
            #Target house with wrap-around (1-12)
            target_house = ((current_house - 1 + distance) % 12) + 1
            affected_houses.append(target_house)

        aspects.append({
            'Planet': planet,
            'Aspect Houses': ', '.join(map(str, drishti_houses)),
            'Houses Affected': ', '.join(map(str, affected_houses))
        })

    return aspects
    
def display_vedic_aspects(aspects):
    """
    Print aspects in a clean table using tabulate
    """
    if not aspects:
        print("No aspects found.")
        return
    
    print("\n================================================================================")
    print("Vedic Planetary Aspects (Drishti)")
    print("================================================================================\n")

    table_data = [[a['Planet'], a['Aspect Houses'], a['Houses Affected']] for a in aspects]
    print(tabulate(table_data, headers=['Planet', 'Aspect Houses', 'Houses Affected'], tablefmt='fancy_grid'))