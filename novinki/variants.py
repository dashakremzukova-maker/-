#!/usr/bin/env python3
"""
Варианты надписей для карусели «Новинки недели»: шесть стилей, у каждого
своя пара шрифтов и своя подача текста. Каждый стиль показан на обложке
и на слайде с образом «Мини» (с призывом написать за артикулами).

Запуск: python3 -I variants.py
На выходе: variants/<стиль>_cover.jpg, variants/<стиль>_slide.jpg, variants/variants.jpg
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import make_novinki as mk  # noqa: E402

W, H, M = mk.W, mk.H, mk.MARGIN
WHITE, PEACH, BORDO = mk.WHITE, mk.PEACH, mk.BORDO
OUT = ROOT / "variants"


def font(name, size, wght=None):
    f = ImageFont.truetype(str(mk.FONTS / name), size)
    if wght:
        f.set_variation_by_axes([wght])
    return f


def put(img, s, f, y, color=WHITE, x=None, track=0, anchor_right=False):
    """Текст по центру (x=None), слева от x или (anchor_right) справа до x."""
    w = mk.spaced_width(s, f, track) if track else f.getlength(s)
    if x is None:
        x = (W - w) / 2
    elif anchor_right:
        x = x - w
    d = ImageDraw.Draw(img)
    if track:
        mk.draw_spaced(d, s, f, x, y, track, (*color, 255))
    else:
        d.text((x, y), s, font=f, fill=(*color, 255))
    return w


def lines(img, ss, f, y, lh, color=WHITE, x=None):
    for i, s in enumerate(ss):
        put(img, s, f, y + i * lh, color, x)


def cover_base():
    img = mk.crop45(mk.load("photo"), 0.0)
    img.alpha_composite(mk.gradient(solid=900, fadelen=520))
    return img


def slide_base(solid=1090, fadelen=320):
    img = mk.full_look(mk.load("look_04"))
    img.alpha_composite(mk.gradient(solid=solid, fadelen=fadelen))
    return img


NOTE = ("Строгий жакет, мини и грубые челси: смешение стилей — главный "
        "приём сезона.")
ASK = "Артикулы — в директ по слову «ХОЧУ»"
ASK_Y = 1272


# ---------- 1. Классика: Yeseva One + Raleway (как сейчас) ----------

def v1():
    c = cover_base()
    mk.title(c, "НОВИНКИ", mk.F_TITLE, 780, 1, 1)
    mk.title(c, "НЕДЕЛИ", mk.F_TITLE, 890, 1, 0)
    lines(c, ["7 образов из примерочной", "от камуфляжа до меха"], mk.F_TEXT, 1030, 54)

    s = slide_base()
    f_note = mk.F_NOTE
    note = mk.wrap(NOTE, f_note, W - 2 * M)
    ny = H - 130 - len(note) * 44
    put(s, "04", mk.F_NUM_S, ny - 182, PEACH, M)
    nx = M + mk.F_NUM_S.getlength("04") + 30
    put(s, "МИНИ", mk.F_TITLE_S, ny - 148, WHITE, nx, track=10)
    put(s, "бордовая, к тому же жакету", mk.F_TEXT_B, ny - 64, PEACH, nx)
    lines(s, note, f_note, ny, 44, x=M)
    put(s, ASK, mk.F_TEXT_B, ASK_Y, PEACH)
    return c, s


# ---------- 2. Журнал: Playfair Display + курсив Cormorant + Montserrat ----------

def v2():
    f_big = font("PlayfairDisplay-700.ttf", 120)
    f_it = font("CormorantGaramond-Italic-VF.ttf", 92, 500)
    f_txt = font("Montserrat-400.ttf", 30)
    f_cap = font("Montserrat-600.ttf", 24)

    c = cover_base()
    put(c, "Новинки", f_big, 760)
    put(c, "этой недели", f_it, 895, PEACH)
    put(c, "7 ОБРАЗОВ ИЗ ПРИМЕРОЧНОЙ", f_cap, 1060, track=6)

    s = slide_base()
    put(s, "Бордо — новый чёрный", f_it, 940, PEACH, M)
    put(s, "Мини к жакету сафари", font("PlayfairDisplay-700.ttf", 64), 1050, WHITE, M)
    lines(s, mk.wrap(NOTE, f_txt, W - 2 * M), f_txt, 1145, 42, x=M)
    put(s, "АРТИКУЛЫ — В ДИРЕКТ ПО СЛОВУ «ХОЧУ»", f_cap, ASK_Y + 8, PEACH, track=4)
    return c, s


# ---------- 3. Рукописный акцент: Marck Script + Tenor Sans + Jost ----------

def v3():
    f_hand = font("MarckScript-Regular.ttf", 170)
    f_caps = font("TenorSans-400.ttf", 46)
    f_txt = font("Jost-400.ttf", 34)

    c = cover_base()
    put(c, "НОВИНКИ НЕДЕЛИ", f_caps, 950, track=12)
    put(c, "new in", f_hand, 760, PEACH)
    put(c, "7 образов из примерочной", f_txt, 1040)

    s = slide_base()
    put(s, "бордо", f_hand, 830, PEACH, M - 6)
    put(s, "МИНИ + ЖАКЕТ САФАРИ", f_caps, 1060, WHITE, M, track=6)
    lines(s, mk.wrap(NOTE, f_txt, W - 2 * M), f_txt, 1130, 44, x=M)
    put(s, ASK, f_txt, ASK_Y, PEACH)
    return c, s


# ---------- 4. Минимал: Tenor Sans + Jost, короткий текст ----------

def v4():
    f_caps = font("TenorSans-400.ttf", 64)
    f_small = font("TenorSans-400.ttf", 26)
    f_txt = font("Jost-400.ttf", 36)

    c = cover_base()
    put(c, "НОВИНКИ", f_caps, 880, track=22)
    put(c, "НЕДЕЛИ", f_caps, 970, track=22)
    d = ImageDraw.Draw(c)
    d.line([(W / 2 - 40, 1085), (W / 2 + 40, 1085)], fill=(*PEACH, 255), width=2)
    put(c, "7 ОБРАЗОВ", f_small, 1115, PEACH, track=10)

    s = slide_base(solid=1180, fadelen=300)
    put(s, "ОБРАЗ 04", f_small, 1040, PEACH, M, track=10)
    put(s, "МИНИ К ЖАКЕТУ", f_caps, 1080, WHITE, M, track=12)
    put(s, "Смешение стилей — главный приём сезона.", f_txt, 1180, WHITE, M)
    put(s, "АРТИКУЛЫ В ДИРЕКТ · «ХОЧУ»", f_small, ASK_Y + 6, PEACH, M, track=8)
    return c, s


# ---------- 5. Смелый: Unbounded + Manrope, плашка ----------

def v5():
    f_bold = font("Unbounded-VF.ttf", 104, 800)
    f_mid = font("Unbounded-VF.ttf", 60, 700)
    f_tag = font("Manrope-700.ttf", 26)
    f_txt = font("Manrope-400.ttf", 32)

    def tag(img, s, x, y, center=False):
        tw = mk.spaced_width(s, f_tag, 4)
        if center:
            x = (W - tw - 36) / 2
        ImageDraw.Draw(img).rounded_rectangle([x, y, x + tw + 36, y + 50], 25, fill=(*PEACH, 255))
        mk.draw_spaced(ImageDraw.Draw(img), s, f_tag, x + 18, y + 9, 4, (*mk.OVERLAY, 255))

    c = cover_base()
    tag(c, "ТРЕНДЫ ОСЕНИ", 0, 740, center=True)
    put(c, "НОВИНКИ", f_bold, 820)
    put(c, "НЕДЕЛИ", f_bold, 940, PEACH)
    put(c, "7 образов из примерочной", f_txt, 1090)

    s = slide_base()
    tag(s, "СМЕШЕНИЕ СТИЛЕЙ", M, 955)
    put(s, "МИНИ + САФАРИ", f_mid, 1030, WHITE, M)
    lines(s, mk.wrap(NOTE, f_txt, W - 2 * M), f_txt, 1125, 42, x=M)
    tag(s, "АРТИКУЛЫ В ДИРЕКТ → «ХОЧУ»", M, ASK_Y - 6)
    return c, s


# ---------- 6. Элегант: Cormorant Garamond + Manrope, по центру ----------

def v6():
    f_big = font("CormorantGaramond-SemiBold.ttf", 128)
    f_it = font("CormorantGaramond-Italic-VF.ttf", 54, 500)
    f_cap = font("Manrope-400.ttf", 24)
    f_txt = font("Manrope-400.ttf", 32)

    c = cover_base()
    put(c, "Новинки недели", f_big, 820)
    put(c, "семь образов из примерочной", f_it, 980, PEACH)
    put(c, "ОСЕНЬ · 2026", f_cap, 1080, track=8)

    s = slide_base()
    put(s, "N° 04", f_cap, 930, PEACH, track=8)
    put(s, "Бордовое мини", font("CormorantGaramond-SemiBold.ttf", 96), 960)
    put(s, "к молочному жакету сафари", f_it, 1075, PEACH)
    put(s, "Смешение стилей — главный приём сезона.", f_txt, 1180)
    put(s, "артикулы — в директ по слову «хочу»", f_it, ASK_Y - 14, PEACH)
    return c, s


VARIANTS = [
    ("1_klassika", "1. Классика · Yeseva One + Raleway", v1),
    ("2_zhurnal", "2. Журнал · Playfair + Cormorant курсив", v2),
    ("3_rukopis", "3. Рукописный · Marck Script + Tenor Sans", v3),
    ("4_minimal", "4. Минимал · Tenor Sans + Jost", v4),
    ("5_smelyi", "5. Смелый · Unbounded + Manrope", v5),
    ("6_elegant", "6. Элегант · Cormorant Garamond + Manrope", v6),
]


def main():
    OUT.mkdir(exist_ok=True)
    tw, th, gap, lab = 300, 375, 14, 44
    sheet = Image.new("RGB", (3 * (2 * tw + gap) + 4 * 28, 2 * (th + lab) + 3 * 24), (243, 235, 227))
    d = ImageDraw.Draw(sheet)
    f_lab = font("Manrope-700.ttf", 22)
    for i, (slug, label, fn) in enumerate(VARIANTS):
        c, s = fn()
        c.convert("RGB").save(OUT / f"{slug}_cover.jpg", quality=92)
        s.convert("RGB").save(OUT / f"{slug}_slide.jpg", quality=92)
        col, row = i % 3, i // 3
        x = 28 + col * (2 * tw + gap + 28)
        y = 24 + row * (th + lab + 24)
        d.text((x, y), label, font=f_lab, fill=(60, 40, 35))
        sheet.paste(c.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y + lab))
        sheet.paste(s.convert("RGB").resize((tw, th), Image.LANCZOS), (x + tw + gap, y + lab))
        print("готово:", slug)
    sheet.save(OUT / "variants.jpg", quality=90)


if __name__ == "__main__":
    main()
