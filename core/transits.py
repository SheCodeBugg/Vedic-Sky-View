import swisseph as swe
from datetime import datetime
import argparse
import pytz

RASIS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

def get_transit_chart(lat, lon, ayanamsha='lahiri'):
    """
    Calculate current transiting planetary positions (sidereal).
    Returns sign and degrees within sign.
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

    ayanamsha_val = swe.get_ayanamsa(jd)

    planets = {
        swe.SUN: 'Sun',
        swe.MOON: 'Moon',
        swe.MARS: 'Mars',
        swe.MERCURY: 'Mercury',
        swe.JUPITER: 'Jupiter',
        swe.VENUS: 'Venus',
        swe.SATURN: 'Saturn',
        swe.MEAN_NODE: 'Rahu',
    }

    chart = {
        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        'julian_day': jd,
        'ayanamsha': ayanamsha_val,
        'planets': {}
    }

    for pid, name in planets.items():
        pos, ret = swe.calc_ut(jd, pid)
        tropical_lon = pos[0] % 360
        
        # Convert to sidereal
        sidereal_lon = (tropical_lon - ayanamsha_val) % 360
        
        # Calculate sign and degrees within sign
        sign_index = int(sidereal_lon // 30)
        degrees_in_sign = sidereal_lon % 30

        chart['planets'][name] = {
            'sign': RASIS[sign_index],
            'degrees': round(degrees_in_sign, 2),
        }

    # Ketu is opposite Rahu
    if 'Rahu' in chart['planets']:
        rahu_data = chart['planets']['Rahu']
        rahu_sign_idx = RASIS.index(rahu_data['sign'])
        ketu_sign_idx = (rahu_sign_idx + 6) % 12
        ketu_degrees = (rahu_data['degrees'] + 180) % 30
        
        chart['planets']['Ketu'] = {
            'sign': RASIS[ketu_sign_idx],
            'degrees': round(ketu_degrees, 2),
        }

    return chart


def print_ephemeris(chart):
    print("=" * 50)
    print("🌌 Daily Ephemeris (Vedic Sidereal)")
    print("=" * 50)
    print(f"Time: {chart['timestamp']}")
    print(f"Ayanamsha (Lahiri): {chart['ayanamsha']:.4f}°")
    print("-" * 50)
    print(f"{'Planet':<12} {'Sign':<15} {'Degrees':<10}")
    print("-" * 50)
    
    planet_order = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']
    
    for planet in planet_order:
        if planet in chart['planets']:
            data = chart['planets'][planet]
            print(f"{planet:<12} {data['sign']:<15} {data['degrees']:>8.2f}°")
    
    print("=" * 50)


def make_simple_prediction(chart):
    """
    Example prediction logic based on current transits.
    Replace with your own interpretation rules.
    """
    print("\n📊 Daily Insights:")
    print("-" * 50)
    
    # Get current positions
    sun_sign = chart['planets']['Sun']['sign']
    moon_sign = chart['planets']['Moon']['sign']
    
    print(f"☀️  Sun in {sun_sign} - Focus on {sun_sign} themes")
    print(f"🌙 Moon in {moon_sign} - Emotional energy of {moon_sign}")
    
    # Check for same sign (conjunction energy)
    if sun_sign == moon_sign:
        print("✨ Sun-Moon in same sign: Strong alignment of mind and emotions!")
    
    # Check Jupiter for luck
    jupiter_sign = chart['planets']['Jupiter']['sign']
    print(f"🍀 Jupiter in {jupiter_sign} - Blessings in {jupiter_sign} areas")
    
    # Check Saturn for challenges
    saturn_sign = chart['planets']['Saturn']['sign']
    print(f"⚖️  Saturn in {saturn_sign} - Discipline needed in {saturn_sign} matters")
    
    print("-" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Display today's planetary transits (Vedic astrology).")
    parser.add_argument('--lat', type=float, default=28.6139, help="Latitude (default: Delhi)")
    parser.add_argument('--lon', type=float, default=77.2090, help="Longitude (default: Delhi)")
    parser.add_argument('--ayanamsha', type=str, default='lahiri', help="Ayanamsha (default: lahiri)")
    args = parser.parse_args()

    chart = get_transit_chart(args.lat, args.lon, args.ayanamsha)
    print_ephemeris(chart)
    make_simple_prediction(chart)