"""Generate neofetch-style profile cards (ASCII pfp + info panel) as SVG.

Usage: python tools/make_card.py path/to/pfp.jpg
Writes assets/card-dark.svg and assets/card-light.svg
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import colorsys

from PIL import Image, ImageOps, ImageEnhance

COLS, ROWS = 72, 36          # ASCII art size (chars are ~2x taller than wide)
ART_FONT = 8                 # px, art uses a smaller font for more detail
ACW, ALH = ART_FONT * 0.602, ART_FONT * 1.25
FONT = 13                    # px
CW, LH = FONT * 0.602, FONT * 1.25   # monospace char width, line height
RAMP = " .:-=+*#%@"          # light to dense

INFO = [
    ("title", "donovan@djxsec"),
    ("rule", ""),
    ("OS", "Kali Linux / Proxmox VE homelab"),
    ("Host", "University of North Texas"),
    ("Major", "BCIS, Class of 2027"),
    ("Focus", "Cybersecurity, Cloud Security"),
    ("Certs", "CompTIA A+ | Security+ (in progress)"),
    ("Tools", "Burp Suite, Python, n8n, VirtualBox"),
    ("Langs", "Python, Bash, SQL"),
    ("Location", "Dallas Fort Worth, TX"),
    ("Motto", "Let's build, let's learn, let's secure"),
    ("blank", ""),
    ("Contact", "LINKEDIN_PLACEHOLDER"),
    ("blank", ""),
    ("swatch", ""),
]

THEMES = {
    "dark": dict(bg="#0b1220", border="#22324a", art="#c9d1d9", key="#9be7ff",
                 val="#c9d1d9", title="#ffffff", dim="#4b6587", invert=False),
    "light": dict(bg="#ffffff", border="#d0d7de", art="#24292f", key="#0a3069",
                  val="#24292f", title="#0a3069", dim="#8c959f", invert=True),
}
SWATCH = ["#14233a", "#1f3a5a", "#2d4a6b", "#3f6d9a", "#5aa3d6", "#9be7ff", "#cdf3ff", "#ffffff"]


CROP = (162, 170, 862, 870)   # (left, top, right, bottom) in source pixels; frames the figure and server aisle


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _mix(a, b, t):
    a, b = _hex(a), _hex(b)
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _is_figure(rgb):
    h, s, val = colorsys.rgb_to_hsv(*(x / 255 for x in rgb))
    return 0.68 <= h <= 0.93 and s > 0.28


# Each palette: (density 0..1, source rgb, row position 0..1) -> rgb for the dark theme
PALETTES = {
    "matrix":    lambda v, c, y: _mix("#0b3d1a", "#7CFF9B", v),
    "highlight": lambda v, c, y: _mix("#9b6bff", "#ff7ad9", v) if _is_figure(c) else _mix("#1f2a37", "#4b5a6e", v),
    "synthwave": lambda v, c, y: _mix(*(("#ff4fd8", "#ffd1f5") if _is_figure(c) else ("#1b6f8a", "#39c5cf")), v),
    "amber":     lambda v, c, y: _mix("#3d2600", "#ffb347", v),
    "gradient":  lambda v, c, y: _mix("#39c5cf", "#bc8cff", y) if v > 0.35 else _mix("#1f2a37", "#2f3b4c", v),
    "ice":       lambda v, c, y: _mix("#9be7ff", "#ffffff", v) if _is_figure(c) else _mix("#14233a", "#2d4a6b", v),
}
# Light-theme versions (dark ink on white); palettes without one are darkened automatically
PALETTES_LIGHT = {
    "ice": lambda v, c, y: _mix("#0a3069", "#010409", v) if _is_figure(c) else _mix("#d8e1ea", "#9fb3c8", v),
}
PALETTE = "ice"


def ascii_cells(img_path, invert):
    """Return rows of (char, hex color) built from the image."""
    img = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
    if CROP:
        img = img.crop(CROP)
    else:
        s = min(img.size)
        img = img.crop(((img.width - s) // 2, (img.height - s) // 2,
                        (img.width + s) // 2, (img.height + s) // 2))
    img = ImageEnhance.Color(img).enhance(1.4)
    small = img.resize((COLS, ROWS), Image.LANCZOS)
    gray = ImageOps.equalize(small.convert("L"))
    g, rgb = gray.tobytes(), small.tobytes()
    rows = []
    for r in range(ROWS):
        row = []
        for c in range(COLS):
            i = r * COLS + c
            v = 1 - g[i] / 255          # darker pixel = denser char, so the figure reads solid
            ch = RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
            R, G, B = rgb[i * 3:i * 3 + 3]
            own_light = invert and PALETTE in PALETTES_LIGHT
            if PALETTE != "source":
                fn = PALETTES_LIGHT[PALETTE] if own_light else PALETTES[PALETTE]
                R, G, B = fn(v, (R, G, B), r / (ROWS - 1))
            if own_light:
                pass
            elif invert:   # light theme: darken so colors read on white
                R, G, B = int(R * .55), int(G * .55), int(B * .55)
            elif PALETTE == "source":   # dark theme: lift so dim pixels still show
                m = max(R, G, B) or 1
                k = max(1.0, 170 / m)
                R, G, B = min(255, int(R * k)), min(255, int(G * k)), min(255, int(B * k))
            q = lambda x: (x // 32) * 32 + 16          # quantize for fewer tspans
            row.append((ch, "#%02x%02x%02x" % (q(R), q(G), q(B))))
        rows.append(row)
    return rows


def build(img_path, theme):
    t = THEMES[theme]
    art = ascii_cells(img_path, t["invert"])
    pad = 28
    art_w = COLS * ACW
    info_x = pad + art_w + 36
    width = int(info_x + 46 * CW + pad)
    height = int(pad * 2 + max(ROWS * ALH, len(INFO) * LH * 1.15))
    info_y0 = (height - len(INFO) * LH * 1.15) / 2 + FONT

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
         f'font-size="{FONT}">',
         f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
         ]
    for i, row in enumerate(art):
        runs, cur, buf = [], None, ""
        for ch, col in row:
            col = None if ch == " " else col
            if col != cur and buf.strip():
                runs.append((cur, buf)); buf = ""
            if ch != " ":
                cur = col
            buf += ch
        if buf.strip():
            runs.append((cur, buf))
        spans = "".join(f'<tspan fill="{c or t["art"]}">{escape(s)}</tspan>' for c, s in runs)
        art_y0 = (height - ROWS * ALH) / 2 + ART_FONT
        p.append(f'<text x="{pad}" y="{art_y0 + i * ALH:.2f}" font-size="{ART_FONT}" xml:space="preserve">{spans}</text>')

    y = info_y0
    for kind, val in INFO:
        if kind == "title":
            p.append(f'<text x="{info_x}" y="{y:.1f}" fill="{t["title"]}" font-weight="bold">{escape(val)}</text>')
        elif kind == "rule":
            p.append(f'<text x="{info_x}" y="{y:.1f}" fill="{t["dim"]}">{"-" * 14}</text>')
        elif kind == "swatch":
            for i, col in enumerate(SWATCH):
                p.append(f'<rect x="{info_x + i * 3 * CW:.1f}" y="{y - FONT + 2:.1f}" width="{3 * CW:.1f}" height="{FONT + 2}" fill="{col}"/>')
        elif kind != "blank":
            p.append(f'<text x="{info_x}" y="{y:.1f}" xml:space="preserve">'
                     f'<tspan fill="{t["key"]}" font-weight="bold">{escape(kind)}:</tspan>'
                     f'<tspan fill="{t["val"]}"> {escape(val)}</tspan></text>')
        y += LH * 1.15
    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    src = sys.argv[1]
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    for theme in THEMES:
        (out / f"card-{theme}.svg").write_text(build(src, theme), encoding="utf-8")
    print("wrote", *sorted(p.name for p in out.glob("card-*.svg")))
