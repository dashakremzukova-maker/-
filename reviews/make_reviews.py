#!/usr/bin/env python3
"""
Карусель «Отзывы» (пост Instagram 1080x1350), оформление как у сторис об услугах:
заголовки Yeseva One, текст Raleway, палитра крем / бордо.

Скриншоты одного отзыва склеиваются в одну ленту (без повторяющихся строк
и без кнопки-стрелки Telegram), обрезаются по белому «облачку» сообщения и
режутся на слайды по пробелам между строками, чтобы текст читался с телефона.

Запуск: python3 -I make_reviews.py
На выходе: output/02_*.jpg ... (01 — обложка-видео, её делает make_cover_video.py)
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
FONTS = ROOT.parent / "stories" / "fonts"
OUT = ROOT / "output"

W, H = 1080, 1350
BG = (244, 239, 232)        # светлый крем, как на светлых слайдах услуг
TEXT = (26, 22, 19)
ACCENT = (139, 42, 34)      # бордо
MUTED = (120, 108, 100)

BUBBLE_X = (31, 1071)       # белое облачко сообщения на скриншотах
CARD_W = 940
CARD_PAD = 44
IMG_W = CARD_W - 2 * CARD_PAD
SCALE = IMG_W / (BUBBLE_X[1] - BUBBLE_X[0])
MAX_PART = int(960 / SCALE)  # сколько строк скриншота помещается на слайд

# кнопка «вниз» Telegram поверх текста: закрашиваем белым
CHEVRONS = {
    "vedenie_1": (1012, 1735, 1206, 1865),
    "vedenie_2": (900, 1665, 1206, 1795),
    "shopping_2": (880, 1650, 1206, 1745),
}

# отзывы: (подпись, [(файл, с какой строки, по какую)])
# стыки найдены сравнением строк: начало следующего скриншота совпадает
# с этой строкой предыдущего
REVIEWS = [
    ("Ведение 3 месяца", [("vedenie_1", "skip_partial", 1831), ("vedenie_2", 0, "text_end")]),
    ("Шопинг-сопровождение", [("shopping_1", "skip_partial", 1687), ("shopping_2", 0, None),
                              ("shopping_3", "skip_partial", "text_end")]),
]

# эмодзи в тексте — единственное цветное, что надо сохранить
KEEP_COLOR = {"vedenie_1": (30, 1060, 130, 1145)}


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def load(name):
    im = Image.open(SRC / f"{name}.jpg").convert("RGB")
    if name in CHEVRONS:
        ImageDraw.Draw(im).rectangle(CHEVRONS[name], fill=(255, 255, 255))
    # убираем цветной фон Telegram по краям облачка и светлые тени:
    # цветные и почти белые пиксели -> белые (текст чёрный, его это не задевает)
    a = np.asarray(im).astype(int)
    sat = a.max(2) - a.min(2)
    clean = (sat > 10) | (a.min(2) > 238)
    if name in KEEP_COLOR:
        x0, y0, x1, y1 = KEEP_COLOR[name]
        clean[y0:y1, x0:x1] = False
    a[clean] = 255
    return Image.fromarray(a.astype("uint8"))


def is_blank(a, y):
    return a[y, 40:1060].min() > 225


def first_full_line_start(im):
    """Пропускает край облачка или обрывок строки в самом верху скриншота."""
    a = np.asarray(im.convert("L"))
    marks = [y for y in range(40) if not is_blank(a, y)]
    if not marks:
        return 0
    y = marks[0]
    while not is_blank(a, y):
        y += 1
    return y


def last_text_line_end(im):
    """Низ последней строки текста: отрезает край облачка под ней."""
    a = np.asarray(im.convert("L"))
    ys = [y for y in range(im.height) if a[y, 40:1000].min() < 100]
    return min(im.height, ys[-1] + 8)


def remove_grey(im, y0, y1):
    """Стирает серые элементы Telegram (время сообщения, край облачка) в полосе строк.
    Чёрный текст не трогаем: серые пиксели рядом с чёрными — его сглаживание."""
    a = np.asarray(im).astype(int)
    lum = a.min(2)
    band = lum[y0:y1]
    dark = band < 60
    near = np.zeros_like(dark)
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            near |= np.roll(np.roll(dark, dy, 0), dx, 1)
    grey = (band >= 60) & (band < 255) & ~near
    a[y0:y1][grey] = 255
    return Image.fromarray(a.astype("uint8"))


def whiten_above_text(im):
    """Верхний край облачка (серая полоса) до первой строки текста -> белый."""
    a = np.asarray(im).astype(int)
    lum = a.min(2)
    first = next(y for y in range(im.height) if lum[y, 40:1000].min() < 150)
    a[:max(0, first - 2)] = 255
    return Image.fromarray(a.astype("uint8"))


def stitch(parts):
    pieces = []
    for name, top, bottom in parts:
        im = load(name)
        if top == "skip_partial":
            top = first_full_line_start(im)
        if bottom == "text_end":
            bottom = last_text_line_end(im)
        piece = im.crop((BUBBLE_X[0], top, BUBBLE_X[1], bottom or im.height))
        if not pieces:
            piece = remove_grey(whiten_above_text(piece), 0, 90)
        pieces.append(piece)
    last = pieces[-1]
    pieces[-1] = remove_grey(last, last.height - 80, last.height)
    out = Image.new("RGB", (pieces[0].width, sum(p.height for p in pieces)), "white")
    y = 0
    for p in pieces:
        out.paste(p, (0, y))
        y += p.height
    return out


def split(strip):
    """Режет ленту на равные части по пустым строкам между строками текста."""
    a = np.asarray(strip.convert("L"))
    h = strip.height
    n = -(-h // MAX_PART)
    blank = [y for y in range(h) if a[y, 20:1020].min() > 225]
    cuts = [0]
    for i in range(1, n):
        target = h * i // n
        cuts.append(min(blank, key=lambda y: abs(y - target)))
    cuts.append(h)
    return [strip.crop((0, cuts[i], strip.width, cuts[i + 1])) for i in range(n)]


def shadow(size, radius, blur=28, alpha=60):
    w, h = size
    pad = blur * 3
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(m).rounded_rectangle([pad, pad + 14, pad + w, pad + h + 14], radius, fill=alpha)
    return m.filter(ImageFilter.GaussianBlur(blur)), pad


def slide(part, label, idx, total, first, last_of_all):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # шапка: тема отзыва + номер части
    x0 = (W - CARD_W) // 2
    fl = font("YesevaOne-400.ttf", 40)
    d.text((x0, 70), label.upper(), font=fl, fill=ACCENT)
    if total > 1:
        fn = font("Raleway-400.ttf", 30)
        t = f"{idx}/{total}"
        d.text((x0 + CARD_W - fn.getlength(t), 80), t, font=fn, fill=MUTED)

    # карточка со скриншотом
    shot = part.resize((IMG_W, round(part.height * SCALE)), Image.LANCZOS)
    card_h = shot.height + 2 * CARD_PAD
    top = 150 + (H - 150 - 110 - card_h) // 2
    sh, pad = shadow((CARD_W, card_h), 36)
    img.paste((60, 40, 30), (x0 - pad, top - pad), sh)
    card = Image.new("RGB", (CARD_W, card_h), "white")
    mask = Image.new("L", (CARD_W, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W - 1, card_h - 1], 36, fill=255)
    card.paste(shot, (CARD_PAD, CARD_PAD))
    img.paste(card, (x0, top), mask)

    # большая кавычка на первой части отзыва
    if first:
        fq = font("YesevaOne-400.ttf", 190)
        d.text((x0 - 10, top - 95), "\u201c", font=fq, fill=ACCENT)

    # подвал
    ff = font("Raleway-400.ttf", 30)
    if last_of_all:
        t = "Хочешь так же? Напиши в директ слово СТИЛЬ"
        fb = font("Raleway-600.ttf", 30)
        d.text(((W - fb.getlength(t)) // 2, H - 82), t, font=fb, fill=ACCENT)
    else:
        t = "листай"
        x = x0 + CARD_W - ff.getlength(t + "  ") - 30
        d.text((x, H - 82), t, font=ff, fill=MUTED)
        fa = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        d.text((x + ff.getlength(t + " "), H - 80), "→", font=fa, fill=MUTED)
    return img


def main():
    OUT.mkdir(exist_ok=True)
    n = 2
    all_parts = []
    for label, parts in REVIEWS:
        chunks = split(stitch(parts))
        for i, c in enumerate(chunks, 1):
            all_parts.append((label, c, i, len(chunks)))
    for k, (label, c, i, total) in enumerate(all_parts):
        im = slide(c, label, i, total, first=(i == 1), last_of_all=(k == len(all_parts) - 1))
        p = OUT / f"{n:02d}_otzyv.jpg"
        im.save(p, quality=93)
        print("OK", p.name, label, f"{i}/{total}")
        n += 1


if __name__ == "__main__":
    main()
