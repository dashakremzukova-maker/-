#!/usr/bin/env python3
"""
Подбор цвета надписей для карусели «Новинки недели» (стиль «Минимал»).
Каждая палитра — основной цвет текста и акцент (подписи «ОБРАЗ 0N»,
«АРТИКУЛЫ В ДИРЕКТ», «7 ОБРАЗОВ»). Показаны обложка, слайд «Мини»
и последний слайд с призывом.

Запуск: python3 -I colors.py
На выходе: colors/colors.jpg
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import make_novinki as mk  # noqa: E402

OUT = ROOT / "colors"

PALETTES = [
    ("1. Белый + персик (сейчас)", (255, 255, 255), (240, 201, 168)),
    ("2. Молочный + карамель", (243, 235, 227), (201, 160, 115)),
    ("3. Шампань + золото", (236, 222, 196), (214, 182, 120)),
    ("4. Белый монохром", (255, 255, 255), (190, 186, 180)),
    ("5. Белый + пудровый розовый", (255, 255, 255), (232, 180, 184)),
    ("6. Белый + винный", (255, 255, 255), (200, 92, 100)),
]


def main():
    OUT.mkdir(exist_ok=True)
    cover_src = mk.load("photo")
    looks = {fn: (name, phrase, opt) for fn, name, phrase, *opt in mk.LOOKS}
    # крупные фрагменты с текстом: низ обложки, низ слайда «Мини», низ последнего
    cw, ch = 400, 250
    sw = 46
    gap = 12
    row_h = 40 + ch
    sheet = Image.new("RGB", (28 + 3 * (cw + gap) + 28, 24 + len(PALETTES) * (row_h + 24)), (243, 235, 227))
    d = ImageDraw.Draw(sheet)
    f_lab = ImageFont.truetype(str(mk.FONTS / "Manrope-700.ttf"), 24)

    for i, (label, main_c, accent) in enumerate(PALETTES):
        mk.MAIN, mk.ACCENT = main_c, accent
        cover = mk.cover_frame(cover_src)(3.0).convert("RGB")
        n, p, o = looks["look_04"]
        mid = mk.look_slide(mk.load("look_04"), "04", n, p, False, *o)
        n, p, o = looks["look_07"]
        last = mk.look_slide(mk.load("look_07"), "07", n, p, True, *o)
        mid.save(OUT / f"{i + 1}_slide.jpg", quality=92)
        last.save(OUT / f"{i + 1}_last.jpg", quality=92)

        y = 24 + i * (row_h + 24)
        d.text((28, y + 4), label, font=f_lab, fill=(60, 40, 35))
        lx = 28 + f_lab.getlength(label) + 20
        for k, c in enumerate([main_c, accent]):
            d.ellipse([lx + k * (sw - 14), y, lx + k * (sw - 14) + 32, y + 32], fill=c, outline=(60, 40, 35))
        crops = [cover.crop((90, 840, 990, 1190)), mid.crop((0, 990, 1080, 1350)), last.crop((0, 900, 1080, 1350))]
        for k, im in enumerate(crops):
            im = im.resize((cw, int(cw * im.height / im.width)), Image.LANCZOS)
            im = im.crop((0, 0, cw, min(ch, im.height)))
            sheet.paste(im, (28 + k * (cw + gap), y + 40))
        print("готово:", label)
    sheet.save(OUT / "colors.jpg", quality=92)


if __name__ == "__main__":
    main()
