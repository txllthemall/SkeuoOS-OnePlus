from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from liquid27.material import (
    WORK, OUT, ENCL, FONT_REG, blank_mask, union, rgb, luminance,
    background, composite_layer, finish_enclosure,
)
from liquid27.geometry import (
    glyph as production_glyph,
    geometry_owner,
    PRODUCTION_KINDS,
)
from liquid27.clear_material import (
    clearify_layers,
    clear_background,
    finish_clear_enclosure,
    clear_reflection_coverage_pct,
    reflection_style,
    preview_refract_patch,
    material_metrics,
)
from liquid27.geometry_meta import geometry_meta
from liquid27.catalog import ICON_SPECS

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('color', 'clear')

GEOMETRY_FOCUS = [
    'skeuo_gamehub', 'skeuo_github', 'skeuo_playstore', 'skeuo_kaspi',
    'skeuo_pinterest', 'skeuo_telegram', 'skeuo_gmail', 'skeuo_discord',
    'skeuo_facebook', 'skeuo_reddit', 'skeuo_tiktok', 'skeuo_whatsapp',
    'skeuo_twitter', 'skeuo_steam', 'skeuo_snapchat', 'skeuo_instagram',
    'skeuo_amazon', 'skeuo_paypal', 'skeuo_strava', 'skeuo_google_drive',
    'skeuo_chatgpt', 'skeuo_spotify', 'skeuo_youtube', 'skeuo_revanced',
    'skeuo_chrome', 'skeuo_soundcloud', 'skeuo_2gis',
]

HOME_SHOW = [
    'skeuo_phone', 'skeuo_messages', 'skeuo_camera', 'skeuo_photos', 'skeuo_settings',
    'skeuo_gmail', 'skeuo_maps', 'skeuo_clock', 'skeuo_weather', 'skeuo_notes',
    'skeuo_calendar', 'skeuo_playstore', 'skeuo_telegram', 'skeuo_discord', 'skeuo_youtube',
    'skeuo_chrome', 'skeuo_spotify', 'skeuo_instagram', 'skeuo_chatgpt', 'skeuo_gamehub',
    'skeuo_github', 'skeuo_kaspi', 'skeuo_pinterest', 'skeuo_steam', 'skeuo_whatsapp',
]
QUICK_NAMES = list(dict.fromkeys(GEOMETRY_FOCUS + HOME_SHOW))


def base_layers(kind):
    """The only production geometry entry point. No fallback chain exists."""
    return production_glyph(kind)


def layers_for(kind, variant='color', key=None):
    layers = base_layers(kind)
    if variant == 'clear':
        return clearify_layers(layers, key or kind)
    return layers


def render(name, bgspec, kind, variant='color'):
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))
    if variant == 'clear':
        canvas.alpha_composite(clear_background(name))
    else:
        canvas.alpha_composite(background(bgspec))

    for lay in layers_for(kind, variant, name):
        composite_layer(canvas, **lay)

    if variant == 'clear':
        finish_clear_enclosure(canvas, name)
    else:
        finish_enclosure(canvas)
        canvas.putalpha(ENCL)

    return canvas.resize((OUT, OUT), Image.Resampling.LANCZOS)


def output_paths(variant):
    return (
        ROOT / f'app/src/{variant}/res/drawable-nodpi',
        ROOT / f'build/liquid27-v4/{variant}',
    )


def _foreground_mask(name):
    kind = ICON_SPECS[name][1]
    fg = blank_mask()
    for lay in base_layers(kind):
        fg = union(fg, lay['mask'])
    return fg


def _sheet(images, outpath, bg, names, cols=5, icon_size=132):
    names = [n for n in names if n in images]
    font = ImageFont.truetype(FONT_REG, 18)
    cell = 190
    row_h = 205
    rows = max(1, math.ceil(len(names) / cols))
    can = Image.new('RGB', (cols * cell + 60, rows * row_h + 60), rgb(bg))
    d = ImageDraw.Draw(can)
    fg = (235, 235, 238) if luminance(bg) < 128 else (34, 34, 38)
    for i, name in enumerate(names):
        x = 30 + (i % cols) * cell
        y = 30 + (i // cols) * row_h
        ic = images[name].resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        can.paste(ic, (x + (cell - icon_size) // 2, y), ic)
        label = name[6:].replace('_', ' ')[:18]
        b = d.textbbox((0, 0), label, font=font)
        d.text((x + cell / 2 - (b[2] - b[0]) / 2, y + icon_size + 12), label, font=font, fill=fg)
    can.save(outpath)


def _wallpaper_canvas(w=1080, h=1640):
    """Programmatic optical test wallpaper; deliberately not an AI image."""
    wall = Image.new('RGB', (w, h), '#6c596b')
    for col, xy, rad in [
        ('#d9a4a7', (230, 260), 720),
        ('#776f98', (850, 420), 760),
        ('#51455d', (780, 1240), 940),
    ]:
        m = ImageOps.invert(Image.radial_gradient('L').resize((rad, rad))).point(lambda v: int(v * .68))
        fm = Image.new('L', (w, h), 0)
        fm.paste(m, (xy[0] - rad // 2, xy[1] - rad // 2))
        wall = Image.composite(Image.new('RGB', (w, h), rgb(col)), wall, fm)

    wd = ImageDraw.Draw(wall)
    # Thin high-contrast rails cross icon cells. In a valid Clear preview these
    # rails bend subtly inside the lens instead of merely dimming underneath it.
    wd.arc((-300, -260, 850, 650), 8, 122, fill=(244, 236, 240), width=6)
    wd.arc((-180, 260, 1320, 1120), 8, 126, fill=(236, 228, 236), width=5)
    wd.arc((250, 750, 1500, 1800), 195, 315, fill=(236, 228, 236), width=5)
    wd.line((0, 820, w, 690), fill=(82, 69, 82), width=12)
    return wall


def _paste_wallpaper_icon(wall, images, name, x, y, size, variant):
    ic = images[name].resize((size, size), Image.Resampling.LANCZOS)
    if variant == 'clear':
        patch = wall.crop((x, y, x + size, y + size)).convert('RGB')
        patch = preview_refract_patch(patch, _foreground_mask(name))
        wall.paste(patch, (x, y))
    wall.paste(ic, (x, y), ic)


def preview(images, outdir, variant, quick=False):
    show = [n for n in HOME_SHOW if n in images]
    focus = [n for n in GEOMETRY_FOCUS if n in images]

    _sheet(images, outdir / 'preview_light.png', '#eff0f3', show)
    _sheet(images, outdir / 'preview_dark.png', '#17181c', show)
    _sheet(images, outdir / 'preview_geometry_focus.png', '#252936', focus, cols=4, icon_size=144)
    _sheet(images, outdir / f'preview_{variant}_light.png', '#eff0f3', show)
    _sheet(images, outdir / f'preview_{variant}_dark.png', '#17181c', show)

    if not quick:
        _sheet(images, outdir / 'preview_vector_reference.png', '#17181c', list(images.keys()), cols=4, icon_size=144)
        _sheet(images, outdir / 'preview_full.png', '#17181c', list(images.keys()), cols=6, icon_size=118)

    wall = _wallpaper_canvas()
    d = ImageDraw.Draw(wall)
    font = ImageFont.truetype(FONT_REG, 22)
    for i, name in enumerate(focus[:20]):
        x = 72 + (i % 4) * 250
        y = 90 + (i // 4) * 270
        _paste_wallpaper_icon(wall, images, name, x, y, 126, variant)
        label = name[6:].replace('_', ' ')[:14]
        b = d.textbbox((0, 0), label, font=font)
        d.text((x + 63 - (b[2] - b[0]) / 2, y + 139), label, font=font, fill=(249, 247, 250))
    wall.save(outdir / 'preview_wallpaper.png')
    wall.save(outdir / f'preview_{variant}_wallpaper.png')

    hs = _wallpaper_canvas(1080, 1920)
    d = ImageDraw.Draw(hs)
    f = ImageFont.truetype(FONT_REG, 24)
    for i, name in enumerate(show[:20]):
        x = 92 + (i % 4) * 245
        y = 270 + (i // 4) * 245
        _paste_wallpaper_icon(hs, images, name, x, y, 122, variant)
        label = name[6:].replace('_', ' ')[:13]
        b = d.textbbox((0, 0), label, font=f)
        d.text((x + 61 - (b[2] - b[0]) / 2, y + 136), label, font=f, fill=(246, 243, 248))
    hs.save(outdir / 'preview_home.png')
    hs.save(outdir / f'preview_home_{variant}.png')


def _mass_center(mask):
    a = np.asarray(mask, dtype=np.float64) / 255.0
    total = float(a.sum())
    if total <= 1e-8:
        return WORK / 2.0, WORK / 2.0
    ys, xs = np.indices(a.shape, dtype=np.float64)
    return float((xs * a).sum() / total), float((ys * a).sum() / total)


def qa(images, outdir, variant):
    rows = []
    for name, (_, kind, _) in ICON_SPECS.items():
        if name not in images:
            continue
        geom_layers = base_layers(kind)
        fg = blank_mask()
        for lay in geom_layers:
            fg = union(fg, lay['mask'])
        bb = fg.getbbox()
        coverage = sum(fg.getdata()) / (255 * WORK * WORK)
        if bb:
            bbox_cx = (bb[0] + bb[2]) / 2
            bbox_cy = (bb[1] + bb[3]) / 2
        else:
            bbox_cx = bbox_cy = WORK / 2
        mass_cx, mass_cy = _mass_center(fg)

        im = images[name]
        small = im.convert('RGB').resize((64, 64))
        vals = [.2126 * r + .7152 * g + .0722 * b for r, g, b in small.getdata()]
        alpha = list(im.getchannel('A').resize((64, 64)).getdata())
        meta = geometry_meta(kind)
        mm = material_metrics(name) if variant == 'clear' else {}
        rows.append({
            'icon': name,
            'kind': kind,
            'variant': variant,
            'geometry_source': meta['source'],
            'geometry_owner': geometry_owner(kind),
            'renderer': 'cairosvg-2048',
            'geometry_engine': f"svg2048-{geometry_owner(kind)}",
            'legacy': False,
            'raster_fallback': False,
            'foreground_bbox': bb,
            'coverage_pct': round(coverage * 100, 2),
            'center_offset_x': round((bbox_cx - WORK / 2) / WORK * 100, 2),
            'center_offset_y': round((bbox_cy - WORK / 2) / WORK * 100, 2),
            'mass_center_offset_x': round((mass_cx - WORK / 2) / WORK * 100, 2),
            'mass_center_offset_y': round((mass_cy - WORK / 2) / WORK * 100, 2),
            'optical_dx': meta['optical_dx'],
            'optical_dy': meta['optical_dy'],
            'optical_scale': meta['optical_scale'],
            'mean_luminance': round(sum(vals) / len(vals), 1),
            'contrast_estimate': round((max(vals) - min(vals)) / 255, 3),
            'mean_alpha': round(sum(alpha) / len(alpha), 1),
            'layer_count': len(geom_layers),
            'clear_reflection_coverage_pct': round(clear_reflection_coverage_pct(name), 4) if variant == 'clear' else 0.0,
            'clear_reflection_style': reflection_style(name) if variant == 'clear' else 0,
            'enclosure_center_density': round(mm.get('enclosure_center_density', 0.0), 3),
            'enclosure_edge_density': round(mm.get('enclosure_edge_density', 0.0), 3),
            'specular_coverage_pct': round(mm.get('specular_coverage_pct', 0.0), 4),
            'refraction_displacement_mean': round(mm.get('refraction_displacement_mean', 0.0), 4),
            'refraction_displacement_max': round(mm.get('refraction_displacement_max', 0.0), 4),
        })

    (outdir / 'qa.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    fields = [
        'icon', 'kind', 'variant', 'geometry_source', 'geometry_owner', 'renderer', 'legacy',
        'raster_fallback', 'foreground_bbox', 'coverage_pct', 'center_offset_x', 'center_offset_y',
        'mass_center_offset_x', 'mass_center_offset_y', 'optical_dx', 'optical_dy',
        'optical_scale', 'mean_luminance', 'contrast_estimate', 'mean_alpha', 'layer_count',
        'clear_reflection_coverage_pct', 'clear_reflection_style', 'enclosure_center_density',
        'enclosure_edge_density', 'specular_coverage_pct', 'refraction_displacement_mean',
        'refraction_displacement_max',
    ]
    with (outdir / 'qa.tsv').open('w', encoding='utf-8') as f:
        f.write('\t'.join(fields) + '\n')
        for r in rows:
            f.write('\t'.join(str(r[k]) for k in fields) + '\n')
    return rows


def generate_variant(variant, quick=False):
    res, outdir = output_paths(variant)
    outdir.mkdir(parents=True, exist_ok=True)
    if not quick:
        res.mkdir(parents=True, exist_ok=True)
        for p in res.glob('skeuo_*.png'):
            p.unlink()

    wanted = set(QUICK_NAMES) if quick else set(ICON_SPECS)
    images = {}
    for name, (bg, kind, _) in ICON_SPECS.items():
        if name not in wanted:
            continue
        im = render(name, bg, kind, variant)
        if not quick:
            im.save(res / f'{name}.png', optimize=True)
        images[name] = im

    preview(images, outdir, variant, quick=quick)
    rows = qa(images, outdir, variant)

    if not quick:
        launch = render('skeuo_settings', ICON_SPECS['skeuo_settings'][0], 'settings', variant)
        for dens, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
            d = ROOT / f'app/src/{variant}/res/mipmap-{dens}'
            d.mkdir(parents=True, exist_ok=True)
            launch.resize((size, size), Image.Resampling.LANCZOS).save(d / 'ic_launcher.png')

    mean_alpha = sum(r['mean_alpha'] for r in rows) / len(rows)
    print(
        f'Liquid27 {variant}{" quick" if quick else ""}: {len(images)} icons; '
        f'{len(PRODUCTION_KINDS)} production vector kinds; legacy=0; mean alpha={mean_alpha:.1f}'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('color', 'clear', 'all'), default='all')
    parser.add_argument('--quick', action='store_true', help='render representative preview set only')
    args = parser.parse_args()
    variants = VARIANTS if args.variant == 'all' else (args.variant,)
    for variant in variants:
        generate_variant(variant, quick=args.quick)


if __name__ == '__main__':
    main()
