#!/usr/bin/env python3
"""
Отзывы «на одной странице»: каждый отзыв целиком на одном слайде 1080x1350.

Вариант A — скриншоты: склеенная лента отзыва делится пополам по пустой
строке и ставится в две колонки на одной карточке.
Вариант B — текст отзыва набран шрифтом Raleway (дословно, без длинных тире).
Вариант C — как A, но скриншоты как есть: фон и облачко Telegram, время
сообщения. Видно, что это настоящая переписка.
Вариант D — плитки как в C на красном фото-фоне, двухуровневый заголовок.

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


# ---------- вариант C: скриншоты как есть, в две колонки ----------

def raw_pieces(parts):
    """Скриншоты как есть (фон, облачко и время Telegram), без повторов на стыках."""
    pieces = []
    for name, top, bottom in parts:
        im = Image.open(mr.SRC / f"{name}.jpg").convert("RGB")
        if top == "skip_partial":
            top = mr.first_full_line_start(im) if pieces else 0
        if bottom == "text_end":
            bottom = None
        pieces.append(im.crop((0, top, im.width, bottom or im.height)))
    return pieces


def split_at_blank(im, y):
    a = np.asarray(im.convert("L"))
    blank = [r for r in range(im.height) if a[r, 60:1000].min() > 225]
    cut = min(blank, key=lambda r: abs(r - y))
    return im.crop((0, 0, im.width, cut)), im.crop((0, cut, im.width, im.height))


def two_columns(pieces):
    """Раскладывает скриншоты по двум колонкам примерно поровну;
    скриншот на границе делится по пустой строке."""
    half = sum(p.height for p in pieces) / 2
    left, right, acc = [], [], 0
    for p in pieces:
        if right or acc >= half:
            right.append(p)
        elif acc + p.height <= half + 60:
            left.append(p)
            acc += p.height
        else:
            a, b = split_at_blank(p, int(half - acc))
            left.append(a)
            right.append(b)
            acc = half
    return left, right


def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    return m


def variant_c(label, parts, last):
    img = Image.new("RGB", (W, H), mr.BG)
    d = ImageDraw.Draw(img)
    x0 = (W - CARD_W) // 2
    header(d, label, x0)
    cols = two_columns(raw_pieces(parts))
    gap, vgap = 28, 16
    src_w = cols[0][0].width
    col_h = [sum(p.height for p in c) for c in cols]
    n_gaps = [len(c) - 1 for c in cols]
    s = (CARD_W - gap) / 2 / src_w
    s = min(s, min((H - TOP - BOTTOM - g * vgap) / h for h, g in zip(col_h, n_gaps)))
    tw = round(src_w * s)
    heights = [round(h * s) + g * vgap for h, g in zip(col_h, n_gaps)]
    top0 = TOP + (H - TOP - BOTTOM - max(heights)) // 2
    x = (W - (2 * tw + gap)) // 2
    for c in cols:
        y = top0
        for p in c:
            tile = p.resize((tw, round(p.height * s)), Image.LANCZOS)
            sh, pad = mr.shadow(tile.size, 24, blur=20, alpha=70)
            img.paste((60, 40, 30), (x - pad, y - pad), sh)
            img.paste(tile, (x, y), rounded(tile, 24))
            y += tile.height + vgap
        x += tw + gap
    footer(d, x0, last)
    return img, s


# ---------- вариант D: красный фон и стильный заголовок ----------

RED_BG = mr.ROOT.parent / "stories" / "src" / "09_zapis.jpg"   # бордовый отпечаток
PEACH = (240, 201, 168)


def spaced(d, xy, text, f, fill, track):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + track
    return x


# фоны с красным: (файл, центр кропа, размытие, затемнение бордовым 0..255)
BACKGROUNDS = {
    "otpechatok": (RED_BG, (0.5, 0.6), 0, 40),
    "kostyum": (mr.ROOT.parent / "stories" / "src" / "08_ne_znaesh.jpg", (0.5, 0.45), 10, 120),
    "kostyum_sidya": (mr.ROOT.parent / "stories" / "src" / "01_vhod.jpg", (0.3, 0.5), 10, 120),
    "telefon": (mr.ROOT.parent / "highlights" / "src" / "02_otzyvy.jpg", (0.5, 0.5), 6, 110),
    "plate": (mr.ROOT.parent / "highlights" / "src" / "04_obo_mne.jpg", (0.65, 0.4), 8, 120),
    "krasnyi": (None, None, 0, 0),
}
BG_TINT = (40, 6, 10)


STORIES_SRC = mr.ROOT.parent / "stories" / "src"


def _top_shade(img, height=330, alpha=200):
    """Тёмно-бордовая тень сверху, чтобы белый заголовок читался на светлом фото."""
    m = Image.new("L", (1, H), 0)
    for y in range(height):
        m.putpixel((0, y), int(alpha * (1 - y / height) ** 1.3))
    shade = Image.new("RGB", (W, H), BG_TINT)
    return Image.composite(shade, img, m.resize((W, H)))


def _vivid(path, centering, blur, dark, sat=1.35):
    from PIL import ImageEnhance, ImageFilter, ImageOps
    bg = ImageOps.fit(Image.open(path).convert("RGB"), (W, H), Image.LANCZOS, centering=centering)
    bg = ImageEnhance.Color(bg).enhance(sat)
    if blur:
        bg = bg.filter(ImageFilter.GaussianBlur(blur))
    return _top_shade(Image.blend(bg, Image.new("RGB", (W, H), BG_TINT), dark / 255))


def _fabric():
    """Крупный план красной ткани костюма."""
    from PIL import ImageEnhance, ImageFilter
    im = Image.open(STORIES_SRC / "08_ne_znaesh.jpg").convert("RGB")
    w, h = im.size
    crop = im.crop((int(w * 0.36), int(h * 0.36), int(w * 0.64), int(h * 0.71)))
    crop = crop.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5))
    crop = ImageEnhance.Color(crop).enhance(1.2)
    return Image.blend(crop, Image.new("RGB", (W, H), BG_TINT), 70 / 255)


def _duotone(path, centering, dark=(45, 4, 10), light=(214, 38, 48)):
    from PIL import ImageOps
    g = ImageOps.fit(Image.open(path).convert("L"), (W, H), Image.LANCZOS, centering=centering)
    return ImageOps.colorize(ImageOps.autocontrast(g, cutoff=2), dark, light)


def _gradient(c1=(205, 32, 42), c2=(70, 6, 14)):
    """Диагональный градиент: яркий красный слева сверху -> бордо справа снизу."""
    yy, xx = np.mgrid[0:H, 0:W]
    k = ((xx / W) * 0.45 + (yy / H) * 0.55)[..., None]
    a = np.array(c1) * (1 - k) + np.array(c2) * k
    return Image.fromarray(a.astype("uint8"))


def _band():
    """Кремовый фон с красной полосой сверху под заголовком."""
    img = Image.new("RGB", (W, H), mr.BG)
    img.paste(_gradient((185, 26, 36), (120, 14, 24)).crop((0, 0, W, 560)), (0, 0))
    return img


FONY = mr.SRC / "fony"
FONY_CROP = {1: (0.5, 0.5), 2: (0.5, 0.35), 3: (0.5, 0.25), 4: (0.5, 0.5), 5: (0.4, 0.5)}


def _fon(n):
    from PIL import ImageOps
    return ImageOps.fit(ImageOps.exif_transpose(Image.open(FONY / f"fon_{n}.jpg")).convert("RGB"),
                        (W, H), Image.LANCZOS, centering=FONY_CROP[n])


EXTRA = {
    **{f"fon_{n}": (lambda n=n: _fon(n)) for n in FONY_CROP},
    "kostyum_yarko": lambda: _vivid(STORIES_SRC / "08_ne_znaesh.jpg", (0.5, 0.45), 4, 50),
    "telefon_yarko": lambda: _vivid(mr.ROOT.parent / "highlights" / "src" / "02_otzyvy.jpg", (0.5, 0.5), 3, 45),
    "tkan": _fabric,
    "duotone": lambda: _duotone(STORIES_SRC / "01_vhod.jpg", (0.3, 0.5)),
    "gradient": _gradient,
    "polosa": _band,
}


def red_background(kind="otpechatok"):
    from PIL import ImageFilter, ImageOps
    if kind in EXTRA:
        return EXTRA[kind]()
    path, centering, blur, dark = BACKGROUNDS[kind]
    if path is None:  # однотонный красный с мягкой виньеткой
        bg = Image.new("RGB", (W, H), (150, 22, 30))
        vign = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vign).ellipse([-300, -200, W + 300, H + 200], fill=255)
        vign = vign.filter(ImageFilter.GaussianBlur(220))
        dark_bg = Image.new("RGB", (W, H), (90, 10, 18))
        return Image.composite(bg, dark_bg, vign)
    bg = ImageOps.fit(Image.open(path).convert("RGB"), (W, H), Image.LANCZOS, centering=centering)
    if blur:
        bg = bg.filter(ImageFilter.GaussianBlur(blur))
    tint = Image.new("RGB", (W, H), BG_TINT)
    return Image.blend(bg, tint, dark / 255)


def kind_has_photo(kind):
    return kind.startswith("fon_")


def variant_d(label, parts, num, last, bg="otpechatok"):
    img = red_background(bg)
    d = ImageDraw.Draw(img)
    x0 = 70
    # надзаголовок разрядкой
    light = np.asarray(img.crop((x0, 50, W - x0, 230)).convert("L")).mean() > 150
    title_c = mr.ACCENT if light else (255, 255, 255)
    label_c = (110, 90, 84) if light else PEACH
    plaque_c = (244, 239, 232, 225) if light else (40, 6, 10, 165)
    size = 76
    ft = mr.font("YesevaOne-400.ttf", size)
    while ft.getlength(label) > W - 2 * x0:
        size -= 2
        ft = mr.font("YesevaOne-400.ttf", size)
    if kind_has_photo(bg):
        # плашка под заголовком, чтобы он читался поверх предметов на фото
        pw = int(max(ft.getlength(label), 320)) + 56
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle([x0 - 28, 44, x0 - 28 + pw, 236], 26, fill=plaque_c)
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(img)
    fs = mr.font("Raleway-600.ttf", 26)
    spaced(d, (x0, 64), f"ОТЗЫВ  ·  {num:02d}", fs, label_c, 7)
    # заголовок строчными, Yeseva One
    d.text((x0, 104), label, font=ft, fill=title_c)
    lw = ft.getlength(label)
    d.line([(x0, 214), (x0 + 90, 214)], fill=title_c if light else PEACH, width=3)

    top_area, bottom_area = 250, 110
    cols = two_columns(raw_pieces(parts))
    gap, vgap = 26, 14
    src_w = cols[0][0].width
    col_h = [sum(p.height for p in c) for c in cols]
    n_gaps = [len(c) - 1 for c in cols]
    s = (W - 2 * x0 - gap) / 2 / src_w
    s = min(s, min((H - top_area - bottom_area - g * vgap) / h for h, g in zip(col_h, n_gaps)))
    tw = round(src_w * s)
    heights = [round(h * s) + g * vgap for h, g in zip(col_h, n_gaps)]
    top0 = top_area + (H - top_area - bottom_area - max(heights)) // 2
    x = (W - (2 * tw + gap)) // 2
    for c in cols:
        y = top0
        for p in c:
            tile = p.resize((tw, round(p.height * s)), Image.LANCZOS)
            sh, pad = mr.shadow(tile.size, 24, blur=24, alpha=150)
            img.paste((20, 5, 8), (x - pad, y - pad), sh)
            img.paste(tile, (x, y), rounded(tile, 24))
            y += tile.height + vgap
        x += tw + gap

    if last:
        t = "Хочешь так же? Напиши в директ слово СТИЛЬ"
        fb = mr.font("Raleway-600.ttf", 30)
        under = np.asarray(img.crop((200, H - 80, W - 200, H - 40)).convert("L")).mean()
        lt = under > 150
        color = mr.ACCENT if lt else (255, 255, 255)   # на светлом фоне бордо
        tw_ = fb.getlength(t)
        if kind_has_photo(bg):
            pc = (244, 239, 232, 225) if lt else (40, 6, 10, 165)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle(
                [(W - tw_) // 2 - 30, H - 92, (W + tw_) // 2 + 30, H - 30], 31, fill=pc)
            img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
            d = ImageDraw.Draw(img)
        d.text(((W - tw_) // 2, H - 78), t, font=fb, fill=color)
    return img, s, lw


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


FINAL_BG = {"Ведение 3 месяца": "fon_3", "Шопинг-сопровождение": "fon_4"}
FINAL = mr.ROOT / "final"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(exist_ok=True)
    names = {"Ведение 3 месяца": "02_vedenie.jpg", "Шопинг-сопровождение": "03_shopping.jpg"}
    for i, (label, parts) in enumerate(mr.REVIEWS):
        img, _, _ = variant_d(label, parts, i + 1, i == len(mr.REVIEWS) - 1, FINAL_BG[label])
        img.save(FINAL / names[label], quality=95)
    for i, (label, parts) in enumerate(mr.REVIEWS):
        last = i == len(mr.REVIEWS) - 1
        a, s = variant_a(label, parts, last)
        a.save(OUT / f"A_{i + 1:02d}.jpg", quality=93)
        b, size = variant_b(label, TEXTS[label], last)
        b.save(OUT / f"B_{i + 1:02d}.jpg", quality=93)
        c, sc = variant_c(label, parts, last)
        c.save(OUT / f"C_{i + 1:02d}.jpg", quality=93)
        print(label, f"C: масштаб скриншота {sc:.2f}")
        dimg, sd, lw = variant_d(label, parts, i + 1, last)
        dimg.save(OUT / f"D_{i + 1:02d}.jpg", quality=93)
        for kind in list(BACKGROUNDS) + list(EXTRA):
            v, _, _ = variant_d(label, parts, i + 1, last, kind)
            v.save(OUT / f"bg_{kind}_{i + 1:02d}.jpg", quality=93)
        print(label, f"D: масштаб {sd:.2f}, ширина заголовка {lw:.0f}px")
        print(label, f"A: масштаб скриншота {s:.2f}", f"B: шрифт {size}px")


if __name__ == "__main__":
    main()
