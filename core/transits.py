import swisseph as swe
from datetime import datetime

def get_transit_chart(lat, lon, ayanamsha='lahiri'):
    """
    Calculate current transiting planetary positions and houses.
    """

    # Get current UTC time
    now = datetime.now()

    # Compute Julian day for now
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60.0)

    # Apply ayanamsha correction (Vedic sidereal)
    if ayanamsha == 'lahiri':
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    else: 
        swe.set_sid_mode(swe.SIDM_USER, ayanamsha)

    # Ascendant calulation
    houses, ascmc = swe.houses(jd, lat, lon, b'A')
    sidereal_asc = ascmc[0]

    planets = {
        swe.SUN: 'Sun',
        swe.MOON: 'Moon',
        swe.MARS: 'Mars',
        swe.MERCURY: 'Mercury',
        swe.JUPITER: 'Jupiter',
        swe.VENUS: 'Venus',
        swe.SATURN: 'Saturn',
        swe.MEAN_NODE: 'Rahu',
        swe.TRUE_NODE: 'Ketu',
    }

    chart = {'planets': {}}

    for pid, name in planets.items():
        pos, ret = swe.calc_ut(jd, pid)
        lon = pos[0] % 360
        lat_ = pos[1]
        dist = pos[2]
        speed = pos[3]

        # Determine house from Ascendant
        house = int(((lon - sidereal_asc) % 360) / 30) + 1

        chart['planets'][name] = {
            'longitude': lon,
            'house': house,
        }

    return chart