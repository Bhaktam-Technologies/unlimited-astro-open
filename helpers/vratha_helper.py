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



