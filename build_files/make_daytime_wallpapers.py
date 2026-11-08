"""Обои «по времени суток» из точечных обоев AstraMars: утро, день, вечер, ночь.

Запуск (один раз, результат лежит в репозитории):
  python build_files/make_daytime_wallpapers.py
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "system_files", "usr", "share", "wallpapers")
SRC = os.path.join(ROOT, "AstraMarsDots", "contents", "images", "3840x2160.jpg")
DST = os.path.join(ROOT, "AstraMarsDaytime")

# свечение: (центр x, центр y в долях кадра, радиус x, радиус y, цвет RGB, сила), подъём фона, оттенок
LOOKS = {
    "morning": ((0.78, 0.62, 0.55, 0.45), (255, 150, 90), 0.55, 6, (1.04, 1.0, 0.96)),
    "day": ((0.50, 0.30, 0.90, 0.70), (150, 175, 210), 0.35, 26, (0.98, 1.0, 1.05)),
    "evening": ((0.22, 0.60, 0.60, 0.42), (255, 70, 48), 0.6, 4, (1.06, 0.98, 0.95)),
    "night": ((0.50, 0.10, 0.80, 0.50), (60, 80, 140), 0.18, 0, (0.95, 0.97, 1.05)),
}


def render(base, look):
    (cx, cy, rx, ry), color, strength, lift, tint = look
    h, w, _ = base.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((x / w - cx) / rx) ** 2 + ((y / h - cy) / ry) ** 2
    glow = np.exp(-d * 2.2)[..., None] * strength
    out = base * np.array(tint, np.float32) + lift
    out = 255 - (255 - out) * (1 - glow * np.array(color, np.float32) / 255)   # «осветление»
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    base = np.asarray(Image.open(SRC).convert("RGB"), np.float32)
    os.makedirs(DST, exist_ok=True)
    for name, look in LOOKS.items():
        img = Image.fromarray(render(base, look))
        img.save(os.path.join(DST, f"{name}.jpg"), quality=88, optimize=True, progressive=True)
        if "--preview" in sys.argv:
            img.resize((640, 360)).save(os.path.join(sys.argv[-1], f"wp-{name}.png"))
        print(name)


if __name__ == "__main__":
    main()
