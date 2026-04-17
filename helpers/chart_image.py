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


def _group_planets_by_sign(chart_data):
    """Group planet names by sign_number from rasi_chart output."""
    houses = {}
    for entry in chart_data:
        sign_num = entry["sign_number"]
        planet = entry["planet"]
        abbr = PLANET_ABBR.get(planet, planet[:2])
        deg = entry.get("degrees", 0)
        label = f"{abbr} {deg:.0f}°"
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


def generate_south_indian_chart(chart_data, title="Rasi Chart", size=600):
    """
    Generate a South Indian style chart image.

    Args:
        chart_data: list of dicts from pyjhora_helper.get_rasi_chart()
        title: chart title text
        size: image width/height in pixels

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
    houses = _group_planets_by_sign(chart_data)

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


def generate_chart_image(chart_data, chart_name="Rasi Chart", size=600):
    """
    Public API: generate chart image bytes from chart data.

    Args:
        chart_data: list from pyjhora_helper.get_rasi_chart() or any divisional chart
        chart_name: title for the chart
        size: image size in pixels

    Returns:
        PNG image as bytes
    """
    return generate_south_indian_chart(chart_data, title=chart_name, size=size)
