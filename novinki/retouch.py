#!/usr/bin/env python3
"""
Ретушь кожи лица для фото карусели.

В заданных зонах лица (доли кадра) ищем кожу по цвету (YCrCb), сглаживаем
её фильтром, сохраняющим края (глаза, брови, губы остаются резкими),
и возвращаем часть мелкой текстуры, чтобы кожа не выглядела пластиковой.
Чуть выравниваем тон и высветляем. Маска растушёвана — швов не видно.

Запуск: python3 -I retouch.py
Берёт src/*.jpg, пишет src/retouched/*.jpg
"""

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = SRC / "retouched"

# зоны лиц: (x0, y0, x1, y1) в долях кадра — с запасом, кожа ищется внутри
FACES = {
    "photo": [(0.48, 0.07, 0.76, 0.26), (0.0, 0.08, 0.30, 0.28)],
    "look_01": [(0.55, 0.10, 0.80, 0.26), (0.0, 0.12, 0.25, 0.30)],
    "look_02": [(0.58, 0.15, 0.85, 0.32)],
    "look_03": [(0.0, 0.22, 0.20, 0.40), (0.66, 0.22, 0.90, 0.36)],
    "look_04": [(0.55, 0.13, 0.78, 0.27), (0.18, 0.11, 0.40, 0.26)],
    "look_05": [(0.0, 0.17, 0.22, 0.34), (0.50, 0.15, 0.80, 0.33)],
    "look_06": [(0.30, 0.03, 0.72, 0.30)],
    "look_07": [(0.45, 0.20, 0.70, 0.36)],
}

STRENGTH = 0.75     # насколько сильно подмешиваем сглаженную кожу
TEXTURE = 0.35      # сколько мелкой текстуры возвращаем


def skin_mask(img):
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycc)
    m = ((cr >= 135) & (cr <= 178) & (cb >= 82) & (cb <= 130) & (y >= 50)).astype(np.float32)
    return m


def retouch_zone(crop, feather):
    mask = skin_mask(crop)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.GaussianBlur(mask, (31, 31), 0) * feather
    if mask.max() == 0:
        return crop

    # сглаживание с сохранением краёв, в два прохода
    smooth = cv2.bilateralFilter(crop, 11, 28, 9)
    smooth = cv2.bilateralFilter(smooth, 15, 22, 14)

    f = crop.astype(np.float32)
    s = smooth.astype(np.float32)
    # мелкая текстура (поры) — разница с лёгким размытием
    fine = f - cv2.GaussianBlur(f, (0, 0), 1.6)
    s = s + TEXTURE * fine
    # тон: чуть светлее и ровнее
    s = s * 1.03 + 2

    a = (mask * STRENGTH)[..., None]
    return np.clip(f * (1 - a) + s * a, 0, 255).astype(np.uint8)


def retouch(img, boxes):
    """Обрабатываем только зоны лиц: вырезаем, ретушируем, вставляем обратно
    с растушёванным краем."""
    h, w = img.shape[:2]
    out = img.copy()
    for x0, y0, x1, y1 in boxes:
        xa, ya, xb, yb = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
        crop = out[ya:yb, xa:xb]
        ch, cw = crop.shape[:2]
        feather = np.zeros((ch, cw), np.float32)
        pad = int(min(ch, cw) * 0.12)
        feather[pad:ch - pad, pad:cw - pad] = 1.0
        k = (pad * 2) | 1
        feather = cv2.GaussianBlur(feather, (k, k), 0)
        out[ya:yb, xa:xb] = retouch_zone(crop, feather)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    for name, boxes in FACES.items():
        img = cv2.imread(str(SRC / f"{name}.jpg"))
        cv2.imwrite(str(OUT / f"{name}.jpg"), retouch(img, boxes), [cv2.IMWRITE_JPEG_QUALITY, 93])
        print("ретушь:", name)


if __name__ == "__main__":
    main()
