"""Стиль Plasma «AstraMars»: чёрное «стекло» со скруглениями для меню и всплывающих окон.

python make_plasma_theme.py OUT_DIR
Создаёт SVG в формате Plasma: каждый элемент нарезан на 9 частей (углы, края, центр),
hint-*-margin — внутренние отступы, mask-* — форма для размытия под окном.
Рамка рисуется заливкой, а не обводкой, чтобы размеры частей были ровно целыми.
Остальные элементы стиля берутся из Breeze Dark (их копирует build_files/build.sh).
"""

import os
import sys

OUT = sys.argv[1]
PARTS = ["topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright"]
EDGE = 4  # ширина/высота частей-краёв в файле (растягиваются)


def _id(prefix, part):
    return f"{prefix}-{part}" if prefix else part


def _corner_paths(part, x, y, r, fill, fill_op, line, line_op, draw_line):
    """Угол r×r: четверть круга (заливка) и кольцевой сектор толщиной 1 (рамка)."""
    left, top = "left" in part, "top" in part
    cx = x + (r if left else 0)          # центр дуги — внутренний угол части
    cy = y + (r if top else 0)
    sx, sy = (-1 if left else 1), (-1 if top else 1)
    sweep = 1 if sx * sy > 0 else 0       # дуга выгибается наружу
    back = 1 - sweep

    def arc(rad):
        return (cx + sx * rad, cy), (cx, cy + sy * rad)

    a0, a1 = arc(r)
    out = [f'<path d="M{cx},{cy} L{a0[0]},{a0[1]} A{r},{r} 0 0 {sweep} {a1[0]},{a1[1]} Z" '
           f'fill="{fill}" fill-opacity="{fill_op}"/>']
    if draw_line:
        b0, b1 = arc(r - 1)
        out.append(f'<path d="M{a0[0]},{a0[1]} A{r},{r} 0 0 {sweep} {a1[0]},{a1[1]} '
                   f'L{b1[0]},{b1[1]} A{r - 1},{r - 1} 0 0 {back} {b0[0]},{b0[1]} Z" '
                   f'fill="{line}" fill-opacity="{line_op}"/>')
    return out


def frame(prefix, r, fill, fill_op, line=None, line_op=0.0, margin=8, edges=("top", "bottom", "left", "right"),
          mask=False, y0=0):
    edges = set(edges)
    gap = 6
    col = [0, r + gap, r + gap + EDGE + gap]
    row = [y0, y0 + r + gap, y0 + r + gap + EDGE + gap]
    size = {"topleft": (r, r), "top": (EDGE, r), "topright": (r, r),
            "left": (r, EDGE), "center": (EDGE, EDGE), "right": (r, EDGE),
            "bottomleft": (r, r), "bottom": (EDGE, r), "bottomright": (r, r)}
    pos = {p: (col[i % 3], row[i // 3]) for i, p in enumerate(PARTS)}

    def body(part, x, y, w, h, fill_color, opacity, with_line):
        paths = []
        if part in ("topleft", "topright", "bottomleft", "bottomright"):
            # Линия на угле — только если рисуются обе соседние стороны
            sides = {"top" if "top" in part else "bottom", "left" if "left" in part else "right"}
            paths += _corner_paths(part, x, y, r, fill_color, opacity, line, line_op,
                                   with_line and sides <= edges)
        else:
            paths.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill_color}" fill-opacity="{opacity}"/>')
            if with_line and part in edges:
                lx, ly, lw, lh = {"top": (x, y, w, 1), "bottom": (x, y + h - 1, w, 1),
                                  "left": (x, y, 1, h), "right": (x + w - 1, y, 1, h)}[part]
                paths.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" fill="{line}" fill-opacity="{line_op}"/>')
        # Прозрачный прямоугольник задаёт точные границы части
        paths.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#000000" fill-opacity="0"/>')
        return "".join(paths)

    out = []
    for part in PARTS:
        x, y = pos[part]
        w, h = size[part]
        out.append(f'<g id="{_id(prefix, part)}">{body(part, x, y, w, h, fill, fill_op, line is not None)}</g>')
    if mask:
        mx = col[2] + r + 20
        for part in PARTS:
            x, y = pos[part]
            w, h = size[part]
            out.append(f'<g id="{_id((prefix + "-mask") if prefix else "mask", part)}">'
                       f'{body(part, x + mx, y, w, h, "#000000", 1, False)}</g>')
    hy = row[2] + r + gap
    for i, side in enumerate(["top", "bottom", "left", "right"]):
        out.append(f'<rect id="{_id(prefix, "hint-" + side + "-margin")}" x="{i * (margin + 4)}" y="{hy}" '
                   f'width="{margin}" height="{margin}" fill="#000000" fill-opacity="0"/>')
    return "\n".join(out), hy + margin + 10


def write(path, *frames):
    body, y = [], 0
    for f in frames:
        part, y_next = f(y)
        body.append(part)
        y = y_next + 10
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{y}" viewBox="0 0 400 {y}">\n'
           + "\n".join(body) + "\n</svg>\n")
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print(path)


# Всплывающие окна (меню, календарь, трей): чёрное стекло, скругление 22, тонкая светлая рамка
write("dialogs/background.svg",
      lambda y: frame("", 22, "#0c0c0c", 0.86, "#ffffff", 0.12, margin=10, mask=True, y0=y))

# Подсветка пункта: мягкая белая плашка, как в iOS
write("widgets/viewitem.svg",
      lambda y: frame("hover", 12, "#ffffff", 0.07, margin=6, y0=y),
      lambda y: frame("selected", 12, "#ffffff", 0.13, margin=6, y0=y),
      lambda y: frame("selected+hover", 12, "#ffffff", 0.17, margin=6, y0=y))

# Шапка и низ меню: прозрачные, с одной прямой разделительной линией
write("widgets/plasmoidheading.svg",
      lambda y: frame("header", 22, "#000000", 0.0, "#ffffff", 0.09, margin=8, edges=("bottom",), y0=y),
      lambda y: frame("footer", 22, "#000000", 0.0, "#ffffff", 0.09, margin=8, edges=("top",), y0=y))

# Вкладки «Приложения | Места» в меню: активная — белая полупрозрачная плашка
write("widgets/tabbar.svg",
      lambda y: frame("north-active-tab", 10, "#ffffff", 0.12, margin=6, y0=y),
      lambda y: frame("south-active-tab", 10, "#ffffff", 0.12, margin=6, y0=y))
