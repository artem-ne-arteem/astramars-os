"""Картинки заставки загрузки (Plymouth) AstraMars из logo.png.

Запуск (нужны Pillow и шрифт Doto): python make_splash_assets.py logo.png Doto.ttf OUT_DIR
Результат лежит в system_files/usr/share/astramars/plymouth — перегенерировать только при смене логотипа.
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

logo_path, font_path, out = sys.argv[1:4]

# Логотип с краями, растворёнными в чёрном фоне заставки
LOGO = 380
logo = Image.open(logo_path).convert("RGB").resize((LOGO, LOGO), Image.LANCZOS)
mask = Image.new("L", (LOGO, LOGO), 0)
d = ImageDraw.Draw(mask)
for i in range(LOGO // 2, 0, -1):
    t = i / (LOGO / 2)
    a = 255 if t < 0.74 else int(255 * max(0.0, (1 - t) / 0.26) ** 1.3)
    d.ellipse((LOGO / 2 - i, LOGO / 2 - i, LOGO / 2 + i, LOGO / 2 + i), fill=a)
mark = Image.new("RGBA", (LOGO, LOGO))
mark.paste(logo, (0, 0), mask)

# «ASTRAMARS OS» точечным шрифтом Doto: круглые точки (Roundness=100)
font = ImageFont.truetype(font_path, 48)
font.set_variation_by_axes([100, 700])
text, spacing = "ASTRAMARS OS", 11
widths = [font.getbbox(c)[2] - font.getbbox(c)[0] if c != " " else 22 for c in text]
word = Image.new("RGBA", (sum(widths) + spacing * (len(text) - 1) + 20, 66), (0, 0, 0, 0))
wd = ImageDraw.Draw(word)
x = 10
for c, w in zip(text, widths):
    if c != " ":
        wd.text((x - font.getbbox(c)[0], 4), c, font=font, fill=(240, 240, 240, 255))
    x += w + spacing

# Водяной знак two-step: логотип, под ним надпись с красной точкой
GAP = -10
W = max(LOGO, word.width + 30) + 20
H = LOGO + GAP + word.height
wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
wm.alpha_composite(mark, ((W - LOGO) // 2, 0))
wx = (W - word.width) // 2 + 10
wm.alpha_composite(word, (wx, LOGO + GAP))
r = 6
cx, cy = wx - 14, LOGO + GAP + word.height // 2 - 2
ImageDraw.Draw(wm).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 59, 48, 255))
wm.save(f"{out}/watermark.png", optimize=True)

# Индикатор: кольцо из 12 точек, по нему бежит огонёк с затухающим хвостом
FRAMES, SIZE, SS = 36, 72, 4
for f in range(FRAMES):
    big = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    bd = ImageDraw.Draw(big)
    head = f / FRAMES * 12
    for i in range(12):
        ang = -math.pi / 2 + i / 12 * 2 * math.pi
        px = SIZE * SS / 2 + math.cos(ang) * SIZE * SS * 0.38
        py = SIZE * SS / 2 + math.sin(ang) * SIZE * SS * 0.38
        glow = max(0.0, 1 - ((head - i) % 12) / 5)
        alpha = int(255 * (0.18 + 0.82 * glow ** 1.6))
        rr = SIZE * SS * (0.045 + 0.02 * glow)
        bd.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(255, 255, 255, alpha))
    big.resize((SIZE, SIZE), Image.LANCZOS).save(f"{out}/throbber-{f + 1:04d}.png", optimize=True)

# Предпросмотр 1920×1080 (так расставит two-step: знак .5/.42, индикатор .5/.80)
if len(sys.argv) > 4:
    scr = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255))
    scr.alpha_composite(wm, (int((1920 - W) * .5), int((1080 - H) * .42)))
    th = Image.open(f"{out}/throbber-0010.png")
    scr.alpha_composite(th, (int((1920 - th.width) * .5), int((1080 - th.height) * .80)))
    scr.convert("RGB").save(sys.argv[4])
print("watermark", wm.size, "frames", FRAMES)
