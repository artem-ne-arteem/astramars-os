"""Оформление установщика (Anaconda) для ISO AstraMars: содержимое product.img.

Anaconda при загрузке распаковывает images/product.img из ISO поверх своей системы:
  /.buildstamp                               — название продукта («ДОБРО ПОЖАЛОВАТЬ В ASTRAMARS OS»)
  /etc/anaconda/conf.d/90-astramars.conf     — подключает наш CSS вместо стиля Fedora
  /usr/share/anaconda/pixmaps/astramars/…    — CSS и картинки: чёрная боковая панель с точками,
                                               логотип, надпись ASTRAMARS точками, красный акцент

Запуск (результат лежит в репозитории, ISO-сборка упаковывает его в product.img):
  python build_files/make_installer_branding.py [папка-для-предпросмотра]
"""

import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "installer", "product")
PIX = os.path.join(OUT, "usr", "share", "anaconda", "pixmaps", "astramars")
LOGO = os.path.join(ROOT, "system_files", "usr", "share", "astramars", "branding", "about-logo.png")
ACCENT = (255, 59, 48)

# Точечный шрифт 5×7 для надписи (только нужные буквы)
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    " ": ["00000"] * 7,
}


def dots_text(text, pitch, radius, color=(255, 255, 255, 255)):
    cols = sum(6 for _ in text) - 1
    w, h = round(cols * pitch + radius * 2), round(7 * pitch - pitch + radius * 2)
    img = Image.new("RGBA", (w * 4 + 4, h * 4 + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = 0
    for ch in text:
        for y, row in enumerate(FONT[ch]):
            for x, bit in enumerate(row):
                if bit == "1":
                    cx, cy = (x0 + x) * pitch + radius, y * pitch + radius
                    d.ellipse([(cx - radius) * 4, (cy - radius) * 4, (cx + radius) * 4, (cy + radius) * 4], fill=color)
        x0 += 6
    return img.resize((w, h), Image.LANCZOS)


def dot_field(w, h, pitch, fade_from_bottom=True, max_alpha=70):
    """Чёрный фон с сеткой точек, которая плавно проявляется к низу (как дюны на обоях)."""
    img = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(pitch // 2, h, pitch):
        k = (y / h) if fade_from_bottom else 1 - y / h
        a = int(max_alpha * max(0.0, k) ** 1.6)
        if a < 4:
            continue
        for x in range(pitch // 2, w, pitch):
            d.ellipse([(x - 1.2) * 2, (y - 1.2) * 2, (x + 1.2) * 2, (y + 1.2) * 2], fill=(255, 255, 255, a))
    return img.resize((w, h), Image.LANCZOS)


def main():
    os.makedirs(PIX, exist_ok=True)

    # Боковая панель (видна левая часть, ~200 px): точки снизу и красная точка
    side = dot_field(657, 500, 14)
    side.save(os.path.join(PIX, "sidebar-bg.png"), optimize=True)

    # Логотип сверху боковой панели
    logo = Image.open(LOGO).convert("RGBA").resize((104, 104), Image.LANCZOS)
    logo.save(os.path.join(PIX, "sidebar-logo.png"), optimize=True)

    # Надпись ASTRAMARS точками под логотипом, ниже — маленькая «OS» с красной точкой
    word = dots_text("ASTRAMARS", 3.5, 1.45)
    os_word = dots_text("OS", 3.5, 1.45, (170, 170, 170, 255))
    prod = Image.new("RGBA", (max(word.width, 150), word.height + os_word.height + 10), (0, 0, 0, 0))
    prod.alpha_composite(word, (0, 0))
    prod.alpha_composite(os_word, (0, word.height + 10))
    ImageDraw.Draw(prod).ellipse([os_word.width + 6, word.height + 10 + os_word.height // 2 - 3,
                                  os_word.width + 12, word.height + 10 + os_word.height // 2 + 3], fill=ACCENT + (255,))
    prod.save(os.path.join(PIX, "product-logo.png"), optimize=True)

    # Верхняя полоса в окнах шагов: чёрная с редкими точками справа
    top = Image.new("RGBA", (657, 497), (0, 0, 0, 255))
    d = ImageDraw.Draw(top)
    for y in range(7, 120, 12):
        for x in range(400, 657, 12):
            a = int(60 * ((x - 400) / 257) ** 1.5)
            if a > 4:
                d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, a))
    top.save(os.path.join(PIX, "topbar-bg.png"), optimize=True)

    if len(sys.argv) > 1:
        # Предпросмотр боковой панели так, как её рисует CSS ниже
        prev = Image.new("RGBA", (220, 500), (0, 0, 0, 255))
        prev.alpha_composite(side.crop((0, 0, 220, 500)))
        prev.alpha_composite(logo, ((220 - 104) // 2, 24))
        prev.alpha_composite(prod, (22, 150))
        prev.convert("RGB").save(os.path.join(sys.argv[1], "installer-sidebar.png"))
    print("ok:", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
