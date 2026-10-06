#!/usr/bin/env python3
"""
Отзывы «на одной странице»: каждый отзыв целиком на одном слайде 1080x1350.

Вариант A — скриншоты: склеенная лента отзыва делится пополам по пустой
строке и ставится в две колонки на одной карточке.
Вариант B — текст отзыва набран шрифтом Raleway (дословно, без длинных тире).

Запуск: python3 -I make_reviews_onepage.py
На выходе: output/onepage/A_*.jpg и B_*.jpg
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_reviews as mr  # noqa: E402

OUT = mr.OUT / "onepage"
W, H = mr.W, mr.H
CARD_W = 980
TOP = 150          # под шапкой
BOTTOM = 100       # под подвалом

# дословно из скриншотов; длинные тире заменены на двоеточие и запятую
TEXTS = {
    "Ведение 3 месяца": [
        "Дарья, три месяца с тобой пролетели очень быстро. И это было что-то невероятное. "
        "Ты поняла мои «хочу», которые я не могла объяснить.",
        "Мне было очень сложно сформировать в своей голове словами, что я хочу получить, "
        "так как у меня новый этап в жизни, и я изучаю себя с нуля не только внутренне, "
        "но я даже понятия не имела, как хочу выглядеть-ты все почувствовала и попала в точку.",
        "Ты постоянно была на связи со мной \U0001F923, консультировала меня по всем выборам одежды.",
        "Наша каждодневная вечерняя подготовка на работу, как тренировка в зале - это отдельный "
        "сеанс психотерапии, но только с помощью выбора одежды.",
        "И я очень рада, что мы купили мне несколько вещей, но таких классных, качественных, "
        "красивых. На которые хочется смотреть и ходить в них не снимая.",
        "И я себе в них нравлюсь.",
        "Никогда не думала, что мне понравится выбирать вещи и ходить по магазинам. Зато на "
        "каждых выходных теперь думаю, «чтобы еще такого красивенького прикупить, куда потратить "
        "деньги». Мой запрос с тобой отработали на все 100%, миллион %. Хочется еще, но попозже "
        "повторим. Особенно в работе понравились твои комплименты. Никто еще так не говорил про "
        "мою изогнутую талию. И я начала по-новому смотреть на себя. Видеть в этом не недостаток - "
        "а то, что тебе начинает нравится. Только украшать ту же талию нужно правильно. "
        "Придать красивую огранку.",
        "И черт, красивая одежда придает уверенность. Спасибо тебе большое!",
    ],
    "Шопинг-сопровождение": [
        "Я уже давно поняла, что мой гардероб не отзывается мне, и я не чувствую себя собой в том, "
        "что у меня сейчас есть. Переезд в Питер, желание начать новую жизнь стали для меня "
        "толчком во многом. И вот дело дошло до гардероба. Мне не пришлось долго искать "
        "проводника в этом. Дарья стала моим выбором, т.к. она красивая, стильная и опытная.",
        "Я думала будет простая встреча в ТЦ, примерка нескольких образов и все. Но работа "
        "началась с того, что я получила профессиональный разбор моих параметров, метрик фигуры "
        "и цветотипа. И только после этого было собрано несколько образов во французском стиле.",
        "Мне кажется, я впервые в жизни поняла, как это работает. Я смотрела на себя в зеркало и "
        "буквально не узнавала человека в отражении. Оказывается, можно стать ярким, заметным и "
        "открытым, просто надев красную рубашку или мини-юбку. Мне безумно понравилось, что "
        "Дарья объясняла механику: почему именно нужно подвернуть рукав, а не оставить его "
        "длинным, как работают пропорции в открытости тела, и почему нам нужно увести все "
        "внимание на мои красивые ноги, руки и тату на них.",
        "Я точно влюбилась в два образа из подборки. В них я совсем другая: заметная, высокая, "
        "уверенная (просто не хочется опускать плечи в такой одежде), красивая, желанная (даже "
        "для себя), деловая. Не та, которая сейчас прячется в черно-сером оверсайз на съемной "
        "квартире и ездит только на работу и обратно, а та, которая уверенно идет по питерским "
        "улицам.",
        "Кажется, моя новая жизнь в этом городе действительно началась, хотя бы с красной "
        "рубашки или белой мини-юбки. Безумно благодарна Дарье, что она дала мне возможность "
        "увидеть меня именно так и дала понять мне, что есть другие цвета помимо серого.",
    ],
}

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def header(d, label, x0):
    d.text((x0, 70), label.upper(), font=mr.font("YesevaOne-400.ttf", 40), fill=mr.ACCENT)


def footer(d, x0, last):
    if last:
        t = "Хочешь так же? Напиши в директ слово СТИЛЬ"
        fb = mr.font("Raleway-600.ttf", 30)
        d.text(((W - fb.getlength(t)) // 2, H - 76), t, font=fb, fill=mr.ACCENT)


def card(img, x0, top, w, h):
    sh, pad = mr.shadow((w, h), 36)
    img.paste((60, 40, 30), (x0 - pad, top - pad), sh)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 36, fill=255)
    img.paste(Image.new("RGB", (w, h), "white"), (x0, top), m)


def quote_mark(d, x0, top):
    d.text((x0 - 10, top - 95), "“", font=mr.font("YesevaOne-400.ttf", 190), fill=mr.ACCENT)


# ---------- вариант A: скриншоты в две колонки ----------

def halves(strip):
    a = np.asarray(strip.convert("L"))
    blank = [y for y in range(strip.height) if a[y, 20:1020].min() > 225]
    cut = min(blank, key=lambda y: abs(y - strip.height // 2))
    return strip.crop((0, 0, strip.width, cut)), strip.crop((0, cut, strip.width, strip.height))


def variant_a(label, parts, last):
    img = Image.new("RGB", (W, H), mr.BG)
    d = ImageDraw.Draw(img)
    x0 = (W - CARD_W) // 2
    header(d, label, x0)
    left, right = halves(mr.stitch(parts))
    pad, gap = 30, 30
    col_w = (CARD_W - 2 * pad - gap) // 2
    s = col_w / left.width
    max_h = H - TOP - BOTTOM - 2 * pad
    s = min(s, max_h / max(left.height, right.height))
    L = left.resize((round(left.width * s), round(left.height * s)), Image.LANCZOS)
    R = right.resize((round(right.width * s), round(right.height * s)), Image.LANCZOS)
    ch = max(L.height, R.height) + 2 * pad
    top = TOP + (H - TOP - BOTTOM - ch) // 2
    card(img, x0, top, CARD_W, ch)
    cx = x0 + (CARD_W - (L.width + gap + R.width)) // 2
    img.paste(L, (cx, top + pad))
    img.paste(R, (cx + L.width + gap, top + pad))
    d.line([(cx + L.width + gap // 2, top + pad + 10), (cx + L.width + gap // 2, top + ch - pad - 10)],
           fill=(230, 222, 214), width=2)
    quote_mark(d, x0, top)
    footer(d, x0, last)
    return img, s


# ---------- вариант B: набранный текст ----------

def layout_text(paras, size, maxw):
    f = mr.font("Raleway-400.ttf", size)
    lh = int(size * 1.42)
    rows, y = [], 0
    for p in paras:
        cur = ""
        for w in p.split():
            trial = f"{cur} {w}".strip()
            if f.getlength(trial) <= maxw or not cur:
                cur = trial
            else:
                rows.append((y, cur))
                y += lh
                cur = w
        rows.append((y, cur))
        y += lh + int(size * 0.55)
    return f, rows, y - int(size * 0.55)


def draw_line(img, d, xy, text, f):
    """Строка текста; эмодзи рисуется цветным шрифтом, если он есть."""
    x, y = xy
    for ch in text:
        if ord(ch) > 0xFFFF and Path(EMOJI_FONT).exists():
            from PIL import ImageFont
            ef = ImageFont.truetype(EMOJI_FONT, 109)
            em = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
            ImageDraw.Draw(em).text((0, 0), ch, font=ef, embedded_color=True)
            em = em.crop(em.getbbox())
            sz = int(f.size * 1.05)
            em = em.resize((sz, sz), Image.LANCZOS)
            img.paste(em, (int(x), int(y + f.size * 0.12)), em)
            x += sz
        else:
            d.text((x, y), ch, font=f, fill=mr.TEXT)
            x += f.getlength(ch)


def variant_b(label, paras, last):
    img = Image.new("RGB", (W, H), mr.BG)
    d = ImageDraw.Draw(img)
    x0 = (W - CARD_W) // 2
    header(d, label, x0)
    pad = 52
    maxw = CARD_W - 2 * pad
    max_h = H - TOP - BOTTOM - 2 * pad
    size = 34
    while True:
        f, rows, th = layout_text(paras, size, maxw)
        if th <= max_h or size <= 18:
            break
        size -= 1
    ch = th + 2 * pad
    top = TOP + (H - TOP - BOTTOM - ch) // 2
    card(img, x0, top, CARD_W, ch)
    for y, line in rows:
        draw_line(img, d, (x0 + pad, top + pad + y), line, f)
    footer(d, x0, last)
    return img, size


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (label, parts) in enumerate(mr.REVIEWS):
        last = i == len(mr.REVIEWS) - 1
        a, s = variant_a(label, parts, last)
        a.save(OUT / f"A_{i + 1:02d}.jpg", quality=93)
        b, size = variant_b(label, TEXTS[label], last)
        b.save(OUT / f"B_{i + 1:02d}.jpg", quality=93)
        print(label, f"A: масштаб скриншота {s:.2f}", f"B: шрифт {size}px")


if __name__ == "__main__":
    main()
