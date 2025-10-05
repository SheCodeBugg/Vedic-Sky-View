import swisseph as swe
from datetime import datetime
import pytz

# Planet constants
PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,
    'Ketu': swe.MEAN_NODE
}

#Zodiac signs (Rasis)
RASIS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

def get_julian_day(date_str, time_str, timezone='UTC'):
    """Convert date and time to Julian Day."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    if timezone != 'UTC':
        local_tz = pytz.timezone(timezone)
        dt = local_tz.localize(dt)
        dt = dt.astimezone(pytz.UTC)

    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)
    return jd
def calculate_ayanamsha(jd):
    """Calculate Lahiri Ayanamsha for given Julian Day"""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa(jd)

def get_planet_position(planet_id, jd, ayanamsha):
    """Calculate sideral position of a planet."""
    tropical_long = swe.calc_ut(jd, planet_id)[0][0]
    sidereal_long = tropical_long - ayanamsha
    if sidereal_long < 0:
        sidereal_long +=360

    rasi_num = int(sidereal_long / 30)
    degrees_in_sign = sidereal_long % 30

    return {
        'longitude': round(sidereal_long, 6),
        'rasi': RASIS[rasi_num],
        'rasi_num': rasi_num + 1,
        'degrees': round(degrees_in_sign, 2)
    }

def calculate_natal_chart(date, time, lat, lon, timezone='UTC'):
    """Calculate complete natal chart with sidereal positions."""
    swe.set_ephe_path('')
    jd = get_julian_day(date, time, timezone)
    ayanamsha = calculate_ayanamsha(jd)

    # Ascendant
    houses = swe.houses(jd, lat, lon, b'P')
    tropical_asc = houses[1][0]
    sidereal_asc = tropical_asc - ayanamsha
    if sidereal_asc < 0:
        sidereal_asc += 360
    asc_rasi = int(sidereal_asc / 30)
    asc_degrees = sidereal_asc % 30

    chart = {
        'birth_details': {
            'date': date,
            'time': time,
            'latitude': lat,
            'longitude': lon,
            'timezone': timezone,
            'julian_day': round(jd, 6),
            'ayanamsha': round(ayanamsha, 6)
        },
        'ascendant': {
            'longitude': round(sidereal_asc, 6),
            'rasi': RASIS[asc_rasi],
            'rasi_num': asc_rasi + 1,
            'degrees': round(asc_degrees, 2)
        },
        'planets': {}
    }

    for planet_name, planet_id in PLANETS.items():
        if planet_name == 'Ketu':
            rahu_pos = chart['planets']['Rahu']['longitude']
            ketu_long = (rahu_pos + 180) % 360
            ketu_rasi = int(ketu_long / 30)
            ketu_degrees = ketu_long % 30
            chart['planets']['ketu'] = {
                'longitude': round(ketu_long, 6),
                'rasi': RASIS[ketu_rasi],
                'rasi_num': ketu_rasi + 1,
                'degrees': round(ketu_degrees, 2)
            }
        else:
            chart['planets'][planet_name] = get_planet_position(planet_id, jd, ayanamsha)

    return chart

def format_chart_display(chart):
    """Format chart data for display."""
    output = ["="*60, "VEDIC NATAL CHART (Sidereal - Lahiri Ayanamsha)", "="*60]

    bd = chart['birth_details']
    output += [
        f"\nBirth Details:",
        f"  Date: {bd['date']}",
        f"  Time: {bd['time']} ({bd['timezone']})",
        f"  Location: {bd['latitude']}°, {bd['longitude']}°",
        f"  Ayanamsha: {bd['ayanamsha']}°"
    ]

    asc = chart['ascendant']
    output += [
        f"\nAscendant (Lagna):",
        f"  {asc['rasi']} {asc['degrees']}° (Total: {asc['longitude']}°)"
    ]

    output += ["\nPlanetary Positions:", "-"*60,
               f"{'Planet':<12} {'Rasi':<15} {'Degrees':<12} {'Longitude':<12}",
               "-"*60]
    
    for planet, data in chart['planets'].items():
        output.append(f"{planet:<12} {data['rasi']:<15} {data['degrees']:<12.2f} {data['longitude']:<12.6f}")

    output.append("="*60)
    return "\n".join(output)

if __name__ == "__main__":
    print("Welcome to Vedic Natal Chart Calculator!")

    birth_date = input("Enter birth date (YYYY-MM-DD): ").strip()
    birth_time = input("Enter birth time (HH:MM, 24h format): ").strip()
    latitude = float(input("Enter latitude (e.g., 28.6139): ").strip())
    longitude = float(input("Enter longitude (e.g., 77.2090): ").strip())
    timezone = input("Enter timezone (e.g., Asia/Kolkata): ").strip() or "UTC"

    print("\nCalculating Vedic Natal Chart...\n")
    chart = calculate_natal_chart(birth_date, birth_time, latitude, longitude, timezone)

    print(format_chart_display(chart))

