# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Extended panchanga: muhurtas, vaasa, thaara, samvatsara, lunar month/year,
Tamil calendar, triguna, eclipses, panchaka etc. Thin JSON-friendly wrappers
over `jhora.panchanga.drik`."""

from jhora.panchanga import drik
from jhora import const, utils

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import (
    _build_inputs, _to_hms, SIGN_NAMES, NAKSHATRA_NAMES, WEEKDAY_NAMES,
    TITHI_NAMES,
)


# The standard 60-year Jovian cycle. Index into this using
# drik.samvatsara(...) output (1..60 or 0..59).
SAMVATSARA_NAMES = [
    "Prabhava", "Vibhava", "Shukla", "Pramoda", "Prajapati", "Angirasa",
    "Srimukha", "Bhava", "Yuva", "Dhatu", "Ishvara", "Bahudhanya",
    "Pramadi", "Vikrama", "Vrishabha", "Chitrabhanu", "Svabhanu", "Tarana",
    "Parthiva", "Vyaya", "Sarvajit", "Sarvadhari", "Virodhi", "Vikrita",
    "Khara", "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukha",
    "Hemalamba", "Vilamba", "Vikari", "Sharvari", "Plava", "Shubhakrit",
    "Shobhakrit", "Krodhi", "Vishvavasu", "Parabhava", "Plavanga", "Keelaka",
    "Saumya", "Sadharana", "Virodhikrit", "Paridhavi", "Pramadi", "Ananda",
    "Rakshasa", "Nala", "Pingala", "Kalayukti", "Siddharthi", "Raudra",
    "Durmati", "Dundubhi", "Rudhirodgari", "Raktakshi", "Krodhana", "Akshaya",
]

# Six ritus (seasons) indexed by the lunar maasa.
RITU_NAMES = [
    "Vasanta (Spring)", "Grishma (Summer)", "Varsha (Monsoon)",
    "Sharad (Autumn)", "Hemanta (Pre-winter)", "Shishira (Winter)",
]

# 12 lunar months (maasa).
MAASA_NAMES = [
    "Chaitra", "Vaisakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
]

# Names for the 30 daytime + night muhurthas returned by drik.muhurthas.
MUHURTHA_NAMES = list(const.muhurthas_of_the_day.keys())

# 7-stage shiva_vaasa interpretation keyed by index 1..7.
SHIVA_VAASA_MEANINGS = {
    1: "In Cemetery (Death)",
    2: "With Gowri (Happiness & Wealth)",
    3: "In Assembly (Grief)",
    4: "At Work/Play (Difficulty)",
    5: "At Kailash (Happiness)",
    6: "Mounted on Nandi (Success)",
    7: "At Dinner/Meditation (Trouble)",
}

# Triguna phase names (returned by drik.triguna as an index).
TRIGUNA_NAMES = ["Sattva", "Rajas", "Tamas"]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"} if default is None else default


def _hms_range(pair):
    """Accepts (start_hour, end_hour). Returns dict with both as HH:MM:SS."""
    if not pair or len(pair) < 2:
        return None
    return {
        "start": _to_hms(pair[0]),
        "end": _to_hms(pair[1]),
        "start_hours": round(float(pair[0]), 6),
        "end_hours": round(float(pair[1]), 6),
    }


def _muhurtha_entry(entry):
    """drik.muhurthas returns (name, is_auspicious, (start, end))."""
    name, is_auspicious, span = entry
    return {
        "name": name.title(),
        "auspicious": bool(is_auspicious),
        **(_hms_range(span) or {}),
    }


def _hora_entry(entry):
    """(lord_index, start_hour, end_hour) — used by udhaya_lagna_muhurtha and
    panchaka_rahitha."""
    lord, start, end = entry
    return {
        "sign": SIGN_NAMES[int(lord)] if 0 <= int(lord) < 12 else int(lord),
        **(_hms_range((start, end)) or {}),
    }


def get_panchanga_extras(**params):
    """Return the full extended panchanga in one call."""
    place, dob, tob, jd = _build_inputs(**params)

    # --- Muhurthas ---
    muh_raw = _safe(lambda: drik.muhurthas(jd, place), default=[])
    muhurthas = [_muhurtha_entry(m) for m in muh_raw] if isinstance(muh_raw, list) else []

    udhaya = _safe(lambda: drik.udhaya_lagna_muhurtha(jd, place), default=[])
    udhaya_out = [_hora_entry(e) for e in udhaya] if isinstance(udhaya, list) else []

    panchaka = _safe(lambda: drik.panchaka_rahitha(jd, place), default=[])
    panchaka_out = [_hora_entry(e) for e in panchaka] if isinstance(panchaka, list) else []

    sandhya_raw = _safe(lambda: drik.sandhya_periods(jd, place), default=None)
    sandhya_out = None
    if isinstance(sandhya_raw, (list, tuple)) and len(sandhya_raw) >= 3:
        labels = ["pratah", "madhyahna", "sayam"]
        sandhya_out = {lbl: _hms_range(p) for lbl, p in zip(labels, sandhya_raw)}

    vijaya_raw = _safe(lambda: drik.vijaya_muhurtha(jd, place), default=None)
    vijaya_out = None
    if isinstance(vijaya_raw, (list, tuple)) and vijaya_raw:
        first = vijaya_raw[0]
        # Two shapes: ((abhijit_s, abhijit_e), (nishita_s, nishita_e)) OR (start, end)
        if isinstance(first, (list, tuple)):
            vijaya_out = {
                "abhijit": _hms_range(vijaya_raw[0]),
                "nishita": _hms_range(vijaya_raw[1]) if len(vijaya_raw) > 1 else None,
            }
        else:
            vijaya_out = _hms_range(vijaya_raw)

    # --- Vaasa / thaara ---
    vaara = _safe(lambda: drik.vaara(jd, place), default=None)
    yogini_vaasa_raw = _safe(lambda: drik.yogini_vaasa(jd, place), default=None)
    shiva_vaasa_raw = _safe(lambda: drik.shiva_vaasa(jd, place), default=None)
    shiva_idx = int(shiva_vaasa_raw[0]) if isinstance(shiva_vaasa_raw, (list, tuple)) else None

    thaara_good = _safe(lambda: drik.thaaraabalam(jd, place, return_only_good_stars=True), default=[])
    thaara_all = _safe(lambda: drik.thaaraabalam(jd, place, return_only_good_stars=False), default=[])
    nava_thaara = _safe(lambda: drik.nava_thaara(jd, place), default=[])
    special_thaara = _safe(lambda: drik.special_thaara(jd, place), default=[])

    # --- Lunar / solar year, month, tithi, ritu ---
    lm = _safe(lambda: drik.lunar_month(jd, place), default=None)
    maasa_idx = None
    maasa_name = None
    adhik = False
    kshaya = False
    if isinstance(lm, (list, tuple)) and lm:
        maasa_idx = int(lm[0])
        maasa_name = MAASA_NAMES[maasa_idx] if 0 <= maasa_idx < 12 else str(maasa_idx)
        adhik = bool(lm[1]) if len(lm) > 1 else False
        kshaya = bool(lm[2]) if len(lm) > 2 else False

    ritu_idx = None
    ritu_name = None
    if maasa_idx is not None:
        try:
            ritu_idx = int(drik.ritu(maasa_idx))
            if 0 <= ritu_idx < len(RITU_NAMES):
                ritu_name = RITU_NAMES[ritu_idx]
        except Exception:
            pass

    # Samvatsara requires ephemeris files that may be absent; fall back to raw index.
    samvatsara = _safe_samvatsara(dob, place)

    lunar_year_days = _safe(lambda: drik.lunar_year(jd, place), default=None)
    savana_year_days = _safe(lambda: drik.savana_year(jd, place), default=None)

    triguna_raw = _safe(lambda: drik.triguna(jd, place), default=None)
    triguna_out = None
    if isinstance(triguna_raw, (list, tuple)) and triguna_raw:
        idx = int(triguna_raw[0])
        triguna_out = {
            "guna_index": idx,
            "guna_name": TRIGUNA_NAMES[idx] if 0 <= idx < 3 else str(idx),
            **(_hms_range(triguna_raw[1:3]) or {}),
        }

    # --- Eclipses, conjunctions, special yogas ---
    lunar_eclipse = _safe(lambda: drik.next_lunar_eclipse(jd, place), default=None)
    solar_eclipse = _safe(lambda: drik.next_solar_eclipse(jd, place), default=None)
    next_full_moon_jd = _safe(lambda: drik.next_tithi(jd, place, 15), default=None)
    next_new_moon_jd = _safe(lambda: drik.next_tithi(jd, place, 30), default=None)
    pushkara = _safe(lambda: drik.pushkara_yoga(jd, place), default=None)
    vidaal = _safe(lambda: drik.vidaal_yoga(jd, place), default=None)
    varjyam = _safe(lambda: drik.varjyam(jd, place), default=None)
    graha_yudh = _safe(lambda: drik.planets_in_graha_yudh(jd, place), default=[])
    sahasra_chandrodayam = _safe(lambda: drik.sahasra_chandrodayam(jd, place), default=None)
    next_panchaka = _safe(lambda: drik.next_panchaka_days(jd, place), default=None)

    # Tamil calendar
    tamil_jaamam = _safe(lambda: drik.tamil_jaamam(jd, place), default=[])
    tamil_yogam = _safe(lambda: drik.tamil_yogam(jd, place), default=None)

    return {
        "muhurthas": {
            "thirty": muhurthas,
            "nishita": _hms_range(_safe(lambda: drik.nishita_muhurtha(jd, place))),
            "nishita_kaala": _hms_range(_safe(lambda: drik.nishita_kaala(jd, place))),
            "brahma": _hms_range(_safe(lambda: drik.brahma_muhurtha(jd, place))),
            "godhuli": _hms_range(_safe(lambda: drik.godhuli_muhurtha(jd, place))),
            "vijaya": vijaya_out,
            "udhaya_lagna": udhaya_out,
            "panchaka_rahitha": panchaka_out,
            "sandhya_periods": sandhya_out,
            "shubha_hora": _safe(lambda: drik.shubha_hora(jd, place)),
        },
        "vaasa": {
            "vaara_index": vaara,
            "vaara_name": WEEKDAY_NAMES[int(vaara)] if isinstance(vaara, int) and 0 <= vaara < 7 else None,
            "yogini_vaasa_index": yogini_vaasa_raw if isinstance(yogini_vaasa_raw, int) else None,
            "shiva_vaasa": {
                "index": shiva_idx,
                "meaning": SHIVA_VAASA_MEANINGS.get(shiva_idx),
                "end_hours": round(float(shiva_vaasa_raw[1]), 6) if isinstance(shiva_vaasa_raw, (list, tuple)) and len(shiva_vaasa_raw) > 1 else None,
            } if shiva_idx is not None else None,
        },
        "thaara": {
            "good_stars": list(thaara_good) if isinstance(thaara_good, list) else [],
            "nine_thaaras": _format_nava_thaara(nava_thaara),
            "special_thaaras": _format_special_thaara(special_thaara),
        },
        "lunar_month": {
            "index": maasa_idx,
            "name": maasa_name,
            "is_adhik_masa": adhik,
            "is_kshaya_masa": kshaya,
        },
        "ritu": {
            "index": ritu_idx,
            "name": ritu_name,
        },
        "samvatsara": samvatsara,
        "year_lengths": {
            "lunar_days": lunar_year_days,
            "savana_days": savana_year_days,
        },
        "triguna": triguna_out,
        "special_yogas": {
            "pushkara_yoga": _format_yoga_span(pushkara),
            "vidaal_yoga": _format_yoga_span(vidaal),
            "varjyam": _hms_range(varjyam) if isinstance(varjyam, (list, tuple)) else None,
        },
        "eclipses": {
            "next_lunar": _format_eclipse(lunar_eclipse),
            "next_solar": _format_eclipse(solar_eclipse),
        },
        "conjunctions": {
            "next_full_moon_jd": float(next_full_moon_jd) if isinstance(next_full_moon_jd, (int, float)) else None,
            "next_new_moon_jd": float(next_new_moon_jd) if isinstance(next_new_moon_jd, (int, float)) else None,
            "sahasra_chandrodayam": list(sahasra_chandrodayam) if isinstance(sahasra_chandrodayam, (list, tuple)) else None,
        },
        "graha_yudh": _format_graha_yudh(graha_yudh),
        "panchaka_next_jd_range": list(next_panchaka) if isinstance(next_panchaka, (list, tuple)) else None,
        "tamil_panchangam": {
            "jaamams": [_hms_range(j) for j in tamil_jaamam] if isinstance(tamil_jaamam, list) else [],
            "yogam": list(tamil_yogam) if isinstance(tamil_yogam, (list, tuple)) else tamil_yogam,
        },
    }


def _safe_samvatsara(dob, place):
    """Tries drik.samvatsara; falls back to a plain cycle calculation if the
    ephemeris isn't available. dob is a plain (y,m,d) tuple."""
    year = int(dob[0]) if dob else None
    try:
        from collections import namedtuple
        Date = getattr(drik, "Date", namedtuple("Date", ["year", "month", "day"]))
        d = Date(int(dob[0]), int(dob[1]), int(dob[2]))
        idx = int(drik.samvatsara(d, place))
        name = SAMVATSARA_NAMES[(idx - 1) % 60] if idx > 0 else SAMVATSARA_NAMES[idx % 60]
        return {"index": idx, "name": name, "method": "drik"}
    except Exception:
        pass
    # Fallback: Telugu/Andhra zero-offset approximation — (year - 1867) mod 60.
    if year is not None:
        idx = (year - 1867) % 60
        return {"index": idx, "name": SAMVATSARA_NAMES[idx], "method": "approx"}
    return None


def _format_yoga_span(raw):
    """pushkara_yoga and vidaal_yoga return () when absent."""
    if not raw:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return _hms_range(raw[:2])
    return list(raw)


def _format_nava_thaara(nava):
    if not isinstance(nava, list):
        return []
    out = []
    for entry in nava:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            thaara_idx, nak_indices = entry
            out.append({
                "thaara_index": int(thaara_idx),
                "nakshatras": [
                    NAKSHATRA_NAMES[int(n)] if 0 <= int(n) < 27 else int(n)
                    for n in (nak_indices or [])
                ],
            })
    return out


def _format_special_thaara(special):
    if not isinstance(special, list):
        return []
    return [
        {"thaara_index": int(a), "nakshatra_index": int(b)}
        for a, b in special if isinstance((a, b), tuple)
    ]


def _format_eclipse(raw):
    """next_lunar_eclipse / next_solar_eclipse return [code, (jd times...), (angles)]."""
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    out = {"code": int(raw[0])}
    times = raw[1]
    if isinstance(times, (list, tuple)):
        keys = ["maximum_jd", "first_contact_jd", "penumbra_start_jd",
                "penumbra_end_jd", "last_contact_jd"]
        for i, v in enumerate(times):
            if i < len(keys):
                out[keys[i]] = float(v) if v else 0.0
    return out


def _format_graha_yudh(raw):
    """planets_in_graha_yudh returns list of (p1, p2, winner_flag)."""
    from helpers.pyjhora_helper import PLANET_NAMES
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            p1, p2 = entry[0], entry[1]
            winner = entry[2] if len(entry) > 2 else None
            out.append({
                "planet_a": PLANET_NAMES.get(int(p1), int(p1)),
                "planet_b": PLANET_NAMES.get(int(p2), int(p2)),
                "winner_flag": winner,
            })
    return out
