from pathlib import Path
import argparse
import json
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Visual-review gate: these marks were explicitly called out as broken or too
# weak/heavy. SVG provenance alone is not sufficient for them to pass.
STRICT_GEOMETRY = {
    'skeuo_gamehub', 'skeuo_github', 'skeuo_playstore', 'skeuo_kaspi',
    'skeuo_pinterest', 'skeuo_telegram', 'skeuo_gmail', 'skeuo_discord',
    'skeuo_facebook', 'skeuo_reddit', 'skeuo_tiktok', 'skeuo_whatsapp',
    'skeuo_twitter', 'skeuo_steam', 'skeuo_snapchat', 'skeuo_instagram',
    'skeuo_amazon', 'skeuo_paypal', 'skeuo_strava', 'skeuo_google_drive',
    'skeuo_chatgpt', 'skeuo_spotify', 'skeuo_youtube', 'skeuo_revanced',
    'skeuo_chrome', 'skeuo_soundcloud', 'skeuo_2gis',
}


def mapping_checks(errors):
    res_path = ROOT / 'app/src/main/res/xml/appfilter.xml'
    assets_path = ROOT / 'app/src/main/assets/appfilter.xml'
    appfilter = res_path.read_text(encoding='utf-8')

    if assets_path.exists():
        assets = assets_path.read_text(encoding='utf-8')
        if appfilter != assets:
            errors.append('res/xml/appfilter.xml and assets/appfilter.xml are desynchronized')

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

    forbidden = {
        'com.android.vending/com.google.android.finsky.activities.MainActivity': 'skeuo_appstore',
        'org.fdroid.fdroid': 'skeuo_appstore',
        'com.aurora.store': 'skeuo_appstore',
        'md.obsidian': 'skeuo_notes',
        'xyz.blueskyweb.app': 'skeuo_twitter',
    }
    for component_or_package, drawable in forbidden.items():
        if component_or_package in appfilter and f'drawable="{drawable}"' in appfilter:
            errors.append(f'Forbidden cross-brand alias remains: {component_or_package} -> {drawable}')


def _reflection_iou(a, b):
    aa = np.asarray(a.resize((96, 96)), dtype=np.uint8) > 12
    bb = np.asarray(b.resize((96, 96)), dtype=np.uint8) > 12
    union = np.logical_or(aa, bb).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(aa, bb).sum() / union)


def reflection_checks(rows, errors, warnings):
    from liquid27.clear_material import clear_reflection_mask

    reflected = [r for r in rows if r['clear_reflection_coverage_pct'] > 0.005]
    zero_count = len(rows) - len(reflected)
    if zero_count < int(len(rows) * .45):
        errors.append(f'Environmental reflection is too ubiquitous: only {zero_count}/{len(rows)} icons have none')

    for r in rows:
        cov = r['clear_reflection_coverage_pct']
        if cov > 2.5:
            errors.append(f"{r['icon']}: environmental reflection coverage {cov:.3f}% is too large")
        elif cov > 1.6:
            warnings.append(f"{r['icon']}: environmental reflection coverage {cov:.3f}% is high")

    masks = [(r['icon'], clear_reflection_mask(r['icon'])) for r in reflected]
    similarities = []
    worst = (0.0, None, None)
    for i in range(len(masks)):
        for j in range(i + 1, len(masks)):
            score = _reflection_iou(masks[i][1], masks[j][1])
            similarities.append(score)
            if score > worst[0]:
                worst = (score, masks[i][0], masks[j][0])

    if similarities:
        median_similarity = statistics.median(similarities)
        highly_similar = sum(1 for x in similarities if x >= .88)
        if median_similarity > .72 or highly_similar > max(2, len(masks) // 4):
            errors.append(
                'procedural reflection repetition: '
                f'median IoU={median_similarity:.3f}, high-similarity pairs={highly_similar}, '
                f'worst={worst[0]:.3f} ({worst[1]}, {worst[2]})'
            )


def check_variant(variant):
    base = ROOT / f'build/liquid27-v4/{variant}'
    report = base / 'qa.json'
    if not report.exists():
        raise SystemExit(f'Missing {variant} QA report; run the release generator first')
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
        bbox_x = r['center_offset_x']
        bbox_y = r['center_offset_y']
        mass_x = r['mass_center_offset_x']
        mass_y = r['mass_center_offset_y']
        c = r['coverage_pct']
        k = r['contrast_estimate']
        strict = r['icon'] in STRICT_GEOMETRY
        max_bbox_offset = 5.0 if strict else 12.0
        max_mass_offset = 4.5 if strict else 10.0

        if abs(bbox_x) > max_bbox_offset or abs(bbox_y) > max_bbox_offset:
            errors.append(f"{r['icon']}: bbox center offset {bbox_x},{bbox_y}% (limit {max_bbox_offset}%)")
        if abs(mass_x) > max_mass_offset or abs(mass_y) > max_mass_offset:
            errors.append(f"{r['icon']}: visual mass center offset {mass_x},{mass_y}% (limit {max_mass_offset}%)")
        if c < 2.5 or c > 70:
            errors.append(f"{r['icon']}: extreme foreground coverage {c}%")
        elif strict and (c < 6.0 or c > 52.0):
            errors.append(f"{r['icon']}: reviewed foreground coverage {c}% is outside 6-52%")
        elif c < 5.5 or c > 55:
            warnings.append(f"{r['icon']}: foreground coverage {c}% vs median {median}%")
        if k < 0.10:
            warnings.append(f"{r['icon']}: low contrast estimate {k}")
        if r.get('legacy') or r.get('renderer') != 'cairosvg-2048':
            errors.append(f"{r['icon']}: legacy/non-vector geometry is forbidden")
        if not r.get('geometry_source'):
            errors.append(f"{r['icon']}: missing geometry provenance")
        if int(r.get('layer_count', 0)) <= 0:
            errors.append(f"{r['icon']}: empty geometry layer stack")

    generic_previews = [
        'preview_full.png', 'preview_light.png', 'preview_dark.png',
        'preview_wallpaper.png', 'preview_home.png', 'preview_vector_reference.png',
        'preview_geometry_focus.png',
    ]
    named_previews = [
        f'preview_{variant}_light.png', f'preview_{variant}_dark.png',
        f'preview_{variant}_wallpaper.png', f'preview_home_{variant}.png',
    ]
    for name in generic_previews + named_previews:
        p = base / name
        if not p.exists() or p.stat().st_size < 10000:
            errors.append(f'Missing/invalid preview {name}')

    mean_alpha = statistics.mean(alphas)
    if variant == 'clear':
        if mean_alpha >= 130:
            errors.append(f'Clear pack is too opaque: mean alpha {mean_alpha:.1f}')
        if mean_alpha <= 16:
            errors.append(f'Clear pack is too faint: mean alpha {mean_alpha:.1f}')
        reflection_checks(rows, errors, warnings)
    elif mean_alpha <= 145:
        warnings.append(f'Color pack unexpectedly transparent: mean alpha {mean_alpha:.1f}')

    svg_count = sum(1 for r in rows if not r.get('legacy'))
    if svg_count != len(rows):
        errors.append(f'Vector coverage incomplete: {svg_count}/{len(rows)}; release requires 100% SVG2048')

    for icon in STRICT_GEOMETRY:
        if icon not in by_name:
            errors.append(f'Missing strict geometry row: {icon}')

    gmail = by_name.get('skeuo_gmail')
    mail = by_name.get('skeuo_mail')
    if not gmail or gmail.get('kind') != 'gmail':
        errors.append('Gmail is not mapped to dedicated gmail geometry')
    if gmail and mail:
        if gmail.get('foreground_bbox') == mail.get('foreground_bbox') and abs(gmail['coverage_pct'] - mail['coverage_pct']) < .05:
            errors.append('Gmail geometry appears identical to generic Mail')

    play = by_name.get('skeuo_playstore')
    appstore = by_name.get('skeuo_appstore')
    if not play or play.get('kind') != 'playstore':
        errors.append('Google Play is not mapped to dedicated playstore geometry')
    if play and appstore:
        if play.get('foreground_bbox') == appstore.get('foreground_bbox') and abs(play['coverage_pct'] - appstore['coverage_pct']) < .05:
            errors.append('Google Play geometry appears identical to App Store')

    mapping_checks(errors)

    print(
        f'Liquid27 {variant} QA: {len(rows)} icons; {svg_count}/{len(rows)} SVG2048; '
        f'median coverage {median:.1f}%; mean contrast {statistics.mean(contrast):.3f}; '
        f'mean alpha {mean_alpha:.1f}'
    )
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
