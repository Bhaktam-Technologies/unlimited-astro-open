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

PLANET_ABBR_HI = {
    "Lagna": "ल",
    "Sun": "सू",
    "Moon": "चं",
    "Mars": "मं",
    "Mercury": "बु",
    "Jupiter": "गु",
    "Venus": "शु",
    "Saturn": "श",
    "Rahu": "रा",
    "Ketu": "के",
    "Uranus": "यू",
    "Neptune": "ने",
    "Pluto": "प्लू",
}

SIGN_NAMES_SHORT_HI = [
    "मेष", "वृष", "मिथु", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चि", "धनु", "मकर", "कुंभ", "मीन",
]


def _try_load_font(size):
    font_paths = [
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux — DejaVu (most distros)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        # Linux — Liberation / FreeSans (common Docker images)
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/freefont/FreeSans.ttf",
        # Linux — Noto (Ubuntu/Debian)
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _try_load_devanagari_font(size):
    """Load a Devanagari-capable font; falls back to default if none found."""
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Devanagari MT.ttf",
        "/Library/Fonts/Devanagari MT.ttf",
        "/System/Library/Fonts/Kohinoor.ttc",
        # Linux (Noto, Lohit)
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/lohit-devanagari/Lohit-Devanagari.ttf",
        # Generic fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _planet_abbr(planet_name, language="en"):
    if language == "hi":
        return PLANET_ABBR_HI.get(planet_name, planet_name[:2])
    return PLANET_ABBR.get(planet_name, planet_name[:2])


def _sign_short(sign_idx, language="en"):
    if language == "hi":
        try:
            return SIGN_NAMES_SHORT_HI[sign_idx]
        except IndexError:
            pass
    try:
        return SIGN_NAMES_SHORT[sign_idx]
    except IndexError:
        return str(sign_idx)


RETRO_LABEL = {"en": "Retrograde", "hi": "वक्री"}
COMBUST_LABEL = {"en": "Combust", "hi": "अस्त"}


def _measure_legend(retrograde, combust, font_size):
    """Return (line_count, legend_height_px) needed for the legend strip."""
    lines = int(bool(retrograde)) + int(bool(combust))
    if lines == 0:
        return 0, 0
    line_h = font_size + 10
    return lines, 12 + lines * line_h + 6


def _draw_retro_combust_legend(draw, retrograde, combust, x, y, font, language="en",
                               color=(0, 0, 0)):
    """Draw '* Retrograde: ...' and '^ Combust: ...' lines starting at (x, y)."""
    try:
        line_h = font.size + 10
    except AttributeError:
        line_h = 28
    lang = "hi" if language == "hi" else "en"
    if retrograde:
        planets = ", ".join(_planet_abbr(p, language) for p in retrograde)
        draw.text((x, y), f"* {RETRO_LABEL[lang]}: {planets}", fill=color, font=font)
        y += line_h
    if combust:
        planets = ", ".join(_planet_abbr(p, language) for p in combust)
        draw.text((x, y), f"^ {COMBUST_LABEL[lang]}: {planets}", fill=color, font=font)


def _group_planets_by_sign(chart_data, label_mode="degrees", language="en"):
    """Group planet labels by 0-based sign index."""
    houses = {}
    for entry in chart_data:
        sign_num_1based = int(entry["sign_number"])
        sign_idx = sign_num_1based - 1
        planet = entry["planet"]
        abbr = _planet_abbr(planet, language)
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


# ---------------------------------------------------------------------------
# South Indian chart
# ---------------------------------------------------------------------------

def generate_south_indian_chart(chart_data, title="Rasi Chart", size=600,
                                label_mode="degrees", language="en",
                                retrograde=None, combust=None):
    """South Indian style: signs are fixed in cells, planets/lagna move."""
    margin = 0
    img_w = size
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 4

    _font = _try_load_devanagari_font if language == "hi" else _try_load_font
    legend_font_size = max(16, size // 30)
    _lines, legend_h = _measure_legend(retrograde, combust, legend_font_size)
    img_h = size + legend_h

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    sign_font   = _font(14)
    planet_font = _font(13)
    legend_font = _font(legend_font_size) if legend_h else None

    ox, oy = margin, margin
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

    houses = _group_planets_by_sign(chart_data, label_mode=label_mode, language=language)

    for sign_idx in range(12):
        row, col = SOUTH_INDIAN_POSITIONS[sign_idx]
        x = ox + col * cell_w
        y = oy + row * cell_h

        draw.text((x + 3, y + 2), _sign_short(sign_idx, language), fill="red", font=sign_font)

        planets = houses.get(sign_idx, [])
        py = y + 20
        for p_label in planets:
            draw.text((x + 3, py), p_label, fill="darkblue", font=planet_font)
            py += 20

    if legend_h:
        _draw_retro_combust_legend(
            draw, retrograde, combust,
            x=ox + 6, y=oy + 4 * cell_h + 8,
            font=legend_font, language=language,
        )

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

def _polygon_inradius(pts, cx, cy):
    """Minimum distance from (cx, cy) to any edge of the polygon — the largest
    circle centred there that fits entirely inside."""
    min_d = float("inf")
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            continue
        d = abs(dx * (ay - cy) - dy * (ax - cx)) / length
        min_d = min(min_d, d)
    return min_d if min_d != float("inf") else 0


def _centroid(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _safe_center(pts):
    """Return the best interior point for text placement.

    For triangles: uses the incenter (maximises min-distance to all sides),
    which guarantees text placed here is as far from every boundary as possible.
    For quadrilaterals: centroid is already well-interior.
    """
    if len(pts) == 3:
        (ax, ay), (bx, by), (cx, cy) = pts
        a = ((bx - cx) ** 2 + (by - cy) ** 2) ** 0.5  # side opposite A
        b = ((ax - cx) ** 2 + (ay - cy) ** 2) ** 0.5  # side opposite B
        c = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5  # side opposite C
        perim = a + b + c
        if perim == 0:
            return _centroid(pts)
        return (a * ax + b * bx + c * cx) / perim, (a * ay + b * by + c * cy) / perim
    return _centroid(pts)


def generate_north_indian_chart(chart_data, title="Rasi Chart", size=600,
                                label_mode="degrees", theme="light", start_sign=None,
                                language="en", retrograde=None, combust=None):
    """North Indian style chart.

    theme: "light" (white bg) or "dark" (black bg, yellow lines, white text).
    start_sign: 1-based sign number to force into House 1 (overrides auto-detect).
    language: "en" or "hi" — switches planet/sign abbreviations to Hindi.
    retrograde / combust: optional lists of planet names to show in a legend
        strip below the chart (marked with `*` and `^` respectively).
    """
    margin = 0
    S = size - 2 * margin
    img_w = size

    if theme == "dark":
        COLOR_LINE   = (255, 180, 0)    # Yellow lines
        COLOR_SIGN   = (255, 180, 0)    # Gold house numbers
        COLOR_PLANET = (255, 255, 255)  # White planets
        COLOR_DEGREE = (255, 255, 255)  # White degrees
        COLOR_LEGEND = (255, 255, 255)
    else:
        COLOR_LINE   = (255, 180, 0)    # Yellow lines
        COLOR_SIGN   = (255, 0, 0)      # Red sign numbers
        COLOR_PLANET = (0, 0, 139)      # DarkBlue planets
        COLOR_DEGREE = (0, 0, 0)        # Black degrees
        COLOR_LEGEND = (0, 0, 0)

    _font = _try_load_devanagari_font if language == "hi" else _try_load_font
    legend_font_size = max(16, size // 30)
    _lines, legend_h = _measure_legend(retrograde, combust, legend_font_size)
    img_h = size + legend_h

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    num_font        = _font(max(12, size // 36))  # sign-number label near inner vertex
    legend_font     = _font(legend_font_size) if legend_h else None
    BASE_PLANET_PT  = 24  # max planet font size
    BASE_DEG_PT     = 15   # max degree font size

    ox = margin
    oy = margin

    def pt(rx, ry):
        return (ox + int(rx * S), oy + int(ry * S))

    TL = pt(0,   0);   TR = pt(1,   0)
    BR = pt(1,   1);   BL = pt(0,   1)
    T  = pt(.5,  0);   R  = pt(1,  .5)
    B  = pt(.5,  1);   L  = pt(0,  .5)
    C  = pt(.5,  .5)
    P1 = pt(.25, .25); P2 = pt(.75, .25)
    P3 = pt(.75, .75); P4 = pt(.25, .75)

    # Standard North Indian houses: H1=Top, H4=Left, H7=Bottom, H10=Right
    # house_polys[h] connects vertices for House h
    house_polys = {
        1:  [C, P1, T, P2],   # Top
        2:  [TL, T, P1],
        3:  [TL, P1, L],
        4:  [C, P4, L, P1],   # Left
        5:  [BL, P4, L],
        6:  [BL, B, P4],
        7:  [C, P3, B, P4],   # Bottom
        8:  [BR, P3, B],
        9:  [BR, R, P3],
        10: [C, P2, R, P3],   # Right
        11: [TR, P2, R],
        12: [TR, T, P2],
    }

    # Inner vertex for each house: sign numbers are drawn near this point so
    # they sit alongside the inner diamond's intersection lines (standard
    # North Indian convention — see e.g. JHora / most Vedic software).
    house_inner = {
        1:  C,  2:  P1, 3:  P1, 4:  C,
        5:  P4, 6:  P4, 7:  C,  8:  P3,
        9:  P3, 10: C,  11: P2, 12: P2,
    }

    # Fixed sign layout: position 1=Aries (bottom-center), anti-clockwise to 12=Pisces.
    # sign_number in chart_data is 1-based (1=Aries), matching the polygon key directly.

    # Determine the reference planet for House 1 (Lagna/Ascendant)
    # For Moon Chart, we use Moon as the reference. For Sun Chart, we use Sun.
    ref_name = "Lagna"
    if title and "Moon" in title:
        ref_name = "Moon"
    elif title and "Sun" in title:
        ref_name = "Sun"

    # Find the starting sign for House 1 (use override if provided)
    if start_sign is None:
        start_sign = 1
        for entry in chart_data:
            p_name = entry.get("planet", "").lower()
            p_id = str(entry.get("planet_id", "")).lower()
            if p_name == ref_name.lower() or p_id == ref_name[0].lower() or (ref_name == "Lagna" and (p_name == "as" or p_id == "l")):
                start_sign = int(entry["sign_number"])
                break

    # Group planets by House (1-12)
    house_planets = {h: [] for h in range(1, 13)}
    for entry in chart_data:
        sign_num = int(entry["sign_number"])
        h = (sign_num - start_sign) % 12 + 1

        p_name = entry.get("planet", "")
        p_id = str(entry.get("planet_id", ""))
        if p_name.lower() == ref_name.lower() or p_id.lower() == ref_name[0].lower():
            abbr = _planet_abbr("Lagna" if ref_name == "Lagna" else ref_name, language)
            deg = float(entry.get("degrees", 0))
            house_planets[h].insert(0, (abbr, deg))
        else:
            abbr = _planet_abbr(p_name, language)
            deg  = float(entry.get("degrees", 0))
            house_planets[h].append((abbr, deg))

    # Sign number to display in each cell corner (sign that occupies each house)
    house_sign_num = {h: (start_sign - 1 + h - 1) % 12 + 1 for h in range(1, 13)}

    # --- Draw chart border + lines ---
    draw.rectangle([ox, oy, ox + S, oy + S], outline=COLOR_LINE, width=3)
    draw.line([T, R], fill=COLOR_LINE, width=2)
    draw.line([R, B], fill=COLOR_LINE, width=2)
    draw.line([B, L], fill=COLOR_LINE, width=2)
    draw.line([L, T], fill=COLOR_LINE, width=2)
    draw.line([TL, BR], fill=COLOR_LINE, width=2)
    draw.line([TR, BL], fill=COLOR_LINE, width=2)

    # --- Render each house cell ---
    for h, pts in house_polys.items():
        cx_c, cy_c = _centroid(pts)
        inner = house_inner[h]

        # Sign Number (Rashi): placed just inside the polygon from its inner
        # vertex, offset toward the centroid so adjacent houses that share the
        # same inner vertex (e.g. H2/H3 both meet at P1) end up on opposite
        # sides of the diagonal.
        nx = inner[0] + (cx_c - inner[0]) * 0.22
        ny = inner[1] + (cy_c - inner[1]) * 0.22
        sign_str = str(house_sign_num[h])
        nbbox = draw.textbbox((0, 0), sign_str, font=num_font)
        nw, nh = nbbox[2]-nbbox[0], nbbox[3]-nbbox[1]
        draw.text((nx - nw / 2, ny - nh / 2), sign_str, fill=COLOR_SIGN, font=num_font)

        # Planets: use incenter for triangles (deepest interior point),
        # centroid for diamonds — guarantees text stays inside the cell.
        planets = house_planets[h]
        if not planets:
            continue

        sx, sy = _safe_center(pts)
        show_degrees = label_mode != "none"

        # Auto-scale font so all planets fit within the inscribed circle
        inradius = _polygon_inradius(pts, sx, sy)
        avail_h = inradius * 1.8   # usable vertical span (slightly less than diameter)
        avail_w = inradius * 1.8   # usable horizontal span

        use_two_cols = len(planets) >= 3
        col_count = 2 if use_two_cols else 1
        rows = (len(planets) + 1) // 2 if use_two_cols else len(planets)

        # Binary-search for the largest font that fits
        lo, hi = 6, BASE_PLANET_PT
        planet_pt = lo
        while lo <= hi:
            mid = (lo + hi) // 2
            pf = _font(mid)
            # measure tallest planet label
            max_pw = max(draw.textbbox((0, 0), a, font=pf)[2] for a, _ in planets)
            max_ph = max(draw.textbbox((0, 0), a, font=pf)[3] for a, _ in planets)
            spacing = max(2, mid // 4)
            block_h = rows * (max_ph + spacing)
            block_w = col_count * (max_pw + (mid // 2 if show_degrees else 0) + 4)
            if block_h <= avail_h and block_w <= avail_w:
                planet_pt = mid
                lo = mid + 1
            else:
                hi = mid - 1

        p_font = _font(planet_pt)
        d_font = _font(max(6, planet_pt // 2))

        def _draw_planet_row(cx, ty, abbr, deg):
            pbbox = draw.textbbox((0, 0), abbr, font=p_font)
            pw, ph = pbbox[2] - pbbox[0], pbbox[3] - pbbox[1]
            x0 = cx - pw / 2
            draw.text((x0, ty), abbr, fill=COLOR_PLANET, font=p_font)
            if show_degrees:
                deg_str = f"{int(round(deg)):02d}"
                dbbox = draw.textbbox((0, 0), deg_str, font=d_font)
                dh = dbbox[3] - dbbox[1]
                draw.text((x0 + pw + 2, ty - dh // 2), deg_str, fill=COLOR_DEGREE, font=d_font)

        spacing = max(2, planet_pt // 4)
        if use_two_cols:
            col_size = (len(planets) + 1) // 2
            max_ph = max(draw.textbbox((0, 0), a, font=p_font)[3] for a, _ in planets)
            block_h = col_size * (max_ph + spacing)
            for i, (abbr, deg) in enumerate(planets):
                col = 0 if i < col_size else 1
                row = i if i < col_size else i - col_size
                tx = sx - inradius * 0.3 if col == 0 else sx + inradius * 0.3
                ty = sy - block_h / 2 + row * (max_ph + spacing)
                _draw_planet_row(tx, ty, abbr, deg)
        else:
            max_ph = max(draw.textbbox((0, 0), a, font=p_font)[3] for a, _ in planets)
            block_h = len(planets) * (max_ph + spacing)
            ty = sy - block_h / 2
            for abbr, deg in planets:
                _draw_planet_row(sx, ty, abbr, deg)
                ty += max_ph + spacing

    if legend_h:
        _draw_retro_combust_legend(
            draw, retrograde, combust,
            x=ox + 6, y=oy + S + 8,
            font=legend_font, language=language, color=COLOR_LEGEND,
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Bhava / Chalit chart (South Indian style)
# ---------------------------------------------------------------------------

def generate_bhava_chart(bhava_data, title="Bhava / Chalit Chart", size=600,
                         label_mode="house", style="north", language="en"):
    """Render a bhava (chalit) chart in North or South Indian style.
    bhava_data: dict with 'houses' key — list of
      {house, sign, cusp_start, cusp_mid, cusp_end, planets, planet_ids}
    label_mode:
      * "house"       → shows "H9" + planets          (default)
      * "cusp"        → shows "H9 \u00b7 283\u00b0" (cusp mid)
      * "sign_number" → shows Rashi number in corner
      * "none"        → just planets, no house prefix
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
            cell["planets"].append(_planet_abbr(p, language))

    if style == "south":
        return _bhava_south(cells, title=title, size=size, label_mode=label_mode, language=language)
    return _bhava_north(cells, houses_list, title=title, size=size, label_mode=label_mode, language=language)


def _bhava_south(cells, title="Bhava / Chalit Chart", size=600, label_mode="house", language="en"):
    """South Indian fixed-sign grid for the bhava chart."""
    margin = 0
    img_w = size
    img_h = size
    cell_w = (size - 2 * margin) // 4
    cell_h = (size - 2 * margin) // 4

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _font = _try_load_devanagari_font if language == "hi" else _try_load_font
    sign_font   = _font(14)
    house_font  = _font(17)
    planet_font = _font(14)

    ox, oy = margin, margin
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

        draw.text((x + 3, y + 2), _sign_short(sign_idx, language), fill="red", font=sign_font)

        if cell["house"] is not None:
            if label_mode == "cusp" and cell["cusp_mid"] is not None:
                hlabel = f"H{cell['house']} \u00b7 {float(cell['cusp_mid']):.0f}\u00b0"
            elif label_mode == "sign_number":
                hlabel = str(sign_idx + 1)
            elif label_mode == "none":
                hlabel = ""
            else:
                hlabel = f"H{cell['house']}"
            if hlabel:
                color = "red" if label_mode == "sign_number" else "darkgreen"
                draw.text((x + cell_w - 48, y + 2), hlabel,
                          fill=color, font=house_font)

        py = y + 20
        for p_abbr in cell["planets"]:
            draw.text((x + 3, py), p_abbr, fill="darkblue", font=planet_font)
            py += 18

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _bhava_north(cells, houses_list, title="Bhava / Chalit Chart", size=600,
                 label_mode="house", language="en"):
    """North Indian diamond layout for the bhava chart.

    Houses are fixed in the 12 diamond regions (same geometry as generate_north_indian_chart).
    The Bhava-1 house determines which sign goes in region H1; subsequent signs follow
    clockwise — identical rotation logic to the rasi North Indian renderer.
    """
    margin = 0
    S = size - 2 * margin
    img_w = size
    img_h = size

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _font = _try_load_devanagari_font if language == "hi" else _try_load_font
    sign_font   = _font(14)
    house_font  = _font(14)
    planet_font = _font(14)

    ox = margin
    oy = margin

    def pt(rx, ry):
        return (ox + int(rx * S), oy + int(ry * S))

    TL = pt(0,   0);   TR = pt(1,   0)
    BR = pt(1,   1);   BL = pt(0,   1)
    T  = pt(.5,  0);   R  = pt(1,  .5)
    B  = pt(.5,  1);   L  = pt(0,  .5)
    C  = pt(.5,  .5)
    P1 = pt(.25, .25); P2 = pt(.75, .25)
    P3 = pt(.75, .75); P4 = pt(.25, .75)

    # Determine rotation offset: we want the house containing Lagna (or House 1) at the Top
    # In North Indian charts, the Top Diamond is traditionally House 1.
    # We find which h_num from the data should be in Polygon 1.
    # Usually, House 1 is the one we want at the Top.
    # If the API data is already house-ordered, we map h_num directly to Polygon h_num.
    # If the user says it's "opposite", it might be because they want House 1 at the Top
    # but the API returned a fixed Aries-based chart. 
    # However, we'll stick to H1=Top and ensure House 1 from data goes there.
    
    # house_polys[h] maps house number (1-12) to polygon vertices
    # H1=Top, H4=Left, H7=Bottom, H10=Right
    house_polys = {
        1:  [C, P1, T, P2],   # Top
        2:  [TL, T, P1],
        3:  [TL, P1, L],
        4:  [C, P4, L, P1],   # Left
        5:  [BL, P4, L],
        6:  [BL, B, P4],
        7:  [C, P3, B, P4],   # Bottom
        8:  [BR, P3, B],
        9:  [BR, R, P3],
        10: [C, P2, R, P3],   # Right
        11: [TR, P2, R],
        12: [TR, T, P2],
    }
    house_outer = {
        1: T,  2: TL, 3: L,  4: L,
        5: BL, 6: B,  7: B,  8: BR,
        9: R,  10: R, 11: TR, 12: T,
    }

    # Build per-house data directly from the input houses_list
    region_data = {}
    for h_entry in houses_list:
        h_num = int(h_entry.get("house", 0))
        if h_num < 1 or h_num > 12: continue
        
        sign_name = h_entry.get("sign", "")
        sign_idx = SIGN_NAMES_FULL.index(sign_name) if sign_name in SIGN_NAMES_FULL else 0
        
        planets_to_draw = []
        is_lagna_house = False
        for p in h_entry.get("planets", []):
            if p in {"Lagna", "As", "L"}:
                planets_to_draw.insert(0, _planet_abbr("Lagna", language))
                is_lagna_house = True
            else:
                planets_to_draw.append(_planet_abbr(p, language))

        region_data[h_num] = {
            "sign_idx": sign_idx,
            "house_label": h_num,
            "planets": planets_to_draw,
            "cusp_mid": h_entry.get("cusp_mid"),
            "is_lagna": is_lagna_house
        }

    # Determine rotation: find which house has Lagna. 
    # If no house has "La", we assume House 1 is the top.
    lagna_h = 1
    for h_num, rd in region_data.items():
        if rd["is_lagna"]:
            lagna_h = h_num
            break
    
    # rotation_offset: house h_num will be placed in polygon ((h_num - lagna_h) % 12) + 1
    # This ensures lagna_h goes to polygon 1 (Top).
    
    # --- Draw chart lines ---
    draw.rectangle([ox, oy, ox + S, oy + S], outline=(255, 180, 0), width=2)
    line_color = (255, 180, 0) # Yellow lines
    for pair in [(T, R), (R, B), (B, L), (L, T), (TL, BR), (TR, BL)]:
        draw.line([pair[0], pair[1]], fill=line_color, width=1)

    # --- Fill each region ---
    # Polygon p_num (1..12) should contain House h_num
    # where House lagna_h goes to Polygon 1.
    # So House h_num goes to Polygon p_num = (h_num - lagna_h) % 12 + 1
    # Conversely, Polygon p_num contains House h_num = (p_num - 1 + lagna_h - 1) % 12 + 1
    
    for p_num, pts in house_polys.items():
        h_num = (p_num - 1 + lagna_h - 1) % 12 + 1
        rd = region_data.get(h_num)
        if not rd: continue
        
        sign_short = SIGN_NAMES_SHORT[rd["sign_idx"]]
        cx_c, cy_c = _centroid(pts)
        outer = house_outer[p_num]

        # House/Sign label in corner
        if label_mode != "none":
            if label_mode == "cusp" and rd["cusp_mid"] is not None:
                hlabel = f"H{rd['house_label']} \u00b7 {float(rd['cusp_mid']):.0f}\u00b0"
            elif label_mode == "sign_number":
                hlabel = str(rd["sign_idx"] + 1)
            else:
                hlabel = f"H{rd['house_label']}"
            
            nx = cx_c + (outer[0] - cx_c) * 0.42
            ny = cy_c + (outer[1] - cy_c) * 0.42
            bb = draw.textbbox((0, 0), hlabel, font=house_font)
            draw.text((nx - (bb[2]-bb[0])/2, ny - (bb[3]-bb[1])/2), hlabel, 
                      fill="red" if label_mode == "sign_number" else "darkgreen", font=house_font)

        # Build list of lines to draw in the center
        lines = []
        for p in rd["planets"]:
            lines.append(("planet", p))

        # Layout calculations
        planet_lines = [l for l in lines if l[0] == "planet"]
        other_lines = [l for l in lines if l[0] != "planet"]
        _lh = 18  # line height — extra room for Devanagari matras
        planet_rows = (len(planet_lines) + 1) // 2 if len(planet_lines) > 4 else len(planet_lines)
        total_h = (len(other_lines) + planet_rows) * _lh

        shift_factor = 0.18
        inner_x = cx_c + (outer[0] - cx_c) * shift_factor
        inner_y = cy_c + (outer[1] - cy_c) * shift_factor

        current_y = inner_y - total_h / 2
        color_map = {"sign": "darkred", "planet": "darkblue"}
        font_map  = {"sign": sign_font,  "planet": planet_font}

        for kind, text in other_lines:
            f = font_map[kind]
            bb = draw.textbbox((0, 0), text, font=f)
            draw.text((inner_x - (bb[2]-bb[0])/2, current_y), text, fill=color_map[kind], font=f)
            current_y += _lh

        if len(planet_lines) > 4:
            col_size = (len(planet_lines) + 1) // 2
            for i, p_item in enumerate(planet_lines):
                p_text = p_item[1]
                col = 0 if i < col_size else 1
                row = i if i < col_size else i - col_size
                tx = inner_x - 16 if col == 0 else inner_x + 16
                ty = current_y + row * _lh
                bb = draw.textbbox((0, 0), p_text, font=planet_font)
                draw.text((tx - (bb[2]-bb[0])/2, ty), p_text, fill=color_map["planet"], font=planet_font)
        else:
            for kind, text in planet_lines:
                f = font_map[kind]
                bb = draw.textbbox((0, 0), text, font=f)
                draw.text((inner_x - (bb[2]-bb[0])/2, current_y), text, fill=color_map[kind], font=f)
                current_y += _lh

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_chart_image(chart_data, chart_name="Rasi Chart", size=600,
                         label_mode="degrees", style="north", language="en",
                         retrograde=None, combust=None):
    """Generate chart image bytes.

    Args:
        chart_data: list from pyjhora_helper.get_rasi_chart() or any divisional chart
        chart_name: title for the chart
        size: image size in pixels
        label_mode: "degrees" | "sign_number" | "both" | "none"
        style: "north" (default) | "south"
        language: "en" (default) | "hi"
        retrograde: optional list of retrograde planet names — shown as
            "* Retrograde: ..." legend below the chart.
        combust: optional list of combust planet names — shown as
            "^ Combust: ..." legend below the chart.

    Returns:
        PNG image as bytes
    """
    if style == "south":
        return generate_south_indian_chart(
            chart_data, title=chart_name, size=size, label_mode=label_mode, language=language,
            retrograde=retrograde, combust=combust,
        )
    return generate_north_indian_chart(
        chart_data, title=chart_name, size=size, label_mode=label_mode, language=language,
        retrograde=retrograde, combust=combust,
    )


def generate_gochar_chart_image(planets, ref_sign, title="Gochar", size=600, language="en"):
    """Render a Gochar (Transit) chart."""
    return generate_north_indian_chart(
        planets, title=title, size=size,
        label_mode="degrees", theme="light", start_sign=ref_sign, language=language,
    )
