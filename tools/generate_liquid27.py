from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from liquid27.material import *
from liquid27.glyphs import glyph
from liquid27.glyphs_v4 import glyph_v4
from liquid27.glyphs_v4_extra import glyph_v4_extra
from liquid27.glyphs_vector import glyph_vector, VECTOR_KINDS
from liquid27.glyphs_vector_tuned import glyph_vector_tuned
from liquid27.glyphs_vector_home import glyph_vector_home, HOME_VECTOR_KINDS
from liquid27.vector import rounded_rect_mask, stroked_path_mask
from liquid27.catalog import ICON_SPECS

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('color', 'clear')
ALL_VECTOR_KINDS = set(VECTOR_KINDS) | set(HOME_VECTOR_KINDS) | {'gmail'}


def gmail_layers():
    """A Gmail-specific multicolor M, never the generic Mail/envelope glyph."""
    body = rounded_rect_mask(190, 258, 644, 508, 108)
    left = stroked_path_mask('M286 382 L286 690', width=64)
    diag_l = stroked_path_mask('M286 382 L512 552', width=64)
    diag_r = stroked_path_mask('M512 552 L738 382', width=64)
    right = stroked_path_mask('M738 382 L738 690', width=64)
    return [
        layer(body, '#ffffff', .73, .070, 'inside', .016, 'glass', 'normal', (0, -1), 0, 2.0, 5.0),
        layer(left, '#4285f4', .88, .072, 'outside', .008, 'glass', 'normal', (0, -2), 0, 1.5, 4.0),
        layer(diag_l, '#ea4335', .90, .075, 'outside', .008, 'glass', 'normal', (0, -2), 0, 1.5, 4.0),
        layer(diag_r, '#fbbc04', .88, .075, 'outside', .008, 'glass', 'normal', (0, -2), 0, 1.5, 4.0),
        layer(right, '#34a853', .88, .072, 'outside', .008, 'glass', 'normal', (0, -2), 0, 1.5, 4.0),
    ]


def base_layers(kind):
    if kind == 'gmail':
        return gmail_layers()
    return (
        glyph_vector_tuned(kind)
        or glyph_vector_home(kind)
        or glyph_vector(kind)
        or glyph_v4(kind)
        or glyph_v4_extra(kind)
        or glyph(kind)
    )


def clearify_layers(layers):
    """Convert shared geometry to a low-chroma, genuinely translucent glass preset."""
    result = []
    for src in layers:
        item = dict(src)
        source_luma = luminance(item.get('fill', '#ffffff'))
        if item.get('material') == 'ink':
            # Preserve hierarchy without opaque black/brand ink in the Clear pack.
            item['material'] = 'glass'
            item['fill'] = '#aab2bd' if source_luma < 150 else '#eef2f6'
            item['opacity'] = .48 if source_luma < 150 else .52
            item['refraction'] = .085
            item['specular'] = 'inside'
            item['shadow'] = .004
            item['blend'] = 'normal'
            item['blur'] = 0
        else:
            # Brand color is intentionally removed in Clear. Geometry remains identical.
            item['fill'] = '#e9eef4' if source_luma >= 105 else '#c5cdd7'
            item['opacity'] = .46 if source_luma >= 105 else .42
            item['refraction'] = max(.095, float(item.get('refraction', .06)) * 1.35)
            item['specular'] = 'outside'
            item['shadow'] = min(.009, float(item.get('shadow', 0)))
            item['blend'] = 'normal'
            item['blur'] = min(1.0, float(item.get('blur', 0)))
        item['shadow_offset'] = min(1.5, float(item.get('shadow_offset', 2.0)))
        item['shadow_blur'] = min(4.0, float(item.get('shadow_blur', 5.0)))
        result.append(item)
    return result


def layers_for(kind, variant='color'):
    layers = base_layers(kind)
    return clearify_layers(layers) if variant == 'clear' else layers


def clear_background():
    """Partially transparent enclosure that lets the actual OxygenOS wallpaper show through."""
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))

    # Neutral glass body. Deliberately not opaque: Android composites this over the wallpaper.
    body = Image.new('RGBA', (WORK, WORK), (232, 237, 243, 0))
    body.putalpha(ENCL.point(lambda v: int(v * .20)))
    canvas.alpha_composite(body)

    # Soft frost, strongest toward the top, still retaining real alpha transparency.
    frost = ImageOps.invert(Image.linear_gradient('L').resize((WORK, WORK)))
    frost = inter(frost.point(lambda v: int((v / 255.0) ** 2.0 * 28)), ENCL)
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(frost)
    canvas.alpha_composite(white)

    # Directional glass boundary rather than a decorative frame.
    top = inter(top_facing_edge(ENCL, 4.0), ImageOps.invert(Image.linear_gradient('L').resize((WORK, WORK))))
    top = top.point(lambda v: int(v * .55))
    hi = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    hi.putalpha(top)
    canvas.alpha_composite(hi)

    low = inter(bottom_facing_edge(ENCL, 2.2), Image.linear_gradient('L').resize((WORK, WORK)))
    low = low.point(lambda v: int(v * .12))
    shade = Image.new('RGBA', (WORK, WORK), (74, 82, 94, 0))
    shade.putalpha(low)
    canvas.alpha_composite(shade)
    return canvas


def finish_clear_enclosure(canvas):
    # Add one restrained interior specular sweep, while preserving partial alpha.
    sheen = ImageOps.invert(Image.linear_gradient('L').resize((WORK, WORK)))
    sheen = inter(sheen.point(lambda v: int((v / 255.0) ** 3.0 * 18)), ENCL)
    white = Image.new('RGBA', (WORK, WORK), (255, 255, 255, 0))
    white.putalpha(sheen)
    canvas.alpha_composite(white)
    canvas.putalpha(inter(canvas.getchannel('A'), ENCL))


def render(name, bgspec, kind, variant='color'):
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))
    if variant == 'clear':
        canvas.alpha_composite(clear_background())
    else:
        canvas.alpha_composite(background(bgspec))

    for lay in layers_for(kind, variant):
        composite_layer(canvas, **lay)

    if variant == 'clear':
        finish_clear_enclosure(canvas)
    else:
        finish_enclosure(canvas)
        canvas.putalpha(ENCL)

    return canvas.resize((OUT, OUT), Image.Resampling.LANCZOS)


def output_paths(variant):
    return (
        ROOT / f'app/src/{variant}/res/drawable-nodpi',
        ROOT / f'build/liquid27-v4/{variant}',
    )


def preview(images, outdir, variant):
    show = [
        'skeuo_phone', 'skeuo_messages', 'skeuo_camera', 'skeuo_photos', 'skeuo_settings',
        'skeuo_mail', 'skeuo_gmail', 'skeuo_maps', 'skeuo_clock', 'skeuo_weather',
        'skeuo_notes', 'skeuo_calendar', 'skeuo_appstore', 'skeuo_telegram', 'skeuo_discord',
        'skeuo_youtube', 'skeuo_revanced', 'skeuo_chrome', 'skeuo_spotify', 'skeuo_instagram',
        'skeuo_soundcloud', 'skeuo_kaspi', 'skeuo_2gis', 'skeuo_chatgpt', 'skeuo_gamehub',
    ]
    font = ImageFont.truetype(FONT_REG, 18)

    def sheet(name, bg, names=show, cols=5, icon_size=132):
        cell = 190
        rows = math.ceil(len(names) / cols)
        w = cols * cell + 60
        h = rows * 210 + 60
        can = Image.new('RGB', (w, h), rgb(bg))
        d = ImageDraw.Draw(can)
        fg = (235, 235, 238) if luminance(bg) < 128 else (34, 34, 38)
        for i, n in enumerate(names):
            x = 30 + (i % cols) * cell
            y = 30 + (i // cols) * 210
            ic = images[n].resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            can.paste(ic, (x + (cell - icon_size) // 2, y), ic)
            label = n[6:].replace('_', ' ')[:16]
            b = d.textbbox((0, 0), label, font=font)
            d.text((x + cell / 2 - (b[2] - b[0]) / 2, y + 145), label, font=font, fill=fg)
        can.save(outdir / name)

    sheet('preview_light.png', '#eff0f3')
    sheet('preview_dark.png', '#17181c')

    vector_names = [name for name, (_, kind, _) in ICON_SPECS.items() if kind in ALL_VECTOR_KINDS]
    sheet('preview_vector_reference.png', '#17181c', vector_names, cols=4, icon_size=144)

    all_names = list(images.keys())
    cols_all = 6
    cell_all = 170
    row_h = 190
    rows_all = math.ceil(len(all_names) / cols_all)
    full = Image.new('RGB', (cols_all * cell_all + 60, rows_all * row_h + 60), rgb('#17181c'))
    fd = ImageDraw.Draw(full)
    ff = ImageFont.truetype(FONT_REG, 16)
    for i, n in enumerate(all_names):
        x = 30 + (i % cols_all) * cell_all
        y = 30 + (i // cols_all) * row_h
        ic = images[n].resize((118, 118), Image.Resampling.LANCZOS)
        full.paste(ic, (x + 26, y), ic)
        label = n[6:].replace('_', ' ')[:17]
        b = fd.textbbox((0, 0), label, font=ff)
        fd.text((x + 85 - (b[2] - b[0]) / 2, y + 132), label, font=ff, fill=(238, 238, 242))
    full.save(outdir / 'preview_full.png')

    # Color-rich field makes actual transparency in the Clear variant obvious.
    w, h = 1080, 1280
    wall = Image.new('RGB', (w, h), '#171326')
    for col, xy, rad in [('#7f335f', (240, 280), 600), ('#233b8a', (850, 260), 650), ('#693b22', (800, 970), 650)]:
        m = Image.radial_gradient('L').resize((rad, rad))
        m = ImageOps.invert(m).point(lambda v: int(v * .65))
        fm = Image.new('L', (w, h), 0)
        fm.paste(m, (xy[0] - rad // 2, xy[1] - rad // 2))
        wall = Image.composite(Image.new('RGB', (w, h), rgb(col)), wall, fm)
    d = ImageDraw.Draw(wall)
    font2 = ImageFont.truetype(FONT_REG, 22)
    for i, n in enumerate(show[:20]):
        x = 75 + (i % 4) * 245
        y = 110 + (i // 4) * 220
        ic = images[n].resize((116, 116), Image.Resampling.LANCZOS)
        wall.paste(ic, (x, y), ic)
        label = n[6:].replace('_', ' ')[:12]
        b = d.textbbox((0, 0), label, font=font2)
        d.text((x + 58 - (b[2] - b[0]) / 2, y + 126), label, font=font2, fill=(245, 245, 248))
    wall.save(outdir / 'preview_wallpaper.png')

    hs_bg = (235, 236, 240) if variant == 'color' else (62, 68, 84)
    hs = Image.new('RGB', (1080, 1920), hs_bg)
    d = ImageDraw.Draw(hs)
    f = ImageFont.truetype(FONT_REG, 24)
    for i, n in enumerate(show[:20]):
        x = 93 + (i % 4) * 245
        y = 300 + (i // 4) * 240
        ic = images[n].resize((122, 122), Image.Resampling.LANCZOS)
        hs.paste(ic, (x, y), ic)
        label = n[6:].replace('_', ' ')[:12]
        b = d.textbbox((0, 0), label, font=f)
        label_color = (35, 35, 40) if variant == 'color' else (240, 242, 246)
        d.text((x + 61 - (b[2] - b[0]) / 2, y + 135), label, font=f, fill=label_color)
    hs.save(outdir / 'preview_home.png')


def qa(images, outdir, variant):
    rows = []
    for name, (bg, kind, defaults) in ICON_SPECS.items():
        layers = layers_for(kind, variant)
        fg = blank_mask()
        for l in layers:
            fg = union(fg, l['mask'])
        bb = fg.getbbox()
        coverage = sum(fg.getdata()) / (255 * WORK * WORK)
        if bb:
            cx = (bb[0] + bb[2]) / 2
            cy = (bb[1] + bb[3]) / 2
            off = ((cx - WORK / 2) / WORK, (cy - WORK / 2) / WORK)
        else:
            off = (0, 0)
        im = images[name]
        small = im.convert('RGB').resize((64, 64))
        vals = [.2126 * r + .7152 * g + .0722 * b for r, g, b in small.getdata()]
        alpha = list(im.getchannel('A').resize((64, 64)).getdata())
        rows.append({
            'icon': name,
            'kind': kind,
            'variant': variant,
            'geometry_engine': 'svg2048' if kind in ALL_VECTOR_KINDS else 'legacy',
            'foreground_bbox': bb,
            'coverage_pct': round(coverage * 100, 1),
            'center_offset_pct': [round(off[0] * 100, 1), round(off[1] * 100, 1)],
            'mean_luminance': round(sum(vals) / len(vals), 1),
            'contrast_estimate': round((max(vals) - min(vals)) / 255, 3),
            'mean_alpha': round(sum(alpha) / len(alpha), 1),
        })
    (outdir / 'qa.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    with (outdir / 'qa.tsv').open('w', encoding='utf-8') as f:
        f.write('icon\tkind\tvariant\tgeometry_engine\tforeground_bbox\tcoverage_pct\tcenter_offset_pct\tmean_luminance\tcontrast_estimate\tmean_alpha\n')
        for r in rows:
            f.write(f"{r['icon']}\t{r['kind']}\t{r['variant']}\t{r['geometry_engine']}\t{r['foreground_bbox']}\t{r['coverage_pct']}\t{r['center_offset_pct']}\t{r['mean_luminance']}\t{r['contrast_estimate']}\t{r['mean_alpha']}\n")
    return rows


def generate_variant(variant):
    res, outdir = output_paths(variant)
    res.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    for p in res.glob('skeuo_*.png'):
        p.unlink()

    images = {}
    for name, (bg, kind, defaults) in ICON_SPECS.items():
        im = render(name, bg, kind, variant)
        im.save(res / f'{name}.png', optimize=True)
        images[name] = im

    preview(images, outdir, variant)
    rows = qa(images, outdir, variant)

    launch = render('skeuo_settings', ICON_SPECS['skeuo_settings'][0], 'settings', variant)
    for dens, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        d = ROOT / f'app/src/{variant}/res/mipmap-{dens}'
        d.mkdir(parents=True, exist_ok=True)
        launch.resize((size, size), Image.Resampling.LANCZOS).save(d / 'ic_launcher.png')

    vector_count = sum(1 for r in rows if r['geometry_engine'] == 'svg2048')
    mean_alpha = sum(r['mean_alpha'] for r in rows) / len(rows)
    print(f'Liquid27 {variant}: generated {len(images)} icons; {vector_count} SVG2048 glyphs; mean alpha {mean_alpha:.1f}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('color', 'clear', 'all'), default='all')
    args = parser.parse_args()
    requested = VARIANTS if args.variant == 'all' else (args.variant,)
    for variant in requested:
        generate_variant(variant)


if __name__ == '__main__':
    main()
