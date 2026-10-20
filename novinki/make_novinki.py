#!/usr/bin/env python3
"""
Карусель «Новинки недели»: 5 анимированных слайдов 1080x1350 (MP4, H.264, 30 к/с)
и JPG-кадр каждого слайда (на случай, если нужна статичная версия).

Все слайды собраны из одного фото в примерочной (src/photo.jpg):
  01 обложка — камера едет по образу сверху вниз, «НОВИНКИ НЕДЕЛИ»
     выплывает снизу, выскакивает бейдж NEW, список вещей появляется по одной;
  02–04 — наезд на каждую вещь (верх, карго, ботинки), номер, название
     и короткий комментарий стилиста выезжают по очереди;
  05 — образ целиком на размытом фоне, формула образа и призыв.

Шрифты как на прошлых каруселях: Yeseva One (заголовки, капс с разрядкой
и тонкими линиями по бокам) и Raleway (текст).

Запуск: python3 -I make_novinki.py
На выходе: output/0N_*.mp4, output/0N_*.jpg, output/preview.jpg, novinki_karusel.zip
"""

import math
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
OUT = ROOT / "output"

W, H = 1080, 1350
FPS = 30
DUR = 6.0
MARGIN = 84
OVERLAY = (20, 17, 15)
WHITE = (255, 255, 255)
PEACH = (240, 201, 168)
BORDO = (122, 28, 30)

TOTAL = 5


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


F_TITLE = font("YesevaOne-400.ttf", 92)
F_TITLE_S = font("YesevaOne-400.ttf", 66)
F_NUM = font("YesevaOne-400.ttf", 150)
F_KICK = font("Raleway-600.ttf", 28)
F_TEXT = font("Raleway-400.ttf", 38)
F_TEXT_B = font("Raleway-600.ttf", 38)
F_CTA = font("Raleway-600.ttf", 34)
F_BADGE = font("Raleway-600.ttf", 40)
F_ARROW = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)


# ---------- анимационные помощники ----------

def clamp(t):
    return min(1.0, max(0.0, t))


def ease(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def back(t):
    """Выскакивание с лёгким перелётом (для бейджа)."""
    t = clamp(t)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def appear(t, start, dur=0.6):
    return ease((t - start) / dur)


def out_fade(t):
    """В конце всё гаснет, чтобы повтор начинался мягко."""
    return 1 - ease_io((t - (DUR - 0.5)) / 0.5)


# ---------- рисование ----------

def gradient(solid=880, fadelen=460, top=False):
    """Тёмная подложка снизу (и при top=True — лёгкая сверху под кикер)."""
    mask = Image.new("L", (1, H), 0)
    px = mask.load()
    for y in range(H):
        a = 1.0 if y >= solid else max(0.0, 1 - (solid - y) / fadelen)
        v = 225 * a ** 1.4
        if top:
            v = max(v, 150 * max(0.0, 1 - y / 260) ** 1.6)
        px[0, y] = int(v)
    layer = Image.new("RGBA", (W, H), (*OVERLAY, 255))
    layer.putalpha(mask.resize((W, H)))
    return layer


def spaced_width(text, f, track):
    return sum(f.getlength(c) + track for c in text) - track


def draw_spaced(d, text, f, x, y, track, fill):
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + track


def title(img, text, f, y, alpha, grow, track=14, dy=0):
    """Капс с разрядкой по центру и персиковыми линиями по бокам."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = spaced_width(text, f, track)
    x0 = (W - tw) / 2
    draw_spaced(d, text, f, x0, y + dy, track, (*WHITE, int(255 * alpha)))
    bb = f.getbbox("Н")
    cy = y + dy + (bb[1] + bb[3]) / 2
    left_end, right_start = x0 - 30, x0 + tw + 30
    seg = (left_end - MARGIN + 30) * grow
    if seg > 1:
        lc = (*PEACH, int(255 * alpha))
        d.line([(left_end - seg, cy), (left_end, cy)], fill=lc, width=2)
        d.line([(right_start, cy), (right_start + seg, cy)], fill=lc, width=2)
    img.alpha_composite(layer)


def text(img, s, f, y, alpha, color=WHITE, x=None, track=0, dx=0, dy=0):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = spaced_width(s, f, track) if track else f.getlength(s)
    lx = (W - w) / 2 if x is None else x
    if track:
        draw_spaced(d, s, f, lx + dx, y + dy, track, (*color, int(255 * alpha)))
    else:
        d.text((lx + dx, y + dy), s, font=f, fill=(*color, int(255 * alpha)))
    img.alpha_composite(layer)


def wrap(s, f, maxw):
    lines, cur = [], ""
    for w in s.split():
        trial = f"{cur} {w}".strip()
        if f.getlength(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def cta(img, t, start, label="Листай"):
    """«Листай →» внизу с покачивающейся стрелкой."""
    a = appear(t, start) * out_fade(t)
    if a <= 0:
        return
    wl = F_CTA.getlength(label)
    wa = F_ARROW.getlength("→")
    x = (W - wl - 16 - wa) / 2
    y = H - 104
    text(img, label, F_CTA, y, a, PEACH, x=x)
    sway = 8 * math.sin((t - start) * 2 * math.pi / 1.2)
    text(img, "→", F_ARROW, y + 2, a, PEACH, x=x + wl + 16 + sway)


def dots(img, idx, alpha):
    """Индикатор слайда сверху справа: 01 / 05."""
    s = f"{idx:02d} / {TOTAL:02d}"
    text(img, s, F_KICK, 64, alpha * 0.85, WHITE, x=W - MARGIN - spaced_width(s, F_KICK, 4), track=4)


def kicker(img, s, alpha):
    text(img, s, F_KICK, 64, alpha * 0.85, WHITE, x=MARGIN, track=6)


def kenburns(src, box, t, z0, z1, pan=(0, 0)):
    """Кадр из области box=(cx, cy, h) исходника (доли): наезд z0→z1 и сдвиг."""
    sw, sh = src.size
    cx, cy, hfrac = box
    k = ease_io(t / DUR)
    z = z0 + (z1 - z0) * k
    ch = sh * hfrac / z
    cw = ch * W / H
    x = sw * cx - cw / 2 + pan[0] * sw * k
    y = sh * cy - ch / 2 + pan[1] * sh * k
    x = min(max(0, x), sw - cw)
    y = min(max(0, y), sh - ch)
    return src.resize((W, H), Image.LANCZOS, box=(x, y, x + cw, y + ch)).convert("RGBA")


# ---------- слайды ----------

ITEMS = [
    {
        "slug": "02_verh",
        "num": "01",
        "kick": "ВЕРХ",
        "name": "ВОДОЛАЗКА",
        "sub": "без рукавов, чёрная",
        "note": "Высокое горло и открытые плечи вытягивают силуэт. "
                "База, которая работает и под жакет, и под кожанку, и сама по себе.",
        "box": (0.58, 0.31, 0.42),  # доли исходника: центр x, центр y, высота
        "zoom": (1.0, 1.12),
        "pan": (0, 0.01),
    },
    {
        "slug": "03_niz",
        "num": "02",
        "kick": "НИЗ",
        "name": "КАРГО",
        "sub": "в песочный камуфляж",
        "note": "Низкая посадка, прямой свободный крой, объёмные карманы. "
                "Песочный камуфляж мягче классического хаки и легче сочетается.",
        "box": (0.6, 0.58, 0.46),
        "zoom": (1.12, 1.0),
        "pan": (0, 0.03),
    },
    {
        "slug": "04_obuv",
        "num": "03",
        "kick": "ОБУВЬ",
        "name": "БОТИНКИ",
        "sub": "на тракторной подошве",
        "note": "Массивная подошва уравновешивает объём брюк: "
                "силуэт собран, а не «утонул» в широких штанинах.",
        "box": (0.59, 0.89, 0.44),
        "zoom": (1.0, 1.1),
        "pan": (0, 0),
        "floor": True,
    },
]


def render(name, frame_fn):
    """Рендерит кадры в MP4 через ffmpeg и сохраняет JPG-кадр для превью."""
    mp4 = OUT / f"{name}.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
         "-profile:v", "high", "-movflags", "+faststart", str(mp4)],
        stdin=subprocess.PIPE,
    )
    still_t = DUR - 1.0
    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        fr = frame_fn(t).convert("RGB")
        proc.stdin.write(fr.tobytes())
        if i == int(still_t * FPS):
            fr.save(OUT / f"{name}.jpg", quality=94)
    proc.stdin.close()
    proc.wait()
    print("готово:", mp4.name)


def cover_frame(src, grad):
    lines = ["водолазка без рукавов", "карго в камуфляж", "грубые ботинки"]

    def frame(t):
        # камера едет по образу: от ботинок к лицу
        k = ease_io(t / DUR)
        img = kenburns(src, (0.55, 0.62 - 0.26 * k, 0.70), 0, 1.0, 1.0)
        img.alpha_composite(grad)
        fo = out_fade(t)
        kicker(img, "ПРИМЕРОЧНАЯ · ОКТЯБРЬ", appear(t, 0.2) * fo)
        dots(img, 1, appear(t, 0.2) * fo)

        a = appear(t, 0.35, 0.8) * fo
        title(img, "НОВИНКИ", F_TITLE, 760, a, appear(t, 0.9, 0.9), dy=40 * (1 - a))
        a2 = appear(t, 0.6, 0.8) * fo
        title(img, "НЕДЕЛИ", F_TITLE, 870, a2, 0, dy=40 * (1 - a2))

        # пункты по одному, разделены персиковыми точками
        for i, ln in enumerate(lines):
            ai = appear(t, 1.5 + 0.35 * i, 0.5) * fo
            text(img, ln, F_TEXT, 1010 + i * 54, ai, dx=-30 * (1 - ai))

        # бейдж NEW выскакивает справа сверху и чуть покачивается
        bs = back((t - 1.1) / 0.55) if t > 1.1 else 0
        if bs > 0:
            r = 82
            badge = Image.new("RGBA", (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge)
            bd.ellipse([4, 4, 2 * r + 4, 2 * r + 4], fill=(*BORDO, 255), outline=(*PEACH, 255), width=3)
            tw = spaced_width("NEW", F_BADGE, 4)
            bb = F_BADGE.getbbox("N")
            draw_spaced(bd, "NEW", F_BADGE, r + 4 - tw / 2, r + 4 - (bb[1] + bb[3]) / 2, 4, (*WHITE, 255))
            ang = -12 + 5 * math.sin(t * 2.4)
            size = max(1, int(badge.width * bs))
            b2 = badge.resize((size, size), Image.LANCZOS).rotate(ang, Image.BICUBIC, expand=True)
            if fo < 1:
                b2.putalpha(b2.getchannel("A").point(lambda v: int(v * fo)))
            cx, cy = W - MARGIN - r + 10, 210
            img.alpha_composite(b2, (int(cx - b2.width / 2), int(cy - b2.height / 2)))

        cta(img, t, 2.8)
        return img

    return frame


def with_floor(src, extra=0.35):
    """Достраивает пол снизу (зеркалим и размываем нижнюю полосу),
    чтобы обувь можно было поднять в верхнюю часть кадра над текстом."""
    sw, sh = src.size
    strip_h = int(sh * 0.06)
    strip = src.crop((0, sh - strip_h, sw, sh))
    ext_h = int(sh * extra)
    ext = Image.new("RGB", (sw, ext_h))
    y, flip = 0, True
    while y < ext_h:
        ext.paste(ImageOps.flip(strip) if flip else strip, (0, y))
        y += strip_h
        flip = not flip
    ext = ext.filter(ImageFilter.GaussianBlur(30))
    out = Image.new("RGB", (sw, sh + ext_h))
    out.paste(src, (0, 0))
    out.paste(ext, (0, sh))
    # мягкий шов
    seam = out.crop((0, sh - 60, sw, sh + 60)).filter(ImageFilter.GaussianBlur(14))
    out.paste(seam, (0, sh - 60))
    return out


def item_frame(src, grad, it, idx):
    note = wrap(it["note"], F_TEXT, W - 2 * MARGIN)
    if it.get("floor"):
        sh = src.height
        src = with_floor(src)
        cx, cy, hf = it["box"]
        it = {**it, "box": (cx, cy * sh / src.height, hf * sh / src.height)}

    def frame(t):
        img = kenburns(src, it["box"], t, *it["zoom"], pan=it["pan"])
        img.alpha_composite(grad)
        fo = out_fade(t)
        kicker(img, f"НОВИНКИ НЕДЕЛИ · {it['kick']}", appear(t, 0.1) * fo)
        dots(img, idx, appear(t, 0.1) * fo)

        # большой номер слева, название и подпись справа от него
        base_y = 1350 - 140 - len(note) * 50 - 230
        an = appear(t, 0.25, 0.7) * fo
        text(img, it["num"], F_NUM, base_y - 30, an * 0.9, PEACH, x=MARGIN, dy=50 * (1 - an))
        nx = MARGIN + F_NUM.getlength(it["num"]) + 36
        a1 = appear(t, 0.5, 0.7) * fo
        text(img, it["name"], F_TITLE_S, base_y + 18, a1, x=nx, track=10, dx=-40 * (1 - a1))
        a2 = appear(t, 0.75, 0.7) * fo
        text(img, it["sub"], F_TEXT_B, base_y + 110, a2, PEACH, x=nx, dx=-40 * (1 - a2))

        # линия растёт слева направо
        g = appear(t, 1.0, 0.9) * fo
        if g > 0:
            d = ImageDraw.Draw(img)
            ly = base_y + 190
            d.line([(MARGIN, ly), (MARGIN + (W - 2 * MARGIN) * g, ly)], fill=(*PEACH, int(255 * fo)), width=2)

        # комментарий стилиста построчно
        for i, ln in enumerate(note):
            ai = appear(t, 1.3 + 0.18 * i, 0.5) * fo
            text(img, ln, F_TEXT, base_y + 222 + i * 50, ai, x=MARGIN, dy=16 * (1 - ai))

        cta(img, t, 2.4)
        return img

    return frame


def final_frame(src):
    # размытый затемнённый фон + чёткое фото образа целиком
    bg = ImageOps.fit(src, (W, H), Image.LANCZOS, centering=(0.5, 0.45))
    bg = bg.filter(ImageFilter.GaussianBlur(40)).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", (W, H), (*OVERLAY, 170)))
    ph_h = 820
    ph = src.resize((int(src.width * ph_h / src.height), ph_h), Image.LANCZOS).convert("RGBA")
    frame_img = Image.new("RGBA", (ph.width + 12, ph.height + 12), (*PEACH, 255))
    frame_img.alpha_composite(ph, (6, 6))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sx = (W - frame_img.width) // 2
    sy = 200
    ImageDraw.Draw(shadow).rectangle([sx + 14, sy + 20, sx + frame_img.width + 14, sy + frame_img.height + 20], fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))

    parts = ["облегающий верх", "объём внизу", "грубая обувь"]

    def frame(t):
        img = bg.copy()
        fo = out_fade(t)
        kicker(img, "НОВИНКИ НЕДЕЛИ", appear(t, 0.1) * fo)
        dots(img, TOTAL, appear(t, 0.1) * fo)

        a = appear(t, 0.2, 0.8)
        if a > 0:
            s = shadow.copy()
            s.putalpha(s.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(s)
            # фото «приезжает» снизу и слегка увеличивается
            sc = 0.94 + 0.06 * a
            fi = frame_img.resize((int(frame_img.width * sc), int(frame_img.height * sc)), Image.LANCZOS)
            fi.putalpha(fi.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(fi, (int((W - fi.width) / 2), int(sy + 60 * (1 - a) + (frame_img.height - fi.height) / 2)))

        title(img, "ФОРМУЛА ОБРАЗА", F_TITLE_S, 104, appear(t, 0.4, 0.8) * fo, appear(t, 0.8, 0.9))

        # формула одной строкой: части по очереди, между ними персиковый «+»
        y = 1070
        sep = "  +  "
        full = sep.join(parts)
        x = (W - F_TEXT_B.getlength(full)) / 2
        for i, p in enumerate(parts):
            ai = appear(t, 1.1 + 0.45 * i, 0.5) * fo
            text(img, p, F_TEXT_B, y, ai, x=x, dy=20 * (1 - ai))
            x += F_TEXT_B.getlength(p)
            if i < len(parts) - 1:
                ap = appear(t, 1.35 + 0.45 * i, 0.4) * fo
                text(img, sep, F_TEXT_B, y, ap, PEACH, x=x)
                x += F_TEXT_B.getlength(sep)

        ac = appear(t, 2.8, 0.7) * fo
        text(img, "Сохрани, чтобы повторить", F_CTA, H - 150, ac, PEACH)
        return img

    return frame


def main():
    OUT.mkdir(exist_ok=True)
    src = ImageOps.exif_transpose(Image.open(ROOT / "src" / "photo.jpg")).convert("RGB")

    render("01_oblozhka", cover_frame(src, gradient(solid=900, fadelen=520, top=True)))
    for i, it in enumerate(ITEMS, start=2):
        render(it["slug"], item_frame(src, gradient(solid=860, fadelen=480, top=True), it, i))
    render("05_obraz", final_frame(src))

    names = ["01_oblozhka"] + [it["slug"] for it in ITEMS] + ["05_obraz"]
    thumbs = [Image.open(OUT / f"{n}.jpg") for n in names]
    tw, th = 360, 450
    prev = Image.new("RGB", (tw * len(thumbs) + 12 * (len(thumbs) + 1), th + 24), (243, 235, 227))
    for i, im in enumerate(thumbs):
        prev.paste(im.resize((tw, th), Image.LANCZOS), (12 + i * (tw + 12), 12))
    prev.save(OUT / "preview.jpg", quality=90)

    with zipfile.ZipFile(ROOT / "novinki_karusel.zip", "w", zipfile.ZIP_STORED) as z:
        for n in names:
            z.write(OUT / f"{n}.mp4", f"novinki_nedeli/{n}.mp4")
            z.write(OUT / f"{n}.jpg", f"novinki_nedeli/jpg/{n}.jpg")
    print("архив: novinki_karusel.zip")


if __name__ == "__main__":
    main()
