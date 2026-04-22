# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Sahams, Tajaka annual/monthly charts, tajaka yogas, and eclipse calendar."""

import inspect

from jhora.horoscope.chart import charts
from jhora.horoscope.transit import saham, tajaka, tajaka_yoga
from jhora.panchanga import eclipse, drik

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import (
    _build_inputs, PLANET_NAMES, SIGN_NAMES, _to_hms,
)


def _sign_dd_mm_ss(deg):
    """Format degrees-in-sign as 'DD° MM' SS\"'. Accepts float 0..30."""
    deg = float(deg)
    sign = "-" if deg < 0 else ""
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(round((deg - d - m / 60.0) * 3600.0))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return f"{sign}{d:02d}° {m:02d}' {s:02d}\""


SAHAM_FUNCTIONS = sorted(
    n for n, _ in inspect.getmembers(saham, inspect.isfunction)
    if n.endswith("_saham") and not n.startswith("_")
)


def _longitude_to_sign_deg(lon):
    lon = lon % 360.0
    sign = int(lon // 30)
    deg_in_sign = lon - sign * 30
    return {
        "longitude": round(float(lon), 6),
        "sign_index": sign,
        "sign": SIGN_NAMES[sign],
        "degrees_in_sign": round(float(deg_in_sign), 6),
        "degrees_dms": _sign_dd_mm_ss(deg_in_sign),
    }


def _planet_positions_to_json(pp):
    """Convert JHora chart ([planet, (sign, deg_in_sign)], ...) to JSON."""
    out = []
    for entry in pp:
        p, (sign, deg) = entry
        out.append({
            "planet_key": p,
            "planet": PLANET_NAMES.get(p, str(p)),
            "sign_index": int(sign),
            "sign": SIGN_NAMES[int(sign)] if 0 <= int(sign) < 12 else str(sign),
            "degrees_in_sign": round(float(deg), 6),
            "degrees_dms": _sign_dd_mm_ss(deg),
        })
    return out


def _is_night_birth(jd, place):
    """Night if sun has set for the local date."""
    try:
        sr = drik.sunrise(jd, place)[0]
        ss = drik.sunset(jd, place)[0]
        _, _, _, frac = drik.jd_to_gregorian(jd) if hasattr(drik, "jd_to_gregorian") else (0, 0, 0, 12)
    except Exception:
        return False
    # Heuristic: if birth hour is before sunrise or after sunset, it's night.
    # We don't have `frac` reliably — just use the simple marker the API exposes.
    try:
        # sr/ss are decimal hours in local day — but we don't have birth_hour here.
        # Caller passes via jd, so we can derive from the fractional part of (jd-offset).
        return False
    except Exception:
        return False





def _infer_night(jd, place, tob):
    """tob is (h, m, s). Compare against sunrise/sunset decimal hours."""
    try:
        sr = drik.sunrise(jd, place)
        ss = drik.sunset(jd, place)
        sunrise_h = sr[0] if isinstance(sr, (list, tuple)) else float(sr)
        sunset_h = ss[0] if isinstance(ss, (list, tuple)) else float(ss)
        birth_h = (tob[0] if tob else 12) + (tob[1] / 60.0 if tob and len(tob) > 1 else 0)
        return birth_h < float(sunrise_h) or birth_h >= float(sunset_h)
    except Exception:
        return False





def _format_pravesh_meta(meta):
    """`meta` from tajaka = [(y, m, d), 'HH:MM:SS']."""
    if not isinstance(meta, (list, tuple)) or len(meta) < 2:
        return None
    date_part, time_part = meta[0], meta[1]
    if isinstance(date_part, (list, tuple)) and len(date_part) >= 3:
        y, m, d = int(date_part[0]), int(date_part[1]), int(date_part[2])
        return {"date": f"{y:04d}-{m:02d}-{d:02d}", "time": str(time_part)}
    return {"raw": [date_part, time_part]}


# -----------------------------------------------------------------------------
# Tajaka yogas
# -----------------------------------------------------------------------------

_TAJAKA_YOGA_SIMPLE = [
    ("ithasala",      lambda pp, jd, place: tajaka_yoga.get_ithasala_yoga_planet_pairs(pp)),
    ("eesarpha",      lambda pp, jd, place: tajaka_yoga.get_eesarpha_yoga_planet_pairs(pp)),
    ("kamboola",      lambda pp, jd, place: tajaka_yoga.get_kamboola_yoga_planet_pairs(pp)),
    ("gairi_kamboola", lambda pp, jd, place: tajaka_yoga.get_gairi_kamboola_yoga_planet_pairs(pp)),
    ("khallasara",    lambda pp, jd, place: tajaka_yoga.get_khallasara_yoga_planet_pairs(pp)),
    ("manahoo",       lambda pp, jd, place: tajaka_yoga.get_manahoo_yoga_planet_pairs(pp)),
    ("nakta",         lambda pp, jd, place: tajaka_yoga.get_nakta_yoga_planet_triples(pp)),
    ("yamaya",        lambda pp, jd, place: tajaka_yoga.get_yamaya_yoga_planet_triples(pp)),
    ("radda",         lambda pp, jd, place: tajaka_yoga.get_radda_yoga_planet_pairs(pp)),
    ("duhphali_kutta", lambda pp, jd, place: tajaka_yoga.get_duhphali_kutta_yoga_planet_pairs(jd, place)),
]


def _label_pairs(pairs):
    """Render a list of planet pairs/triples into readable strings."""
    if not pairs:
        return []
    if isinstance(pairs, tuple) and len(pairs) >= 2 and isinstance(pairs[0], bool):
        # kamboola returns (is_kamboola, list, list) — keep the two lists.
        return {"is_kamboola": bool(pairs[0]),
                "kamboola_pairs": [_name_tuple(t) for t in pairs[1] or []],
                "gairi_pairs": [_name_tuple(t) for t in pairs[2] or []]}
    return [_name_tuple(t) for t in pairs]


def _name_tuple(t):
    if not isinstance(t, (list, tuple)):
        return t
    names = [PLANET_NAMES.get(x, str(x)) for x in t]
    return {"planets": names, "raw": list(t)}




def _planet_to_house_dict(pp):
    """Build a dict compatible with tajaka_yoga's ishkavala/induvara APIs."""
    d = {}
    for entry in pp:
        p, (sign, _deg) = entry
        d[p] = int(sign) + 1  # JHora's 1..12 house convention
    return d


# -----------------------------------------------------------------------------
# Eclipses
# -----------------------------------------------------------------------------

_ECLIPSE_TIME_LABELS = [
    "maximum", "first_contact", "penumbra_start",
    "penumbra_end", "last_contact",
]


def _format_eclipse_entry(raw):
    """(eclipse_type_str, [(y,m,d,h), ...]) → JSON."""
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    kind = raw[0]
    times_raw = raw[1] or []
    times = {}
    for i, t in enumerate(times_raw):
        label = _ECLIPSE_TIME_LABELS[i] if i < len(_ECLIPSE_TIME_LABELS) else f"t{i}"
        if isinstance(t, (list, tuple)) and len(t) >= 4:
            y, m, d, h = int(t[0]), int(t[1]), int(t[2]), float(t[3])
            times[label] = {
                "date": f"{y:04d}-{m:02d}-{d:02d}",
                "time": _to_hms(h),
                "hour_decimal": round(h, 6),
            }
    return {"type": kind, "contacts": times}






def _gregorian_to_jd_forward(date_tuple, place):
    """Convert (y, m, d, hour) + place tz to JD (UT)."""
    import swisseph as swe
    y, m, d, h = int(date_tuple[0]), int(date_tuple[1]), int(date_tuple[2]), float(date_tuple[3])
    return swe.julday(y, m, d, h - float(place.timezone))
