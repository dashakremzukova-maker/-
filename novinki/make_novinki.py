#!/usr/bin/env python3
"""
Карусель «Новинки недели»: 8 слайдов 1080x1350.

  01 обложка — видео (MP4, H.264, 30 к/с): фото стоит на месте,
     всплывает только заголовок «НОВИНКИ НЕДЕЛИ»;
  02–08 — статичные JPG: фото образа, номер, название, подпись
     и короткий комментарий стилиста.

Фото берутся из src/retouched (сначала запустить retouch.py — ретушь кожи лица).
Шрифты как на прошлых каруселях: Yeseva One (заголовки, капс с разрядкой
и тонкими линиями по бокам) и Raleway (текст).

Запуск: python3 -I retouch.py && python3 -I make_novinki.py
На выходе: output/01_oblozhka.mp4, output/0N_obraz_*.jpg, preview.jpg, novinki_karusel.zip
"""

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

TOTAL = 8


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


F_TITLE = font("YesevaOne-400.ttf", 92)
F_TITLE_S = font("YesevaOne-400.ttf", 66)
F_NUM = font("YesevaOne-400.ttf", 150)
F_KICK = font("Raleway-600.ttf", 28)
F_TEXT = font("Raleway-400.ttf", 38)
F_TEXT_B = font("Raleway-600.ttf", 38)
F_NOTE = font("Raleway-400.ttf", 34)
F_NUM_S = font("YesevaOne-400.ttf", 120)
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


def dots(img, idx, alpha):
    """Индикатор слайда сверху справа: 01 / 05."""
    s = f"{idx:02d} / {TOTAL:02d}"
    text(img, s, F_KICK, 64, alpha * 0.85, WHITE, x=W - MARGIN - spaced_width(s, F_KICK, 4), track=4)


def kicker(img, s, alpha):
    text(img, s, F_KICK, 64, alpha * 0.85, WHITE, x=MARGIN, track=6)


# ---------- слайды ----------

# образы по порядку: фото (src/retouched), название, подпись, комментарий стилиста
# и необязательный масштаб фото (<1 — фото меньше, низ образа выше подписи)
LOOKS = [
    ("look_01", "КАРГО", "в тёмный камуфляж",
     "Укороченный топ и низкая посадка открывают талию — силуэт сразу стройнее."),
    ("look_02", "КОСТЮМ", "графитовый, с поясом",
     "Широкий ремень поверх жакета делает костюм не офисным, а модным."),
    ("look_03", "САФАРИ", "молочный жакет с баской",
     "С чёрными брюками и лодочками — готовый образ на работу и встречи."),
    ("look_04", "МИНИ", "бордовая, к тому же жакету",
     "Грубые челси и мини превращают деловой жакет в дерзкий образ на вечер."),
    ("look_05", "ТРИКОТАЖ", "пушистый комплект",
     "Укороченный кардиган с золотыми пуговицами и длинная юбка — уютно и дорого."),
    ("look_06", "ПЛАТЬЕ", "с меховым подолом",
     "Лаконичный чёрный силуэт, весь акцент — на пушистом крае. Добавь жемчуг.", 0.74),
    ("look_07", "КУРТКА", "с меховым воротником",
     "Шоколад, фактурный трикотаж и белые джинсы — тёплая и светлая осень.", 0.9),
]


def load(name):
    p = ROOT / "src" / "retouched" / f"{name}.jpg"
    return ImageOps.exif_transpose(Image.open(p)).convert("RGB")


def crop45(src, top, cx=0.5):
    """Кадр 4:5 на всю ширину исходника, начиная с доли top по высоте."""
    sw, sh = src.size
    cw = sw
    ch = cw * H / W
    y = min(max(0, sh * top), sh - ch)
    return src.resize((W, H), Image.LANCZOS, box=(0, y, cw, y + ch)).convert("RGBA")


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


def badge():
    r = 82
    b = Image.new("RGBA", (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
    bd = ImageDraw.Draw(b)
    bd.ellipse([4, 4, 2 * r + 4, 2 * r + 4], fill=(*BORDO, 255), outline=(*PEACH, 255), width=3)
    tw = spaced_width("NEW", F_BADGE, 4)
    bb = F_BADGE.getbbox("N")
    draw_spaced(bd, "NEW", F_BADGE, r + 4 - tw / 2, r + 4 - (bb[1] + bb[3]) / 2, 4, (*WHITE, 255))
    return b.rotate(-12, Image.BICUBIC, expand=True), r


def static_cta(img, label):
    wl = F_CTA.getlength(label)
    wa = F_ARROW.getlength("→")
    x = (W - wl - 16 - wa) / 2
    y = H - 104
    text(img, label, F_CTA, y, 1, PEACH, x=x)
    text(img, "→", F_ARROW, y + 2, 1, PEACH, x=x + wl + 16)


def cover_frame(src):
    """Обложка: фото стоит на месте, всплывает только заголовок."""
    lines = ["7 образов из примерочной", "от камуфляжа до меха"]
    base = crop45(src, 0.0)
    base.alpha_composite(gradient(solid=900, fadelen=520, top=True))
    kicker(base, "ПРИМЕРОЧНАЯ · ОКТЯБРЬ", 1)
    dots(base, 1, 1)
    for i, ln in enumerate(lines):
        text(base, ln, F_TEXT, 1030 + i * 54, 1)
    b, r = badge()
    base.alpha_composite(b, (int(W - MARGIN - r + 10 - b.width / 2), int(210 - b.height / 2)))
    static_cta(base, "Листай")

    def frame(t):
        img = base.copy()
        fo = out_fade(t)
        a = appear(t, 0.3, 1.0) * fo
        title(img, "НОВИНКИ", F_TITLE, 780, a, appear(t, 0.9, 0.9) * fo, dy=60 * (1 - a))
        a2 = appear(t, 0.55, 1.0) * fo
        title(img, "НЕДЕЛИ", F_TITLE, 890, a2, 0, dy=60 * (1 - a2))
        return img

    return frame


def full_look(src, scale=1.0):
    """Образ целиком: фото по всей высоте по центру, по бокам — размытое
    и затемнённое это же фото, чтобы ничего не обрезать."""
    bg = ImageOps.fit(src, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(45)).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", (W, H), (*OVERLAY, 120)))
    fh = int(H * scale)
    fg = src.resize((int(src.width * fh / src.height), fh), Image.LANCZOS).convert("RGBA")
    x = (W - fg.width) // 2
    y = 0 if scale == 1.0 else 110  # уменьшенное фото — с отступом под кикер
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([x - 6, y, x + fg.width + 6, y + fh], fill=(0, 0, 0, 150))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    bg.alpha_composite(fg, (x, y))
    return bg


def look_slide(src, idx, num, name, sub, note, last, scale=1.0):
    img = full_look(src, scale)
    img.alpha_composite(gradient(solid=1090, fadelen=320, top=True))
    kicker(img, "НОВИНКИ НЕДЕЛИ", 1)
    dots(img, idx, 1)

    lines = wrap(note, F_NOTE, W - 2 * MARGIN)
    note_y = H - 70 - len(lines) * 44 - (56 if last else 0)
    sub_y = note_y - 64
    name_y = sub_y - 84
    text(img, num, F_NUM_S, name_y - 34, 0.9, PEACH, x=MARGIN)
    nx = MARGIN + F_NUM_S.getlength(num) + 30
    text(img, name, F_TITLE_S, name_y, 1, x=nx, track=10)
    text(img, sub, F_TEXT_B, sub_y, 1, PEACH, x=nx)
    for k, ln in enumerate(lines):
        text(img, ln, F_NOTE, note_y + k * 44, 1, x=MARGIN)
    if last:
        text(img, "Сохрани, чтобы не потерять", F_CTA, H - 96, 1, PEACH)
    return img.convert("RGB")


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()

    render("01_oblozhka", cover_frame(load("photo")))
    names = ["01_oblozhka.mp4"]
    for i, (fn, name, sub, note, *opt) in enumerate(LOOKS):
        slug = f"{i + 2:02d}_obraz_{i + 1}"
        img = look_slide(load(fn), i + 2, f"{i + 1:02d}", name, sub, note, i == len(LOOKS) - 1, *opt)
        img.save(OUT / f"{slug}.jpg", quality=94)
        names.append(f"{slug}.jpg")
        print("готово:", slug)

    thumbs = [Image.open(OUT / "01_oblozhka.jpg")] + [Image.open(OUT / n) for n in names[1:]]
    tw, th = 270, 338
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    prev = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 12) + 12), (243, 235, 227))
    for i, im in enumerate(thumbs):
        prev.paste(im.resize((tw, th), Image.LANCZOS), (12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 12)))
    prev.save(ROOT / "preview.jpg", quality=90)

    with zipfile.ZipFile(ROOT / "novinki_karusel.zip", "w", zipfile.ZIP_STORED) as z:
        for n in names:
            z.write(OUT / n, f"novinki_nedeli/{n}")
        z.write(OUT / "01_oblozhka.jpg", "novinki_nedeli/01_oblozhka_static.jpg")
    print("архив: novinki_karusel.zip")


if __name__ == "__main__":
    main()
