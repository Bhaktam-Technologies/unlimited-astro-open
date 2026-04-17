# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
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


# -----------------------------------------------------------------------------
# Sahams
# -----------------------------------------------------------------------------

def get_sahams(night_time_birth=None, **params):
    place, dob, tob, jd = _build_inputs(**params)
    pp = charts.rasi_chart(jd, place)
    night = bool(night_time_birth) if night_time_birth is not None else _infer_night(jd, place, tob)

    sahams = {}
    for fn_name in SAHAM_FUNCTIONS:
        fn = getattr(saham, fn_name)
        try:
            try:
                val = fn(pp, night_time_birth=night)
            except TypeError:
                val = fn(pp)
            if val is None:
                continue
            sahams[fn_name.replace("_saham", "")] = _longitude_to_sign_deg(float(val))
        except Exception as e:
            sahams[fn_name.replace("_saham", "")] = {"error": f"{type(e).__name__}: {e}"}
    return {"night_time_birth": night, "sahams": sahams}


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


# -----------------------------------------------------------------------------
# Tajaka — Annual (Varsha) and Monthly (Maasa) charts
# -----------------------------------------------------------------------------

def get_annual_chart(years=1, divisional_chart_factor=1, **params):
    place, dob, tob, jd = _build_inputs(**params)
    chart, meta = tajaka.varsha_pravesh(jd, place,
                                        divisional_chart_factor=divisional_chart_factor,
                                        years=int(years))
    lord = tajaka.lord_of_the_year(jd, place, int(years))
    asc_house = chart[0][1][0] if chart and chart[0][0] == "L" else 0
    muntha = tajaka.muntha_house(int(asc_house), int(years))
    return {
        "years_completed": int(years),
        "divisional_chart_factor": int(divisional_chart_factor),
        "pravesh_meta": _format_pravesh_meta(meta),
        "planet_positions": _planet_positions_to_json(chart),
        "lord_of_the_year": {
            "planet_index": int(lord),
            "planet": PLANET_NAMES.get(int(lord), str(lord)),
        },
        "muntha_house": int(muntha),
    }


def get_monthly_chart(years=1, months=1, divisional_chart_factor=1, **params):
    place, dob, tob, jd = _build_inputs(**params)
    chart, meta = tajaka.monthly_chart(jd, place,
                                       divisional_chart_factor=divisional_chart_factor,
                                       years=int(years), months=int(months))
    lord = tajaka.lord_of_the_month(jd, place, int(years), int(months))
    return {
        "years_completed": int(years),
        "months_into_year": int(months),
        "divisional_chart_factor": int(divisional_chart_factor),
        "pravesh_meta": _format_pravesh_meta(meta),
        "planet_positions": _planet_positions_to_json(chart),
        "lord_of_the_month": {
            "planet_index": int(lord),
            "planet": PLANET_NAMES.get(int(lord), str(lord)),
        },
    }


def get_sixty_hour_chart(years=1, months=1, sixty_hour_count=1,
                         divisional_chart_factor=1, **params):
    place, dob, tob, jd = _build_inputs(**params)
    chart, meta = tajaka.sixty_hour_chart(jd, place,
                                          divisional_chart_factor=divisional_chart_factor,
                                          years=int(years), months=int(months),
                                          sixty_hour_count=int(sixty_hour_count))
    return {
        "years_completed": int(years),
        "months_into_year": int(months),
        "sixty_hour_count": int(sixty_hour_count),
        "pravesh_meta": _format_pravesh_meta(meta),
        "planet_positions": _planet_positions_to_json(chart),
    }


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


def get_tajaka_yogas(**params):
    place, dob, tob, jd = _build_inputs(**params)
    pp = charts.rasi_chart(jd, place)
    out = {}
    for name, fn in _TAJAKA_YOGA_SIMPLE:
        try:
            result = fn(pp, jd, place)
            out[name] = _label_pairs(result)
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {e}"}
    # Simple house-based yogas
    phd = _planet_to_house_dict(pp)
    for n in ("ishkavala_yoga", "induvara_yoga"):
        fn = getattr(tajaka_yoga, n, None)
        if fn:
            try:
                out[n] = bool(fn(phd))
            except Exception as e:
                out[n] = {"error": f"{type(e).__name__}: {e}"}
    return out


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


def get_eclipses(search_forward_years=10, **params):
    place, dob, tob, jd = _build_inputs(**params)
    lunars, solars = [], []

    cursor = jd
    for _ in range(int(search_forward_years)):
        try:
            le = eclipse.next_lunar_eclipse(cursor, place)
            formatted = _format_eclipse_entry(le)
            if formatted:
                lunars.append(formatted)
                max_time = le[1][0] if le and le[1] else None
                if isinstance(max_time, (list, tuple)) and len(max_time) >= 4:
                    # Advance cursor by ~30 days past the max
                    cursor = _gregorian_to_jd_forward(max_time, place) + 30
                else:
                    break
            else:
                break
        except Exception:
            break

    cursor = jd
    for _ in range(int(search_forward_years)):
        try:
            se = eclipse.next_solar_eclipse(cursor, place)
            formatted = _format_eclipse_entry(se)
            if formatted:
                solars.append(formatted)
                max_time = se[1][0] if se and se[1] else None
                if isinstance(max_time, (list, tuple)) and len(max_time) >= 4:
                    cursor = _gregorian_to_jd_forward(max_time, place) + 30
                else:
                    break
            else:
                break
        except Exception:
            break

    return {
        "searched_years": int(search_forward_years),
        "lunar_eclipses": lunars,
        "solar_eclipses": solars,
    }


def _gregorian_to_jd_forward(date_tuple, place):
    """Convert (y, m, d, hour) + place tz to JD (UT)."""
    import swisseph as swe
    y, m, d, h = int(date_tuple[0]), int(date_tuple[1]), int(date_tuple[2]), float(date_tuple[3])
    return swe.julday(y, m, d, h - float(place.timezone))
