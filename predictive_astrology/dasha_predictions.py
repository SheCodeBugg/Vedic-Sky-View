"""
dasha_predictions.py

Dasha-aware prediction engine that weighs transits based on current Dasha period.
Runs independently with birth data input.

Usage:
    python dasha_predictions.py --date 2000-06-16 --time 01:11 --lat 33.0383 --lon -85.0319 --tz America/New_York
"""

import swisseph as swe
from datetime import datetime, timedelta
import pytz
import argparse
from tabulate import tabulate

# ============================================================================
# CONSTANTS
# ============================================================================

PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,
}

RASIS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer',
    'Leo', 'Virgo', 'Libra', 'Scorpio',
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu',
    'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta',
    'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha',
    'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati'
]

DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10,
    'Mars': 7, 'Rahu': 18, 'Jupiter': 16,
    'Saturn': 19, 'Mercury': 17
}

DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
NAKSHATRA_LORDS = (DASHA_ORDER * 3)  # 27 total

VEDIC_DRISHTI = {
    'Sun': [7],
    'Moon': [7],
    'Mars': [4, 7, 8],
    'Mercury': [7],
    'Jupiter': [5, 7, 9],
    'Venus': [7],
    'Saturn': [3, 7, 10],
    'Rahu': [5, 9],
    'Ketu': [5, 9]
}

# Planet characteristics for predictions
PLANET_NATURE = {
    'Sun': {'type': 'neutral', 'themes': ['authority', 'ego', 'father', 'government', 'health', 'vitality']},
    'Moon': {'type': 'benefic', 'themes': ['mind', 'emotions', 'mother', 'public', 'travel', 'fluids']},
    'Mercury': {'type': 'neutral', 'themes': ['communication', 'business', 'intellect', 'siblings', 'learning']},
    'Venus': {'type': 'benefic', 'themes': ['love', 'luxury', 'arts', 'marriage', 'wealth', 'beauty']},
    'Mars': {'type': 'malefic', 'themes': ['energy', 'courage', 'conflict', 'property', 'sports', 'surgery']},
    'Jupiter': {'type': 'benefic', 'themes': ['wisdom', 'wealth', 'children', 'spirituality', 'expansion', 'luck']},
    'Saturn': {'type': 'malefic', 'themes': ['discipline', 'delays', 'karma', 'hard work', 'losses', 'longevity']},
    'Rahu': {'type': 'malefic', 'themes': ['obsession', 'foreign', 'sudden events', 'materialism', 'illusion']},
    'Ketu': {'type': 'malefic', 'themes': ['spirituality', 'detachment', 'losses', 'moksha', 'mysticism']}
}

HOUSE_MEANINGS = {
    1: 'Self, personality, health, appearance',
    2: 'Wealth, family, speech, food',
    3: 'Siblings, courage, communication, short trips',
    4: 'Home, mother, property, happiness, vehicles',
    5: 'Children, creativity, romance, intelligence, speculation',
    6: 'Health issues, enemies, debts, service, obstacles',
    7: 'Marriage, partnerships, business, spouse',
    8: 'Longevity, transformation, inheritance, occult, sudden events',
    9: 'Luck, father, higher education, spirituality, long journeys',
    10: 'Career, status, authority, public life, reputation',
    11: 'Gains, income, friends, aspirations, elder siblings',
    12: 'Losses, expenses, foreign lands, spirituality, isolation, liberation'
}

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def get_julian_day(date_str, time_str, timezone='UTC'):
    """Convert date/time to Julian Day."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    if timezone != 'UTC':
        local_tz = pytz.timezone(timezone)
        dt = local_tz.localize(dt).astimezone(pytz.UTC)
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)


def calculate_ayanamsha(jd):
    """Calculate Lahiri ayanamsha."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa(jd)


def get_nakshatra_info(longitude):
    """Get nakshatra details from longitude."""
    span = 360.0 / 27.0
    idx = int(longitude // span)
    idx = max(0, min(26, idx))
    lord = NAKSHATRA_LORDS[idx]
    return {
        'nakshatra': NAKSHATRAS[idx],
        'nakshatra_num': idx + 1,
        'lord': lord,
        'degrees_in_nakshatra': round(longitude % span, 4)
    }


def calculate_vimshottari(moon_long, birth_dt, timezone='UTC'):
    """Calculate Vimshottari Dasha periods."""
    nak = get_nakshatra_info(moon_long)
    birth_lord = nak['lord']
    span = 360.0 / 27.0
    traversed = nak['degrees_in_nakshatra']
    balance_ratio = (span - traversed) / span
    total_years = DASHA_YEARS[birth_lord]
    balance_years = total_years * balance_ratio

    if birth_dt.tzinfo is None:
        local_tz = pytz.timezone(timezone)
        birth_dt = local_tz.localize(birth_dt)

    periods = []
    start = birth_dt
    end = start + timedelta(days=balance_years * 365.25)
    periods.append({
        'planet': birth_lord,
        'start_date': start.date(),
        'end_date': end.date(),
        'years': round(balance_years, 2),
    })

    start_idx = DASHA_ORDER.index(birth_lord)
    cur = end
    for i in range(1, len(DASHA_ORDER)):
        p = DASHA_ORDER[(start_idx + i) % len(DASHA_ORDER)]
        yrs = DASHA_YEARS[p]
        nxt = cur + timedelta(days=yrs * 365.25)
        periods.append({
            'planet': p,
            'start_date': cur.date(),
            'end_date': nxt.date(),
            'years': yrs
        })
        cur = nxt

    return {
        'birth_nakshatra': nak['nakshatra'],
        'birth_nakshatra_lord': birth_lord,
        'periods': periods
    }


def get_current_dasha(dasha_info, current_date=None):
    """Find current Mahadasha and Antardasha."""
    if current_date is None:
        current_date = datetime.now().date()
    
    current_maha = None
    for period in dasha_info['periods']:
        if period['start_date'] <= current_date <= period['end_date']:
            current_maha = period
            break
    
    if not current_maha:
        return None, None
    
    # Calculate Antardasha within Mahadasha
    maha_start = current_maha['start_date']
    maha_end = current_maha['end_date']
    maha_lord = current_maha['planet']
    maha_days = (maha_end - maha_start).days
    
    # Start with Mahadasha lord for Antardasha
    start_idx = DASHA_ORDER.index(maha_lord)
    antardasha_periods = []
    current_start = maha_start
    
    for i in range(len(DASHA_ORDER)):
        antara_lord = DASHA_ORDER[(start_idx + i) % len(DASHA_ORDER)]
        # Antardasha duration = (Antara years × Maha years) / 120
        antara_days = int((DASHA_YEARS[antara_lord] * current_maha['years'] * 365.25) / 120)
        antara_end = current_start + timedelta(days=antara_days)
        
        if antara_end > maha_end:
            antara_end = maha_end
        
        antardasha_periods.append({
            'planet': antara_lord,
            'start_date': current_start,
            'end_date': antara_end
        })
        
        current_start = antara_end
        if current_start >= maha_end:
            break
    
    current_antara = None
    for period in antardasha_periods:
        if period['start_date'] <= current_date <= period['end_date']:
            current_antara = period
            break
    
    return current_maha, current_antara


def calculate_natal_chart(date_str, time_str, lat, lon, timezone='UTC'):
    """Calculate natal chart with planets and houses."""
    swe.set_ephe_path('')
    jd = get_julian_day(date_str, time_str, timezone)
    ayanamsha = calculate_ayanamsha(jd)

    houses_ret, ascmc = swe.houses(jd, lat, lon, b'P')
    tropical_asc = ascmc[0]
    sidereal_asc = (tropical_asc - ayanamsha) % 360

    chart = {
        'ascendant': {
            'longitude': round(sidereal_asc, 2),
            'sign': RASIS[int(sidereal_asc // 30)],
            'degrees': round(sidereal_asc % 30, 2)
        },
        'planets': {}
    }

    moon_long = None
    for pname, pid in PLANETS.items():
        pos, _ = swe.calc_ut(jd, pid)
        tropical_long = pos[0] % 360
        sidereal_long = (tropical_long - ayanamsha) % 360
        sign_idx = int(sidereal_long // 30)
        house = int(((sidereal_long - sidereal_asc) % 360) // 30) + 1
        
        chart['planets'][pname] = {
            'longitude': round(sidereal_long, 2),
            'sign': RASIS[sign_idx],
            'degrees': round(sidereal_long % 30, 2),
            'house': house
        }
        
        if pname == 'Moon':
            moon_long = sidereal_long

    # Add Ketu
    if 'Rahu' in chart['planets']:
        rahu_long = chart['planets']['Rahu']['longitude']
        ketu_long = (rahu_long + 180) % 360
        sign_idx = int(ketu_long // 30)
        house = int(((ketu_long - sidereal_asc) % 360) // 30) + 1
        
        chart['planets']['Ketu'] = {
            'longitude': round(ketu_long, 2),
            'sign': RASIS[sign_idx],
            'degrees': round(ketu_long % 30, 2),
            'house': house
        }

    # Calculate Vimshottari Dasha
    if moon_long:
        birth_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        chart['vimshottari'] = calculate_vimshottari(moon_long, birth_dt, timezone)

    return chart


def get_current_transits(natal_asc_long):
    """Get current planetary transits."""
    now = datetime.now()
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60.0)
    
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsha = swe.get_ayanamsa(jd)
    
    transits = {
        'timestamp': now.strftime("%Y-%m-%d %H:%M UTC"),
        'planets': {}
    }
    
    for pname, pid in PLANETS.items():
        pos, _ = swe.calc_ut(jd, pid)
        tropical_long = pos[0] % 360
        sidereal_long = (tropical_long - ayanamsha) % 360
        sign_idx = int(sidereal_long // 30)
        house = int(((sidereal_long - natal_asc_long) % 360) // 30) + 1
        
        transits['planets'][pname] = {
            'longitude': round(sidereal_long, 2),
            'sign': RASIS[sign_idx],
            'degrees': round(sidereal_long % 30, 2),
            'house': house
        }
    
    # Add Ketu
    if 'Rahu' in transits['planets']:
        rahu_long = transits['planets']['Rahu']['longitude']
        ketu_long = (rahu_long + 180) % 360
        sign_idx = int(ketu_long // 30)
        house = int(((ketu_long - natal_asc_long) % 360) // 30) + 1
        
        transits['planets']['Ketu'] = {
            'longitude': round(ketu_long, 2),
            'sign': RASIS[sign_idx],
            'degrees': round(ketu_long % 30, 2),
            'house': house
        }
    
    return transits


# ============================================================================
# PREDICTION ENGINE
# ============================================================================

def check_aspect(transit_planet_house, natal_planet_house, planet_name):
    """Check if transit planet aspects natal planet."""
    if planet_name not in VEDIC_DRISHTI:
        return False
    
    aspects = VEDIC_DRISHTI[planet_name]
    for aspect in aspects:
        aspected_house = ((transit_planet_house - 1 + aspect) % 12) + 1
        if aspected_house == natal_planet_house:
            return True
    return False


def generate_dasha_aware_predictions(natal_chart, transits, dasha_info):
    """Generate predictions weighing Dasha importance."""
    
    current_maha, current_antara = get_current_dasha(dasha_info)
    
    if not current_maha:
        return {"error": "Could not determine current Dasha period"}
    
    maha_lord = current_maha['planet']
    antara_lord = current_antara['planet'] if current_antara else None
    
    predictions = {
        'dasha_context': {
            'mahadasha': maha_lord,
            'mahadasha_period': f"{current_maha['start_date']} to {current_maha['end_date']}",
            'antardasha': antara_lord,
            'antardasha_period': f"{current_antara['start_date']} to {current_antara['end_date']}" if current_antara else None
        },
        'high_priority': [],
        'medium_priority': [],
        'general_transits': [],
        'aspects': []
    }
    
    # Analyze each transiting planet
    for planet, t_data in transits['planets'].items():
        t_house = t_data['house']
        t_sign = t_data['sign']
        
        importance = 0
        prediction_text = ""
        
        # HIGHEST PRIORITY: Mahadasha lord transiting
        if planet == maha_lord:
            importance = 10
            prediction_text = f"🔥 **{planet} (YOUR MAHADASHA LORD)** transiting {t_sign} in your {t_house}th house\n"
            prediction_text += f"   → {HOUSE_MEANINGS[t_house]}\n"
            prediction_text += f"   → This is THE most important transit! {planet} themes are HIGHLY activated.\n"
            prediction_text += f"   → Major life events related to {', '.join(PLANET_NATURE[planet]['themes'])} likely.\n"
            predictions['high_priority'].append(prediction_text)
            
        # HIGH PRIORITY: Antardasha lord transiting
        elif planet == antara_lord:
            importance = 7
            prediction_text = f"⚡ **{planet} (Your Antardasha Lord)** transiting {t_sign} in your {t_house}th house\n"
            prediction_text += f"   → {HOUSE_MEANINGS[t_house]}\n"
            prediction_text += f"   → Strong activation of {planet} themes: {', '.join(PLANET_NATURE[planet]['themes'][:3])}\n"
            predictions['high_priority'].append(prediction_text)
            
        # MEDIUM PRIORITY: Other planets
        else:
            importance = 3
            prediction_text = f"• {planet} in {t_sign} ({t_house}th house): {HOUSE_MEANINGS[t_house]}\n"
            predictions['general_transits'].append(prediction_text)
        
        # Check aspects to natal planets
        for n_planet, n_data in natal_chart['planets'].items():
            if check_aspect(t_house, n_data['house'], planet):
                aspect_text = f"   ⭐ Transit {planet} aspects natal {n_planet} (house {n_data['house']})\n"
                
                # Extra important if aspecting Dasha lords
                if n_planet == maha_lord:
                    aspect_text = f"   🔥🔥 Transit {planet} aspects YOUR NATAL MAHADASHA LORD ({n_planet})!\n"
                    predictions['high_priority'].append(aspect_text)
                elif n_planet == antara_lord:
                    aspect_text = f"   ⚡⚡ Transit {planet} aspects YOUR NATAL ANTARDASHA LORD ({n_planet})!\n"
                    predictions['high_priority'].append(aspect_text)
                else:
                    predictions['aspects'].append(aspect_text)
    
    return predictions


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def print_natal_chart(natal_chart):
    """Display natal chart summary."""
    print("\n" + "="*70)
    print("🌟 NATAL CHART")
    print("="*70)
    
    asc = natal_chart['ascendant']
    print(f"Ascendant: {asc['sign']} at {asc['degrees']:.2f}°\n")
    
    rows = []
    for planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']:
        if planet in natal_chart['planets']:
            p = natal_chart['planets'][planet]
            rows.append([planet, p['sign'], f"{p['degrees']:.2f}°", p['house']])
    
    print(tabulate(rows, headers=['Planet', 'Sign', 'Degrees', 'House'], tablefmt='fancy_grid'))


def print_current_transits(transits):
    """Display current transit positions."""
    print("\n" + "="*70)
    print(f"📅 CURRENT TRANSITS - {transits['timestamp']}")
    print("="*70)
    
    rows = []
    for planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']:
        if planet in transits['planets']:
            p = transits['planets'][planet]
            rows.append([planet, p['sign'], f"{p['degrees']:.2f}°", p['house']])
    
    print(tabulate(rows, headers=['Planet', 'Sign', 'Degrees', 'Transit House'], tablefmt='fancy_grid'))


def print_dasha_predictions(predictions):
    """Display Dasha-aware predictions."""
    print("\n" + "="*70)
    print("🔮 DASHA-AWARE PREDICTIONS")
    print("="*70)
    
    ctx = predictions['dasha_context']
    print(f"\n📊 CURRENT LIFE PHASE:")
    print(f"   Mahadasha: {ctx['mahadasha']} ({ctx['mahadasha_period']})")
    if ctx['antardasha']:
        print(f"   Antardasha: {ctx['antardasha']} ({ctx['antardasha_period']})")
    
    print("\n" + "━"*70)
    print("🔥 HIGH PRIORITY TRANSITS (Dasha Lords Active)")
    print("━"*70)
    if predictions['high_priority']:
        for pred in predictions['high_priority']:
            print(pred)
    else:
        print("No high priority transits at this time.\n")
    
    print("\n" + "━"*70)
    print("⚡ IMPORTANT ASPECTS")
    print("━"*70)
    if predictions['aspects']:
        for asp in predictions['aspects']:
            print(asp)
    else:
        print("No major aspects detected.\n")
    
    print("\n" + "━"*70)
    print("📍 GENERAL TRANSITS")
    print("━"*70)
    for transit in predictions['general_transits']:
        print(transit)


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Dasha-aware Vedic astrology predictions',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--date', required=True, help='Birth date (YYYY-MM-DD)')
    parser.add_argument('--time', required=True, help='Birth time (HH:MM in 24h format)')
    parser.add_argument('--lat', type=float, required=True, help='Latitude')
    parser.add_argument('--lon', type=float, required=True, help='Longitude')
    parser.add_argument('--tz', default='UTC', help='Timezone (e.g., America/New_York)')
    
    args = parser.parse_args()
    
    print("\n🌌 VEDIC SKY VIEW - Dasha Prediction Engine 🌌")
    print(f"Birth Data: {args.date} {args.time} ({args.lat}, {args.lon}) [{args.tz}]")
    
    # Calculate natal chart
    natal_chart = calculate_natal_chart(args.date, args.time, args.lat, args.lon, args.tz)
    print_natal_chart(natal_chart)
    
    # Get current transits
    transits = get_current_transits(natal_chart['ascendant']['longitude'])
    print_current_transits(transits)
    
    # Generate predictions
    predictions = generate_dasha_aware_predictions(
        natal_chart,
        transits,
        natal_chart['vimshottari']
    )
    print_dasha_predictions(predictions)
    
    print("\n" + "="*70)
    print("✨ Analysis Complete ✨")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()