# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Advanced features on top of PyJHora:
  * Ashtakavarga (BAV, SAV, Sodhya Pindas)
  * Arudhas (bhava / graha / chandra / surya)
  * Chara Karakas
  * Upagrahas & Special Lagnas
  * Doshas
  * Raja Yogas (+ Neecha Bhanga / Vipareetha)
  * 284 named Yogas (dispatcher runs every *_from_jd_place)
  * Sphutas (tithi, yoga, rahu_tithi, bheeja, kshetra, tri, chatur, pancha, etc.)
  * Graha Yudh, Marana Karaka Sthana
"""

import inspect

from jhora import const
from jhora.panchanga import drik
from jhora.horoscope.chart import (
    charts, arudhas, ashtakavarga, house, dosha,
    raja_yoga, sphuta, yoga as yoga_mod,
)

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import (
    PLANET_NAMES, SIGN_NAMES, _build_inputs, _planet_label,
)

SUN_TO_SATURN_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rasi_chart_objects(**params):
    place, dob, tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    return place, dob, tob, jd, rc


def _house_to_planet_list(planet_positions):
    h_to_p = ["" for _ in range(12)]
    for p, (h, _) in planet_positions:
        s = str(p)
        if h_to_p[h]:
            h_to_p[h] += "/" + s
        else:
            h_to_p[h] = s
    return h_to_p


# ---------------------------------------------------------------------------
# Ashtakavarga
# ---------------------------------------------------------------------------

def get_ashtakavarga(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    h_to_p = _house_to_planet_list(rc)
    av = ashtakavarga.get_ashtaka_varga(h_to_p)
    # av = (bav_list_of_7, sav_12, sodhya_structures)
    if not isinstance(av, (list, tuple)) or len(av) < 2:
        return {"error": "unexpected ashtakavarga output"}

    bav_raw, sav_raw = av[0], av[1]
    bav = {}
    for i, planet in enumerate(SUN_TO_SATURN_NAMES):
        if i < len(bav_raw):
            bav[planet] = [int(v) for v in bav_raw[i]]
    sav = [int(v) for v in sav_raw]

    result = {
        "bhinna_ashtaka_varga": bav,
        "samudaya_ashtaka_varga": sav,
        "signs": SIGN_NAMES,
    }

    try:
        sodhya = ashtakavarga.sodhaya_pindas(bav_raw, h_to_p)
        # sodhya returns (graha_pinda, rasi_pinda, total) per planet
        graha_pinda, rasi_pinda, total = sodhya
        result["sodhya_pindas"] = {
            SUN_TO_SATURN_NAMES[i]: {
                "graha_pinda": int(graha_pinda[i]),
                "rasi_pinda": int(rasi_pinda[i]),
                "total": int(total[i]),
            }
            for i in range(len(SUN_TO_SATURN_NAMES))
        }
    except Exception as e:
        result["sodhya_pindas"] = {"error": str(e)}

    return result


# ---------------------------------------------------------------------------
# Arudhas
# ---------------------------------------------------------------------------

def get_arudhas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)

    ba = arudhas.bhava_arudhas_from_planet_positions(rc)
    ga = arudhas.graha_arudhas_from_planet_positions(rc)
    ca = arudhas.chandra_arudhas_from_planet_positions(rc)
    sa = arudhas.surya_arudhas_from_planet_positions(rc)

    graha_labels = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                    "Saturn", "Rahu", "Ketu", "Lagna"]

    return {
        "bhava_arudhas": {f"A{i + 1}": SIGN_NAMES[s] for i, s in enumerate(ba)},
        "graha_arudhas": {graha_labels[i]: SIGN_NAMES[s] for i, s in enumerate(ga) if i < len(graha_labels)},
        "chandra_arudhas": {f"C{i + 1}": SIGN_NAMES[s] for i, s in enumerate(ca)},
        "surya_arudhas": {f"S{i + 1}": SIGN_NAMES[s] for i, s in enumerate(sa)},
    }


# ---------------------------------------------------------------------------
# Karakas
# ---------------------------------------------------------------------------

_CHARA_KARAKA_LABELS = [
    "Atma Karaka", "Amatya Karaka", "Bhratri Karaka", "Matri Karaka",
    "Putra Karaka", "Gnati Karaka", "Dara Karaka", "Extra",
]


def get_chara_karakas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    ck = house.chara_karakas(rc)
    out = {}
    for i, planet_id in enumerate(ck):
        if i < len(_CHARA_KARAKA_LABELS):
            out[_CHARA_KARAKA_LABELS[i]] = _planet_label(planet_id)
    return out


# ---------------------------------------------------------------------------
# Upagrahas & Special Lagnas
# ---------------------------------------------------------------------------

_UPAGRAHA_NAMES = {
    0: "Kaala",
    2: "Mrityu",
    3: "Artha Prahara",
    4: "Yama Ghantaka",
    6: "Gulika",
}


def get_upagrahas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    date_obj = drik.Date(dob[0], dob[1], dob[2])
    out = {}
    for planet_id, name in _UPAGRAHA_NAMES.items():
        try:
            r = drik.upagraha_longitude(date_obj, tob, place, planet_id)
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                out[name] = {
                    "sign": SIGN_NAMES[int(r[0])],
                    "sign_number": int(r[0]),
                    "degrees": round(float(r[1]), 4),
                }
        except Exception as e:
            out[name] = {"error": str(e)}

    for name, fn_name in [("Gulika (exact)", "gulika_longitude"), ("Kaala (exact)", "kaala_longitude")]:
        fn = getattr(drik, fn_name, None)
        if fn:
            try:
                r = fn(date_obj, tob, place)
                if isinstance(r, (list, tuple)) and len(r) >= 2:
                    out[name] = {
                        "sign": SIGN_NAMES[int(r[0])],
                        "sign_number": int(r[0]),
                        "degrees": round(float(r[1]), 4),
                    }
            except Exception as e:
                out[name] = {"error": str(e)}

    return out


_SPECIAL_LAGNAS = [
    ("Bhava Lagna", "bhava_lagna"),
    ("Ghati Lagna", "ghati_lagna"),
    ("Hora Lagna", "hora_lagna"),
    ("Indu Lagna", "indu_lagna"),
    ("Kunda Lagna", "kunda_lagna"),
    ("Pranapada Lagna", "pranapada_lagna"),
    ("Bhrigu Bindhu Lagna", "bhrigu_bindhu_lagna"),
    ("Sree Lagna", "sree_lagna"),
    ("Varnada Lagna", "varnada_lagna"),
    ("Vighati Lagna", "vighati_lagna"),
    ("Nisheka Lagna", "nisheka_lagna"),
]


def get_special_lagnas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    out = {}
    for label, fn_name in _SPECIAL_LAGNAS:
        fn = getattr(drik, fn_name, None)
        if fn is None:
            continue
        try:
            r = fn(jd, place)
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                out[label] = {
                    "sign": SIGN_NAMES[int(r[0])],
                    "sign_number": int(r[0]),
                    "degrees": round(float(r[1]), 4),
                }
        except Exception as e:
            out[label] = {"error": str(e)}
    return out


# ---------------------------------------------------------------------------
# Doshas
# ---------------------------------------------------------------------------

def _strip_html(s):
    if not isinstance(s, str):
        return s
    # minimal strip, preserves paragraph breaks
    return (s.replace("<html>", "")
             .replace("</html>", "")
             .replace("<br>", "\n")
             .replace("<br/>", "\n")
             .replace("<br />", "\n")
             .replace("\t", " ")
             .strip())


def get_doshas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    dd = dosha.get_dosha_details(jd, place)
    return {k: _strip_html(v) for k, v in dd.items()}


# ---------------------------------------------------------------------------
# Raja Yogas
# ---------------------------------------------------------------------------

def get_raja_yogas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    details = raja_yoga.get_raja_yoga_details(jd, place)
    # (dict_of_named_yogas, count_pairs_ok, count_pairs_fail)
    if isinstance(details, tuple):
        named = details[0] if details else {}
    else:
        named = details

    pairs = raja_yoga.get_raja_yoga_pairs_from_planet_positions(rc)

    return {
        "named_raja_yogas": named,
        "raja_yoga_planet_pairs": [
            [_planet_label(a), _planet_label(b)] for a, b in pairs
        ] if pairs else [],
    }


# ---------------------------------------------------------------------------
# Yogas (284 named yogas)
# ---------------------------------------------------------------------------

def _discover_yoga_functions():
    names = [n for n in dir(yoga_mod)
             if not n.startswith("_") and n.endswith("_from_jd_place")]
    return sorted(names)


def get_yogas(**params):
    """Run every public *_from_jd_place yoga function and list the ones that fire.
    Each yoga may return True/False or a tuple describing participants — we treat
    any truthy value as 'present'.
    """
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)

    present = []
    errors = []
    for fn_name in _discover_yoga_functions():
        fn = getattr(yoga_mod, fn_name)
        try:
            result = fn(jd, place, divisional_chart_factor=1)
        except Exception as e:
            errors.append({"yoga": fn_name, "error": str(e)})
            continue
        if result:
            pretty = fn_name.replace("_from_jd_place", "").replace("_", " ")
            present.append({
                "yoga": pretty,
                "function": fn_name,
                "details": result if not isinstance(result, bool) else True,
            })

    return {
        "count_checked": len(_discover_yoga_functions()),
        "count_present": len(present),
        "yogas": present,
        "errors": errors[:10],  # cap the noise
    }


# ---------------------------------------------------------------------------
# Sphutas
# ---------------------------------------------------------------------------

_SPHUTA_FUNCS = [
    "tithi_sphuta", "yoga_sphuta", "rahu_tithi_sphuta",
    "beeja_sphuta", "kshetra_sphuta", "tri_sphuta",
    "chatur_sphuta", "pancha_sphuta", "prana_sphuta",
    "deha_sphuta", "mrityu_sphuta", "sookshma_tri_sphuta",
    "yogi_sphuta", "avayogi_sphuta",
]


def get_sphutas(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    out = {}
    for fn_name in _SPHUTA_FUNCS:
        fn = getattr(sphuta, fn_name, None)
        if fn is None:
            continue
        try:
            r = fn(dob, tob, place)
        except Exception as e:
            out[fn_name] = {"error": str(e)}
            continue

        label = fn_name.replace("_sphuta", "").replace("_", " ").title() + " Sphuta"
        if isinstance(r, (list, tuple)) and len(r) >= 2:
            out[label] = {
                "sign": SIGN_NAMES[int(r[0])] if 0 <= int(r[0]) < 12 else str(r[0]),
                "sign_number": int(r[0]),
                "degrees": round(float(r[1]), 4),
            }
        else:
            out[label] = r
    return out


# ---------------------------------------------------------------------------
# Graha Yudh & Marana Karaka Sthana
# ---------------------------------------------------------------------------

def get_graha_yudh(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    try:
        yudh = drik.planets_in_graha_yudh(jd, place)
    except Exception as e:
        return {"error": str(e)}
    return {
        "pairs": [
            {
                "planet_1": _planet_label(p1),
                "planet_2": _planet_label(p2),
                "winner": _planet_label(p1 if winner >= 0 else p2),
                "raw": [int(p1), int(p2), int(winner)],
            }
            for (p1, p2, winner) in yudh
        ]
    }


def get_marana_karaka_sthana(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    try:
        mks = charts.get_planets_in_marana_karaka_sthana(rc)
    except Exception as e:
        return {"error": str(e)}
    return [_planet_label(p) for p in mks]
