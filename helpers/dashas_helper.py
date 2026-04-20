# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Unified dasha dispatcher.

PyJHora's dasha modules follow roughly three calling conventions:
  * graha-nakshatra-based: (jd, place) or (dob, tob, place)
  * raasi-based: (dob, tob, place)
  * annual/varsha: (jd_at_dob, place, years, ...)

This module flattens them into a registry so callers can use one endpoint
with `{"dasha": "narayana", ...}` instead of hand-wiring 40+ URLs.
"""

from jhora import const
from jhora.horoscope.dhasa.graha import (
    vimsottari, ashtottari, yogini, tithi_ashtottari, tithi_yogini,
    shodasottari, dwadasottari, dwisatpathi, panchottari, sataatbika,
    chathuraaseethi_sama, karana_chathuraaseethi_sama, shastihayani,
    shattrimsa_sama, tara, buddhi_gathi, kaala, aayu, rashmi, naisargika,
    saptharishi_nakshathra, moola, karaka, yoga_vimsottari,
)
from jhora.horoscope.dhasa.graha import ashtaka_varga as ashtaka_varga_dhasa
from jhora.horoscope.dhasa.raasi import (
    narayana, lagna_kendraadhi, sudasa, drig, niryaana, shoola,
    karaka_kendraadhi, chara, lagnamsaka, padhanadhamsa, mandooka,
    sthira, tara_lagna, brahma, varnada, yogardha, navamsa as navamsa_dhasa,
    paryaaya, trikona, kalachakra, chakra, sandhya, raashiyanka,
    chathurvidha_utthara,
)
from jhora.horoscope.dhasa import panchasvara, sudharsana_chakra
from jhora.horoscope.dhasa.annual import mudda, patyayini
from jhora.horoscope.chart import charts

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import _build_inputs, _format_dasa_entry


# A lambda per dasha that accepts `ctx` (dict with place, dob, tob, jd) plus
# any caller overrides via **kwargs.
DASHA_REGISTRY = {
    # --- Graha / Nakshatra based ---
    "vimsottari":         lambda c, **kw: vimsottari.get_vimsottari_dhasa_bhukthi(c["jd"], c["place"], **kw),
    "yoga_vimsottari":    lambda c, **kw: yoga_vimsottari.get_dhasa_bhukthi(c["jd"], c["place"], **kw),
    "ashtottari":         lambda c, **kw: ashtottari.get_ashtottari_dhasa_bhukthi(c["jd"], c["place"], **kw),
    "tithi_ashtottari":   lambda c, **kw: tithi_ashtottari.get_dhasa_bhukthi(c["jd"], c["place"], **kw),
    "yogini":             lambda c, **kw: yogini.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "tithi_yogini":       lambda c, **kw: tithi_yogini.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "shodasottari":       lambda c, **kw: shodasottari.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "dwadasottari":       lambda c, **kw: dwadasottari.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "dwisatpathi":        lambda c, **kw: dwisatpathi.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "panchottari":        lambda c, **kw: panchottari.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "sataatbika":         lambda c, **kw: sataatbika.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "chathuraaseethi_sama": lambda c, **kw: chathuraaseethi_sama.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "karana_chathuraaseethi_sama": lambda c, **kw: karana_chathuraaseethi_sama.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "shastihayani":       lambda c, **kw: shastihayani.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "shattrimsa_sama":    lambda c, **kw: shattrimsa_sama.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "saptharishi_nakshathra": lambda c, **kw: saptharishi_nakshathra.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),

    # --- Tara / Buddhi / Kaala / Aayu etc. ---
    "tara":           lambda c, **kw: tara.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "buddhi_gathi":   lambda c, **kw: buddhi_gathi.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "kaala":          lambda c, **kw: kaala.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "aayu":           lambda c, **kw: aayu.get_dhasa_antardhasa(c["jd"], c["place"], **kw),
    "rashmi":         lambda c, **kw: rashmi.get_rashmi_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "naisargika":     lambda c, **kw: naisargika.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "moola":          lambda c, **kw: moola.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "karaka":         lambda c, **kw: karaka.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "ashtaka_varga":  lambda c, **kw: ashtaka_varga_dhasa.get_ashtaka_varga_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),

    # --- Raasi-based ---
    "narayana":       lambda c, **kw: narayana.varsha_narayana_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "lagna_kendraadhi": lambda c, **kw: lagna_kendraadhi.get_lagna_kendradhi_rasi_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "sudasa":         lambda c, **kw: sudasa.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "drig":           lambda c, **kw: drig.drig_dhasa(charts.rasi_chart(c["jd"], c["place"]), c["dob"], c["tob"], **kw),
    "niryaana":       lambda c, **kw: niryaana.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "shoola":         lambda c, **kw: shoola.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "karaka_kendraadhi": lambda c, **kw: karaka_kendraadhi.get_karaka_kendradhi_rasi_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "chara":          lambda c, **kw: chara.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "lagnamsaka":     lambda c, **kw: lagnamsaka.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "padhanadhamsa":  lambda c, **kw: padhanadhamsa.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "mandooka":       lambda c, **kw: mandooka.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "sthira":         lambda c, **kw: sthira.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "tara_lagna":     lambda c, **kw: tara_lagna.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "brahma":         lambda c, **kw: brahma.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "varnada":        lambda c, **kw: varnada.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "yogardha":       lambda c, **kw: yogardha.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "navamsa":        lambda c, **kw: navamsa_dhasa.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "paryaaya":       lambda c, **kw: paryaaya.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "trikona":        lambda c, **kw: trikona.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "kalachakra":     lambda c, **kw: kalachakra.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "chakra":         lambda c, **kw: chakra.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "sandhya":        lambda c, **kw: sandhya.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),
    "raashiyanka":    lambda c, **kw: raashiyanka.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "chathurvidha_utthara": lambda c, **kw: chathurvidha_utthara.get_dhasa_antardhasa(c["dob"], c["tob"], c["place"], **kw),

    # --- Specials ---
    "panchasvara":        lambda c, **kw: panchasvara.get_dhasa_bhukthi(c["dob"], c["tob"], c["place"], **kw),
    "sudharsana_chakra":  lambda c, **kw: sudharsana_chakra.sudharsana_chakra_dhasa_for_divisional_chart(c["jd"], c["place"], **kw),

    # --- Annual (Varsha) ---
    "mudda":          lambda c, **kw: mudda.mudda_dhasa_bhukthi(c["jd"], c["place"], kw.pop("years", 1), **kw),
    "patyayini":      lambda c, **kw: patyayini.get_dhasa_bhukthi(c["jd"], c["place"], **kw),
}




def _normalise_entries(raw):
    """Best-effort normalisation of a dasha output into our formatted list.
    Returns {"periods": [...]} or {"raw": ...} if the shape is unknown.
    """
    if raw is None:
        return {"periods": []}

    meta = None
    data = raw
    if isinstance(raw, (list, tuple)) and len(raw) == 2 and isinstance(raw[1], list):
        head, tail = raw[0], raw[1]
        # Some modules return (seed_tuple, entries); others return (scalar_flag, entries).
        if isinstance(head, tuple) and len(head) <= 4 and all(isinstance(x, (int, float)) for x in head):
            meta = {"seed": [int(x) for x in head]}
            data = tail
        elif isinstance(head, (int, str)):
            meta = {"seed": head}
            data = tail

    def _looks_like_date(t):
        return (isinstance(t, (list, tuple)) and len(t) >= 3
                and all(isinstance(x, (int, float)) for x in t[:3]))

    def _is_entry(e):
        return (isinstance(e, (list, tuple)) and len(e) >= 2
                and isinstance(e[0], (list, tuple)) and _looks_like_date(e[1]))

    periods = []
    if isinstance(data, list):
        for e in data:
            if _is_entry(e):
                try:
                    periods.append(_format_dasa_entry(e))
                except Exception:
                    periods.append({"raw": str(e)})
            elif isinstance(e, (list, tuple)) and e and _is_entry(e[0]):
                for x in e:
                    try:
                        periods.append(_format_dasa_entry(x))
                    except Exception:
                        periods.append({"raw": str(x)})

    result = {"periods": periods}
    if meta:
        result["meta"] = meta
    if not periods:
        # Unknown shape — expose the raw payload so callers can still work.
        result["raw"] = raw
    return result



