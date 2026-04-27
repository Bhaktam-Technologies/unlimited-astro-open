# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
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




# ---------------------------------------------------------------------------
# Karakas
# ---------------------------------------------------------------------------

_CHARA_KARAKA_LABELS = [
    "Atma Karaka", "Amatya Karaka", "Bhratri Karaka", "Matri Karaka",
    "Putra Karaka", "Gnati Karaka", "Dara Karaka", "Extra",
]



def get_karakamsa(**params):
    """Jaimini Karakamsa + Swamsa analysis.

    Karakamsa = sign in the D9 (Navamsa) chart where the AtmaKaraka sits.
    Swamsa    = sign in the D9 chart where the Lagna sits.
    Houses counted from each are the foundation of Jaimini personality/profession
    and spirituality readings.
    """
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    ck = house.chara_karakas(rc)
    ak_planet_id = int(ck[0])

    d9 = charts.navamsa_chart(rc)

    # Locate each key entity in D9
    ak_in_d9 = next((e for e in d9 if e[0] == ak_planet_id), None)
    lagna_in_d9 = next((e for e in d9 if e[0] == "L"), None)
    if ak_in_d9 is None or lagna_in_d9 is None:
        raise RuntimeError("Could not locate AtmaKaraka or Lagna in D9 chart")

    ak_sign = int(ak_in_d9[1][0])
    lagna_sign = int(lagna_in_d9[1][0])

    # D9 planet-to-sign map, for "planets in each house from Karakamsa"
    d9_sign_to_planets = {i: [] for i in range(12)}
    for entry in d9:
        pid, (sign_idx, _deg) = entry[0], entry[1]
        if pid == "L":
            continue
        d9_sign_to_planets[int(sign_idx)].append(_planet_label(pid))

    def _houses_from(start_sign):
        rows = []
        for h in range(12):
            s = (start_sign + h) % 12
            rows.append({
                "house": h + 1,
                "sign_number": s,
                "sign": SIGN_NAMES[s],
                "planets": d9_sign_to_planets[s],
            })
        return rows

    return {
        "atma_karaka": {
            "planet": _planet_label(ak_planet_id),
            "planet_id": ak_planet_id,
        },
        "karakamsa_lagna": {
            "description": "AtmaKaraka's sign in Navamsa (D9) — used in Jaimini "
                           "spirituality/personality analysis.",
            "sign_number": ak_sign,
            "sign": SIGN_NAMES[ak_sign],
            "degrees_in_sign": round(float(ak_in_d9[1][1]), 4),
            "houses_from_karakamsa": _houses_from(ak_sign),
        },
        "swamsa_lagna": {
            "description": "Lagna's sign in Navamsa (D9) — indicates inner self "
                           "and profession tendencies.",
            "sign_number": lagna_sign,
            "sign": SIGN_NAMES[lagna_sign],
            "degrees_in_sign": round(float(lagna_in_d9[1][1]), 4),
            "houses_from_swamsa": _houses_from(lagna_sign),
        },
    }



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





# ---------------------------------------------------------------------------
# Raja Yogas
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Yogas (284 named yogas)
# ---------------------------------------------------------------------------

def _discover_yoga_functions():
    names = [n for n in dir(yoga_mod)
             if not n.startswith("_") and n.endswith("_from_jd_place")]
    return sorted(names)





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




# ---------------------------------------------------------------------------
# Graha Yudh & Marana Karaka Sthana
# ---------------------------------------------------------------------------

def get_retrograde_combustion(**params):
    place, dob, tob, jd, rc = _rasi_chart_objects(**params)
    retro_indices = drik.planets_in_retrograde(jd, place)
    planet_positions = charts.divisional_chart(jd, place)
    combust_indices = charts.planets_in_combustion(planet_positions)
    return {
        "retrograde": [_planet_label(p) for p in retro_indices],
        "combustion": [_planet_label(p) for p in combust_indices],
    }


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


