#!/usr/bin/env python3
"""
Карусель «Новинки недели»: 8 слайдов 1080x1350.

  01 обложка — видео (MP4, H.264, 30 к/с): фото стоит на месте,
     всплывает только заголовок «НОВИНКИ НЕДЕЛИ»;
  02–08 — статичные JPG: фото образа, «ОБРАЗ 0N», название, одна фраза
     и строка «АРТИКУЛЫ В ДИРЕКТ»; на последнем слайде — крупный призыв.

Фото берутся из src/retouched (сначала запустить retouch.py — ретушь кожи лица).
Стиль «Минимал» (вариант 4 из variants.py): Tenor Sans — капс с разрядкой,
Jost — текст.

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

# цвета надписей: основной и акцентный (подбор — в colors.py)
MAIN = WHITE
ACCENT = (190, 186, 180)  # светло-серый — палитра 4 «Белый монохром»



def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


# стиль «Минимал»: Tenor Sans (капс с разрядкой) + Jost (текст)
F_CAPS = font("TenorSans-400.ttf", 64)
F_SMALL = font("TenorSans-400.ttf", 26)
F_BODY = font("Jost-400.ttf", 36)
F_ASK = font("TenorSans-400.ttf", 40)

# прежний стиль (Yeseva One + Raleway) — нужен для листа вариантов variants.py
F_TITLE = font("YesevaOne-400.ttf", 92)
F_TITLE_S = font("YesevaOne-400.ttf", 66)
F_NUM_S = font("YesevaOne-400.ttf", 120)
F_TEXT = font("Raleway-400.ttf", 38)
F_TEXT_B = font("Raleway-600.ttf", 38)
F_NOTE = font("Raleway-400.ttf", 34)

ASK = "АРТИКУЛЫ В ДИРЕКТ · «ХОЧУ»"


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

def gradient(solid=880, fadelen=460):
    """Тёмная подложка снизу."""
    mask = Image.new("L", (1, H), 0)
    px = mask.load()
    for y in range(H):
        a = 1.0 if y >= solid else max(0.0, 1 - (solid - y) / fadelen)
        v = 225 * a ** 1.4
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


def text(img, s, f, y, alpha, color=None, x=None, track=0, dx=0, dy=0):
    if alpha <= 0:
        return
    color = color or MAIN
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


# ---------- слайды ----------

# образы по порядку: фото (src/retouched), название капсом, одна фраза
# и необязательный масштаб фото (<1 — фото меньше, низ образа выше подписи)
LOOKS = [
    ("look_01", "КАРГО-КАМУФЛЯЖ",
     "Утилитарный кэжуал — самый стильный антигламур осени."),
    ("look_02", "КОСТЮМ С ПОЯСОМ",
     "Сильные плечи и подчёркнутая талия — классика на выход."),
    ("look_03", "ЖАКЕТ САФАРИ",
     "Молочный, с баской и поясом — графичный контраст с чёрным."),
    ("look_04", "МИНИ К ЖАКЕТУ",
     "Смешение стилей — главный приём сезона. Бордо — новый чёрный."),
    ("look_05", "ТРИКОТАЖ",
     "Осень тактильных фактур: уют, который выглядит дорого."),
    ("look_06", "ПЛАТЬЕ С МЕХОМ",
     "Мех ушёл в детали — тот самый dark romance.", 0.74),
    ("look_07", "КУРТКА С МЕХОМ",
     "Шоколадный — база сезона, укороченная длина — главный акцент.", 0.9),
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


def fit_caps(s, f, track, maxw):
    """Капс с разрядкой: уменьшаем кегль, если строка не влезает."""
    size = f.size
    while spaced_width(s, f, track) > maxw and size > 30:
        size -= 2
        f = font(Path(f.path).name, size)
    return f


def cover_frame(src):
    """Обложка: фото стоит на месте, всплывает только заголовок."""
    base = crop45(src, 0.0)
    base.alpha_composite(gradient(solid=900, fadelen=520))
    d = ImageDraw.Draw(base)
    d.line([(W / 2 - 40, 1085), (W / 2 + 40, 1085)], fill=(*ACCENT, 255), width=2)
    text(base, "7 ОБРАЗОВ", F_SMALL, 1115, 1, ACCENT, track=10)

    def frame(t):
        img = base.copy()
        fo = out_fade(t)
        a = appear(t, 0.3, 1.0) * fo
        text(img, "НОВИНКИ", F_CAPS, 880, a, track=22, dy=60 * (1 - a))
        a2 = appear(t, 0.55, 1.0) * fo
        text(img, "НЕДЕЛИ", F_CAPS, 970, a2, track=22, dy=60 * (1 - a2))
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
    y = 0 if scale == 1.0 else 60  # уменьшенное фото — с небольшим отступом сверху
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([x - 6, y, x + fg.width + 6, y + fh], fill=(0, 0, 0, 150))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    bg.alpha_composite(fg, (x, y))
    return bg


def look_slide(src, num, name, phrase, last, scale=1.0):
    img = full_look(src, scale)
    lines = wrap(phrase, F_BODY, W - 2 * MARGIN)
    ask_y = H - 78 - (70 if last else 0)
    body_y = ask_y - 46 - len(lines) * 46
    name_y = body_y - 100
    label_y = name_y - 40
    img.alpha_composite(gradient(solid=label_y + 120, fadelen=320))

    text(img, f"ОБРАЗ {num}", F_SMALL, label_y, 1, ACCENT, x=MARGIN, track=10)
    text(img, name, fit_caps(name, F_CAPS, 12, W - 2 * MARGIN), name_y, 1, x=MARGIN, track=12)
    for k, ln in enumerate(lines):
        text(img, ln, F_BODY, body_y + k * 46, 1, x=MARGIN)
    if last:
        # крупный призыв на последнем слайде
        d = ImageDraw.Draw(img)
        d.line([(MARGIN, ask_y - 6), (MARGIN + 80, ask_y - 6)], fill=(*ACCENT, 255), width=2)
        text(img, "ХОЧЕШЬ АРТИКУЛЫ?", F_ASK, ask_y + 20, 1, x=MARGIN, track=8)
        text(img, "ПИШИ «ХОЧУ» В ДИРЕКТ", F_ASK, ask_y + 76, 1, ACCENT, x=MARGIN, track=8)
    else:
        text(img, ASK, F_SMALL, ask_y + 6, 1, ACCENT, x=MARGIN, track=8)
    return img.convert("RGB")


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()

    render("01_oblozhka", cover_frame(load("photo")))
    names = ["01_oblozhka.mp4"]
    for i, (fn, name, phrase, *opt) in enumerate(LOOKS):
        slug = f"{i + 2:02d}_obraz_{i + 1}"
        img = look_slide(load(fn), f"{i + 1:02d}", name, phrase, i == len(LOOKS) - 1, *opt)
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
