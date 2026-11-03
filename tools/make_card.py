"""Generate neofetch-style profile cards (ASCII pfp + info panel) as SVG.

Usage: python tools/make_card.py path/to/pfp.jpg
Writes assets/card-dark.svg and assets/card-light.svg
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps, ImageEnhance

COLS, ROWS = 46, 23          # ASCII art size (chars are ~2x taller than wide)
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
    "dark": dict(bg="#0d1117", border="#30363d", art="#c9d1d9", key="#58a6ff",
                 val="#c9d1d9", title="#3fb950", dim="#8b949e", invert=False),
    "light": dict(bg="#ffffff", border="#d0d7de", art="#24292f", key="#0969da",
                  val="#24292f", title="#1a7f37", dim="#57606a", invert=True),
}
SWATCH = ["#f85149", "#d29922", "#3fb950", "#58a6ff", "#bc8cff", "#39c5cf", "#8b949e", "#f0f6fc"]


def ascii_lines(img_path, invert):
    img = Image.open(img_path).convert("L")
    img = ImageOps.exif_transpose(img) or img
    s = min(img.size)                                  # center square crop
    img = img.crop(((img.width - s) // 2, (img.height - s) // 2,
                    (img.width + s) // 2, (img.height + s) // 2))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = img.resize((COLS, ROWS), Image.LANCZOS)
    px = list(img.tobytes())
    out = []
    for r in range(ROWS):
        row = ""
        for c in range(COLS):
            v = px[r * COLS + c] / 255
            if invert:
                v = 1 - v
            row += RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
        out.append(row.rstrip())
    return out


def build(img_path, theme):
    t = THEMES[theme]
    art = ascii_lines(img_path, t["invert"])
    pad = 28
    art_w = COLS * CW
    info_x = pad + art_w + 36
    width = int(info_x + 46 * CW + pad)
    height = int(pad * 2 + ROWS * LH)
    info_y0 = pad + (ROWS * LH - len(INFO) * LH * 1.15) / 2 + FONT

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
         f'font-size="{FONT}">',
         f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
         f'<text x="{pad}" y="{pad + FONT}" fill="{t["art"]}" xml:space="preserve">']
    for i, line in enumerate(art):
        p.append(f'<tspan x="{pad}" dy="{0 if i == 0 else LH:.2f}">{escape(line) or " "}</tspan>')
    p.append("</text>")

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
