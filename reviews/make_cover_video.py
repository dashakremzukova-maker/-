#!/usr/bin/env python3
"""
Обложка карусели «Отзывы»: видео 1080x1350 (MP4, H.264), 30 кадров/с.

Плавный наезд камеры на фото, снизу тёмная подложка как на сторис об
услугах. Заголовок «ОТЗЫВЫ» (Yeseva One) выплывает снизу, под ним по
очереди сменяются короткие цитаты клиенток (Raleway), внизу «Листай →»
с покачивающейся стрелкой. Видео зациклено: в конце текст гаснет,
чтобы повтор начинался мягко.

Запуск: python3 -I make_cover_video.py
На выходе: output/01_cover.mp4 и output/01_cover_preview.jpg (кадр для превью)
"""

import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
FONTS = ROOT.parent / "stories" / "fonts"
OUT = ROOT / "output"

W, H = 1080, 1350
FPS = 30
DUR = 8.0
FOCUS_X = 0.62              # девушка у окна — правее центра
ZOOM = (1.10, 1.0)          # наезд: от крупного к общему плану
OVERLAY = (20, 17, 15)
WHITE = (255, 255, 255)
MARGIN = 84

TITLE = "ОТЗЫВЫ"
QUOTES = [  # дословно из отзывов
    "«Ты всё почувствовала и попала в точку»",
    "«Красивая одежда придаёт уверенность»",
    "«Есть другие цвета помимо серого»",
]
CTA = "Листай"


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def fade(t, start, dur=0.6):
    return ease((t - start) / dur)


def gradient():
    """Тёмная подложка снизу: плотная под текстом, растворяется вверх."""
    mask = Image.new("L", (1, H), 0)
    px = mask.load()
    solid, fadelen = 860, 420
    for y in range(H):
        a = 1.0 if y >= solid else max(0.0, 1 - (solid - y) / fadelen)
        px[0, y] = int(225 * a ** 1.4)
    layer = Image.new("RGBA", (W, H), (*OVERLAY, 255))
    layer.putalpha(mask.resize((W, H)))
    return layer


def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if f.getlength(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def text_layer(lines, f, x, y, alpha, lh):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, ln in enumerate(lines):
        d.text((x, y + i * lh), ln, font=f, fill=(*WHITE, int(255 * alpha)))
    return layer


def main():
    OUT.mkdir(exist_ok=True)
    src = ImageOps.exif_transpose(Image.open(ROOT / "src" / "cover.jpg")).convert("RGB")
    # базовый кадр с запасом под наезд
    big_w = int(W * ZOOM[0])
    big_h = int(H * ZOOM[0])
    base = ImageOps.fit(src, (big_w, big_h), Image.LANCZOS, centering=(FOCUS_X, 0.5))
    grad = gradient()

    f_title = font("YesevaOne-400.ttf", 120)
    f_quote = font("Raleway-400.ttf", 44)
    f_cta = font("Raleway-600.ttf", 38)
    f_arrow = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)

    title_y = 900
    quote_y = title_y + 150
    cta_y = H - 120
    q_lines = [wrap(q, f_quote, W - 2 * MARGIN) for q in QUOTES]

    q_start, q_len = 1.4, 1.9          # каждая цитата ~1.9 с
    out_start = DUR - 0.6              # всё гаснет перед повтором

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = OUT / "01_cover.mp4"
    proc = subprocess.Popen(
        [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
         "-profile:v", "high", "-movflags", "+faststart", str(mp4)],
        stdin=subprocess.PIPE)

    n = int(DUR * FPS)
    preview = None
    for i in range(n):
        t = i / FPS
        # наезд камеры
        z = ZOOM[0] + (ZOOM[1] - ZOOM[0]) * (i / (n - 1))
        cw, ch = min(big_w, round(big_w / z)), min(big_h, round(big_h / z))
        left = int((big_w - cw) * FOCUS_X)
        top = (big_h - ch) // 2
        frame = base.crop((left, top, left + cw, top + ch)).resize((W, H), Image.LANCZOS).convert("RGBA")
        frame.alpha_composite(grad)

        out = 1 - ease((t - out_start) / 0.6)
        # заголовок выплывает снизу
        a = fade(t, 0.3, 0.9) * out
        dy = int(40 * (1 - fade(t, 0.3, 0.9)))
        frame.alpha_composite(text_layer([TITLE], f_title, MARGIN, title_y + dy, a, 0))

        # цитаты сменяют друг друга
        k = int((t - q_start) // q_len)
        if t >= q_start and k < len(QUOTES):
            local = t - q_start - k * q_len
            qa = min(ease(local / 0.4), 1 - ease((local - (q_len - 0.4)) / 0.4)) * out
            if k == len(QUOTES) - 1:
                qa = ease(local / 0.4) * out  # последняя держится до конца
            frame.alpha_composite(text_layer(q_lines[k], f_quote, MARGIN, quote_y, qa, 58))

        # «Листай →» с покачивающейся стрелкой
        ca = fade(t, 1.0, 0.6) * out
        if ca > 0:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.text((MARGIN, cta_y), CTA, font=f_cta, fill=(*WHITE, int(255 * ca)))
            nudge = 10 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 1.2))
            ax = MARGIN + f_cta.getlength(CTA + " ") + nudge
            d.text((ax, cta_y + 4), "→", font=f_arrow, fill=(*WHITE, int(255 * ca)))
            frame.alpha_composite(layer)

        rgb = frame.convert("RGB")
        proc.stdin.write(rgb.tobytes())
        if abs(t - (q_start + 0.9)) < 0.5 / FPS:
            preview = rgb
    proc.stdin.close()
    proc.wait()
    (preview or rgb).save(OUT / "01_cover_preview.jpg", quality=92)
    print("OK", mp4, f"{n} кадров, {DUR} с")


if __name__ == "__main__":
    main()
