#!/usr/bin/env python3
"""
Обложки для актуальных в Instagram: тонкая линейная иконка по центру
на однотонном фоне. Размер 1080x1920 (загружается как сторис), иконка
вписана в центральный круг, который Instagram показывает в кружке актуального.

Запуск: python3 make_highlights.py
На выходе: output/<тема>/<вкладка>.png и preview_<тема>.png
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
W, H = 1080, 1920
SS = 4                      # суперсэмплинг для гладких линий
ICON = 440                  # размер иконки, px
STROKE = 14                 # толщина линии, px

THEMES = {
    "bordo": {"bg": "#6E1F2A", "line": "#F3E6D3"},
    "cream": {"bg": "#F3E6D3", "line": "#6E1F2A"},
}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Pen:
    """Рисует в координатах иконки 0..1, центр иконки в центре кадра."""

    def __init__(self, draw, color):
        self.d = draw
        self.c = color
        self.w = STROKE * SS
        self.s = ICON * SS
        self.ox = (W * SS - self.s) / 2
        self.oy = (H * SS - self.s) / 2

    def p(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def dot(self, x, y, r=None):
        r = r or self.w / 2
        cx, cy = self.p(x, y)
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self.c)

    def line(self, pts, closed=False):
        pts = [self.p(x, y) for x, y in pts]
        if closed:
            pts = pts + [pts[0]]
        self.d.line(pts, fill=self.c, width=self.w, joint="curve")
        for x, y in (pts[0], pts[-1]):   # скруглённые концы
            r = self.w / 2
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=self.c)

    def arc_pts(self, cx, cy, r, a0, a1, n=60, ry=None):
        ry = ry if ry is not None else r
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                 cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
                for i in range(n + 1)]


def hanger(pen):
    # крючок: дуга сверху, уходящая вниз к вершине
    hook = pen.arc_pts(0.5, 0.28, 0.075, 180, 450)
    pen.line(hook + [(0.5, 0.44)])
    # плечики и перекладина
    pen.line([(0.5, 0.44), (0.04, 0.80), (0.96, 0.80)], closed=True)


def bubble(pen):
    # облачко: скруглённый прямоугольник + хвостик
    x0, y0, x1, y1, r = 0.06, 0.14, 0.94, 0.72, 0.12
    pts = []
    pts += pen.arc_pts(x1 - r, y0 + r, r, 270, 360, 15)
    pts += pen.arc_pts(x1 - r, y1 - r, r, 0, 90, 15)
    pts += [(0.42, y1), (0.26, 0.88), (0.28, y1)]
    pts += pen.arc_pts(x0 + r, y1 - r, r, 90, 180, 15)
    pts += pen.arc_pts(x0 + r, y0 + r, r, 180, 270, 15)
    pen.line(pts, closed=True)
    for x in (0.32, 0.5, 0.68):
        pen.dot(x, 0.43, r=STROKE * SS * 1.1)


def dress(pen):
    # платье: бретели, лиф, талия, расклёшенная юбка
    pts = [
        (0.40, 0.04), (0.40, 0.18),          # левая бретель
        (0.34, 0.30), (0.40, 0.44),          # лиф слева до талии
        (0.18, 0.94),                        # юбка слева
        (0.82, 0.94),                        # подол
        (0.60, 0.44),                        # юбка справа до талии
        (0.66, 0.30), (0.60, 0.18),          # лиф справа
        (0.60, 0.04),                        # правая бретель
    ]
    pen.line(pts)
    # вырез между бретелями
    pen.line(pen.arc_pts(0.5, 0.18, 0.10, 180, 0, 30, ry=0.07))
    pen.line([(0.40, 0.44), (0.60, 0.44)])  # пояс


def heart(pen):
    pts = []
    for i in range(241):
        t = 2 * math.pi * i / 240
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.5 + x / 36, 0.47 - y / 36))
    pen.line(pts, closed=True)


TABS = [("01_uslugi", "Услуги", hanger), ("02_otzyvy", "Отзывы", bubble),
        ("03_keisy", "Кейсы", dress), ("04_obo_mne", "Обо мне", heart)]


def render(theme, draw_fn):
    img = Image.new("RGB", (W * SS, H * SS), rgb(theme["bg"]))
    draw_fn(Pen(ImageDraw.Draw(img), rgb(theme["line"])))
    return img.resize((W, H), Image.LANCZOS)


def preview(images, bg):
    """Как это выглядит в профиле: кружки 220px в ряд."""
    d = 220
    pad = 40
    sheet = Image.new("RGB", (pad + len(images) * (d + pad), d + 2 * pad), (255, 255, 255))
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    for i, im in enumerate(images):
        top = (H - W) // 2
        c = im.crop((0, top, W, top + W)).resize((d, d), Image.LANCZOS)
        x = pad + i * (d + pad)
        ring = ImageDraw.Draw(sheet)
        ring.ellipse([x - 8, pad - 8, x + d + 8, pad + d + 8], outline=(210, 205, 200), width=3)
        sheet.paste(c, (x, pad), mask)
    return sheet


def main():
    for tname, theme in THEMES.items():
        out = ROOT / "output" / tname
        out.mkdir(parents=True, exist_ok=True)
        imgs = []
        for fname, _, fn in TABS:
            im = render(theme, fn)
            im.save(out / f"{fname}.png")
            imgs.append(im)
        preview(imgs, theme["bg"]).save(ROOT / f"preview_{tname}.png")
        print("OK", tname)


if __name__ == "__main__":
    main()
