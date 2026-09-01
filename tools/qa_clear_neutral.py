from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))

from generate_liquid27 import render
from liquid27.catalog import ICON_SPECS

CHECK = [
    'skeuo_phone', 'skeuo_messages', 'skeuo_photos', 'skeuo_clock',
    'skeuo_settings', 'skeuo_playstore', 'skeuo_discord', 'skeuo_gamehub',
    'skeuo_telegram', 'skeuo_chrome', 'skeuo_chatgpt', 'skeuo_spotify',
]

MAX_CHANNEL_SPREAD = 4.0
MAX_CYAN_BIAS = 3.0


def weighted_rgb(im):
    arr = np.asarray(im.convert('RGBA'), dtype=np.float32)
    alpha = arr[..., 3] / 255.0
    weight = float(alpha.sum())
    if weight <= 1e-6:
        return np.array([0.0, 0.0, 0.0], dtype=np.float32)
    return (arr[..., :3] * alpha[..., None]).sum(axis=(0, 1)) / weight


def main() -> int:
    failed = []
    for name in CHECK:
        bg, kind, _ = ICON_SPECS[name]
        rgb = weighted_rgb(render(name, bg, kind, 'clear'))
        r, g, b = [float(v) for v in rgb]
        spread = max(r, g, b) - min(r, g, b)
        cyan_bias = ((g + b) * 0.5) - r
        print(f'{name}: rgb=({r:.2f}, {g:.2f}, {b:.2f}) spread={spread:.2f} cyan_bias={cyan_bias:.2f}')
        if spread > MAX_CHANNEL_SPREAD or cyan_bias > MAX_CYAN_BIAS:
            failed.append((name, r, g, b, spread, cyan_bias))

    if failed:
        print('\nClear neutral-color QA FAILED:')
        for name, r, g, b, spread, cyan_bias in failed:
            print(f'  {name}: rgb=({r:.2f}, {g:.2f}, {b:.2f}), spread={spread:.2f}, cyan_bias={cyan_bias:.2f}')
        return 1

    print('\nClear neutral-color QA passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
