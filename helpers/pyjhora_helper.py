# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
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


def _format_planet_position(entry):
    label, sign_data = entry[0], entry[1]
    if isinstance(sign_data, (list, tuple)) and len(sign_data) >= 2:
        sign_index, degrees = sign_data[0], sign_data[1]
    else:
        sign_index, degrees = sign_data, 0
    return {
        "planet": _planet_label(label),
        "planet_id": label if label != "L" else "L",
        "sign": _safe_name(SIGN_NAMES, sign_index, "Sign"),
        "sign_number": int(sign_index),
        "degrees": round(float(degrees), 4),
    }


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


def get_shad_bala(**params):
    place, dob, tob, jd = _build_inputs(**params)
    sb = strength.shad_bala(jd, place)
    if not sb or len(sb) < 6:
        return {}

    bala_rows = ["Sthana", "Kaala", "Dig", "Cheshta", "Naisargika", "Drik"]
    out = {}
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
        out[planet] = p
    return out


def get_harsha_bala(**params):
    place, dob, tob, jd = _build_inputs(**params)
    hb = strength.harsha_bala(dob, tob, place)
    return {_planet_label(k): v for k, v in hb.items()}


def get_bhava_bala(**params):
    place, dob, tob, jd = _build_inputs(**params)
    try:
        bb = strength.bhava_bala(jd, place)
    except Exception as e:
        return {"error": str(e)}
    return bb


def get_benefics_malefics(**params):
    place, dob, tob, jd = _build_inputs(**params)
    ben = charts.benefics(jd, place)
    mal = charts.malefics(jd, place)
    return {
        "benefics": [_planet_label(p) for p in ben],
        "malefics": [_planet_label(p) for p in mal],
    }


def get_retrograde_combustion(**params):
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    retro = charts.planets_in_retrograde(rc)
    comb = charts.planets_in_combustion(rc)
    return {
        "retrograde": [_planet_label(p) for p in retro],
        "combust": [_planet_label(p) for p in comb],
    }


def get_kp_chart(**params):
    """KP sub-lords up to 5 levels for each planet and the Lagna."""
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    kp = charts.get_KP_lords_from_planet_positions(rc)

    level_keys = ["kp_number", "star_lord", "sub_lord", "sub_sub_lord",
                  "sub_sub_sub_lord", "sub_sub_sub_sub_lord", "sub_sub_sub_sub_sub_lord"]
    out = {}
    for key, values in kp.items():
        name = _planet_label(key) if key != "L" else "Lagna"
        record = {}
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

def get_ashtakoota_match(boy_nakshatra, boy_pada, girl_nakshatra, girl_pada, method="North"):
    ak = compatibility.Ashtakoota(
        int(boy_nakshatra), int(boy_pada), int(girl_nakshatra), int(girl_pada), method=method,
    )
    result = {
        "total_score": ak.compatibility_score(),
        "boy_nakshatra": _safe_name(NAKSHATRA_NAMES, boy_nakshatra - 1, "Nak"),
        "boy_pada": boy_pada,
        "girl_nakshatra": _safe_name(NAKSHATRA_NAMES, girl_nakshatra - 1, "Nak"),
        "girl_pada": girl_pada,
        "method": method,
        "details": {
            "varna": ak.varna_porutham(),
            "vasiya": ak.vasiya_porutham(),
            "tara": ak.tara_porutham(),
            "yoni": ak.yoni_porutham(),
            "maitri": ak.maitri_porutham(),
            "gana": ak.gana_porutham(),
            "bahut": ak.bahut_porutham(),
            "naadi": ak.naadi_porutham(),
            "dina": ak.dina_porutham(),
            "raasi": ak.raasi_porutham(),
            "raasi_adhipathi": ak.raasi_adhipathi_porutham(),
            "rajju": ak.rajju_porutham(),
            "vedha": ak.vedha_porutham(),
            "mahendra": ak.mahendra_porutham(),
            "sthree_dheerga": ak.sthree_dheerga_porutham(),
        },
    }
    if method == "South":
        result["details_south"] = {
            "dina": ak.dina_porutham_south(),
            "gana": ak.gana_porutham_south(),
            "raasi": ak.raasi_porutham_south(),
            "raasi_adhipathi": ak.raasi_adhipathi_porutham_south(),
            "rajju": ak.rajju_porutham_south(),
            "vedha": ak.vedha_porutham_south(),
            "vasiya": ak.vasiya_porutham_south(),
            "yoni": ak.yoni_porutham_south(),
            "mahendra": ak.mahendra_porutham_south(),
            "sthree_dheerga": ak.sthree_dheerga_porutham_south(),
        }
    return result


def get_muhurta_data(**params):
    place, dob, tob, jd = _build_inputs(**params)
    safe_calls = [
        ("abhijit_muhurta", drik.abhijit_muhurta),
        ("durmuhurtam", drik.durmuhurtam),
        ("raahu_kaalam", drik.raahu_kaalam),
        ("gulikai_kaalam", drik.gulikai_kaalam),
        ("yamaganda_kaalam", drik.yamaganda_kaalam),
        ("shubha_hora", drik.shubha_hora),
        ("brahma_muhurtha", getattr(drik, "brahma_muhurtha", None)),
        ("godhuli_muhurtha", getattr(drik, "godhuli_muhurtha", None)),
        ("nishita_kaala", getattr(drik, "nishita_kaala", None)),
        ("sahasra_chandrodayam", getattr(drik, "sahasra_chandrodayam", None)),
        ("anandhaadhi_yoga", getattr(drik, "anandhaadhi_yoga", None)),
        ("pushkara_yoga", getattr(drik, "pushkara_yoga", None)),
        ("triguna", getattr(drik, "triguna", None)),
    ]
    out = {}
    for key, fn in safe_calls:
        if fn is None:
            continue
        try:
            out[key] = fn(jd, place)
        except Exception as e:
            out[key] = {"error": str(e)}
    return out


# ---------------------------------------------------------------------------
# Bundled horoscope
# ---------------------------------------------------------------------------

def get_complete_horoscope(**params):
    result = {
        "rasi_chart": get_rasi_chart(**params),
        "panchanga": get_panchanga(**params),
        "bhava_chart": get_bhava_chart(**params),
        "benefics_malefics": get_benefics_malefics(**params),
        "retrograde_combustion": get_retrograde_combustion(**params),
        "kp_chart": None,
        "shad_bala": None,
        "vimsottari_dasa": None,
        "navamsa_chart": None,
    }
    for key, call in [
        ("shad_bala", lambda: get_shad_bala(**params)),
        ("vimsottari_dasa", lambda: get_vimsottari_dasa(**params)),
        ("kp_chart", lambda: get_kp_chart(**params)),
        ("navamsa_chart", lambda: get_divisional_chart(divisional_chart_factor=9, **params)),
    ]:
        try:
            result[key] = call()
        except Exception as e:
            result[key] = {"error": str(e)}
    return result
