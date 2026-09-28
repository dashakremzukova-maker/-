#!/usr/bin/env python3
"""
Обложки для актуальных из фото (папка «Фото для иконок» на Google Диске).

Каждое фото кадрируется так, чтобы главный предмет оказался в центральном
круге 1080x1080 кадра 1080x1920 (эту часть Instagram показывает в кружке).
Остальная часть кадра заполняется тем же фото; если его не хватает по
высоте, края заливаются однотонным цветом фото.

Параметры на фото:
  center — точка фото (доли 0..1), которая встанет в центр круга
  side   — сторона квадрата вокруг центра в долях ширины фото
           (меньше = крупнее план)

Запуск: python3 make_photo_covers.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parent
W, H = 1080, 1920

COVERS = [
    ("01_uslugi", {"center": (0.55, 0.62), "side": 0.85}),
    ("02_otzyvy", {"center": (0.50, 0.50), "side": 1.0}),
    ("03_keisy", {"center": (0.50, 0.55), "side": 0.88}),
    ("04_obo_mne", {"center": (0.62, 0.42), "side": 0.75}),
]


def cover(src, center, side):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    scale = W / (side * img.width)
    big = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    cx, cy = center[0] * big.width, center[1] * big.height
    left, top = round(cx - W / 2), round(cy - H / 2)

    # фон: однотонный, в средний цвет краёв фото (виден, только если фото
    # не хватает по высоте; в кружок актуального не попадает)
    band = max(4, img.height // 40)
    top_c = ImageStat.Stat(img.crop((0, 0, img.width, band))).mean
    bot_c = ImageStat.Stat(img.crop((0, img.height - band, img.width, img.height))).mean
    bg = Image.new("RGB", (W, H), tuple(int(v) for v in top_c))
    bg.paste(tuple(int(v) for v in bot_c), (0, H // 2, W, H))
    bg.paste(big, (-left, -top))
    return bg


def preview(images):
    d, pad = 220, 40
    sheet = Image.new("RGB", (pad + len(images) * (d + pad), d + 2 * pad), (255, 255, 255))
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    draw = ImageDraw.Draw(sheet)
    for i, im in enumerate(images):
        top = (H - W) // 2
        c = im.crop((0, top, W, top + W)).resize((d, d), Image.LANCZOS)
        x = pad + i * (d + pad)
        draw.ellipse([x - 8, pad - 8, x + d + 8, pad + d + 8], outline=(210, 205, 200), width=3)
        sheet.paste(c, (x, pad), mask)
    return sheet


def main():
    out = ROOT / "output" / "photo"
    out.mkdir(parents=True, exist_ok=True)
    imgs = []
    for name, p in COVERS:
        im = cover(ROOT / "src" / f"{name}.jpg", p["center"], p["side"])
        im.save(out / f"{name}.jpg", quality=93)
        imgs.append(im)
        print("OK", name)
    preview(imgs).save(ROOT / "preview_photo.png")


if __name__ == "__main__":
    main()
