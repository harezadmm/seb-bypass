#!/usr/bin/env python3
"""Buat icon aplikasi (SEB Config Bypass Studio) sebagai .icns dan .ico.

Desain: perisai (shield) dengan kunci terbuka di tengah - melambangkan
"membuka kunci config". Latar gradien gelap, aksen hijau.
"""
import math
import os
import struct
import subprocess
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("butuh pillow: pip install pillow")
    sys.exit(1)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BG_TOP = (24, 32, 48)
BG_BOT = (12, 18, 30)
ACCENT = (46, 204, 113)
ACCENT_D = (30, 150, 80)
SHIELD_HI = (58, 78, 110)
SHIELD_LO = (30, 42, 62)


def rounded_shield(size):
    """Gambar perisai dengan kunci terbuka."""
    S = size * 4  # supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # latar bulat (app icon style)
    pad = int(S * 0.06)
    r = int(S * 0.22)
    # gradien vertikal
    for y in range(pad, S - pad):
        t = (y - pad) / max(1, (S - 2 * pad))
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.line([(pad, y), (S - pad, y)], fill=c + (255,))
    # mask bulat
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, S - pad, S - pad], radius=r, fill=255)
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(bg)

    # perisai
    cx = S // 2
    top = int(S * 0.18)
    bot = int(S * 0.84)
    half = int(S * 0.30)
    shield = []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        # sisi kanan turun lalu menuju titik bawah
        y = top + (bot - top) * t
        w = half * (1 - t ** 2.2) ** 0.5 if t < 1 else 0
        shield.append((cx + w, y))
    for i in range(steps, -1, -1):
        t = i / steps
        y = top + (bot - top) * t
        w = half * (1 - t ** 2.2) ** 0.5 if t < 1 else 0
        shield.append((cx - w, y))
    # gradien perisai
    sw = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sw)
    sd.polygon(shield, fill=(255, 255, 255, 255))
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(top, bot + 1):
        t = (y - top) / max(1, (bot - top))
        c = tuple(int(SHIELD_HI[i] + (SHIELD_LO[i] - SHIELD_HI[i]) * t) for i in range(3))
        gd.line([(0, y), (S, y)], fill=c + (255,))
    bg.paste(grad, (0, 0), sw)
    d = ImageDraw.Draw(bg)
    # garis tepi perisai
    d.line(shield + [shield[0]], fill=ACCENT_D + (200,), width=max(2, S // 160))

    # gembok terbuka: badan
    bw = int(S * 0.20)
    bh = int(S * 0.17)
    bx0, by0 = cx - bw // 2, int(S * 0.50)
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=max(2, S // 90),
                        fill=ACCENT + (255,))
    # gelang (shackle) terbuka - melengkung ke kanan atas, tidak menutup
    lw = max(3, S // 70)
    rr = int(S * 0.075)
    cx2 = cx - int(S * 0.012)
    cy2 = by0 - int(S * 0.055)
    d.arc([cx2 - rr, cy2 - rr, cx2 + rr, cy2 + rr], start=180, end=340,
          fill=ACCENT + (255,), width=lw)
    # batang keluar (kunci terbuka = tidak terkunci)
    d.line([(cx2 + rr * math.cos(math.radians(-20)), cy2 + rr * math.sin(math.radians(-20))),
            (cx2 + rr * 1.0, by0 - int(S * 0.005))], fill=ACCENT + (255,), width=lw)
    # lubang kunci
    d.ellipse([cx - int(S * 0.022), by0 + int(S * 0.045),
               cx + int(S * 0.022), by0 + int(S * 0.089)], fill=BG_TOP + (255,))
    d.line([(cx, by0 + int(S * 0.085)), (cx, by0 + int(S * 0.125))],
           fill=BG_TOP + (255,), width=max(2, S // 110))

    return bg.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    pngs = {}
    for s in sizes:
        im = rounded_shield(s)
        p = os.path.join(OUT_DIR, "icon_%d.png" % s)
        im.save(p, "PNG")
        pngs[s] = p
    # icon utama
    rounded_shield(512).save(os.path.join(OUT_DIR, "icon.png"), "PNG")

    # ---- .icns (macOS) ----
    iconset = os.path.join(OUT_DIR, "sebstudio.iconset")
    os.makedirs(iconset, exist_ok=True)
    mapping = [(16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
               (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
               (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
               (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
               (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png")]
    for s, name in mapping:
        rounded_shield(s).save(os.path.join(iconset, name), "PNG")
    icns = os.path.join(OUT_DIR, "sebstudio.icns")
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns], check=True)
        print("icns OK:", os.path.getsize(icns), "byte")
    except Exception as e:
        print("iconutil gagal:", e)

    # ---- .ico (Windows) ----
    ico = os.path.join(OUT_DIR, "sebstudio.ico")
    imgs = [rounded_shield(s) for s in (16, 24, 32, 48, 64, 128, 256)]
    imgs[0].save(ico, format="ICO",
                 sizes=[(i.width, i.height) for i in imgs],
                 append_images=imgs[1:])
    print("ico OK:", os.path.getsize(ico), "byte")

    for s, p in pngs.items():
        os.remove(p)
    print("selesai")


main()
