# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Vratha / festival / parva lookup wrappers over `jhora.panchanga.vratha`.

The original Flask service didn't expose these at all. The JHora module
ships a multilingual festival CSV and helpers for the 19 special vrathas
(ekadhashi, sashti, pradosham, sankranti, sankatahara chathurthi etc.).
"""

from collections import namedtuple

from jhora.panchanga import vratha, drik

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import _build_inputs, TITHI_NAMES


# Date namedtuple shim — some installs expose drik.Date, others don't.
Date = getattr(drik, "Date", namedtuple("Date", ["year", "month", "day"]))


DATE_DISPATCH = {
    "amavasya":            vratha.amavasya_dates,
    "pournami":            vratha.pournami_dates,
    "ekadhashi":           vratha.ekadhashi_dates,
    "pradosham":           vratha.pradosham_dates,
    "sashti":              vratha.sashti_dates,
    "sankatahara_chaturthi": vratha.sankatahara_chathurthi_dates,
    "shivarathri":         vratha.shivarathri_dates,
    "vinayaka_chaturthi":  vratha.vinayaka_chathurthi_dates,
    "durgashtami":         vratha.durgashtami_dates,
    "kaalashtami":         vratha.kaalashtami_dates,
    "ashtaka":             vratha.ashtaka_dates,
    "manvaadhi":           vratha.manvaadhi_dates,
    "yugadhi":             vratha.yugadhi_dates,
    "srartha":             vratha.srartha_dates,
    "srartha_yoga":        vratha.srartha_yoga_dates,
    "mahalaya_paksha":     vratha.mahalaya_paksha_dates,
    "chandra_dharshan":    vratha.chandra_dharshan_dates,
    "moondraam_pirai":     vratha.moondraam_pirai_dates,
    "sathyanarayana_puja": vratha.sathyanarayana_puja_dates,
    "sankranti":           vratha.sankranti_dates,
}


def _as_date(v):
    """Accepts {'year','month','day'} dict, ISO 'YYYY-MM-DD' string, or a list/tuple."""
    if v is None:
        return None
    if isinstance(v, Date):
        return v
    if isinstance(v, dict):
        return Date(int(v["year"]), int(v["month"]), int(v["day"]))
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        return Date(int(v[0]), int(v[1]), int(v[2]))
    if isinstance(v, str):
        parts = v.strip().split("-")
        if len(parts) == 3:
            return Date(int(parts[0]), int(parts[1]), int(parts[2]))
    raise ValueError(f"Cannot interpret as a date: {v!r}")


def _format_date_entry(entry):
    """vratha date helpers return ((y, m, d), start_hour, end_hour, description)."""
    if not isinstance(entry, (list, tuple)):
        return entry
    if len(entry) >= 4 and isinstance(entry[0], (list, tuple)) and len(entry[0]) >= 3:
        y, m, d = int(entry[0][0]), int(entry[0][1]), int(entry[0][2])
        return {
            "date": f"{y:04d}-{m:02d}-{d:02d}",
            "start_hours": round(float(entry[1]), 6) if entry[1] is not None else None,
            "end_hours": round(float(entry[2]), 6) if entry[2] is not None else None,
            "description": entry[3],
        }
    return list(entry)


def list_vratha_types():
    return {
        "date_queries": sorted(DATE_DISPATCH.keys()),
        "special_vratha_types": sorted(vratha.special_vratha_map.keys()),
    }


def get_vratha_dates(vratha_type, start_date, end_date=None, **params):
    """Return all occurrences of the named vratha between two dates."""
    key = str(vratha_type).lower().replace("-", "_")
    if key not in DATE_DISPATCH:
        raise ValueError(
            f"Unknown vratha '{vratha_type}'. Available: {sorted(DATE_DISPATCH.keys())}"
        )
    place, *_ = _build_inputs(**params)
    sd = _as_date(start_date)
    ed = _as_date(end_date) if end_date else None
    fn = DATE_DISPATCH[key]
    try:
        raw = fn(place, sd, ed) if ed else fn(place, sd)
    except TypeError:
        # Some of the date helpers require end_date to be positional.
        raw = fn(place, sd, ed) if ed else fn(place, sd, None)
    return {
        "vratha": key,
        "start_date": f"{sd.year:04d}-{sd.month:02d}-{sd.day:02d}",
        "end_date": f"{ed.year:04d}-{ed.month:02d}-{ed.day:02d}" if ed else None,
        "occurrences": [_format_date_entry(e) for e in raw] if isinstance(raw, list) else raw,
    }


def get_festivals_on_day(language="en", festival_name_contains=None, **params):
    """Festivals active on the birth-moment or a given jd."""
    place, dob, tob, jd = _build_inputs(**params)
    fests = vratha.get_festivals_of_the_day(jd, place, festival_name_contains=festival_name_contains)
    return {"festivals": _format_festivals(fests, language)}


def get_festivals_between(start_date, end_date, language="en",
                          festival_name_contains=None, **params):
    place, *_ = _build_inputs(**params)
    sd = _as_date(start_date)
    ed = _as_date(end_date)
    raw = vratha.get_festivals_between_the_dates(
        sd, ed, place, festival_name_contains=festival_name_contains
    )
    out = []
    for entry in raw or []:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            date_part = entry[0]
            fests = entry[1]
            y, m, d = int(date_part[0]), int(date_part[1]), int(date_part[2])
            out.append({
                "date": f"{y:04d}-{m:02d}-{d:02d}",
                "festivals": _format_festivals(fests, language),
            })
    return {
        "start_date": f"{sd.year:04d}-{sd.month:02d}-{sd.day:02d}",
        "end_date": f"{ed.year:04d}-{ed.month:02d}-{ed.day:02d}",
        "days": out,
    }


def get_tithi_pravesha(year_number, plus_or_minus_duration_in_days=30, **params):
    """Returns the exact tithi-return dates for the native's Nth solar year."""
    place, dob, tob, jd = _build_inputs(**params)
    birth_date = Date(int(dob[0]), int(dob[1]), int(dob[2]))
    birth_time = tuple(tob)
    raw = vratha.tithi_pravesha(
        birth_date=birth_date, birth_time=birth_time, birth_place=place,
        year_number=int(year_number),
        plus_or_minus_duration_in_days=int(plus_or_minus_duration_in_days),
    )
    entries = []
    if isinstance(raw, list):
        for e in raw:
            entries.append(_format_date_entry(e) if isinstance(e, (list, tuple)) else e)
    return {"year_number": int(year_number), "entries": entries}


def _format_festivals(fests, language):
    if not isinstance(fests, list):
        return fests
    lang_key = f"Festival_{language}"
    out = []
    for f in fests:
        if not isinstance(f, dict):
            out.append(f)
            continue
        out.append({
            "name": f.get(lang_key) or f.get("Festival_en") or f.get("Festival_name"),
            "english_name": f.get("Festival_en") or f.get("Festival_name"),
            "tithi": f.get("Tithi") or None,
            "nakshatra": f.get("Nakshatra") or None,
            "tamil_month": f.get("tamil_month") or None,
            "tamil_day": f.get("tamil_day") or None,
            "vaara": f.get("vaara") or None,
            "adhik_maasa": f.get("adhik_maasa") or None,
            "icon": f.get("icon_file"),
        })
    return out
