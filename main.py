# main.py

from core.calc import calculate_natal_chart, format_chart_display
from core.transits import get_transit_chart
from core.aspects import calculate_vedic_aspects, display_vedic_aspects

if __name__ == "__main__":
    print("Welcome to Vedic Sky View!\n")

    # Collect birth details
    birth_date = input("Enter birth date (YYYY-MM-DD): ")
    birth_time = input("Enter birth time (HH:MM, 24h format): ")
    latitude = float(input("Enter latitude (e.g., 33.0383): "))
    longitude = float(input("Enter longitude (e.g., -85.0319): "))
    timezone = input("Enter timezone (e.g., America/New_York): ")

    print("\nCalculating natal chart and current transits...\n")

    # Step 1: Natal chart
    natal_chart = calculate_natal_chart(birth_date, birth_time, latitude, longitude, timezone)
    natal_planets = natal_chart['planets']
    print(format_chart_display(natal_chart))

    # Step 2: Current transits
    transit_chart = get_transit_chart(latitude, longitude)
    transit_planets = transit_chart['planets']

    # Step 3: Calculate and display aspects
    print("\nNATAL ASPECTS:")
    natal_aspects = calculate_vedic_aspects(natal_planets)
    display_vedic_aspects(natal_aspects)

    print("\nTRANSIT ASPECTS:")
    transit_aspects = calculate_vedic_aspects(transit_planets)
    display_vedic_aspects(transit_aspects)
