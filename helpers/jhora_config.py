# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""
Initialise PyJHora defaults for this service.

PyJHora stores several module-level globals (ayanamsa, language, node mode,
Swiss Ephemeris flags, bhaava madhya method) that every downstream call
reads. We normalise them here at import time and expose a per-request
override so API callers can opt in to a different configuration.
"""


import swisseph as swe
from jhora import const, utils

DEFAULT_AYANAMSA = "LAHIRI"
DEFAULT_LANGUAGE = "en"
DEFAULT_USE_TRUE_NODES = False
DEFAULT_BHAAVA_MADHYA_METHOD = 2  # Sripathi (JHora default)

AVAILABLE_AYANAMSAS = set(const.available_ayanamsa_modes.keys())
AVAILABLE_LANGUAGES = set(const.available_languages.values())


def _apply_ayanamsa(mode):
    const._DEFAULT_AYANAMSA_MODE = mode
    swe_mode = const.available_ayanamsa_modes.get(mode)
    if isinstance(swe_mode, int):
        swe.set_sid_mode(swe_mode)


def _apply_language(language):
    try:
        utils.set_language(language)
    except Exception:
        pass


def _apply_flags():
    const._DEFAULT_PLANET_POSITION_FLAGS = utils.set_flags_for_planet_positions(
        sidereal_positions=True,
        geometric_positions=True,
        true_positions=True,
        use_aberration_of_light=True,
        use_gravitational_deflection=False,
        use_nutation=False,
    )


def init_pyjhora_defaults():
    """Called once at process start. Sets Lahiri, Mean Nodes, English, JHora flags."""
    _apply_ayanamsa(DEFAULT_AYANAMSA)
    _apply_language(DEFAULT_LANGUAGE)
    const._use_true_nodes_for_rahu_ketu = DEFAULT_USE_TRUE_NODES
    const.bhaava_madhya_method = DEFAULT_BHAAVA_MADHYA_METHOD
    _apply_flags()


def set_session_config(ayanamsa_mode=None, use_true_nodes=None, language=None,
                       bhaava_madhya_method=None):
    """Per-request override. Returns the applied config for the response."""
    if ayanamsa_mode:
        mode = ayanamsa_mode.upper()
        if mode not in AVAILABLE_AYANAMSAS:
            raise ValueError(
                f"Unknown ayanamsa '{ayanamsa_mode}'. "
                f"Available: {sorted(AVAILABLE_AYANAMSAS)}"
            )
        _apply_ayanamsa(mode)

    if use_true_nodes is not None:
        const._use_true_nodes_for_rahu_ketu = bool(use_true_nodes)

    if language:
        if language not in AVAILABLE_LANGUAGES:
            raise ValueError(
                f"Unknown language '{language}'. "
                f"Available: {sorted(AVAILABLE_LANGUAGES)}"
            )
        _apply_language(language)

    if bhaava_madhya_method is not None:
        const.bhaava_madhya_method = int(bhaava_madhya_method)

    return get_current_config()


def get_current_config():
    return {
        "ayanamsa": const._DEFAULT_AYANAMSA_MODE,
        "language": const._DEFAULT_LANGUAGE,
        "use_true_nodes": bool(const._use_true_nodes_for_rahu_ketu),
        "bhaava_madhya_method": int(const.bhaava_madhya_method),
    }


init_pyjhora_defaults()
