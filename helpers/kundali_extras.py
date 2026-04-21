# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""AstroSage-style kundali extras that JHora doesn't package as single calls:
  * Panchadha friendship  (natural + temporary + compound)
  * Avakhada Chakra       (varna, vashya, yoni, gana, nadi, tatva, paya, …)
  * Ghatak Chakra         (inauspicious tithi/vaara/nakshatra/… for Moon rashi)
  * Favourable            (lucky day/number/colour/stone/direction/deity)

The Ghatak and Favourable tables are standard from classical muhurta texts
(Brihat Parashara / Muhurta Chintamani); small variations exist between
sources. Values here match the commonly-cited table.
"""

from jhora.horoscope.chart import charts, house
from jhora.panchanga import drik
from jhora import utils

from helpers import jhora_config  # noqa: F401
from helpers.pyjhora_helper import (
    PLANET_NAMES, SIGN_NAMES, NAKSHATRA_NAMES,
    TITHI_NAMES, YOGA_NAMES, KARANA_NAMES, WEEKDAY_NAMES,
    _build_inputs, _planet_label,
)


SUN_TO_KETU = [0, 1, 2, 3, 4, 5, 6, 7, 8]
SUN_TO_KETU_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                     "Venus", "Saturn", "Rahu", "Ketu"]

# 7 classical planets only (no Rahu/Ketu) for friendship tables
_7P_IDS  = [0, 1, 2, 3, 4, 5, 6]
_7P_ABBR = ["SU", "MO", "MA", "ME", "JU", "VE", "SA"]

SIGN_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]


# =============================================================================
# 1) PANCHADHA FRIENDSHIP
# =============================================================================
# JHora's compound matrix encodes:
#   4 = adhi_mitra (great friend)   — natural friend + temporary friend
#   3 = mitra (friend)              — natural neutral + temporary friend
#   2 = sama (neutral)              — nat friend + temp enemy  OR  nat enemy + temp friend
#   1 = shatru (enemy)              — natural neutral + temporary enemy
#   0 = adhi_shatru (great enemy)   — natural enemy + temporary enemy
# The diagonal is filled with 0 (self-slot) and must be masked separately.
#
# Display symbols:
#   I  = Intimate / Great Friend (adhi_mitra)
#   F  = Friend (mitra)
#   N  = Neutral (sama)
#   E  = Enemy (shatru)
#   B  = Bitter / Great Enemy (adhi_shatru)
#   -- = self (diagonal)

_COMPOUND_SYMBOL = {4: "I", 3: "F", 2: "N", 1: "E", 0: "B"}


def _build_permanent_matrix(natural):
    rows = []
    for p in _7P_IDS:
        nat_friends = set(int(x) for x in natural[p])
        try:
            from jhora import const as _c
            nat_enemies = set(int(x) for x in _c.enemy_planets[p] if int(x) in _7P_IDS)
        except Exception:
            nat_enemies = set()
        cols = {}
        for p1 in _7P_IDS:
            abbr = _7P_ABBR[p1]
            if p == p1:
                cols[abbr] = "--"
            elif p1 in nat_friends:
                cols[abbr] = "F"
            elif p1 in nat_enemies:
                cols[abbr] = "E"
            else:
                cols[abbr] = "N"
        rows.append({"planet": _7P_ABBR[p], **cols})
    return rows


def _build_temporary_matrix(temp_friends, temp_enemies):
    rows = []
    for p in _7P_IDS:
        tf = set(int(x) for x in temp_friends.get(p, []) if int(x) in _7P_IDS)
        te = set(int(x) for x in temp_enemies.get(p, []) if int(x) in _7P_IDS)
        cols = {}
        for p1 in _7P_IDS:
            abbr = _7P_ABBR[p1]
            if p == p1:
                cols[abbr] = "--"
            elif p1 in tf:
                cols[abbr] = "F"
            elif p1 in te:
                cols[abbr] = "E"
            else:
                cols[abbr] = "N"
        rows.append({"planet": _7P_ABBR[p], **cols})
    return rows


def _build_fivefold_matrix(compound):
    rows = []
    for p in _7P_IDS:
        cols = {}
        for p1 in _7P_IDS:
            abbr = _7P_ABBR[p1]
            if p == p1:
                cols[abbr] = "--"
            else:
                cols[abbr] = _COMPOUND_SYMBOL.get(compound[p][p1], "N")
        rows.append({"planet": _7P_ABBR[p], **cols})
    return rows


def get_friendship(**params):
    place, _dob, _tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)
    h_to_p = utils.get_house_planet_list_from_planet_positions(rc)

    natural      = house.natural_friends_of_planets()
    temp_friends = house._get_temporary_friends_of_planets(h_to_p)
    temp_enemies = house._get_temporary_enemies_of_planets(h_to_p)
    compound     = house._get_compound_relationships_of_planets(h_to_p)

    return {
        "columns": _7P_ABBR,
        "legend": {
            "F":  "Friend",
            "I":  "Intimate (Great Friend)",
            "N":  "Neutral",
            "E":  "Enemy",
            "B":  "Bitter (Great Enemy)",
            "--": "Self",
        },
        "permanent_friendship": _build_permanent_matrix(natural),
        "temporary_friendship": _build_temporary_matrix(temp_friends, temp_enemies),
        "fivefold_friendship":  _build_fivefold_matrix(compound),
    }


# =============================================================================
# 2) AVAKHADA CHAKRA
# =============================================================================
# 16 traditional fields derived from Moon sign / Moon nakshatra.
# Tables are keyed by 0-based indices.

# Varna — Moon rashi classification (BPHS)
_VARNA_BY_RASHI = [
    "Kshatriya",  # Aries
    "Vaishya",    # Taurus
    "Shudra",     # Gemini
    "Brahmana",   # Cancer
    "Kshatriya",  # Leo
    "Vaishya",    # Virgo
    "Shudra",     # Libra
    "Brahmana",   # Scorpio
    "Kshatriya",  # Sagittarius
    "Vaishya",    # Capricorn
    "Shudra",     # Aquarius
    "Brahmana",   # Pisces
]

# Vashya — 5 categories; Sagittarius and Capricorn split at midpoint.
def _vashya(rashi, moon_deg):
    if rashi == 8:   # Sagittarius: 0–15° Manav, 15–30° Chatushpada
        return "Manav" if moon_deg < 15 else "Chatushpada"
    if rashi == 9:   # Capricorn: 0–15° Chatushpada, 15–30° Jalchar
        return "Chatushpada" if moon_deg < 15 else "Jalchar"
    return [
        "Chatushpada",  # Aries
        "Chatushpada",  # Taurus
        "Manav",        # Gemini
        "Jalchar",      # Cancer
        "Vanchar",      # Leo
        "Manav",        # Virgo
        "Manav",        # Libra
        "Keet",         # Scorpio
        None, None,     # Sag, Cap handled above
        "Manav",        # Aquarius
        "Jalchar",      # Pisces
    ][rashi]

# Yoni — 27 nakshatras, 14 yoni animals (m/f)
_YONI_BY_NAK = [
    ("Horse", "male"),      # Ashwini
    ("Elephant", "male"),   # Bharani
    ("Sheep", "female"),    # Krittika
    ("Serpent", "male"),    # Rohini
    ("Serpent", "female"),  # Mrigashira
    ("Dog", "female"),      # Ardra
    ("Cat", "female"),      # Punarvasu
    ("Sheep", "male"),      # Pushya
    ("Cat", "male"),        # Ashlesha
    ("Rat", "male"),        # Magha
    ("Rat", "female"),      # Purva Phalguni
    ("Cow", "female"),      # Uttara Phalguni
    ("Buffalo", "female"),  # Hasta
    ("Tiger", "female"),    # Chitra
    ("Buffalo", "male"),    # Swati
    ("Tiger", "male"),      # Vishakha
    ("Deer", "female"),     # Anuradha
    ("Deer", "male"),       # Jyeshtha
    ("Dog", "male"),        # Mula
    ("Monkey", "male"),     # Purva Ashadha
    ("Mongoose", "female"), # Uttara Ashadha
    ("Monkey", "female"),   # Shravana
    ("Lion", "female"),     # Dhanishta
    ("Horse", "female"),    # Shatabhisha
    ("Lion", "male"),       # Purva Bhadrapada
    ("Cow", "male"),        # Uttara Bhadrapada
    ("Elephant", "female"), # Revati
]

# Gana — by nakshatra 0..26
_GANA_BY_NAK = [
    "Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya",
    "Deva", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya",
    "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva", "Rakshasa",
    "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa",
    "Manushya", "Manushya", "Deva",
]

# Nadi — aadi / madhya / antya, cycles in forward then reverse through the 27.
_NADI_BY_NAK = [
    "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi",
    "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi",
    "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi",
    "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi",
    "Aadi", "Madhya", "Antya",
]

# Vimshottari nakshatra lord cycle (9) — repeats 3× across 27 nakshatras.
_NAK_LORD_CYCLE = [8, 5, 0, 1, 2, 7, 4, 6, 3]  # Ketu,Venus,Sun,Moon,Mars,Rahu,Jup,Sat,Merc

# Starting syllables per nakshatra (4 padas each) — standard Namakshar table.
_SYLLABLES_BY_NAK = [
    ["Chu", "Che", "Cho", "La"],   # Ashwini
    ["Li", "Lu", "Le", "Lo"],       # Bharani
    ["A", "I", "U", "E"],           # Krittika
    ["O", "Va", "Vi", "Vu"],        # Rohini
    ["Ve", "Vo", "Ka", "Ki"],       # Mrigashira
    ["Ku", "Gha", "Ng", "Chh"],     # Ardra
    ["Ke", "Ko", "Ha", "Hi"],       # Punarvasu
    ["Hu", "He", "Ho", "Da"],       # Pushya
    ["Di", "Du", "De", "Do"],       # Ashlesha
    ["Ma", "Mi", "Mu", "Me"],       # Magha
    ["Mo", "Ta", "Ti", "Tu"],       # Purva Phalguni
    ["Te", "To", "Pa", "Pi"],       # Uttara Phalguni
    ["Pu", "Sha", "Na", "Tha"],     # Hasta
    ["Pe", "Po", "Ra", "Ri"],       # Chitra
    ["Ru", "Re", "Ro", "Ta"],       # Swati
    ["Ti", "Tu", "Te", "To"],       # Vishakha
    ["Na", "Ni", "Nu", "Ne"],       # Anuradha
    ["No", "Ya", "Yi", "Yu"],       # Jyeshtha
    ["Ye", "Yo", "Bha", "Bhi"],     # Mula
    ["Bhu", "Dha", "Pha", "Dha"],   # Purva Ashadha
    ["Bhe", "Bho", "Ja", "Ji"],     # Uttara Ashadha
    ["Ju", "Je", "Jo", "Gha"],      # Shravana
    ["Ga", "Gi", "Gu", "Ge"],       # Dhanishta
    ["Go", "Sa", "Si", "Su"],       # Shatabhisha
    ["Se", "So", "Da", "Di"],       # Purva Bhadrapada
    ["Du", "Tha", "Jha", "Na"],     # Uttara Bhadrapada
    ["De", "Do", "Cha", "Chi"],     # Revati
]

# Tatva (element) by rashi
_TATVA_BY_RASHI = [
    "Agni", "Prithvi", "Vayu", "Jal", "Agni", "Prithvi",
    "Vayu", "Jal", "Agni", "Prithvi", "Vayu", "Jal",
]

# Paya (metal) by Moon rashi — silver/copper/gold/iron
_PAYA_BY_RASHI = [
    "Iron",    # Aries
    "Copper",  # Taurus
    "Silver",  # Gemini
    "Gold",    # Cancer
    "Gold",    # Leo
    "Silver",  # Virgo
    "Copper",  # Libra
    "Iron",    # Scorpio
    "Gold",    # Sagittarius
    "Silver",  # Capricorn
    "Copper",  # Aquarius
    "Gold",    # Pisces
]

# Yunja (Moon nakshatra's 3-phase classification)
_YUNJA_BY_NAK = [
    "Antya", "Madhya", "Aadi", "Antya", "Madhya", "Aadi",
    "Antya", "Madhya", "Aadi", "Antya", "Madhya", "Aadi",
    "Antya", "Madhya", "Aadi", "Antya", "Madhya", "Aadi",
    "Antya", "Madhya", "Aadi", "Antya", "Madhya", "Aadi",
    "Antya", "Madhya", "Aadi",
]


def _moon_longitude(rc):
    moon = next((e for e in rc if e[0] == 1), None)
    if not moon:
        return None
    sign_idx, deg = moon[1][0], moon[1][1]
    return float(sign_idx) * 30.0 + float(deg)


def get_avakhada_chakra(**params):
    place, dob, _tob, jd = _build_inputs(**params)
    rc = charts.rasi_chart(jd, place)

    moon_long = _moon_longitude(rc)
    if moon_long is None:
        raise RuntimeError("Moon position not found in rasi chart")

    moon_sign = int(moon_long // 30) % 12
    moon_deg = moon_long - moon_sign * 30
    nak_idx = int(moon_long / (360.0 / 27.0)) % 27
    nak_pada = int((moon_long % (360.0 / 27.0)) / (360.0 / 27.0 / 4.0)) + 1

    # Panchanga basics at birth moment
    try:
        tithi_raw = drik.tithi(jd, place)
        tithi_idx = int(tithi_raw[0]) - 1 if isinstance(tithi_raw, (list, tuple)) else int(tithi_raw) - 1
    except Exception:
        tithi_idx = None
    try:
        yoga_raw = drik.yogam(jd, place)
        yoga_idx = int(yoga_raw[0]) - 1 if isinstance(yoga_raw, (list, tuple)) else int(yoga_raw) - 1
    except Exception:
        yoga_idx = None
    try:
        karana_raw = drik.karana(jd, place)
        karana_idx = int(karana_raw[0]) - 1 if isinstance(karana_raw, (list, tuple)) else int(karana_raw) - 1
    except Exception:
        karana_idx = None
    try:
        from datetime import date
        weekday = date(dob[0], dob[1], dob[2]).weekday()
        vaara = WEEKDAY_NAMES[(weekday + 1) % 7]  # Python Mon=0; we want Sun=0
    except Exception:
        vaara = None

    yoni_animal, yoni_sex = _YONI_BY_NAK[nak_idx]
    nak_lord_id = _NAK_LORD_CYCLE[nak_idx % 9]

    return {
        "moon": {
            "rashi_number": moon_sign + 1,
            "rashi": SIGN_NAMES[moon_sign],
            "rashi_lord": PLANET_NAMES[SIGN_LORDS[moon_sign]],
            "degrees_in_sign": round(moon_deg, 4),
            "nakshatra": NAKSHATRA_NAMES[nak_idx],
            "nakshatra_number": nak_idx + 1,
            "nakshatra_pada": nak_pada,
            "nakshatra_lord": PLANET_NAMES[nak_lord_id],
            "name_syllable": _SYLLABLES_BY_NAK[nak_idx][nak_pada - 1],
        },
        "varna":   _VARNA_BY_RASHI[moon_sign],
        "vashya":  _vashya(moon_sign, moon_deg),
        "yoni":    {"animal": yoni_animal, "sex": yoni_sex},
        "gana":    _GANA_BY_NAK[nak_idx],
        "nadi":    _NADI_BY_NAK[nak_idx],
        "tatva":   _TATVA_BY_RASHI[moon_sign],
        "paya":    _PAYA_BY_RASHI[moon_sign],
        "yunja":   _YUNJA_BY_NAK[nak_idx],
        "tithi":   TITHI_NAMES[tithi_idx] if tithi_idx is not None else None,
        "yoga":    YOGA_NAMES[yoga_idx] if yoga_idx is not None else None,
        "karana":  KARANA_NAMES[karana_idx] if karana_idx is not None else None,
        "vaara":   vaara,
    }


# =============================================================================
# 3) GHATAK CHAKRA
# =============================================================================
# Inauspicious (ghatak / hostile) period markers keyed by Moon rashi.
# Standard Muhurta Chintamani table; values are 1-based for tithi/prahar.

_GHATAK_TABLE = [
    # rashi: month        tithi  vaara      nakshatra        karana      yoga         lagna         prahar
    ("Aries",        "Bhadrapada", 9, "Saturday",  "Magha",          "Vishti",     "Shoola",      "Aries",       5),
    ("Taurus",       "Phalguna",   4, "Sunday",    "Hasta",          "Chatushpada","Ganda",       "Taurus",      3),
    ("Gemini",       "Ashadha",    6, "Monday",    "Anuradha",       "Garija",     "Vyaghata",    "Gemini",      2),
    ("Cancer",       "Pausha",     2, "Tuesday",   "Purva Ashadha",  "Vanija",     "Vaidhriti",   "Cancer",      5),
    ("Leo",          "Chaitra",   10, "Wednesday", "Shravana",       "Bava",       "Vyatipata",   "Leo",         7),
    ("Virgo",        "Shravana",   5, "Thursday",  "Revati",         "Balava",     "Parigha",     "Virgo",       4),
    ("Libra",        "Vaisakha",  12, "Friday",    "Shatabhisha",    "Kaulava",    "Vyaghata",    "Libra",       6),
    ("Scorpio",      "Margashira",14, "Saturday",  "Ardra",          "Taitila",    "Vishkumbha",  "Scorpio",     5),
    ("Sagittarius",  "Jyeshtha",   1, "Sunday",    "Pushya",         "Bava",       "Ganda",       "Sagittarius", 1),
    ("Capricorn",    "Kartika",    8, "Monday",    "Chitra",         "Balava",     "Atiganda",    "Capricorn",   3),
    ("Aquarius",     "Magha",      3, "Tuesday",   "Swati",          "Kaulava",    "Shoola",      "Aquarius",    4),
    ("Pisces",       "Ashwin",     7, "Wednesday", "Krittika",       "Taitila",    "Ganda",       "Pisces",      2),
]





# =============================================================================
# 4) FAVOURABLE POINTS
# =============================================================================
# Lucky attributes from Moon rashi + Moon nakshatra lord.

_FAVOURABLE_BY_RASHI = [
    # rashi, lucky_day, lucky_number, lucky_numbers_more, colour(s), metal, stone, direction, deity
    ("Aries",        "Tuesday",   9, [1, 8],     ["Red", "Pink"],              "Copper",      "Red Coral",       "East",  "Hanuman"),
    ("Taurus",       "Friday",    6, [5],        ["White", "Pink", "Blue"],    "Silver",      "Diamond",         "South", "Ganesha"),
    ("Gemini",       "Wednesday", 5, [3, 6],     ["Green", "Yellow"],          "Gold",        "Emerald",         "West",  "Durga"),
    ("Cancer",       "Monday",    2, [7],        ["White", "Cream"],           "Silver",      "Pearl",           "North", "Shiva"),
    ("Leo",          "Sunday",    1, [4],        ["Orange", "Gold", "Red"],    "Gold",        "Ruby",            "East",  "Surya"),
    ("Virgo",        "Wednesday", 5, [3],        ["Green", "Brown"],           "Gold",        "Emerald",         "South", "Ganesha"),
    ("Libra",        "Friday",    6, [5, 9],     ["White", "Light Blue"],      "Silver",      "Diamond",         "West",  "Lakshmi"),
    ("Scorpio",      "Tuesday",   9, [1, 8],     ["Red", "Maroon"],            "Copper",      "Red Coral",       "North", "Kali"),
    ("Sagittarius",  "Thursday",  3, [7, 9],     ["Yellow", "Golden"],         "Gold",        "Yellow Sapphire", "East",  "Vishnu"),
    ("Capricorn",    "Saturday",  8, [4],        ["Blue", "Black", "Purple"],  "Iron",        "Blue Sapphire",   "South", "Shiva"),
    ("Aquarius",     "Saturday",  8, [4],        ["Blue", "Sky Blue"],         "Iron",        "Blue Sapphire",   "West",  "Hanuman"),
    ("Pisces",       "Thursday",  3, [7],        ["Yellow", "Golden"],         "Gold",        "Yellow Sapphire", "North", "Vishnu"),
]

# Nakshatra-lord-based secondary stones (strengthens the primary).
_STONE_BY_NAK_LORD = {
    0: "Ruby",              # Sun
    1: "Pearl",             # Moon
    2: "Red Coral",         # Mars
    3: "Emerald",           # Mercury
    4: "Yellow Sapphire",   # Jupiter
    5: "Diamond",           # Venus
    6: "Blue Sapphire",     # Saturn
    7: "Hessonite",         # Rahu
    8: "Cat's Eye",         # Ketu
}


