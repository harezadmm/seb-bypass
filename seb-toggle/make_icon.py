#!/usr/bin/env python3
"""Generate seb.ico (Windows) and icons/ (macOS iconset source).

Motif: a toggle switch. It reads at 16px, unlike a padlock glyph.
Run from this folder: python make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
BG = (22, 35, 46, 255)
TRACK = (46, 74, 99, 255)
TRACK_DIM = (38, 58, 78, 255)
KNOB = (255, 255, 255, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
m = int(S * 0.06)
d.rounded_rectangle([m, m, S - m, S - m], radius=int(S * 0.22), fill=BG)

tx0, ty0 = int(S * 0.16), int(S * 0.40)
tx1, ty1 = int(S * 0.84), int(S * 0.60)
r = (ty1 - ty0) // 2
d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=r, fill=TRACK_DIM)
# the lit segment sits under the knob, which is where a switch reads as ON
half = tx0 + int((tx1 - tx0) * 0.48)
d.rounded_rectangle([half, ty0, tx1, ty1], radius=r, fill=TRACK)

kcx = tx1 - r
d.ellipse([kcx - r, ty0, kcx + r, ty1], fill=KNOB)

ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("seb.ico", sizes=ico_sizes)
print("wrote seb.ico", ico_sizes)

iconset = Path("icons")
iconset.mkdir(exist_ok=True)
for px in (16, 32, 64, 128, 256, 512, 1024):
    img.resize((px, px), Image.LANCZOS).save(iconset / ("icon_%dx%d.png" % (px, px)))
    if px <= 512:
        img.resize((px * 2, px * 2), Image.LANCZOS).save(
            iconset / ("icon_%dx%d@2x.png" % (px, px)))
print("wrote icons/", len(list(iconset.glob('*.png'))), "png")
