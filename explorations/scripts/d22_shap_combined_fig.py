# -*- coding: utf-8 -*-
"""Combine the two SHAP beeswarm PNGs into a single two-panel figure."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "explorations/output"


def main():
    a = Image.open(OUT / "d22_shap_delta_published.png").convert("RGB")
    b = Image.open(OUT / "d22_shap_delta_edges.png").convert("RGB")
    target_h = 900
    a = a.resize((int(a.width * target_h / a.height), target_h))
    b = b.resize((int(b.width * target_h / b.height), target_h))
    gap = 30
    pad = 40
    canvas = Image.new("RGB", (a.width + b.width + gap + 2 * pad, target_h + 2 * pad), "white")
    canvas.paste(a, (pad, pad))
    canvas.paste(b, (pad + a.width + gap, pad))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("arial.ttf", 34)
    draw.text((pad, 8), "a  published \u0394pp", fill="black", font=font)
    draw.text((pad + a.width + gap, 8), "b  pure edge increment \u0394_edge", fill="black", font=font)
    canvas.save(OUT / "d22_shap_combined.png")
    print("saved", OUT / "d22_shap_combined.png", canvas.size)


if __name__ == "__main__":
    main()
