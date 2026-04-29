# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""
Vedic astrology chart renderer (North Indian & South Indian styles) using Pillow.
Generates PNG images from rasi_chart data returned by pyjhora_helper.
"""
import io
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Sign layout for South Indian chart (fixed sign positions, 4x4 grid)
#   Pisces(11)  Aries(0)     Taurus(1)    Gemini(2)
#   Aquarius(10)                          Cancer(3)
#   Capricorn(9)                          Leo(4)
#   Sagittarius(8) Scorpio(7) Libra(6)   Virgo(5)
# sign_index is 0-based internally; sign_number in chart_data is 1-based.
# ---------------------------------------------------------------------------
SIGN_NAMES_SHORT = [
    "Ari", "Tau", "Gem", "Can", "Leo", "Vir",
    "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"
]
SIGN_NAMES_FULL = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# (row, col) in 4x4 grid for each 0-based sign index
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
    """Group planet labels by 0-based sign index.

    sign_number in chart_data is 1-based (1=Aries … 12=Pisces);
    we convert to 0-based for use as a dict key so callers can look up
    by the same 0-based index used in SOUTH_INDIAN_POSITIONS.

    label_mode:
      * "degrees"     → "Su 29°"   (default)
      * "sign_number" → "Su 7"     (1-based rashi number)
      * "both"        → "Su 7 · 29°"
      * "none"        → "Su"
    """
    houses = {}
    for entry in chart_data:
        sign_num_1based = int(entry["sign_number"])          # 1-based from API
        sign_idx = sign_num_1based - 1                       # 0-based for grid lookup
        planet = entry["planet"]
        abbr = PLANET_ABBR.get(planet, planet[:2])
        deg = entry.get("degrees", 0)
        if label_mode == "sign_number":
            label = f"{abbr} {sign_num_1based}"
        elif label_mode == "both":
            label = f"{abbr} {sign_num_1based} · {deg:.0f}\u00b0"
        elif label_mode == "none":
            label = abbr
        else:
            label = f"{abbr} {deg:.0f}\u00b0"
        houses.setdefault(sign_idx, []).append(label)
    return houses


def _try_load_font(size):
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


# ---------------------------------------------------------------------------
# South Indian chart
# ---------------------------------------------------------------------------

def generate_south_indian_chart(chart_data, title="Rasi Chart", size=600,
                                label_mode="degrees"):
    """South Indian style: signs are fixed in cells, planets/lagna move."""
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

    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

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

    houses = _group_planets_by_sign(chart_data, label_mode=label_mode)

    for sign_idx in range(12):
        row, col = SOUTH_INDIAN_POSITIONS[sign_idx]
        x = ox + col * cell_w
        y = oy + row * cell_h

        draw.text((x + 3, y + 2), SIGN_NAMES_SHORT[sign_idx], fill="red", font=sign_font)

        planets = houses.get(sign_idx, [])
        py = y + 16
        for p_label in planets:
            draw.text((x + 3, py), p_label, fill="darkblue", font=planet_font)
            py += 13

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# North Indian chart
# ---------------------------------------------------------------------------
# Construction: outer square + both full diagonals (TL→BR, TR→BL) +
# inner diamond (connecting midpoints T, R, B, L of each side).
# The diagonals intersect the diamond sides at P1..P4, creating 12 regions:
#   4 inner quadrilaterals  → H1 (bottom), H4 (right), H7 (top), H10 (left)
#   8 corner triangles (2 per corner) → H2–H3, H5–H6, H8–H9, H11–H12
# Houses go clockwise from H1. Signs rotate; Lagna sign goes in H1.
# ---------------------------------------------------------------------------

def _centroid(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def generate_north_indian_chart(chart_data, title="Rasi Chart", size=600,
                                label_mode="degrees"):
    """North Indian (Uttara Bharatiya) style: houses are fixed, signs rotate."""
    margin = 40
    title_height = 50
    S = size - 2 * margin        # chart square side length
    img_w = size
    img_h = size + title_height

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    title_font  = _try_load_font(18)
    sign_font   = _try_load_font(10)
    planet_font = _try_load_font(10)

    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

    ox = margin
    oy = margin + title_height

    # Named key points (integer coords)
    def pt(rx, ry):   # rx, ry in [0,1] relative to chart square
        return (ox + int(rx * S), oy + int(ry * S))

    TL = pt(0,   0);   TR = pt(1,   0)
    BR = pt(1,   1);   BL = pt(0,   1)
    T  = pt(.5,  0);   R  = pt(1,  .5)
    B  = pt(.5,  1);   L  = pt(0,  .5)
    C  = pt(.5,  .5)
    P1 = pt(.25, .25); P2 = pt(.75, .25)
    P3 = pt(.75, .75); P4 = pt(.25, .75)

    # 12 house polygons — clockwise from H1 (bottom inner)
    house_polys = {
        1:  [C, P3, B, P4],
        2:  [BR, P3, B],
        3:  [BR, R, P3],
        4:  [C, P2, R, P3],
        5:  [TR, P2, R],
        6:  [TR, T, P2],
        7:  [C, P1, T, P2],
        8:  [TL, T, P1],
        9:  [TL, P1, L],
        10: [C, P4, L, P1],
        11: [BL, P4, L],
        12: [BL, B, P4],
    }

    # Find Lagna sign (1-based)
    lagna_sign = 1
    for entry in chart_data:
        if entry.get("planet") == "Lagna" or entry.get("planet_id") == "L":
            lagna_sign = int(entry["sign_number"])
            break

    # house_sign[h] = 0-based sign index for house h
    house_sign = {h: (lagna_sign - 1 + h - 1) % 12 for h in range(1, 13)}

    # Group planet labels by house
    house_planets = {h: [] for h in range(1, 13)}
    sign_to_house = {si: h for h, si in house_sign.items()}
    for entry in chart_data:
        if entry.get("planet") == "Lagna":
            continue
        sign_idx = int(entry["sign_number"]) - 1
        abbr = PLANET_ABBR.get(entry["planet"], entry["planet"][:2])
        deg  = entry.get("degrees", 0)
        if label_mode == "sign_number":
            label = f"{abbr} {sign_idx + 1}"
        elif label_mode == "both":
            label = f"{abbr} {sign_idx+1}·{deg:.0f}°"
        elif label_mode == "none":
            label = abbr
        else:
            label = f"{abbr} {deg:.0f}°"
        h = sign_to_house.get(sign_idx)
        if h:
            house_planets[h].append(label)

    # --- Draw chart lines ---
    # Outer border
    draw.rectangle([ox, oy, ox + S, oy + S], outline="black", width=2)
    # Inner diamond sides
    line_color = (160, 80, 0)   # dark amber, similar to AstroSage dashed lines
    draw.line([T, R], fill=line_color, width=1)
    draw.line([R, B], fill=line_color, width=1)
    draw.line([B, L], fill=line_color, width=1)
    draw.line([L, T], fill=line_color, width=1)
    # Full diagonals (TL→BR and TR→BL)
    draw.line([TL, BR], fill=line_color, width=1)
    draw.line([TR, BL], fill=line_color, width=1)

    # --- Fill each house cell with sign + planets ---
    for h, pts in house_polys.items():
        sign_idx   = house_sign[h]
        sign_short = SIGN_NAMES_SHORT[sign_idx]
        cx_c, cy_c = _centroid(pts)

        # Sign abbreviation (red, small)
        sbbox = draw.textbbox((0, 0), sign_short, font=sign_font)
        sw = sbbox[2] - sbbox[0]
        sh = sbbox[3] - sbbox[1]

        planets = house_planets[h]
        block_h = sh + len(planets) * 13
        top_y   = cy_c - block_h / 2

        draw.text((cx_c - sw / 2, top_y), sign_short, fill="darkred", font=sign_font)
        py = top_y + sh + 2
        for p_label in planets:
            pbbox = draw.textbbox((0, 0), p_label, font=planet_font)
            pw = pbbox[2] - pbbox[0]
            draw.text((cx_c - pw / 2, py), p_label, fill="darkblue", font=planet_font)
            py += 13

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Bhava / Chalit chart (South Indian style)
# ---------------------------------------------------------------------------

def generate_bhava_chart(bhava_data, title="Bhava / Chalit Chart", size=600,
                         label_mode="house", style="north"):
    """Render a bhava (chalit) chart in North or South Indian style.

    bhava_data: dict with 'houses' key — list of
      {house, sign, cusp_start, cusp_mid, cusp_end, planets, planet_ids}
    label_mode:
      * "house"      → shows "H9" + planets          (default)
      * "cusp"       → shows "H9 · 283°" (cusp mid)
      * "none"       → just planets, no house prefix
    style:
      * "north"      → North Indian diamond layout    (default)
      * "south"      → South Indian fixed-sign grid
    """
    houses_list = bhava_data.get("houses") if isinstance(bhava_data, dict) else bhava_data
    if not houses_list:
        raise ValueError("bhava_data has no 'houses' entries to render")

    sign_name_to_idx = {n: i for i, n in enumerate(SIGN_NAMES_FULL)}

    # Build per-sign-cell data: house number(s), planets, cusp_mid
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

    if style == "south":
        return _bhava_south(cells, title=title, size=size, label_mode=label_mode)
    return _bhava_north(cells, houses_list, title=title, size=size, label_mode=label_mode)


def _bhava_south(cells, title="Bhava / Chalit Chart", size=600, label_mode="house"):
    """South Indian fixed-sign grid for the bhava chart."""
    margin = 40
    title_height = 50
    img_w = size
    img_h = size + title_height
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 4

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    title_font  = _try_load_font(18)
    sign_font   = _try_load_font(11)
    house_font  = _try_load_font(14)
    planet_font = _try_load_font(11)

    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

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


def _bhava_north(cells, houses_list, title="Bhava / Chalit Chart", size=600,
                 label_mode="house"):
    """North Indian diamond layout for the bhava chart.

    Houses are fixed in the 12 diamond regions (same geometry as generate_north_indian_chart).
    The Bhava-1 house determines which sign goes in region H1; subsequent signs follow
    clockwise — identical rotation logic to the rasi North Indian renderer.
    """
    margin = 40
    title_height = 50
    S = size - 2 * margin
    img_w = size
    img_h = size + title_height

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    title_font  = _try_load_font(18)
    sign_font   = _try_load_font(10)
    house_font  = _try_load_font(10)
    planet_font = _try_load_font(10)

    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) // 2, 10), title, fill="black", font=title_font)

    ox = margin
    oy = margin + title_height

    def pt(rx, ry):
        return (ox + int(rx * S), oy + int(ry * S))

    TL = pt(0,   0);   TR = pt(1,   0)
    BR = pt(1,   1);   BL = pt(0,   1)
    T  = pt(.5,  0);   R  = pt(1,  .5)
    B  = pt(.5,  1);   L  = pt(0,  .5)
    C  = pt(.5,  .5)
    P1 = pt(.25, .25); P2 = pt(.75, .25)
    P3 = pt(.75, .75); P4 = pt(.25, .75)

    house_polys = {
        1:  [C, P3, B, P4],
        2:  [BR, P3, B],
        3:  [BR, R, P3],
        4:  [C, P2, R, P3],
        5:  [TR, P2, R],
        6:  [TR, T, P2],
        7:  [C, P1, T, P2],
        8:  [TL, T, P1],
        9:  [TL, P1, L],
        10: [C, P4, L, P1],
        11: [BL, P4, L],
        12: [BL, B, P4],
    }

    # Determine lagna sign from bhava-1 entry
    lagna_sign_1based = 1
    for h in houses_list:
        if int(h.get("house", 0)) == 1:
            sign_name = h.get("sign", "")
            if sign_name in SIGN_NAMES_FULL:
                lagna_sign_1based = SIGN_NAMES_FULL.index(sign_name) + 1
            else:
                cusp = float(h.get("cusp_start", 0))
                lagna_sign_1based = int(cusp // 30) % 12 + 1
            break

    # house_sign[h] = 0-based sign index placed in diamond region h
    house_sign = {h: (lagna_sign_1based - 1 + h - 1) % 12 for h in range(1, 13)}
    sign_to_region = {si: h for h, si in house_sign.items()}

    # Build per-region data from cells (keyed by sign index)
    region_data = {h: {"sign_idx": house_sign[h], "house_label": None,
                       "planets": [], "cusp_mid": None}
                   for h in range(1, 13)}
    for sign_idx, cell in cells.items():
        region = sign_to_region.get(sign_idx)
        if region is None:
            continue
        rd = region_data[region]
        rd["house_label"] = cell["house"]
        rd["planets"] = cell["planets"]
        rd["cusp_mid"] = cell["cusp_mid"]

    # --- Draw chart lines ---
    draw.rectangle([ox, oy, ox + S, oy + S], outline="black", width=2)
    line_color = (160, 80, 0)
    draw.line([T, R], fill=line_color, width=1)
    draw.line([R, B], fill=line_color, width=1)
    draw.line([B, L], fill=line_color, width=1)
    draw.line([L, T], fill=line_color, width=1)
    draw.line([TL, BR], fill=line_color, width=1)
    draw.line([TR, BL], fill=line_color, width=1)

    # --- Fill each region ---
    for region, pts in house_polys.items():
        rd = region_data[region]
        sign_short = SIGN_NAMES_SHORT[rd["sign_idx"]]
        cx_c, cy_c = _centroid(pts)

        # Build label lines: [sign, house_label, ...planets]
        lines = []

        # House label (e.g. "H3") in darkgreen
        if rd["house_label"] is not None and label_mode != "none":
            if label_mode == "cusp" and rd["cusp_mid"] is not None:
                hlabel = f"H{rd['house_label']} \u00b7 {float(rd['cusp_mid']):.0f}\u00b0"
            else:
                hlabel = f"H{rd['house_label']}"
            lines.append(("house", hlabel))

        # Sign abbr in darkred
        lines.append(("sign", sign_short))

        # Planets in darkblue
        for p in rd["planets"]:
            lines.append(("planet", p))

        total_h = len(lines) * 13
        top_y = cy_c - total_h / 2

        color_map = {"house": "darkgreen", "sign": "darkred", "planet": "darkblue"}
        font_map  = {"house": house_font,  "sign": sign_font,  "planet": planet_font}

        for kind, text in lines:
            f = font_map[kind]
            bb = draw.textbbox((0, 0), text, font=f)
            tw2 = bb[2] - bb[0]
            draw.text((cx_c - tw2 / 2, top_y), text, fill=color_map[kind], font=f)
            top_y += 13

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_chart_image(chart_data, chart_name="Rasi Chart", size=600,
                         label_mode="degrees", style="north"):
    """Generate chart image bytes.

    Args:
        chart_data: list from pyjhora_helper.get_rasi_chart() or any divisional chart
        chart_name: title for the chart
        size: image size in pixels
        label_mode: "degrees" | "sign_number" | "both" | "none"
        style: "north" (default) | "south"

    Returns:
        PNG image as bytes
    """
    if style == "south":
        return generate_south_indian_chart(
            chart_data, title=chart_name, size=size, label_mode=label_mode,
        )
    return generate_north_indian_chart(
        chart_data, title=chart_name, size=size, label_mode=label_mode,
    )
