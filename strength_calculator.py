#!/usr/bin/env python3
"""
Vedic Astrology Transit & Dasha Prediction System (Jyotish-style drishti)
---------------------------------------------------------------------
Sidereal (Lahiri) positions, whole-sign houses, and Jyotish aspect rules.

Requirements: pip install pyswisseph pytz

Author: Shelby (rewritten)
"""

import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import pytz

try:
    import swisseph as swe
except ImportError:
    print("Error: Swiss Ephemeris not found. Install with: pip install pyswisseph")
    exit(1)

# --- Constants ---

PLANETS = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
    'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER,
    'Venus': swe.VENUS, 'Saturn': swe.SATURN,
    # Use MEAN_NODE for Rahu; Ketu computed as opposite.
    'Rahu': swe.MEAN_NODE, 'Ketu': 'KETU'
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

HOUSES = [
    "Self, Appearance", "Wealth, Family", "Siblings, Courage",
    "Home, Mother", "Children, Creativity", "Health, Enemies",
    "Partnership, Marriage", "Transformation, Longevity", "Fortune, Religion",
    "Career, Status", "Gains, Friends", "Loss, Liberation"
]

VIMSHOTTARI_DASHA = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10,
    'Mars': 7, 'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
}

# --- Jyotish drishti mapping (whole-sign aspects) ---
# Offsets are in signs ahead from the planet's own sign (1 = next sign)
# But we express them as 0-based indices: 0 = own sign (conjunction), 6 = 7th, etc.
DRISHTI_OFFSETS = {
    'Sun':   [6],                 # 7th
    'Moon':  [6],
    'Mercury':[6],
    'Venus': [6],
    'Mars':  [3, 6, 7],           # 4th (+3), 7th (+6), 8th (+7)
    'Jupiter':[4, 6, 8],          # 5th (+4), 7th (+6), 9th (+8)
    'Saturn':[2, 6, 9],           # 3rd (+2), 7th (+6), 10th (+9)
    'Rahu':  [6],                 # treat Rahu/Ketu as having traditional 7th; schools vary
    'Ketu':  [6]
}

# Strength weight for a 'full' drishti
DRISHTI_FULL_STRENGTH = 100

# --- Color Support (same as before) ---

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @staticmethod
    def disable():
        Colors.HEADER = Colors.BLUE = Colors.CYAN = ''
        Colors.GREEN = Colors.YELLOW = Colors.RED = ''
        Colors.BOLD = Colors.UNDERLINE = Colors.END = ''

# --- Data Classes ---

@dataclass
class PlanetPosition:
    name: str
    longitude: float           # sidereal longitude (0-360)
    sign: str                  # sign name
    sign_num: int              # 0-11
    house: int                 # 1-12 (whole-sign house)
    degree_in_sign: float      # 0-30
    is_retrograde: bool
    nakshatra: str
    nakshatra_lord: str

@dataclass
class Chart:
    chart_type: str
    datetime: datetime
    ascendant: float           # sidereal ascendant longitude (0-360)
    asc_sign_num: int
    planets: Dict[str, PlanetPosition]
    houses: List[float]        # cusps per sign start (whole sign cusps)

@dataclass
class AspectInfo:
    aspecting_planet: str
    aspect_type: str           # 'conjunction' or 'drishti'
    target_planet: str
    from_sign: str
    to_sign: str
    offset: int
    strength: float

@dataclass
class HouseTransit:
    house_num: int
    house_meaning: str
    transiting_planets: List[PlanetPosition]
    natal_planets: List[PlanetPosition]
    aspects_to_natal: List[AspectInfo]
    overall_strength: float
    interpretation: str

# --- Ephemeris Functions ---

def get_julian_day(dt: datetime) -> float:
    """Convert datetime to Julian Day (UT)."""
    # swe.julday expects UT date/time. Ensure dt is timezone-aware and convert to UTC.
    if dt.tzinfo is not None:
        utc = dt.astimezone(pytz.UTC)
    else:
        utc = pytz.UTC.localize(dt)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute/60 + utc.second/3600)

def get_ayanamsa(jd: float) -> float:
    """Get Lahiri ayanamsa for sidereal calculations."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa(jd)

def calculate_planet_position(planet_name: str, jd: float, ayanamsa: float) -> Tuple[float, bool]:
    """Calculate sidereal position of a planet. Returns (sidereal_longitude, is_retro)."""
    if planet_name == 'Ketu':
        # Compute Ketu as Rahu + 180
        rahu_pos, _ = swe.calc_ut(jd, swe.MEAN_NODE)
        rahu_long = rahu_pos[0]
        longitude = (rahu_long + 180.0) % 360.0
        is_retro = False
    elif planet_name == 'Rahu':
        pos, ret = swe.calc_ut(jd, swe.MEAN_NODE)
        longitude = pos[0]
        # nodes don't have a retrograde flag in the same way; keep False
        is_retro = False
    else:
        planet_id = PLANETS[planet_name]
        pos, ret = swe.calc_ut(jd, planet_id)
        longitude = pos[0]
        # swisseph returns speed in pos[3]; retrograde if speed < 0 for planets (Sun/Moon typically not retro)
        is_retro = (pos[3] < 0) if planet_name not in ['Sun', 'Moon'] else False

    sidereal_long = (longitude - ayanamsa) % 360.0
    return sidereal_long, is_retro

def get_nakshatra(longitude: float) -> Tuple[str, str]:
    """Get nakshatra and its lord from longitude (sidereal)."""
    nakshatras = [
        ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sun"),
        ("Rohini", "Moon"), ("Mrigashira", "Mars"), ("Ardra", "Rahu"),
        ("Punarvasu", "Jupiter"), ("Pushya", "Saturn"), ("Ashlesha", "Mercury"),
        ("Magha", "Ketu"), ("Purva Phalguni", "Venus"), ("Uttara Phalguni", "Sun"),
        ("Hasta", "Moon"), ("Chitra", "Mars"), ("Swati", "Rahu"),
        ("Vishakha", "Jupiter"), ("Anuradha", "Saturn"), ("Jyeshtha", "Mercury"),
        ("Mula", "Ketu"), ("Purva Ashadha", "Venus"), ("Uttara Ashadha", "Sun"),
        ("Shravana", "Moon"), ("Dhanishta", "Mars"), ("Shatabhisha", "Rahu"),
        ("Purva Bhadrapada", "Jupiter"), ("Uttara Bhadrapada", "Saturn"), ("Revati", "Mercury")
    ]
    nak_span = 360.0 / 27.0
    index = int(longitude // nak_span) % 27
    return nakshatras[index]

def calculate_ascendant(jd: float, lat: float, lon: float, ayanamsa: float) -> float:
    """Calculate sidereal ascendant (whole sign aware)."""
    # Use Swiss Ephemeris to get true ascendant (tropical), then convert to sidereal by subtracting ayanamsa.
    # Using Placidus placeholder like before; main result is we convert to sidereal.
    houses_result = swe.houses(jd, lat, lon, b'P')  # returns (cusps, etc)
    # houses_result[0][0] is ascendant (tropical)
    tropical_asc = houses_result[0][0]
    sidereal_asc = (tropical_asc - ayanamsa) % 360.0
    return sidereal_asc

def get_whole_sign_cusps(asc_sign_num: int) -> List[float]:
    """Return the starting longitude of each house in whole-sign system (sidereal)."""
    # Ascendant sign starts the 1st house; cusp longitudes are sign * 30 starting from asc_sign.
    cusps = [((asc_sign_num + i) % 12) * 30.0 for i in range(12)]
    return cusps

def get_house_number_whole_sign(planet_sign_num: int, asc_sign_num: int) -> int:
    """Determine which whole-sign house (1-12) a planet occupies based on sign numbers."""
    # House 1 = asc_sign_num, so compute offset in signs
    offset = (planet_sign_num - asc_sign_num) % 12
    return offset + 1

def calculate_chart(dt: datetime, lat: float, lon: float, chart_type: str = "Natal") -> Chart:
    """Calculate complete sidereal chart (whole-sign houses)."""
    jd = get_julian_day(dt)
    ayanamsa = get_ayanamsa(jd)

    asc = calculate_ascendant(jd, lat, lon, ayanamsa)
    asc_sign_num = int(asc // 30) % 12
    houses = get_whole_sign_cusps(asc_sign_num)

    planets = {}
    for planet_name in PLANETS.keys():
        longitude, is_retro = calculate_planet_position(planet_name, jd, ayanamsa)
        sign_num = int(longitude // 30) % 12
        sign = SIGNS[sign_num]
        degree_in_sign = longitude % 30.0
        house = get_house_number_whole_sign(sign_num, asc_sign_num)
        nakshatra, nak_lord = get_nakshatra(longitude)

        planets[planet_name] = PlanetPosition(
            name=planet_name,
            longitude=longitude,
            sign=sign,
            sign_num=sign_num,
            house=house,
            degree_in_sign=degree_in_sign,
            is_retrograde=is_retro,
            nakshatra=nakshatra,
            nakshatra_lord=nak_lord
        )

    return Chart(
        chart_type=chart_type,
        datetime=dt,
        ascendant=asc,
        asc_sign_num=asc_sign_num,
        planets=planets,
        houses=houses
    )

# --- Jyotish Aspect (Drishti) Calculation ---

def planet_drishti_offsets(planet_name: str) -> List[int]:
    """Return list of whole-sign offsets where this planet casts full drishti."""
    return DRISHTI_OFFSETS.get(planet_name, [6])  # default to 7th if missing

def check_drishti(transit: PlanetPosition, natal: PlanetPosition) -> Optional[AspectInfo]:
    """
    Determine if the transiting planet casts a Jyotish drishti on the natal planet.
    Returns an AspectInfo or None.
    """
    # Conjunction (same sign) => conjunction aspect
    if transit.sign_num == natal.sign_num:
        return AspectInfo(
            aspecting_planet=transit.name,
            aspect_type='conjunction',
            target_planet=natal.name,
            from_sign=transit.sign,
            to_sign=natal.sign,
            offset=0,
            strength=DRISHTI_FULL_STRENGTH
        )

    offsets = planet_drishti_offsets(transit.name)
    # compute sign offset from transit to natal (0..11)
    offset = ( (natal.sign_num - transit.sign_num) ) % 12
    if offset in offsets:
        return AspectInfo(
            aspecting_planet=transit.name,
            aspect_type='drishti',
            target_planet=natal.name,
            from_sign=transit.sign,
            to_sign=natal.sign,
            offset=offset,
            strength=DRISHTI_FULL_STRENGTH
        )
    return None

def calculate_aspects_jyotish(transit_planet: PlanetPosition,
                              natal_planets: Dict[str, PlanetPosition]) -> List[AspectInfo]:
    """Return all Jyotish drishti from a single transiting planet to natal planets."""
    aspects = []
    for natal in natal_planets.values():
        asp = check_drishti(transit_planet, natal)
        if asp:
            aspects.append(asp)
    return aspects

# --- Transit Analysis by House ---

def analyze_transits_by_house(natal: Chart, transit: Chart) -> List[HouseTransit]:
    """Analyze transits organized by natal whole-sign houses (1-12)."""
    house_transits = []

    for house_num in range(1, 13):
        # Transiting planets that occupy this natal house by whole-sign house numbering:
        transiting = [p for p in transit.planets.values() if p.house == house_num]
        natal_in_house = [p for p in natal.planets.values() if p.house == house_num]

        # Aspects: drishti from *transiting planets* to *all natal planets* (whole-sign)
        all_aspects: List[AspectInfo] = []
        for t_planet in transiting:
            aspects = calculate_aspects_jyotish(t_planet, natal.planets)
            all_aspects.extend(aspects)

        # Strength calculations (simple heuristic)
        strength = 0.0
        if transiting:
            strength += len(transiting) * 25.0
        if all_aspects:
            avg = sum(a.strength for a in all_aspects) / len(all_aspects)
            strength += avg * 0.4
        strength = min(100.0, strength)

        interpretation = generate_house_interpretation_jyotish(
            house_num, transiting, natal_in_house, all_aspects
        )

        house_transits.append(HouseTransit(
            house_num=house_num,
            house_meaning=HOUSES[house_num - 1],
            transiting_planets=transiting,
            natal_planets=natal_in_house,
            aspects_to_natal=all_aspects,
            overall_strength=strength,
            interpretation=interpretation
        ))

    return house_transits

def generate_house_interpretation_jyotish(house_num: int,
                                          transiting: List[PlanetPosition],
                                          natal_planets: List[PlanetPosition],
                                          aspects: List[AspectInfo]) -> str:
    """Simple Jyotish-style interpretation (can be extended)."""
    if not transiting and not aspects:
        return "No significant whole-sign activity (transit or drishti) affecting this house."

    lines = []
    house_meaning = HOUSES[house_num - 1]

    if transiting:
        names = ", ".join(p.name for p in transiting)
        lines.append(f"Transiting {names} occupy this house (whole-sign) — focus on: {house_meaning}.")

    if aspects:
        # Prefer drishti entries with strength (all are 'full' here)
        strong = [a for a in aspects if a.strength >= 90]
        if strong:
            lines.append("Significant drishti affecting natal planets:")
            for a in strong[:6]:
                if a.aspect_type == 'conjunction':
                    lines.append(f"  • {a.aspecting_planet} conjunct {a.target_planet} in {a.to_sign}.")
                else:
                    lines.append(f"  • {a.aspecting_planet} casts drishti to {a.target_planet} "
                                 f"({a.from_sign} → {a.to_sign}, offset {a.offset}).")
    return "\n".join(lines) if lines else "Minimal activity."

# --- Dasha Calculation (unchanged logic, minor fixes) ---

def calculate_birth_dasha(moon_longitude: float) -> Tuple[str, float]:
    """Calculate dasha at birth based on Moon's nakshatra."""
    nak, lord = get_nakshatra(moon_longitude)
    nak_span = 360.0 / 27.0
    nak_start = int(moon_longitude // nak_span) * nak_span
    progress = (moon_longitude - nak_start) / nak_span
    total_years = VIMSHOTTARI_DASHA[lord]
    years_elapsed = progress * total_years
    years_remaining = total_years - years_elapsed
    return lord, years_remaining

def calculate_current_dasha(birth_dt: datetime, moon_longitude: float, current_dt: datetime) -> Dict:
    """Return current mahadasha and antardasha information (approximate)."""
    birth_lord, years_remaining = calculate_birth_dasha(moon_longitude)
    days_elapsed = (current_dt - birth_dt).total_seconds() / (3600.0 * 24.0)
    years_elapsed = days_elapsed / 365.25

    dasha_sequence = list(VIMSHOTTARI_DASHA.keys())
    birth_index = dasha_sequence.index(birth_lord)
    ordered_sequence = dasha_sequence[birth_index:] + dasha_sequence[:birth_index]

    # iterate through mahadashas starting from birth dasha remainder
    elapsed = 0.0
    current_maha = birth_lord
    # first mahadasha is partial (years_remaining), then full durations follow
    if years_elapsed < years_remaining:
        current_maha = birth_lord
        maha_start = birth_dt
        time_into_maha = years_elapsed
    else:
        elapsed = years_remaining
        maha_start = birth_dt + timedelta(days=int(years_remaining * 365.25))
        for lord in ordered_sequence[1:] + ordered_sequence[:0]:
            dur = VIMSHOTTARI_DASHA[lord]
            if years_elapsed < elapsed + dur:
                current_maha = lord
                time_into_maha = years_elapsed - elapsed
                break
            elapsed += dur
        else:
            # wrap-around safeguard
            current_maha = ordered_sequence[0]
            time_into_maha = years_elapsed - elapsed

    maha_duration = VIMSHOTTARI_DASHA[current_maha]

    # Antardasha sequence inside current maha (proportional)
    antar_sequence = ordered_sequence[ordered_sequence.index(current_maha):] + \
                     ordered_sequence[:ordered_sequence.index(current_maha)]
    cumulative = 0.0
    current_antar = current_maha
    for antar_lord in antar_sequence:
        antar_duration = (VIMSHOTTARI_DASHA[antar_lord] * maha_duration) / 120.0
        if time_into_maha < cumulative + antar_duration:
            current_antar = antar_lord
            break
        cumulative += antar_duration

    return {
        'mahadasha': current_maha,
        'mahadasha_start': maha_start,
        'mahadasha_years': maha_duration,
        'antardasha': current_antar,
        'years_into_maha': time_into_maha
    }

# --- Output Formatting (slightly adapted) ---

def print_header(title: str):
    width = 96
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'═' * width}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(width)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * width}{Colors.END}\n")

def print_combined_chart_table(natal: Chart, transit: Chart):
    print(f"{Colors.BOLD}Chart Type:{Colors.END} Transit - Natal")
    print(f"{Colors.BOLD}Transit Date/Time:{Colors.END} {transit.datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()

    print(f"{'Transit':<56}{'Natal'}")
    print("─" * 96)
    print(f"{'Planet':<11}{'Sign (deg)':<18}{'House':<8}{'R':<3}    "
          f"{'Planet':<11}{'Sign (deg)':<18}{'House':<8}{'Nakshatra':<19}{'R':<3}")
    print("─" * 96)

    for pname in PLANETS.keys():
        t = transit.planets[pname]
        n = natal.planets[pname]
        t_retro = "R" if t.is_retrograde else ""
        n_retro = "R" if n.is_retrograde else ""
        print(f"{t.name:<11}{t.sign + ' ' + f'{t.degree_in_sign:>5.2f}°':<18}{t.house:<8}{t_retro:<3}    "
              f"{n.name:<11}{n.sign + ' ' + f'{n.degree_in_sign:>5.2f}°':<18}{n.house:<8}{n.nakshatra:<19}{n_retro:<3}")

    print()

def print_house_transit_analysis(house_transits: List[HouseTransit]):
    print_header("Transit Analysis (Jyotish drishti)")
    for ht in house_transits:
        # skip empty
        if not ht.transiting_planets and not ht.aspects_to_natal:
            continue

        if ht.overall_strength > 70:
            color = Colors.GREEN
        elif ht.overall_strength > 40:
            color = Colors.YELLOW
        else:
            color = Colors.BLUE

        print(f"{color}{Colors.BOLD}━━━ Natal House {ht.house_num} Transit ━━━{Colors.END}")
        print(f"{Colors.BOLD}Area of Life:{Colors.END} {ht.house_meaning}")
        print(f"{Colors.BOLD}Overall Strength:{Colors.END} {ht.overall_strength:.0f}/100\n")

        if ht.transiting_planets:
            print(f"{Colors.BOLD}Transiting Planets in House:{Colors.END}")
            for p in ht.transiting_planets:
                retro = " (R)" if p.is_retrograde else ""
                print(f"  • {p.name} in {p.sign} at {p.degree_in_sign:.2f}°{retro}")
            print()

        if ht.natal_planets:
            print(f"{Colors.BOLD}Natal Planets in House:{Colors.END}")
            for p in ht.natal_planets:
                print(f"  • {p.name} in {p.sign} at {p.degree_in_sign:.2f}°")
            print()

        if ht.aspects_to_natal:
            print(f"{Colors.BOLD}Transit Drishti to Natal Planets:{Colors.END}")
            # group by aspecting planet for readability
            grouped = defaultdict(list)
            for a in ht.aspects_to_natal:
                grouped[a.aspecting_planet].append(a)
            for ap, alist in grouped.items():
                for a in alist:
                    if a.aspect_type == 'conjunction':
                        print(f"  • {ap} conjunct {a.target_planet} in {a.to_sign} - Strength {a.strength:.0f}")
                    else:
                        print(f"  • {ap} drishti → {a.target_planet} ({a.from_sign} → {a.to_sign}, offset {a.offset}) - Strength {a.strength:.0f}")
            print()

        print(f"{Colors.BOLD}Interpretation:{Colors.END}")
        for line in ht.interpretation.split('\n'):
            print(f"  {line}")
        print()

def print_dasha_info(dasha: Dict, natal: Chart):
    print_header("Current Vimshottari Dasha Periods (approx.)")
    maha = dasha['mahadasha']
    antar = dasha['antardasha']
    print(f"{Colors.BOLD}Mahadasha:{Colors.END} {Colors.GREEN}{maha}{Colors.END} ({dasha['mahadasha_years']} years)")
    print(f"  Started: {dasha['mahadasha_start'].strftime('%Y-%m-%d')}")
    print(f"  Progress: {dasha['years_into_maha']:.2f} years elapsed\n")
    print(f"{Colors.BOLD}Antardasha:{Colors.END} {Colors.CYAN}{antar}{Colors.END}\n")
    try:
        maha_pos = natal.planets[maha]
        antar_pos = natal.planets[antar]
        print(f"{Colors.BOLD}Dasha Lord Natal Positions:{Colors.END}")
        print(f"  {maha}: {maha_pos.sign} {maha_pos.degree_in_sign:.2f}° in {maha_pos.house}th house")
        print(f"  {antar}: {antar_pos.sign} {antar_pos.degree_in_sign:.2f}° in {antar_pos.house}th house\n")
    except Exception:
        pass

# --- Main Program ---

def main():
    parser = argparse.ArgumentParser(
        description="Vedic Astrology Transit & Dasha Prediction System (Jyotish drishti)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2000-06-16 --time 01:11 --lat 33.0383 --lon -85.0319 --tz America/New_York
  %(prog)s --date 1990-05-15 --time 14:30 --lat 28.6139 --lon 77.2090 --tz Asia/Kolkata
        """
    )

    parser.add_argument('--date', required=True, help='Birth date (YYYY-MM-DD)')
    parser.add_argument('--time', required=True, help='Birth time (HH:MM)')
    parser.add_argument('--lat', type=float, required=True, help='Latitude')
    parser.add_argument('--lon', type=float, required=True, help='Longitude')
    parser.add_argument('--tz', required=True, help='Timezone (e.g., America/New_York)')
    parser.add_argument('--transit-date', help='Transit date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--transit-time', help='Transit time (HH:MM), defaults to now')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--format', choices=['detailed', 'json'], default='detailed', help='Output format')

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Parse birth datetime
    try:
        tz = pytz.timezone(args.tz)
        birth_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        birth_time = datetime.strptime(args.time, '%H:%M').time()
        birth_dt = tz.localize(datetime.combine(birth_date, birth_time))
    except Exception as e:
        print(f"Error parsing birth date/time: {e}")
        return

    # Parse transit datetime
    if args.transit_date:
        try:
            transit_date = datetime.strptime(args.transit_date, '%Y-%m-%d').date()
            if args.transit_time:
                transit_time = datetime.strptime(args.transit_time, '%H:%M').time()
            else:
                transit_time = datetime.now(tz).time()
            transit_dt = tz.localize(datetime.combine(transit_date, transit_time))
        except Exception as e:
            print(f"Error parsing transit date/time: {e}")
            return
    else:
        transit_dt = datetime.now(tz)

    print(f"{Colors.BOLD}Calculating charts (sidereal, whole-sign)...{Colors.END}")
    natal = calculate_chart(birth_dt, args.lat, args.lon, "Natal")
    transit = calculate_chart(transit_dt, args.lat, args.lon, "Transit")

    house_transits = analyze_transits_by_house(natal, transit)

    moon_long = natal.planets['Moon'].longitude
    dasha = calculate_current_dasha(birth_dt, moon_long, transit_dt)

    if args.format == 'json':
        output = {
            'natal': {
                'datetime': birth_dt.isoformat(),
                'ascendant': natal.ascendant,
                'asc_sign_num': natal.asc_sign_num,
                'planets': {name: asdict(pos) for name, pos in natal.planets.items()}
            },
            'transit': {
                'datetime': transit_dt.isoformat(),
                'ascendant': transit.ascendant,
                'asc_sign_num': transit.asc_sign_num,
                'planets': {name: asdict(pos) for name, pos in transit.planets.items()}
            },
            'house_transits': [asdict(ht) for ht in house_transits],
            'dasha': dasha
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_header("Vedic Astrology Predictive Analysis (Jyotish)")
        print_combined_chart_table(natal, transit)
        print_house_transit_analysis(house_transits)
        print_dasha_info(dasha, natal)
        print(f"\n{Colors.BOLD}{Colors.GREEN}Analysis Complete!{Colors.END}\n")

if __name__ == "__main__":
    main()
