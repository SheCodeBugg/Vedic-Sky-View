import swisseph as swe
from datetime import datetime, timedelta
from core.aspects import calculate_vedic_aspects, display_vedic_aspects
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

# Nakshatras (27 lunar mansions)
NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu',
    'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta',
    'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha',
    'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati'
]

SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 
    'Leo', 'Virgo', 'Libra', 'Scorpio', 
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

# Vimshottari Dasha periods (in years)
DASHA_YEARS = {
    'Ketu': 7,
    'Venus': 20,
    'Sun': 6,
    'Moon': 10,
    'Mars': 7,
    'Rahu': 18,
    'Jupiter': 16,
    'Saturn': 19,
    'Mercury': 17
}

# Dasha order starting from each nakshatra lord
DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

# Nakshatra lords (each nakshatra ruled by a planet)
NAKSHATRA_LORDS = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',  # 1-9
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',  # 10-18
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'   # 19-27
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

def get_nakshatra_info(longitude):
    """Get nakshatra info from longitude."""
    nakshatra_num = int(longitude / (360/27))
    nakshatra_lord = NAKSHATRA_LORDS[nakshatra_num]
    degrees_in_nakshatra = (longitude % (360/27))

    return {
        'nakshatra': NAKSHATRAS[nakshatra_num],
        'nakshatra_num': nakshatra_num + 1,
        'lord': nakshatra_lord,
        'degrees_in_nakshatra': round(degrees_in_nakshatra, 2)
    }

def calculate_vimshottari_dasha(moon_longitude, birth_date_str, birth_time_str, timezone='UTC'):
    """Calculate Vimshottari Dasha periods."""

    # for moon
    nak_info = get_nakshatra_info(moon_longitude)
    birth_nakshatra_lord = nak_info['lord']

    # Calc how much nakshatra has been traversed
    nakshatra_span = 360 / 27
    traversed = nak_info['degrees_in_nakshatra']
    balance_ratio = (nakshatra_span - traversed) / nakshatra_span

    # Calc balance of birth dahsas in years
    total_years = DASHA_YEARS[birth_nakshatra_lord]
    balance_years = total_years * balance_ratio

    # Parse birth date
    dt = datetime.strptime(f"{birth_date_str} {birth_time_str}", "%Y-%m-%d %H:%M")
    if timezone != 'UTC':
        local_tz = pytz.timezone(timezone)
        dt = local_tz.localize(dt)

    # Calculate dasha periods
    dasha_periods = []

    # Find starting position in dasha order
    start_idx = DASHA_ORDER.index(birth_nakshatra_lord)

    # First dasha (balance period)
    current_date = dt
    end_date = current_date + timedelta(days=balance_years * 365.25)
    dasha_periods.append({
        'planet': birth_nakshatra_lord,
        'start_date': current_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'years': round(balance_years, 2),
        'is_balance': True
    })
    current_date = end_date

    # Remaining dashas (complete periods)
    for i in range(1, len(DASHA_ORDER)):
        planet = DASHA_ORDER[(start_idx + i) % len(DASHA_ORDER)]
        years = DASHA_YEARS[planet]
        end_date = current_date + timedelta(days=years * 365.25)
        dasha_periods.append({
            'planet': planet,
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'years': years,
            'is_balance': False
        })
        current_date = end_date

    return {
        'birth_nakshatra': nak_info['nakshatra'],
        'birth_nakshatra_lord': birth_nakshatra_lord,
        'balance_at_birth': round(balance_years, 2),
        'periods': dasha_periods
    }

def calculate_antardasha(mahadasha_planet, mahadasha_years, start_date_str):
    """Calculate Antardasha (sub-periods) for a given Mahadasha."""
    antardashas = []

    # Find the starting index for antardasha
    start_idx = DASHA_ORDER.index(mahadasha_planet)

    # Parse start date
    current_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    # Total proportional units for the mahadasha
    total_units = sum(DASHA_YEARS.values())

    for i in range(len(DASHA_ORDER)):
        antardasha_planet = DASHA_ORDER[(start_idx + i) % len(DASHA_ORDER)]

        # Calculate antardasha duration proportionally
        antardasha_years = (mahadasha_years * DASHA_YEARS[antardasha_planet]) / total_units
        end_date = current_date + timedelta(days=antardasha_years * 365.25)

        antardashas.append({
            'planet': antardasha_planet,
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'duration_years': round(antardasha_years, 3),
            'duration_months': round(antardasha_years * 12, 1)
        })

        current_date = end_date

    return antardashas

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

    # Calculate planetary positions
    moon_longitude = None
    for planet_name, planet_id in PLANETS.items():
        if planet_name == 'Ketu':
            rahu_pos = chart['planets']['Rahu']['longitude']
            ketu_long = (rahu_pos + 180) % 360
            ketu_rasi = int(ketu_long / 30)
            ketu_degrees = ketu_long % 30
            house = int(((ketu_long - sidereal_asc) % 360) / 30) + 1
            chart['planets']['Ketu'] = {
                'longitude': round(ketu_long, 6),
                'rasi': RASIS[ketu_rasi],
                'rasi_num': ketu_rasi + 1,
                'degrees': round(ketu_degrees, 2),
                'house': house
            }
        else:
            planet_data = get_planet_position(planet_id, jd, ayanamsha)
            # Calculate house number relative to Ascendant
            house = int(((planet_data['longitude'] - sidereal_asc) % 360) / 30) + 1
            planet_data['house'] = house
            chart['planets'][planet_name] = planet_data
            if planet_name == 'Moon':
                moon_longitude = planet_data['longitude']

    # Add nakshatra info for moon
    if moon_longitude:
        chart['moon_nakshatra'] = get_nakshatra_info(moon_longitude)
        # Calculate Vimshottari Dasha 
        chart['vimshottari_dasha'] = calculate_vimshottari_dasha(moon_longitude, date, time, timezone)

    return chart

def get_sign_from_longitude(lon):
    sign_index = int(lon / 30)
    return SIGNS[sign_index]

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

    # Moon Nakshatra 
    if 'moon_nakshatra' in chart:
        nak = chart['moon_nakshatra']
        output += [
            f"\nMoon Nakshatra:",
            f"  {nak['nakshatra']} (Lord: {nak['lord']}) - {nak['degrees_in_nakshatra']}° traversed"
        ]

    output += ["\nPlanetary Positions:", "-"*60,
               f"{'Planet':<12} {'Rasi':<15} {'Degrees':<12} {'Longitude':<12}",
               "-"*60]
    
    for planet, data in chart['planets'].items():
        output.append(f"{planet:<12} {data['rasi']:<15} {data['degrees']:<12.2f} {data['longitude']:<12.6f}")

    # Vimshottari Dasha
    if 'vimshottari_dasha' in chart:
        dasha = chart['vimshottari_dasha']
        output += [
            "\n" + "="*80,
            "VIMSHOTTARI DASHA SYSTEM",
            "="*80,
            f"\nBirth Nakshatra: {dasha['birth_nakshatra']} (Lord: {dasha['birth_nakshatra_lord']})",
            f"Balance at Birth: {dasha['balance_at_birth']} years",
            f"\nMahadasha Periods:",
            "-"*80,
            f"{'Planet': <12} {'Start Date':<15} {'End Date':<15} {'Duration':<12} {'Status':<12}",
            "-"*80
        ]

        # Show first 5 mahadashas
        for period in dasha['periods'][:5]:
            status = "(Balance)" if period['is_balance'] else ""
            output.append(
                f"{period['planet']:<12} {period['start_date']:<15} {period['end_date']:<15} "
                f"{period['years']:<12.2f} {status:<12}"
            )

        # Current Dasha
        current_date = datetime.now().date()
        current_dasha = None
        for period in dasha['periods']:
            start = datetime.strptime(period['start_date'], '%Y-%m-%d').date()
            end = datetime.strptime(period['end_date'], '%Y-%m-%d').date()
            if start <= current_date <= end:
                current_dasha = period
                break

            if current_dasha:
                output += [
                    "\n" + "-"*80,
                    f"CURRENT MAHADASHA: {current_dasha['planet']}",
                    f"Period: {current_dasha['start_date']} to {current_dasha['end_date']}",
                    "-"*80
                ]

                # Calculate and display antardashas for current mahdasha
                antardashas = calculate_antardasha(
                    current_dasha['planet'],
                    current_dasha['years'],
                    current_dasha['start_date']
                )

                output += [
                    f"\nAntardasha Periods within {current_dasha['planet']} Mahadasha:", 
                    "-"*80,
                    f"{'Sub-Lord':<12} {'Start Date':<15} {'End Date':<15} {'Duration (months)':<18}",
                    "-"*80
                ]

                # Find current antardasha
                current_antardasha = None
                for ad in antardashas:
                    start = datetime.strptime(ad['start_date'], '%Y-%m-%d').date()
                    end = datetime.strptime(ad['end_date'], '%Y-%m-%d').date()
                    marker = "→ " if start <= current_date <= end else " "
                    output.append(
                        f"{marker}{ad['planet']:<10} {ad['start_date']:<15} {ad['end_date']:<15} "
                        f"{ad['duration_months']:<18.1f}"
                    )
                    if start <= current_date <= end:
                        current_antardasha = ad

                if current_antardasha:
                    output += [
                        "\n" + "-"*80,
                        f"CURRENT ANTARDASHA: {current_dasha['planet']}-{current_antardasha['planet']}",
                        f"Period: {current_antardasha['start_date']} to {current_antardasha['end_date']}",
                        "-"*80
                    ]

    output.append("="*80)
    return "\n".join(output)

