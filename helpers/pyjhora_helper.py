# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Core PyJHora wrappers: rasi/bhava/divisional charts, panchanga, core dashas,
strengths and match. Fixes the old helper's bugs:
  * Correct PLANET_NAMES order (Sun..Pluto, index 0-11)
  * Karana lookup uses the full 60-element table (not % 11)
  * Panchanga returns tithi/nakshatra/yoga end-times
  * Bhava chart accepts bhaava_madhya_method
  * Divisional charts cover every JHora factor with custom/mixed support
"""

import swisseph as swe

from jhora import const, utils
from jhora.panchanga import drik
from jhora.horoscope.chart import charts, strength
from jhora.horoscope.dhasa.graha import vimsottari, ashtottari, yogini
from jhora.horoscope.match import compatibility

from helpers import jhora_config  # noqa: F401 — triggers init_pyjhora_defaults()

# ---------------------------------------------------------------------------
# Name tables (match JHora's internal ordering)
# ---------------------------------------------------------------------------
PLANET_NAMES = {
    "L": "Lagna",
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury",
    4: "Jupiter", 5: "Venus", 6: "Saturn", 7: "Rahu",
    8: "Ketu", 9: "Uranus", 10: "Neptune", 11: "Pluto",
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

YOGA_NAMES = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti",
]

# Karana is a 1..60 index. Position 1 is Kimstughna; the seven movable karanas
# (Bava..Vishti) repeat 8 times, then the last three (Shakuni, Chatushpada, Naga)
# cap the list. This matches JHora's KARANA_LIST.
_KARANA_CYCLE = ["Bava", "Balava", "Kaulava", "Taitila", "Garija", "Vanija", "Vishti"]
KARANA_NAMES = (
    ["Kimstughna"]
    + _KARANA_CYCLE * 8
    + ["Shakuni", "Chatushpada", "Naga"]
)  # length == 60

LUNAR_MONTH_NAMES = [
    "", "Chaitra", "Vaisakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashira", "Pausha", "Magha", "Phalguna",
]

# Divisional chart factors and their JHora builders. `None` means "use the
# generic divisional_positions_from_rasi_positions helper".
DIVISIONAL_BUILDERS = {
    1:   ("D1_Rasi",           None),
    2:   ("D2_Hora",            charts.hora_chart),
    3:   ("D3_Drekkana",        charts.drekkana_chart),
    4:   ("D4_Chaturthamsa",    charts.chaturthamsa_chart),
    5:   ("D5_Panchamsa",       None),
    6:   ("D6_Shashthamsa",     None),
    7:   ("D7_Saptamsa",        charts.saptamsa_chart),
    8:   ("D8_Ashtamsa",        charts.ashtamsa_chart),
    9:   ("D9_Navamsa",         charts.navamsa_chart),
    10:  ("D10_Dasamsa",        charts.dasamsa_chart),
    11:  ("D11_Rudramsa",       None),
    12:  ("D12_Dwadasamsa",     charts.dwadasamsa_chart),
    16:  ("D16_Shodasamsa",     charts.shodasamsa_chart),
    20:  ("D20_Vimsamsa",       charts.vimsamsa_chart),
    24:  ("D24_Chaturvimsamsa", charts.chaturvimsamsa_chart),
    27:  ("D27_Nakshatramsa",   charts.nakshatramsa_chart),
    30:  ("D30_Trimsamsa",      charts.trimsamsa_chart),
    40:  ("D40_Khavedamsa",     charts.khavedamsa_chart),
    45:  ("D45_Akshavedamsa",   charts.akshavedamsa_chart),
    60:  ("D60_Shashtyamsa",    charts.shashtyamsa_chart),
    81:  ("D81_Nadiamsa",       charts.nadiamsa_chart),
    108: ("D108_Ashtotharamsa", charts.ashtotharamsa_chart),
    144: ("D144_Dwadas_Dwadas", charts.dwadas_dwadasamsa_chart),
    150: ("D150_Nadiamsa_150",  None),
    300: ("D300_Ardha_Nadiamsa", None),
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_name(names, idx, fallback=""):
    try:
        return names[int(idx)]
    except (IndexError, TypeError, ValueError):
        return f"{fallback}{idx}"


def _planet_label(p):
    # Some dashas (karaka) emit labeled tuples like ('atma_karaka', 5) instead
    # of bare planet indices — render both the label and the resolved name.
    if isinstance(p, (list, tuple)) and len(p) == 2 and isinstance(p[0], str):
        return f"{p[0]}={PLANET_NAMES.get(p[1], p[1])}"
    return PLANET_NAMES.get(p, str(p))


def _build_inputs(year, month, day, hour, minute, latitude, longitude,
                  timezone_offset, location_name, **_):
    """Translate a birth-detail payload into JHora's primitives."""
    place = drik.Place(location_name, float(latitude), float(longitude), float(timezone_offset))
    dob = (int(year), int(month), int(day))
    tob = (int(hour), int(minute), 0)
    time_decimal = hour + minute / 60.0
    jd = swe.julday(int(year), int(month), int(day), time_decimal)
    return place, dob, tob, jd


# Vimshottari nakshatra-lord cycle (9), repeats across 27 nakshatras.
_NAK_LORD_CYCLE = [8, 5, 0, 1, 2, 7, 4, 6, 3]  # Ketu, Ven, Sun, Moo, Mar, Rahu, Jup, Sat, Mer

# Sign-lord table (Aries=Mars ... Pisces=Jupiter)
_SIGN_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]

# Exaltation sign per planet 0-8 (Sun..Ketu); None = no Vedic dignity (outer planets)
_EXALT_SIGN = {0: 0, 1: 1, 2: 9, 3: 5, 4: 3, 5: 11, 6: 6, 7: 1, 8: 7}
_DEBIL_SIGN = {0: 6, 1: 7, 2: 3, 3: 11, 4: 9, 5: 5, 6: 0, 7: 7, 8: 1}
# Moolatrikona: (sign, deg_lo, deg_hi)
_MOOLATRIKONA = {
    0: (4,  0, 20),   # Sun: Leo 0-20
    1: (1,  4, 30),   # Moon: Taurus 4-30
    2: (0,  0, 12),   # Mars: Aries 0-12
    3: (5, 16, 20),   # Mercury: Virgo 16-20
    4: (8,  0, 10),   # Jupiter: Sagittarius 0-10
    5: (6,  0, 15),   # Venus: Libra 0-15
    6: (10, 0, 20),   # Saturn: Aquarius 0-20
}
_OWN_SIGNS = {
    0: [4], 1: [3], 2: [0, 7], 3: [2, 5],
    4: [8, 11], 5: [1, 6], 6: [9, 10],
}


def _nakshatra_of_longitude(sign_index, degrees):
    """Return (1-based nak number, pada 1-4, lord name) from sign + deg."""
    total = float(sign_index) * 30.0 + float(degrees)
    nak = int(total / (360.0 / 27.0)) % 27
    pada = int((total % (360.0 / 27.0)) / (360.0 / 27.0 / 4.0)) + 1
    lord_id = _NAK_LORD_CYCLE[nak % 9]
    return nak + 1, pada, PLANET_NAMES.get(lord_id, str(lord_id))


def _dignity(planet_id, sign_index, degrees):
    """Classical Parasara dignity: Exalted / Debilitated / Moolatrikona /
    Own / Friend / Enemy / Neutral. Returns None for outer planets."""
    try:
        p = int(planet_id)
    except (TypeError, ValueError):
        return None
    if p not in _EXALT_SIGN:   # Uranus/Neptune/Pluto or Lagna
        return None

    if sign_index == _EXALT_SIGN[p]:
        return "Exalted"
    if sign_index == _DEBIL_SIGN[p]:
        return "Debilitated"
    if p in _MOOLATRIKONA:
        m_sign, lo, hi = _MOOLATRIKONA[p]
        if sign_index == m_sign and lo <= degrees < hi:
            return "Moolatrikona"
    if sign_index in _OWN_SIGNS.get(p, []):
        return "Own"

    sign_lord = _SIGN_LORDS[sign_index]
    if p == sign_lord:
        return "Own"
    try:
        from jhora import const
        if sign_lord in const.friendly_planets[p]:
            return "Friend"
        if sign_lord in const.enemy_planets[p]:
            return "Enemy"
        return "Neutral"
    except Exception:
        return None


def _format_planet_position(entry):
    label, sign_data = entry[0], entry[1]
    if isinstance(sign_data, (list, tuple)) and len(sign_data) >= 2:
        sign_index, degrees = sign_data[0], sign_data[1]
    else:
        sign_index, degrees = sign_data, 0
    sign_idx_int = int(sign_index)
    degrees_f = float(degrees)
    nak_num, pada, nak_lord = _nakshatra_of_longitude(sign_idx_int, degrees_f)
    nak_name = _safe_name(NAKSHATRA_NAMES, nak_num - 1, "Nakshatra")

    entry_out = {
        "planet": _planet_label(label),
        "planet_id": label if label != "L" else "L",
        "sign": _safe_name(SIGN_NAMES, sign_idx_int, "Sign"),
        "sign_number": sign_idx_int,
        "sign_lord": PLANET_NAMES.get(_SIGN_LORDS[sign_idx_int], None),
        "degrees": round(degrees_f, 4),
        "nakshatra": nak_name,
        "nakshatra_number": nak_num,
        "nakshatra_pada": pada,
        "nakshatra_lord": nak_lord,
        "relationship": _dignity(label if label != "L" else None,
                                 sign_idx_int, degrees_f),
    }
    return entry_out


def _to_hms(hours_float):
    if hours_float is None:
        return None
    try:
        h = float(hours_float)
    except (TypeError, ValueError):
        return hours_float
    negative = h < 0
    h = abs(h) % 24
    hh = int(h)
    mm_f = (h - hh) * 60
    mm = int(mm_f)
    ss = int(round((mm_f - mm) * 60))
    if ss == 60:
        ss = 0
        mm += 1
    if mm == 60:
        mm = 0
        hh = (hh + 1) % 24
    sign = "-" if negative else ""
    return f"{sign}{hh:02d}:{mm:02d}:{ss:02d}"


def _duration_struct(start, end):
    return {
        "start_hours": round(float(start), 4) if start is not None else None,
        "end_hours": round(float(end), 4) if end is not None else None,
        "start_time": _to_hms(start),
        "end_time": _to_hms(end),
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def get_rasi_chart(**params):
    place, *_rest, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    return [_format_planet_position(e) for e in rc]


def get_divisional_chart(divisional_chart_factor, chart_method=1, **params):
    """Return a single divisional chart by factor."""
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)

    df = int(divisional_chart_factor)
    if df == 1:
        return [_format_planet_position(e) for e in rc]

    if df in DIVISIONAL_BUILDERS and DIVISIONAL_BUILDERS[df][1] is not None:
        builder = DIVISIONAL_BUILDERS[df][1]
        result = builder(rc, chart_method=chart_method)
    else:
        result = charts.divisional_positions_from_rasi_positions(
            rc, divisional_chart_factor=df, chart_method=chart_method,
        )
    return [_format_planet_position(e) for e in result]


def get_divisional_charts(**params):
    """All 24 JHora divisional charts keyed by their canonical name."""
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)

    out = {}
    for df, (name, builder) in DIVISIONAL_BUILDERS.items():
        try:
            if builder is None:
                if df == 1:
                    data = rc
                else:
                    data = charts.divisional_positions_from_rasi_positions(
                        rc, divisional_chart_factor=df, chart_method=1,
                    )
            else:
                data = builder(rc, chart_method=1)
            out[name] = [_format_planet_position(e) for e in data]
        except Exception as e:
            out[name] = {"error": str(e)}
    return out


def get_custom_divisional_chart(divisional_chart_factor, chart_method=0,
                                base_rasi=None, count_from_end_of_sign=False,
                                **params):
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    df = int(divisional_chart_factor)
    if df < 1 or df > const.MAX_DHASAVARGA_FACTOR:
        raise ValueError(f"divisional_chart_factor must be 1..{const.MAX_DHASAVARGA_FACTOR}")
    result = charts.custom_divisional_chart(
        rc, divisional_chart_factor=df, chart_method=chart_method,
        base_rasi=base_rasi, count_from_end_of_sign=bool(count_from_end_of_sign),
    )
    return [_format_planet_position(e) for e in result]


def get_mixed_chart(varga_factor_1, varga_factor_2,
                    chart_method_1=1, chart_method_2=1, **params):
    place, dob, tob, jd = _build_inputs(**params)
    result = charts.mixed_chart(
        jd, place,
        varga_factor_1=int(varga_factor_1), chart_method_1=int(chart_method_1),
        varga_factor_2=int(varga_factor_2), chart_method_2=int(chart_method_2),
    )
    return [_format_planet_position(e) for e in result]


def get_bhava_chart(bhava_madhya_method=None, **params):
    place, dob, tob, jd = _build_inputs(**params)
    method = int(bhava_madhya_method) if bhava_madhya_method is not None else const.bhaava_madhya_method
    bc = charts.bhava_chart(jd, place, bhava_madhya_method=method)

    houses = []
    for entry in bc:
        house_num, cusps, planet_ids = entry[0], entry[1], entry[2]
        cusp_start, cusp_mid, cusp_end = cusps
        houses.append({
            "house": int(house_num),
            "sign": _safe_name(SIGN_NAMES, int(house_num) - 1, "Sign") if isinstance(house_num, int) else None,
            "cusp_start": round(float(cusp_start), 4),
            "cusp_mid": round(float(cusp_mid), 4),
            "cusp_end": round(float(cusp_end), 4),
            "planets": [_planet_label(p) for p in planet_ids],
            "planet_ids": list(planet_ids),
        })

    return {"bhaava_madhya_method": method, "houses": houses}


_SIGN_ABBR = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]


def _deg_to_dms(deg_abs):
    """Convert absolute zodiacal degrees (0-360) to (sign_abbr, deg, min, sec) within sign."""
    deg_abs = float(deg_abs) % 360
    sign_idx = int(deg_abs / 30)
    within = deg_abs - sign_idx * 30
    d = int(within)
    m = int((within - d) * 60)
    s = round(((within - d) * 60 - m) * 60)
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return _SIGN_ABBR[sign_idx % 12], d, m, s


def get_chalit_table(bhava_madhya_method=None, **params):
    place, dob, tob, jd = _build_inputs(**params)
    method = int(bhava_madhya_method) if bhava_madhya_method is not None else const.bhaava_madhya_method
    bc = charts.bhava_chart(jd, place, bhava_madhya_method=method)

    rows = []
    for entry in bc:
        house_num, cusps, _ = entry[0], entry[1], entry[2]
        cusp_start, cusp_mid, _ = cusps
        begin_sign, bd, bm, bs = _deg_to_dms(cusp_start)
        mid_sign, md, mm, ms = _deg_to_dms(cusp_mid)
        rows.append({
            "bh": int(house_num),
            "begin_sign": begin_sign,
            "begin_deg": bd,
            "begin_min": bm,
            "begin_sec": bs,
            "mid_sign": mid_sign,
            "mid_deg": md,
            "mid_min": mm,
            "mid_sec": ms,
        })

    return {"bhaava_madhya_method": method, "chalit_table": rows}


# ---------------------------------------------------------------------------
# Bhav Madhya Chart — planet vs house-midpoint aspect table
# ---------------------------------------------------------------------------

_PLANET_ABBR = ["SU", "MO", "MA", "ME", "JU", "VE", "SA", "RA", "KE"]

_ASPECTS = [
    ("CJ",   0.0, 8.0),
    ("SX",  60.0, 6.0),
    ("SQ",  90.0, 7.0),
    ("TR", 120.0, 8.0),
    ("QC", 150.0, 5.0),
    ("OP", 180.0, 8.0),
]


def _angular_distance(a, b):
    diff = abs(float(a) - float(b)) % 360
    return diff if diff <= 180 else 360 - diff


def _aspect_cell(planet_lon, madhya_lon):
    dist = _angular_distance(planet_lon, madhya_lon)
    best = None
    best_orb = None
    for name, exact, max_orb in _ASPECTS:
        orb = abs(dist - exact)
        if orb <= max_orb:
            if best_orb is None or orb < best_orb:
                best, best_orb = name, orb
    if best is None:
        return "--"
    return f"{best} {round(best_orb, 2)}"


def get_bhav_madhya_chart(bhava_madhya_method=None, **params):
    place, dob, tob, jd = _build_inputs(**params)
    method = int(bhava_madhya_method) if bhava_madhya_method is not None else const.bhaava_madhya_method

    rc = charts.rasi_chart(jd, place)
    planet_lons = {}
    for entry in rc:
        label, sign_data = entry[0], entry[1]
        if isinstance(sign_data, (list, tuple)) and len(sign_data) >= 2:
            lon = int(sign_data[0]) * 30 + float(sign_data[1])
        else:
            lon = float(sign_data) * 30
        idx = int(label) if str(label).lstrip("-").isdigit() else None
        if idx is not None and 0 <= idx <= 8:
            planet_lons[idx] = lon

    bc = charts.bhava_chart(jd, place, bhava_madhya_method=method)
    madhya_lons = {}
    for entry in bc:
        house_num, cusps = entry[0], entry[1]
        madhya_lons[int(house_num)] = float(cusps[1])

    columns = list(range(1, 13))
    rows = []
    for p_idx, abbr in enumerate(_PLANET_ABBR):
        if p_idx not in planet_lons:
            continue
        p_lon = planet_lons[p_idx]
        cols = {"planet": abbr}
        for h in columns:
            m_lon = madhya_lons.get(h)
            cols[str(h)] = _aspect_cell(p_lon, m_lon) if m_lon is not None else "--"
        rows.append(cols)

    return {
        "bhaava_madhya_method": method,
        "columns": [str(h) for h in columns],
        "legend": {
            "CJ": "Conjunction (0°)",
            "SX": "Sextile (60°)",
            "SQ": "Square (90°)",
            "TR": "Trine (120°)",
            "QC": "Quincunx (150°)",
            "OP": "Opposition (180°)",
            "--": "No major aspect",
        },
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Panchanga
# ---------------------------------------------------------------------------

def get_panchanga(**params):
    place, dob, tob, jd = _build_inputs(**params)

    nak = drik.nakshatra(jd, place)
    tit = drik.tithi(jd, place)
    yog = drik.yogam(jd, place)
    kar = drik.karana(jd, place)
    vaara_idx = drik.vaara(jd, place)
    sr = drik.sunrise(jd, place)
    ss = drik.sunset(jd, place)
    mr = drik.moonrise(jd, place)
    ms = drik.moonset(jd, place)
    lm = drik.lunar_month(jd, place)
    rk = drik.raahu_kaalam(jd, place)
    gk = drik.gulikai_kaalam(jd, place)
    yk = drik.yamaganda_kaalam(jd, place)

    tithi_num = int(tit[0])
    tithi_name_idx = (tithi_num - 1) % 30
    karana_num = int(kar[0])

    panchanga = {
        "date": {"year": dob[0], "month": dob[1], "day": dob[2]},
        "nakshatra": {
            "number": int(nak[0]),
            "name": _safe_name(NAKSHATRA_NAMES, int(nak[0]) - 1, "Nakshatra"),
            "pada": int(nak[1]),
            **_duration_struct(nak[2] if len(nak) > 2 else None,
                                nak[3] if len(nak) > 3 else None),
        },
        "tithi": {
            "number": tithi_num,
            "name": _safe_name(TITHI_NAMES, tithi_name_idx, "Tithi"),
            "paksha": "Shukla" if tithi_num <= 15 else "Krishna",
            **_duration_struct(tit[1] if len(tit) > 1 else None,
                                tit[2] if len(tit) > 2 else None),
        },
        "yoga": {
            "number": int(yog[0]),
            "name": _safe_name(YOGA_NAMES, int(yog[0]) - 1, "Yoga"),
            **_duration_struct(yog[1] if len(yog) > 1 else None,
                                yog[2] if len(yog) > 2 else None),
        },
        "karana": {
            "number": karana_num,
            "name": _safe_name(KARANA_NAMES, karana_num - 1, "Karana"),
            **_duration_struct(kar[1] if len(kar) > 1 else None,
                                kar[2] if len(kar) > 2 else None),
        },
        "weekday": {
            "number": int(vaara_idx),
            "name": _safe_name(WEEKDAY_NAMES, int(vaara_idx), "Day"),
        },
        "sunrise": {"hours": float(sr[0]) if sr else None, "time": sr[1] if sr and len(sr) > 1 else None},
        "sunset": {"hours": float(ss[0]) if ss else None, "time": ss[1] if ss and len(ss) > 1 else None},
        "moonrise": {"hours": float(mr[0]) if mr else None, "time": mr[1] if mr and len(mr) > 1 else None},
        "moonset": {"hours": float(ms[0]) if ms else None, "time": ms[1] if ms and len(ms) > 1 else None},
        "lunar_month": {
            "number": int(lm[0]) if lm else None,
            "name": _safe_name(LUNAR_MONTH_NAMES, int(lm[0]), "Maasa") if lm else None,
            "adhika": bool(lm[1]) if lm and len(lm) > 1 else False,
        },
        "raahu_kaalam": {"start": rk[0], "end": rk[1]} if rk else None,
        "gulikai_kaalam": {"start": gk[0], "end": gk[1]} if gk else None,
        "yamaganda_kaalam": {"start": yk[0], "end": yk[1]} if yk else None,
    }

    return panchanga


# ---------------------------------------------------------------------------
# Dashas
# ---------------------------------------------------------------------------

def _format_dasa_entry(entry):
    lords, date_tuple, duration = entry[0], entry[1], entry[2] if len(entry) > 2 else None
    # Lords tuple may contain 2..6 levels (maha→deha). Emit all present levels.
    level_names = ["maha", "antara", "pratyantara", "sookshma", "prana", "deha"]
    levels = {}
    if isinstance(lords, (list, tuple)):
        for i, l in enumerate(lords):
            if i < len(level_names):
                levels[level_names[i]] = _planet_label(l)
    else:
        levels["maha"] = _planet_label(lords)

    y, m, d = int(date_tuple[0]), int(date_tuple[1]), int(date_tuple[2])
    fh = float(date_tuple[3]) if len(date_tuple) > 3 else 0.0
    item = {
        "lords": levels,
        "start_date": f"{y:04d}-{m:02d}-{d:02d}",
        "start_hours": round(fh, 4),
    }
    if duration is not None:
        item["duration_years"] = round(float(duration), 4)
    return item


def get_vimsottari_dasa(**params):
    place, dob, tob, jd = _build_inputs(**params)
    vd = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)

    meta = {}
    data = vd
    if isinstance(vd, (list, tuple)) and len(vd) == 2 and isinstance(vd[0], tuple):
        if len(vd[0]) == 3:
            meta = {
                "nakshatra": int(vd[0][0]),
                "pada": int(vd[0][1]),
                "pada_index": int(vd[0][2]),
            }
        elif len(vd[0]) >= 2:
            meta = {"nakshatra": int(vd[0][0]), "pada": int(vd[0][1])}
        data = vd[1]

    entries = []
    if isinstance(data, list):
        for e in data:
            if isinstance(e, (list, tuple)) and len(e) >= 2 and isinstance(e[0], (list, tuple)) and not isinstance(e[0][0], (list, tuple)):
                entries.append(_format_dasa_entry(e))
            elif isinstance(e, list) and e and isinstance(e[0], (list, tuple)) and e[0] and isinstance(e[0][0], (list, tuple)):
                for x in e:
                    entries.append(_format_dasa_entry(x))
    return {"meta": meta, "periods": entries}


def get_yogini_dasa(**params):
    place, dob, tob, jd = _build_inputs(**params)
    yd = yogini.get_dhasa_bhukthi(dob, tob, place)
    return [_format_dasa_entry(e) for e in yd if isinstance(e, (list, tuple)) and len(e) >= 2]


def get_ashtottari_dasa(**params):
    place, dob, tob, jd = _build_inputs(**params)
    ad = ashtottari.get_ashtottari_dhasa_bhukthi(jd, place)
    return [_format_dasa_entry(e) for e in ad if isinstance(e, (list, tuple)) and len(e) >= 2]


# ---------------------------------------------------------------------------
# Strengths & classifications
# ---------------------------------------------------------------------------

_SUN_TO_SATURN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# Classical Shad Bala minimum Rupa requirements (BPHS)
_SHAD_BALA_MIN_RUPA = {
    "Sun": 5.0, "Moon": 6.0, "Mars": 5.0, "Mercury": 7.0,
    "Jupiter": 6.5, "Venus": 5.5, "Saturn": 5.0,
}


def get_shad_bala(**params):
    place, dob, tob, jd = _build_inputs(**params)
    sb = strength.shad_bala(jd, place)
    if not sb or len(sb) < 6:
        return {}

    bala_rows = ["Sthana", "Kaala", "Dig", "Cheshta", "Naisargika", "Drik"]
    planets = {}
    for i, planet in enumerate(_SUN_TO_SATURN):
        p = {}
        for j, bala in enumerate(bala_rows):
            try:
                p[bala] = round(float(sb[j][i]), 2)
            except (IndexError, TypeError, ValueError):
                p[bala] = None
        try:
            p["Total"] = round(float(sb[6][i]), 2) if len(sb) > 6 else None
            p["Rupa"] = round(float(sb[7][i]), 2) if len(sb) > 7 else None
            p["Ratio"] = round(float(sb[8][i]), 2) if len(sb) > 8 else None
        except (IndexError, TypeError, ValueError):
            pass
        planets[planet] = p

    # Build ranking by Rupa (strongest = rank 1)
    rupa_pairs = [(name, p.get("Rupa")) for name, p in planets.items()]
    rupa_pairs = [(n, r) for n, r in rupa_pairs if r is not None]
    rupa_pairs.sort(key=lambda x: x[1], reverse=True)

    ranking = []
    for rank, (name, rupa) in enumerate(rupa_pairs, start=1):
        min_req = _SHAD_BALA_MIN_RUPA.get(name)
        passes = (rupa >= min_req) if min_req is not None else None
        ranking.append({
            "rank": rank,
            "planet": name,
            "rupa": rupa,
            "ratio": planets[name].get("Ratio"),
            "minimum_required": min_req,
            "meets_minimum": passes,
        })
        planets[name]["rank"] = rank
        planets[name]["minimum_required"] = min_req
        planets[name]["meets_minimum"] = passes

    strongest = ranking[0]["planet"] if ranking else None
    weakest = ranking[-1]["planet"] if ranking else None

    return {
        "planets": planets,
        "ranking": ranking,
        "strongest": strongest,
        "weakest": weakest,
        "note": (
            "Rank is by Rupa (total Shad Bala / 60). 1 = strongest. "
            "meets_minimum compares Rupa against the classical BPHS minimum "
            "(Sun 5, Moon 6, Mars 5, Mercury 7, Jupiter 6.5, Venus 5.5, Saturn 5)."
        ),
    }





# Classical house significations (1-based)
_HOUSE_NAMES = {
    1: "Tanu (Self/Body)",
    2: "Dhana (Wealth/Family)",
    3: "Sahaja (Siblings/Courage)",
    4: "Sukha (Home/Mother)",
    5: "Putra (Children/Intellect)",
    6: "Ari (Enemies/Health)",
    7: "Yuvati (Spouse/Partnership)",
    8: "Randhra (Longevity/Secrets)",
    9: "Dharma (Fortune/Father)",
    10: "Karma (Career/Status)",
    11: "Labha (Gains/Income)",
    12: "Vyaya (Losses/Moksha)",
}


def get_bhava_bala(**params):
    place, dob, tob, jd = _build_inputs(**params)
    try:
        bb = strength.bhava_bala(jd, place)
    except Exception as e:
        return {"error": str(e)}

    # bb is typically [totals(12), rupa(12), ratio(12)]
    if not bb or len(bb) < 2:
        return {"houses": [], "ranking": [], "raw": bb}

    totals = list(bb[0]) if len(bb) > 0 else [None] * 12
    rupas = list(bb[1]) if len(bb) > 1 else [None] * 12
    ratios = list(bb[2]) if len(bb) > 2 else [None] * 12

    houses = []
    for i in range(12):
        houses.append({
            "house": i + 1,
            "name": _HOUSE_NAMES[i + 1],
            "total": round(float(totals[i]), 2) if i < len(totals) and totals[i] is not None else None,
            "rupa": round(float(rupas[i]), 2) if i < len(rupas) and rupas[i] is not None else None,
            "ratio": round(float(ratios[i]), 2) if i < len(ratios) and ratios[i] is not None else None,
        })

    # Rank by rupa (strongest = 1)
    rankable = [h for h in houses if h["rupa"] is not None]
    rankable.sort(key=lambda h: h["rupa"], reverse=True)
    ranking = []
    for rank, h in enumerate(rankable, start=1):
        ranking.append({
            "rank": rank,
            "house": h["house"],
            "name": h["name"],
            "rupa": h["rupa"],
            "ratio": h["ratio"],
        })
        # attach rank back to the per-house entry
        for entry in houses:
            if entry["house"] == h["house"]:
                entry["rank"] = rank
                break

    strongest = ranking[0]["house"] if ranking else None
    weakest = ranking[-1]["house"] if ranking else None

    return {
        "houses": houses,
        "ranking": ranking,
        "strongest_house": strongest,
        "weakest_house": weakest,
        "note": (
            "Rank is by Rupa (total Bhava Bala / 60). 1 = strongest house. "
            "A classically well-supported bhava usually has Rupa >= 1.0 (ratio >= 1). "
            "Weak houses (rupa below 1) indicate areas that need remedial support."
        ),
    }








def get_kp_chart(**params):
    """KP sub-lords up to 5 levels for each planet and the Lagna."""
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    kp = charts.get_KP_lords_from_planet_positions(rc)

    # Build sign-index lookup from rasi chart
    sign_index_map = {}
    for entry in rc:
        label, sign_data = entry[0], entry[1]
        if isinstance(sign_data, (list, tuple)) and len(sign_data) >= 1:
            sign_index_map[label] = int(sign_data[0])
        else:
            try:
                sign_index_map[label] = int(sign_data)
            except (TypeError, ValueError):
                pass

    level_keys = ["kp_number", "star_lord", "sub_lord", "sub_sub_lord",
                  "sub_sub_sub_lord", "sub_sub_sub_sub_lord", "sub_sub_sub_sub_sub_lord"]
    out = {}
    for key, values in kp.items():
        name = _planet_label(key) if key != "L" else "Lagna"
        record = {}

        sign_idx = sign_index_map.get(key)
        if sign_idx is not None:
            record["sign"] = _safe_name(SIGN_NAMES, sign_idx, "Sign")
            record["sign_lord"] = PLANET_NAMES.get(_SIGN_LORDS[sign_idx], None)

        for i, v in enumerate(values):
            if i >= len(level_keys):
                break
            k = level_keys[i]
            record[k] = int(v) if i > 0 else v
            if i > 0:
                record[k + "_name"] = _planet_label(int(v))
        out[name] = record
    return out


# ---------------------------------------------------------------------------
# Match & muhurta
# ---------------------------------------------------------------------------







