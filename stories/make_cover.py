#!/usr/bin/env python3
"""Обложка-вступление к сторис об услугах (тот же стиль, что make_stories.py)."""
from pathlib import Path
from make_stories import render, ROOT

SLIDE = {
    "image": "src/00_uslugi_cover.jpg",
    "focus_x": 0.3, "placement": "bottom",
    "overlay": "#14110F", "alpha": 225, "text": "#F3E6D3", "accent": "#E8B98A",
    "lines": [
        "# Форматы работы со мной",
        "4 формата: от натальной карты стиля до ведения на 3 месяца.",
        "",
        "**Листай и выбирай своё →**",
    ],
}

if __name__ == "__main__":
    out = ROOT / "output" / "story_00_cover.jpg"
    render(SLIDE, out)
    print("OK", out)
