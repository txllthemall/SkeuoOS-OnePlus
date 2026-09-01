from pathlib import Path
import argparse
import json
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]

STRICT_GEOMETRY = {
    'skeuo_gamehub', 'skeuo_github', 'skeuo_playstore', 'skeuo_kaspi',
    'skeuo_pinterest', 'skeuo_telegram', 'skeuo_gmail', 'skeuo_discord',
    'skeuo_facebook', 'skeuo_reddit', 'skeuo_tiktok', 'skeuo_whatsapp',
    'skeuo_twitter', 'skeuo_steam', 'skeuo_snapchat', 'skeuo_instagram',
}


def mapping_checks(errors):
    appfilter = (ROOT / 'app/src/main/res/xml/appfilter.xml').read_text(encoding='utf-8')
    required = {
        'com.android.vending/com.google.android.finsky.activities.MainActivity': 'skeuo_playstore',
        'com.google.android.keep/com.google.android.keep.activities.BrowseActivity': 'skeuo_google_keep',
        'com.google.android.calendar/com.android.calendar.AllInOneActivity': 'skeuo_google_calendar',
        'com.strava/com.strava.ui.splash.SplashActivity': 'skeuo_strava',
    }
    for component, drawable in required.items():
        needle = f'ComponentInfo{{{component}}}" drawable="{drawable}"'
        if needle not in appfilter:
            errors.append(f'Wrong/missing appfilter mapping: {component} -> {drawable}')
    if 'ComponentInfo{com.android.vending/' in appfilter and 'ComponentInfo{com.android.vending/com.google.android.finsky.activities.MainActivity}" drawable="skeuo_appstore"' in appfilter:
        errors.append('Google Play regressed to generic App Store mapping')


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

    by_name = {r['icon']: r for r in rows}
    for r in rows:
        x, y = r['center_offset_pct']
        c = r['coverage_pct']
        k = r['contrast_estimate']
        strict = r['icon'] in STRICT_GEOMETRY
        max_offset = 4.0 if strict else 12.0
        if abs(x) > max_offset or abs(y) > max_offset:
            errors.append(f"{r['icon']}: optical center offset {x},{y}% (limit {max_offset}%)")
        if c < 2.5 or c > 70:
            errors.append(f"{r['icon']}: extreme foreground coverage {c}%")
        elif strict and (c < 8.0 or c > 52.0):
            errors.append(f"{r['icon']}: curated foreground coverage {c}% is outside 8-52%")
        elif c < 5.5 or c > 55:
            warnings.append(f"{r['icon']}: foreground coverage {c}% vs median {median}%")
        if k < 0.10:
            warnings.append(f"{r['icon']}: low contrast estimate {k}")

    for name in [
        'preview_full.png', 'preview_light.png', 'preview_dark.png',
        'preview_wallpaper.png', 'preview_home.png', 'preview_vector_reference.png',
        'preview_geometry_focus.png',
    ]:
        p = base / name
        if not p.exists() or p.stat().st_size < 10000:
            errors.append(f'Missing/invalid preview {name}')

    mean_alpha = statistics.mean(alphas)
    if variant == 'clear':
        if mean_alpha >= 135:
            errors.append(f'Clear pack is too opaque: mean alpha {mean_alpha:.1f}')
        if mean_alpha <= 18:
            errors.append(f'Clear pack is too faint: mean alpha {mean_alpha:.1f}')
    else:
        if mean_alpha <= 145:
            warnings.append(f'Color pack unexpectedly transparent: mean alpha {mean_alpha:.1f}')

    svg_count = sum(1 for r in rows if str(r.get('geometry_engine', '')).startswith('svg2048'))
    curated_count = sum(1 for r in rows if r.get('geometry_engine') == 'svg2048-curated')
    if svg_count < 24:
        errors.append(f'Only {svg_count} SVG2048 glyphs; vector set regressed')
    if curated_count < 14:
        errors.append(f'Only {curated_count} reviewed brand glyphs; expected at least 14')

    for icon in STRICT_GEOMETRY:
        row = by_name.get(icon)
        if not row:
            errors.append(f'Missing strict geometry row: {icon}')
        elif row.get('geometry_engine') == 'legacy':
            errors.append(f'{icon}: legacy geometry is forbidden')

    # Gmail must remain a dedicated M geometry, not Mail.
    gmail = by_name.get('skeuo_gmail')
    mail = by_name.get('skeuo_mail')
    if not gmail or gmail.get('kind') != 'gmail':
        errors.append('Gmail is not mapped to dedicated gmail geometry')
    if gmail and mail and gmail.get('foreground_bbox') == mail.get('foreground_bbox') and gmail.get('coverage_pct') == mail.get('coverage_pct'):
        errors.append('Gmail geometry appears identical to generic Mail')

    mapping_checks(errors)

    print(f'Liquid27 {variant} QA: {len(rows)} icons; {svg_count} SVG2048; {curated_count} curated; median coverage {median:.1f}%; mean contrast {statistics.mean(contrast):.3f}; mean alpha {mean_alpha:.1f}')
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
