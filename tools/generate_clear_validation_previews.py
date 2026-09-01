from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generate_liquid27 import (
    ROOT,
    FONT_REG,
    GEOMETRY_FOCUS,
    HOME_SHOW,
    QUICK_NAMES,
    _paste_wallpaper_icon,
    render,
)
from liquid27.catalog import ICON_SPECS

OUTDIR = ROOT / 'build/liquid27-v4/clear'


def _rails(d: ImageDraw.ImageDraw, w: int, h: int, light=(240, 238, 240), dark=(38, 37, 43)) -> None:
    d.arc((-320, -260, 900, 680), 8, 125, fill=light, width=6)
    d.arc((-200, 300, 1320, 1200), 6, 126, fill=light, width=5)
    d.arc((250, 790, 1510, 1820), 194, 316, fill=light, width=5)
    d.line((0, int(h * .53), w, int(h * .43)), fill=dark, width=11)


def _color_test_wallpaper(w: int = 1080, h: int = 1640) -> Image.Image:
    """Four-region wallpaper: purple, pink/red, blue and warm/orange."""
    wall = Image.new('RGB', (w, h), (92, 70, 104))
    d = ImageDraw.Draw(wall)
    half_w = w // 2
    half_h = h // 2
    d.rectangle((0, 0, half_w, half_h), fill=(111, 75, 144))
    d.rectangle((half_w, 0, w, half_h), fill=(181, 70, 91))
    d.rectangle((0, half_h, half_w, h), fill=(52, 102, 166))
    d.rectangle((half_w, half_h, w, h), fill=(190, 112, 48))
    _rails(d, w, h)
    return wall


def _neutral_test_wallpaper(w: int = 1080, h: int = 1640) -> Image.Image:
    wall = Image.new('RGB', (w, h), (128, 128, 128))
    d = ImageDraw.Draw(wall)
    d.rectangle((0, 0, w // 2, h), fill=(104, 104, 104))
    d.rectangle((w // 2, 0, w, h), fill=(152, 152, 152))
    _rails(d, w, h, light=(224, 224, 224), dark=(66, 66, 66))
    return wall


def _single_wallpaper(kind: str, w: int = 1080, h: int = 1640) -> Image.Image:
    palettes = {
        'warm': ((102, 69, 49), (186, 124, 70), (75, 49, 39)),
        'blue': ((29, 63, 120), (54, 112, 190), (21, 43, 82)),
        'dark': ((18, 18, 21), (42, 43, 49), (8, 9, 12)),
        'bright': ((232, 229, 224), (250, 247, 240), (207, 211, 218)),
    }
    base, accent, low = palettes[kind]
    wall = Image.new('RGB', (w, h), base)
    d = ImageDraw.Draw(wall)
    d.ellipse((-280, -220, int(w * .78), int(h * .62)), fill=accent)
    d.ellipse((int(w * .35), int(h * .42), int(w * 1.28), int(h * 1.08)), fill=low)
    light = (246, 244, 242) if kind != 'bright' else (112, 112, 118)
    dark = (25, 24, 28) if kind != 'dark' else (180, 182, 188)
    _rails(d, w, h, light=light, dark=dark)
    return wall


def _images() -> dict[str, Image.Image]:
    result = {}
    for name in QUICK_NAMES:
        if name not in ICON_SPECS:
            continue
        bg, kind, _ = ICON_SPECS[name]
        result[name] = render(name, bg, kind, 'clear')
    return result


def _render_grid(wall: Image.Image, images: dict[str, Image.Image], names: list[str], home: bool = False) -> Image.Image:
    d = ImageDraw.Draw(wall)
    font = ImageFont.truetype(FONT_REG, 24 if home else 22)
    if home:
        chosen = [n for n in names if n in images][:20]
        for i, name in enumerate(chosen):
            x = 92 + (i % 4) * 245
            y = 270 + (i // 4) * 245
            _paste_wallpaper_icon(wall, images, name, x, y, 122, 'clear')
            label = name[6:].replace('_', ' ')[:13]
            box = d.textbbox((0, 0), label, font=font)
            d.text((x + 61 - (box[2] - box[0]) / 2, y + 136), label, font=font, fill=(248, 248, 248))
    else:
        chosen = [n for n in names if n in images][:20]
        for i, name in enumerate(chosen):
            x = 72 + (i % 4) * 250
            y = 90 + (i // 4) * 270
            _paste_wallpaper_icon(wall, images, name, x, y, 126, 'clear')
            label = name[6:].replace('_', ' ')[:14]
            box = d.textbbox((0, 0), label, font=font)
            d.text((x + 63 - (box[2] - box[0]) / 2, y + 139), label, font=font, fill=(248, 248, 248))
    return wall


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    images = _images()

    _render_grid(_color_test_wallpaper(), images, GEOMETRY_FOCUS).save(OUTDIR / 'preview_color_wallpaper.png')
    _render_grid(_color_test_wallpaper(1080, 1920), images, HOME_SHOW, home=True).save(OUTDIR / 'preview_home_color.png')
    _render_grid(_neutral_test_wallpaper(), images, GEOMETRY_FOCUS).save(OUTDIR / 'preview_neutral_wallpaper.png')

    for kind in ('warm', 'blue', 'dark', 'bright'):
        _render_grid(_single_wallpaper(kind), images, GEOMETRY_FOCUS).save(OUTDIR / f'preview_{kind}_wallpaper.png')

    print('Generated Clear validation previews: color, home color, neutral, warm, blue, dark, bright.')


if __name__ == '__main__':
    main()
