#!/usr/bin/env python3
"""
Собирает сторис 1080x1920 из фото и текстов (stories.json).

Шрифты на всех слайдах одни: заголовки Yeseva One, текст Montserrat. Цвета задаются
индивидуально для каждого слайда в stories.json:
  text     — основной цвет текста
  accent   — цвет заголовка, **выделений** и цены
  overlay  — цвет подложки-градиента под текстом
  alpha    — плотность подложки (0-255)
  placement — "top" | "bottom": у какого края стоит текст
  focus_x / focus_y — какую часть фото оставить при кропе (0..1)

Разметка строк в "lines":
  "# текст"  — заголовок (капс)
  "- текст"  — пункт списка с точкой
  "> текст"  — пункт со стрелкой
  "$ текст"  — строка цены (крупнее, цветом accent)
  "~ текст"  — мелкая строка
  ""         — пустая строка (отступ)
  **слово**  — выделение жирным цветом accent

Запуск: python3 make_stories.py [номер_слайда ...]
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
W, H = 1080, 1920
MARGIN_X = 84
SAFE_TOP = 250      # верх под аватар/полоски Instagram
SAFE_BOTTOM = 300   # низ под поле «Отправить сообщение»

SIZES = {"title": 70, "body": 41, "price": 48, "small": 34}
LEADING = 1.18


FONTS = {
    "Title": "YesevaOne-400.ttf",   # заголовки
    "Medium": "Montserrat-400.ttf", # основной текст
    "Bold": "Montserrat-600.ttf",   # выделения и цены
}


def font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / FONTS[weight]), size)


SYMBOLS = {"→", "•"}  # рисуются шрифтом DejaVu: одинаково в любом шрифте
ARROW_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # одинаковая стрелка во всех шрифтах


def arrow_font(f):
    return ImageFont.truetype(ARROW_FONT, int(f.size * 0.85))


def word_len(word, f):
    return arrow_font(f).getlength(word) if word in SYMBOLS else f.getlength(word)


def draw_word(d, xy, word, f, fill):
    if word in SYMBOLS:
        af = arrow_font(f)
        # выравниваем символ по высоте строчных букв основного шрифта
        dy = (f.getbbox("х")[1] + f.getbbox("х")[3]) / 2 - (af.getbbox(word)[1] + af.getbbox(word)[3]) / 2
        d.text((xy[0], xy[1] + dy), word, font=af, fill=fill)
    else:
        d.text(xy, word, font=f, fill=fill)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cover(img, fx, fy):
    img = ImageOps.exif_transpose(img).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    left = round((img.width - W) * fx)
    top = round((img.height - H) * fy)
    return img.crop((left, top, left + W, top + H))


def parse(line):
    """-> (kind, prefix, text)"""
    for mark, kind, prefix in (("# ", "title", ""), ("- ", "body", "•"),
                               ("> ", "body", "→"), ("$ ", "price", ""),
                               ("~ ", "small", "")):
        if line.startswith(mark):
            return kind, prefix, line[len(mark):]
    return "body", "", line


def tokens(text, upper=False):
    """Слова с флагом выделения. **фраза из слов** выделяется целиком."""
    out = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if upper:
            part = part.upper()
        for w in part.split():
            out.append((w, i % 2 == 1))
    return out


def layout(lines, scale):
    """Раскладывает текст по строкам. Возвращает список строк для отрисовки
    и итоговую высоту блока."""
    rows = []
    y = 0
    maxw = W - 2 * MARGIN_X
    for raw in lines:
        if raw.strip() == "":
            y += int(SIZES["body"] * scale * 0.55)
            continue
        kind, prefix, text = parse(raw)
        size = int(SIZES[kind] * scale)
        weight_n = {"title": "Title", "price": "Bold"}.get(kind, "Medium")
        weight_b = "Title" if kind == "title" else "Bold"
        fn, fb = font(weight_n, size), font(weight_b, size)
        # заголовок: если самое длинное слово не влезает — уменьшаем кегль
        if kind == "title":
            longest = max(text.upper().split(), key=fn.getlength)
            while fn.getlength(longest) > maxw:
                size -= 2
                fn, fb = font(weight_n, size), font(weight_b, size)
        indent = 0
        if prefix:
            indent = int(word_len(prefix, fn) + fn.getlength(" "))
        toks = tokens(text, upper=(kind == "title"))
        cur, curw = [], 0
        space = fn.getlength(" ")
        first = True
        lines_out = []
        for word, hl in toks:
            ww = word_len(word, fb if hl else fn)
            avail = maxw - indent
            add = ww if not cur else curw + space + ww
            if cur and add > avail:
                lines_out.append(cur)
                cur, curw = [(word, hl, ww)], ww
            else:
                cur.append((word, hl, ww))
                curw = add
        if cur:
            lines_out.append(cur)
        lh = int(size * LEADING)
        for j, ln in enumerate(lines_out):
            rows.append(dict(y=y, kind=kind, size=size, fn=fn, fb=fb,
                             prefix=prefix if j == 0 else "", indent=indent,
                             words=ln, space=space))
            y += lh
        if kind == "title":
            y += int(size * 0.25)
    return rows, y


def gradient(placement, text_top, text_bottom, color, alpha):
    """Подложка: плотная под текстом, мягко растворяется к фото."""
    mask = Image.new("L", (1, H), 0)
    px = mask.load()
    fade = 380
    for y in range(H):
        if placement == "top":
            solid_to = text_bottom + 40
            if y <= solid_to:
                a = 1.0
            else:
                a = max(0.0, 1 - (y - solid_to) / fade)
        else:
            solid_from = text_top - 40
            if y >= solid_from:
                a = 1.0
            else:
                a = max(0.0, 1 - (solid_from - y) / fade)
        px[0, y] = int(alpha * (a ** 1.4))
    mask = mask.resize((W, H))
    layer = Image.new("RGBA", (W, H), (*rgb(color), 255))
    layer.putalpha(mask)
    return layer


def render(slide, out_path):
    img = cover(Image.open(ROOT / slide["image"]),
                slide.get("focus_x", 0.5), slide.get("focus_y", 0.5))
    placement = slide.get("placement", "bottom")
    avail = H - SAFE_TOP - SAFE_BOTTOM
    scale = slide.get("scale", 1.0)
    rows, block_h = layout(slide["lines"], scale)
    while block_h > avail and scale > 0.6:
        scale -= 0.03
        rows, block_h = layout(slide["lines"], scale)

    top = SAFE_TOP if placement == "top" else H - SAFE_BOTTOM - block_h
    top += slide.get("offset_y", 0)

    if slide.get("alpha", 0) > 0:
        g = gradient(placement, top, top + block_h, slide["overlay"], slide["alpha"])
        base = img.convert("RGBA")
        base.alpha_composite(g)
        img = base.convert("RGB")

    d = ImageDraw.Draw(img)
    text_c, accent_c = rgb(slide["text"]), rgb(slide.get("accent", slide["text"]))
    for r in rows:
        y = top + r["y"]
        x = MARGIN_X
        base_c = accent_c if r["kind"] in ("title", "price") else text_c
        if r["prefix"]:
            draw_word(d, (x, y), r["prefix"], r["fn"], accent_c)
        x += r["indent"]
        for word, hl, ww in r["words"]:
            draw_word(d, (x, y), word, r["fb"] if hl else r["fn"],
                      accent_c if hl else base_c)
            x += ww + r["space"]
    img.save(out_path, "JPEG", quality=93)


def main():
    cfg = json.loads((ROOT / "stories.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    only = {int(a) for a in sys.argv[1:]}
    for i, slide in enumerate(cfg["slides"], 1):
        if only and i not in only:
            continue
        p = out_dir / f"story_{i:02d}.jpg"
        render(slide, p)
        print("OK", p)


if __name__ == "__main__":
    main()
