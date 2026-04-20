# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""
South Indian style Vedic astrology chart renderer using Pillow.
Generates PNG images from rasi_chart data returned by pyjhora_helper.
"""
import io
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Sign layout for South Indian chart (fixed positions, 4x4 grid)
# The outer 12 cells of a 4x4 grid, each mapped to a rasi (0-based):
#   Pisces(11)  Aries(0)     Taurus(1)    Gemini(2)
#   Aquarius(10)                          Cancer(3)
#   Capricorn(9)                          Leo(4)
#   Sagittarius(8) Scorpio(7) Libra(6)   Virgo(5)
# ---------------------------------------------------------------------------
SIGN_NAMES_SHORT = [
    "Ari", "Tau", "Gem", "Can", "Leo", "Vir",
    "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"
]

# (row, col) position for each rasi index 0-11 in the 4x4 grid
SOUTH_INDIAN_POSITIONS = {
    0: (0, 1),   # Aries
    1: (0, 2),   # Taurus
    2: (0, 3),   # Gemini
    3: (1, 3),   # Cancer
    4: (2, 3),   # Leo
    5: (3, 3),   # Virgo
    6: (3, 2),   # Libra
    7: (3, 1),   # Scorpio
    8: (3, 0),   # Sagittarius
    9: (2, 0),   # Capricorn
    10: (1, 0),  # Aquarius
    11: (0, 0),  # Pisces
}

PLANET_ABBR = {
    "Lagna": "As",
    "Sun": "Su",
    "Moon": "Mo",
    "Mars": "Ma",
    "Mercury": "Me",
    "Jupiter": "Ju",
    "Venus": "Ve",
    "Saturn": "Sa",
    "Rahu": "Ra",
    "Ketu": "Ke",
    "Uranus": "Ur",
    "Neptune": "Ne",
    "Pluto": "Pl",
}


def _group_planets_by_sign(chart_data, label_mode="degrees"):
    """Group planet names by sign_number from rasi_chart output.

    label_mode:
      * "degrees"     → "Su 29°"         (default)
      * "sign_number" → "Su 7"           (1-based rashi number)
      * "both"        → "Su 7 · 29°"
      * "none"        → "Su"
    """
    houses = {}
    for entry in chart_data:
        sign_num = entry["sign_number"]
        planet = entry["planet"]
        abbr = PLANET_ABBR.get(planet, planet[:2])
        deg = entry.get("degrees", 0)
        sign_one_based = int(sign_num) + 1
        if label_mode == "sign_number":
            label = f"{abbr} {sign_one_based}"
        elif label_mode == "both":
            label = f"{abbr} {sign_one_based} · {deg:.0f}\u00b0"
        elif label_mode == "none":
            label = abbr
        else:
            label = f"{abbr} {deg:.0f}\u00b0"
        houses.setdefault(sign_num, []).append(label)
    return houses


def _try_load_font(size):
    """Try to load a good font, fall back to default."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def generate_south_indian_chart(chart_data, title="Rasi Chart", size=600,
                                label_mode="degrees"):
    """
    Generate a South Indian style chart image.

    Args:
        chart_data: list of dicts from pyjhora_helper.get_rasi_chart()
        title: chart title text
        size: image width/height in pixels
        label_mode: "degrees" | "sign_number" | "both" | "none"

    Returns:
        bytes (PNG image)
    """
    margin = 40
    title_height = 50
    img_w = size
    img_h = size + title_height
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 4

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    title_font = _try_load_font(18)
    sign_font = _try_load_font(11)
    planet_font = _try_load_font(10)

    # Title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

    # Draw the 4x4 grid lines
    ox, oy = margin, margin + title_height
    for r in range(5):
        y = oy + r * cell_h
        draw.line([(ox, y), (ox + 4 * cell_w, y)], fill="black", width=2)
    for c in range(5):
        x = ox + c * cell_w
        draw.line([(x, oy), (x, oy + 4 * cell_h)], fill="black", width=2)

    # Draw diagonal lines in the center 2x2 block
    cx1, cy1 = ox + cell_w, oy + cell_h
    cx2, cy2 = ox + 3 * cell_w, oy + 3 * cell_h
    draw.line([(cx1, cy1), (cx2, cy2)], fill="black", width=1)
    draw.line([(cx2, cy1), (cx1, cy2)], fill="black", width=1)

    # Group planets by sign
    houses = _group_planets_by_sign(chart_data, label_mode=label_mode)

    # Fill each cell
    for sign_idx in range(12):
        row, col = SOUTH_INDIAN_POSITIONS[sign_idx]
        x = ox + col * cell_w
        y = oy + row * cell_h

        # Sign name (top-left of cell)
        draw.text((x + 3, y + 2), SIGN_NAMES_SHORT[sign_idx], fill="red", font=sign_font)

        # Planets in this sign
        planets = houses.get(sign_idx, [])
        py = y + 16
        for p_label in planets:
            draw.text((x + 3, py), p_label, fill="darkblue", font=planet_font)
            py += 13

    # Return as PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def generate_bhava_chart(bhava_data, title="Bhava / Chalit Chart", size=600,
                         label_mode="house"):
    """Render a bhava (chalit) chart: each cell shows sign + house # + planets.

    bhava_data: dict with 'houses' key — list of
      {house, sign, cusp_start, cusp_mid, cusp_end, planets, planet_ids}
    label_mode:
      * "house"      → shows "H9" + planets          (default)
      * "cusp"       → shows "H9 · 283°" (cusp mid)
      * "none"       → just planets, no house prefix
    """
    houses_list = bhava_data.get("houses") if isinstance(bhava_data, dict) else bhava_data
    if not houses_list:
        raise ValueError("bhava_data has no 'houses' entries to render")

    sign_name_to_idx = {n: i for i, n in enumerate(
        ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    )}

    # Build a cell dict keyed by sign index.
    cells = {i: {"house": None, "planets": [], "cusp_mid": None} for i in range(12)}
    for h in houses_list:
        sign_idx = sign_name_to_idx.get(h.get("sign"))
        if sign_idx is None:
            cusp_start = float(h.get("cusp_start", 0))
            sign_idx = int(cusp_start // 30) % 12
        cell = cells[sign_idx]
        cell["house"] = int(h["house"]) if cell["house"] is None else f"{cell['house']}/{int(h['house'])}"
        cell["cusp_mid"] = h.get("cusp_mid", cell["cusp_mid"])
        for p in h.get("planets", []):
            cell["planets"].append(PLANET_ABBR.get(p, p[:2]))

    margin = 40
    title_height = 50
    img_w = size
    img_h = size + title_height
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 4

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    title_font = _try_load_font(18)
    sign_font = _try_load_font(11)
    house_font = _try_load_font(14)
    planet_font = _try_load_font(11)

    # Title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

    # Grid
    ox, oy = margin, margin + title_height
    for r in range(5):
        y = oy + r * cell_h
        draw.line([(ox, y), (ox + 4 * cell_w, y)], fill="black", width=2)
    for c in range(5):
        x = ox + c * cell_w
        draw.line([(x, oy), (x, oy + 4 * cell_h)], fill="black", width=2)
    cx1, cy1 = ox + cell_w, oy + cell_h
    cx2, cy2 = ox + 3 * cell_w, oy + 3 * cell_h
    draw.line([(cx1, cy1), (cx2, cy2)], fill="black", width=1)
    draw.line([(cx2, cy1), (cx1, cy2)], fill="black", width=1)

    for sign_idx in range(12):
        row, col = SOUTH_INDIAN_POSITIONS[sign_idx]
        x = ox + col * cell_w
        y = oy + row * cell_h
        cell = cells[sign_idx]

        draw.text((x + 3, y + 2), SIGN_NAMES_SHORT[sign_idx], fill="red", font=sign_font)

        if cell["house"] is not None:
            if label_mode == "cusp" and cell["cusp_mid"] is not None:
                hlabel = f"H{cell['house']} \u00b7 {float(cell['cusp_mid']):.0f}\u00b0"
            elif label_mode == "none":
                hlabel = ""
            else:
                hlabel = f"H{cell['house']}"
            if hlabel:
                draw.text((x + cell_w - 48, y + 2), hlabel,
                          fill="darkgreen", font=house_font)

        py = y + 20
        for p_abbr in cell["planets"]:
            draw.text((x + 3, py), p_abbr, fill="darkblue", font=planet_font)
            py += 14

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def generate_chart_image(chart_data, chart_name="Rasi Chart", size=600,
                         label_mode="degrees"):
    """
    Public API: generate chart image bytes from chart data.

    Args:
        chart_data: list from pyjhora_helper.get_rasi_chart() or any divisional chart
        chart_name: title for the chart
        size: image size in pixels
        label_mode: "degrees" | "sign_number" | "both" | "none"

    Returns:
        PNG image as bytes
    """
    return generate_south_indian_chart(
        chart_data, title=chart_name, size=size, label_mode=label_mode,
    )
