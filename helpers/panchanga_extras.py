# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
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
