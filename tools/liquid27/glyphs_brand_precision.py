from __future__ import annotations

from .material import layer
from .vector import svg_mask

PRECISION_BRAND_KINDS = {'gamehub'}


def glass(mask, fill='#fff', opacity=.90, refraction=.090, specular='inside', shadow=.006):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -1), 0, .8, 2.4)


# GameHub / GameSir app mark, traced from the current official icon.  The mark
# is two independent angular rails; using stroked polylines made the corners,
# caps and optical mass visibly wrong at launcher size.  These are filled paths
# with deliberate terminal angles and constant-looking visual weight.
GAMEHUB_MARK = '''
<path d="M356 246 L202 505 L354 682 L574 682 L620 606 L389 606 L294 503 L431 278 Z" fill="#fff"/>
<path d="M431 314 L649 314 L806 509 L652 730 L559 730 L706 510 L611 390 L389 390 Z" fill="#fff"/>
<path d="M348 477 H397 V428 H459 V477 H508 V539 H459 V588 H397 V539 H348 Z" fill="#fff"/>
<circle cx="574" cy="510" r="35" fill="#fff"/>
<circle cx="663" cy="510" r="35" fill="#fff"/>
'''


def glyph_brand_precision(kind):
    if kind != 'gamehub':
        return None
    mask = svg_mask(GAMEHUB_MARK, viewbox=(0, 0, 1024, 1024))
    return [glass(mask, '#f7f9fc', .91, .094, 'inside', .005)]
