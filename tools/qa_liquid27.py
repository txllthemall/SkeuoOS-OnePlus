from pathlib import Path
import argparse
import json
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]


def check_variant(variant):
    base = ROOT / f'build/liquid27-v4/{variant}'
    report = base / 'qa.json'
    if not report.exists():
        raise SystemExit(f'Missing {variant} QA report; run tools/generate_liquid27.py --variant all first')
    rows = json.loads(report.read_text(encoding='utf-8'))
    if len(rows) < 30:
        raise SystemExit(f'{variant}: only {len(rows)} QA rows; expected complete icon pack')

    coverage = [r['coverage_pct'] for r in rows]
    contrast = [r['contrast_estimate'] for r in rows]
    alphas = [r['mean_alpha'] for r in rows]
    median = statistics.median(coverage)
    errors = []
    warnings = []

    for r in rows:
        x, y = r['center_offset_pct']
        c = r['coverage_pct']
        k = r['contrast_estimate']
        if abs(x) > 15 or abs(y) > 15:
            errors.append(f"{r['icon']}: optical center offset {x},{y}%")
        if c < 2.5 or c > 70:
            errors.append(f"{r['icon']}: extreme foreground coverage {c}%")
        elif c < 5.5 or c > 55:
            warnings.append(f"{r['icon']}: foreground coverage {c}% vs median {median}%")
        if k < 0.12:
            warnings.append(f"{r['icon']}: low contrast estimate {k}")

    for name in ['preview_full.png', 'preview_light.png', 'preview_dark.png', 'preview_wallpaper.png', 'preview_home.png', 'preview_vector_reference.png']:
        p = base / name
        if not p.exists() or p.stat().st_size < 10000:
            errors.append(f'Missing/invalid preview {name}')

    mean_alpha = statistics.mean(alphas)
    if variant == 'clear':
        if mean_alpha >= 175:
            errors.append(f'Clear pack is too opaque: mean alpha {mean_alpha:.1f}')
        if mean_alpha <= 28:
            errors.append(f'Clear pack is too faint: mean alpha {mean_alpha:.1f}')
    else:
        if mean_alpha <= 150:
            warnings.append(f'Color pack unexpectedly transparent: mean alpha {mean_alpha:.1f}')

    svg_count = sum(1 for r in rows if r.get('geometry_engine') == 'svg2048')
    if svg_count < 12:
        errors.append(f'Only {svg_count} SVG2048 glyphs; vector reference set regressed')

    # Gmail must be a dedicated Gmail geometry path, not the generic mail glyph.
    gmail = next((r for r in rows if r['icon'] == 'skeuo_gmail'), None)
    mail = next((r for r in rows if r['icon'] == 'skeuo_mail'), None)
    if not gmail or gmail.get('kind') != 'gmail':
        errors.append('Gmail is not mapped to dedicated gmail geometry')
    if gmail and mail and gmail.get('foreground_bbox') == mail.get('foreground_bbox') and gmail.get('coverage_pct') == mail.get('coverage_pct'):
        errors.append('Gmail geometry appears to be identical to generic Mail')

    print(f'Liquid27 {variant} QA: {len(rows)} icons; {svg_count} SVG2048; median coverage {median:.1f}%; mean contrast {statistics.mean(contrast):.3f}; mean alpha {mean_alpha:.1f}')
    for w in warnings:
        print('WARN', variant, w)
    if errors:
        for e in errors:
            print('ERROR', variant, e)
        return False
    print(f'Liquid27 {variant} QA passed')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('color', 'clear', 'all'), default='all')
    args = parser.parse_args()
    variants = ('color', 'clear') if args.variant == 'all' else (args.variant,)
    if not all(check_variant(v) for v in variants):
        sys.exit(1)


if __name__ == '__main__':
    main()
