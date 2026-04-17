# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

import swisseph as swe
from jhora.panchanga import drik
from jhora.horoscope.chart import charts, house, strength
from jhora.horoscope.dhasa.graha import vimsottari, ashtottari, yogini
from jhora.horoscope.dhasa.raasi import narayana
from jhora.horoscope.match import compatibility

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury",
    4: "Jupiter", 5: "Saturn", 6: "Rahu", 7: "Ketu",
    8: "Ketu(r)", 9: "Uranus", 10: "Neptune", 11: "Pluto"
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
]

YOGA_NAMES = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti"
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garija", "Vanija",
    "Vishti", "Shakuni", "Chatushpada", "Naga", "Kimstughna"
]


def _safe_name(names_list, index, fallback_prefix=""):
    try:
        return names_list[int(index)]
    except (IndexError, TypeError, ValueError):
        return f"{fallback_prefix}{index}"


def _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Build PyJHora inputs from birth details."""
    place = drik.Place(location_name, latitude, longitude, timezone_offset)
    dob = (year, month, day)
    tob = (hour, minute, 0)
    time_decimal = hour + minute / 60.0
    jd = swe.julday(year, month, day, time_decimal)
    return place, dob, tob, jd


def _format_planet_position(entry):
    """Format a single planet position entry from rasi_chart."""
    label = entry[0]
    sign_index, degrees = entry[1] if isinstance(entry[1], (list, tuple)) else (entry[1], 0)
    planet_name = "Lagna" if label == "L" else PLANET_NAMES.get(label, str(label))
    return {
        "planet": planet_name,
        "sign": _safe_name(SIGN_NAMES, sign_index, "Sign"),
        "sign_number": int(sign_index),
        "degrees": round(float(degrees), 4),
    }


def _format_dasa_entry(entry):
    """Format a vimsottari dasa entry."""
    lords, date_tuple, duration = entry[0], entry[1], entry[2]
    maha_lord = PLANET_NAMES.get(lords[0], str(lords[0]))
    bhukti_lord = PLANET_NAMES.get(lords[1], str(lords[1]))
    y, m, d = int(date_tuple[0]), int(date_tuple[1]), int(date_tuple[2])
    return {
        "maha_dasa": maha_lord,
        "bhukti": bhukti_lord,
        "start_date": f"{y:04d}-{m:02d}-{d:02d}",
        "duration_years": round(float(duration), 2),
    }


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------

def get_rasi_chart(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Rasi (D1) chart with planet positions."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    rc = charts.rasi_chart(jd, place)
    return [_format_planet_position(entry) for entry in rc]


def get_divisional_charts(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get all 16 divisional charts (D1 to D60)."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    rc = charts.rasi_chart(jd, place)

    divisional = {}
    chart_map = {
        "D1_Rasi": rc,
        "D2_Hora": charts.hora_chart(rc),
        "D3_Drekkana": charts.drekkana_chart(rc),
        "D4_Chaturthamsa": charts.chaturthamsa_chart(rc),
        "D7_Saptamsa": charts.saptamsa_chart(rc),
        "D9_Navamsa": charts.navamsa_chart(rc),
        "D10_Dasamsa": charts.dasamsa_chart(rc),
        "D12_Dwadasamsa": charts.dwadasamsa_chart(rc),
        "D16_Shodasamsa": charts.shodasamsa_chart(rc),
        "D20_Vimsamsa": charts.vimsamsa_chart(rc),
        "D24_Chaturvimsamsa": charts.chaturvimsamsa_chart(rc),
        "D27_Nakshatramsa": charts.nakshatramsa_chart(rc),
        "D30_Trimsamsa": charts.trimsamsa_chart(rc),
        "D40_Khavedamsa": charts.khavedamsa_chart(rc),
        "D45_Akshavedamsa": charts.akshavedamsa_chart(rc),
        "D60_Shashtyamsa": charts.shashtyamsa_chart(rc),
    }

    for name, chart_data in chart_map.items():
        divisional[name] = [_format_planet_position(entry) for entry in chart_data]

    return divisional


def get_panchanga(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get complete Panchanga data."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)

    nak = drik.nakshatra(jd, place)
    tit = drik.tithi(jd, place)
    yog = drik.yogam(jd, place)
    kar = drik.karana(jd, place)
    sr = drik.sunrise(jd, place)
    ss = drik.sunset(jd, place)
    vaara = drik.vaara(jd, place)
    lm = drik.lunar_month(jd, place)

    rk = drik.raahu_kaalam(jd, place)
    gk = drik.gulikai_kaalam(jd, place)
    yk = drik.yamaganda_kaalam(jd, place)

    return {
        "nakshatra": {
            "number": int(nak[0]),
            "name": _safe_name(NAKSHATRA_NAMES, nak[0], "Nakshatra"),
            "pada": int(nak[1]),
            "remaining_percentage": round(float(nak[2]), 2),
        },
        "tithi": {
            "number": int(tit[0]),
            "name": _safe_name(TITHI_NAMES, (int(tit[0]) - 1) % 15, "Tithi"),
            "remaining_percentage": round(float(tit[1]), 2),
        },
        "yoga": {
            "number": int(yog[0]),
            "name": _safe_name(YOGA_NAMES, int(yog[0]) - 1, "Yoga"),
        },
        "karana": {
            "number": int(kar[0]),
            "name": _safe_name(KARANA_NAMES, int(kar[0]) % 11, "Karana"),
        },
        "weekday": _safe_name(WEEKDAY_NAMES, vaara, "Day"),
        "sunrise": sr[1] if len(sr) > 1 else str(sr),
        "sunset": ss[1] if len(ss) > 1 else str(ss),
        "lunar_month": int(lm[0]) if lm else None,
        "raahu_kaalam": {"start": rk[0], "end": rk[1]} if rk else None,
        "gulikai_kaalam": {"start": gk[0], "end": gk[1]} if gk else None,
        "yamaganda_kaalam": {"start": yk[0], "end": yk[1]} if yk else None,
    }


def get_bhava_chart(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Bhava (house) chart."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    bc = charts.bhava_chart(jd, place)

    result = []
    for entry in bc:
        house_num = entry[0]
        cusp_start, cusp_mid, cusp_end = entry[1]
        planets_in = entry[2]
        planet_names = ["Lagna" if p == "L" else PLANET_NAMES.get(p, str(p)) for p in planets_in]
        result.append({
            "house": house_num,
            "cusp_start": round(float(cusp_start), 4),
            "cusp_mid": round(float(cusp_mid), 4),
            "cusp_end": round(float(cusp_end), 4),
            "planets": planet_names,
        })
    return result


def get_vimsottari_dasa(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Vimsottari Maha Dasa & Bhukti periods."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    vd = vimsottari.get_vimsottari_dhasa_bhukthi(jd, place)

    meta = {
        "nakshatra": int(vd[0][0]) if vd else None,
        "pada": int(vd[0][1]) if vd else None,
    }

    entries = []
    data_list = vd[1] if len(vd) == 2 else vd[2:]
    if isinstance(data_list, list) and data_list:
        # Flat list of entries like [(lords, date, duration), ...]
        if isinstance(data_list[0], (list, tuple)) and len(data_list[0]) >= 2:
            for entry in data_list:
                entries.append(_format_dasa_entry(entry))
        else:
            # Nested groups
            for group in data_list:
                if isinstance(group, list):
                    for entry in group:
                        entries.append(_format_dasa_entry(entry))

    return {"meta": meta, "periods": entries}


def get_yogini_dasa(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Yogini Dasa periods."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    yd = yogini.get_dhasa_bhukthi(dob, tob, place)

    entries = []
    for entry in yd:
        lords, date_tuple = entry[0], entry[1]
        duration = entry[2] if len(entry) > 2 else None
        maha_lord = PLANET_NAMES.get(lords[0], str(lords[0]))
        bhukti_lord = PLANET_NAMES.get(lords[1], str(lords[1]))
        y, m, d = int(date_tuple[0]), int(date_tuple[1]), int(date_tuple[2])
        item = {
            "maha_dasa": maha_lord,
            "bhukti": bhukti_lord,
            "start_date": f"{y:04d}-{m:02d}-{d:02d}",
        }
        if duration is not None:
            item["duration_years"] = round(float(duration), 2)
        entries.append(item)

    return entries


def get_ashtottari_dasa(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Ashtottari Dasa periods."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    ad = ashtottari.get_ashtottari_dhasa_bhukthi(jd, place)

    entries = []
    for entry in ad:
        entries.append(_format_dasa_entry(entry))

    return entries


def get_shad_bala(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get Shadbala (six-fold strength) for all planets."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    sb = strength.shad_bala(jd, place)

    bala_names = ["Sthana Bala", "Dig Bala", "Kaala Bala", "Cheshta Bala", "Naisargika Bala", "Drik Bala", "Total Shad Bala"]
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Saturn", "Rahu"]

    result = {}
    for i, planet_data in enumerate(sb):
        if i < len(planets):
            result[planets[i]] = {bala_names[j]: round(float(v), 2) for j, v in enumerate(planet_data) if j < len(bala_names)}
    return result


def get_benefics_malefics(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get functional benefic and malefic planets."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    ben = charts.benefics(jd, place)
    mal = charts.malefics(jd, place)

    return {
        "benefics": [PLANET_NAMES.get(p, str(p)) for p in ben],
        "malefics": [PLANET_NAMES.get(p, str(p)) for p in mal],
    }


def get_retrograde_combustion(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get retrograde and combust planets."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    rc = charts.rasi_chart(jd, place)

    retro = charts.planets_in_retrograde(rc)
    comb = charts.planets_in_combustion(rc)

    return {
        "retrograde": [PLANET_NAMES.get(p, str(p)) for p in retro],
        "combust": [PLANET_NAMES.get(p, str(p)) for p in comb],
    }


def get_kp_chart(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get KP (Krishnamurti Paddhati) sub-lords for all planets."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)
    rc = charts.rasi_chart(jd, place)
    kp = charts.get_KP_lords_from_planet_positions(rc)
    return kp


def get_ashtakoota_match(boy_nakshatra, boy_pada, girl_nakshatra, girl_pada, method="North"):
    """
    Get Ashtakoota compatibility score.
    Nakshatra: 1-27 number
    Pada: 1-4
    method: 'North' or 'South'
    """
    ak = compatibility.Ashtakoota(boy_nakshatra, boy_pada, girl_nakshatra, girl_pada, method=method)
    score = ak.compatibility_score()

    result = {
        "total_score": score,
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


def get_muhurta_data(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get muhurta-related data: abhijit, durmuhurtam, hora, etc."""
    place, dob, tob, jd = _build_inputs(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name)

    result = {}
    try:
        result["abhijit_muhurta"] = drik.abhijit_muhurta(jd, place)
    except Exception:
        result["abhijit_muhurta"] = None

    try:
        result["durmuhurtam"] = drik.durmuhurtam(jd, place)
    except Exception:
        result["durmuhurtam"] = None

    try:
        result["raahu_kaalam"] = drik.raahu_kaalam(jd, place)
    except Exception:
        result["raahu_kaalam"] = None

    try:
        result["gulikai_kaalam"] = drik.gulikai_kaalam(jd, place)
    except Exception:
        result["gulikai_kaalam"] = None

    try:
        result["yamaganda_kaalam"] = drik.yamaganda_kaalam(jd, place)
    except Exception:
        result["yamaganda_kaalam"] = None

    try:
        result["shubha_hora"] = drik.shubha_hora(jd, place)
    except Exception:
        result["shubha_hora"] = None

    return result


def get_complete_horoscope(year, month, day, hour, minute, latitude, longitude, timezone_offset, location_name):
    """Get a complete horoscope with all data in one call."""
    params = dict(year=year, month=month, day=day, hour=hour, minute=minute,
                  latitude=latitude, longitude=longitude, timezone_offset=timezone_offset,
                  location_name=location_name)

    result = {}
    result["rasi_chart"] = get_rasi_chart(**params)
    result["panchanga"] = get_panchanga(**params)
    result["bhava_chart"] = get_bhava_chart(**params)
    result["benefics_malefics"] = get_benefics_malefics(**params)
    result["retrograde_combustion"] = get_retrograde_combustion(**params)

    try:
        result["shad_bala"] = get_shad_bala(**params)
    except Exception:
        result["shad_bala"] = None

    try:
        result["vimsottari_dasa"] = get_vimsottari_dasa(**params)
    except Exception:
        result["vimsottari_dasa"] = None

    try:
        navamsa = get_divisional_charts(**params).get("D9_Navamsa")
        result["navamsa_chart"] = navamsa
    except Exception:
        result["navamsa_chart"] = None

    return result
