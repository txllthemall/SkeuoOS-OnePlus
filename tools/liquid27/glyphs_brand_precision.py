from __future__ import annotations

from .material import layer
from .vector import path_mask, svg_mask
from .glyphs_vector_complete import AMAZON_D, PAYPAL_D, STRAVA_D
from .glyphs_vector_home import GMAIL_D

PRECISION_BRAND_KINDS = {'gamehub', 'amazon', 'gmail', 'paypal', 'strava'}


def glass(mask, fill='#fff', opacity=.90, refraction=.090, specular='inside', shadow=.006):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -1), 0, .8, 2.4)


# GameHub / GameSir current app-scale mark.  The old renderer used thick
# stroked polylines; that produced round caps, inconsistent corners and a tiny
# visual mass.  This version uses two filled compound rails plus the controls.
# The rail geometry is normalized from the current official GameHub icon and is
# deliberately enlarged for 48–64 px launcher rendering.
GAMEHUB_MARK = '''
<path fill-rule="evenodd" d="
  M352 202 L158 500 L338 724 H590 L650 622 H392 L292 496 L438 270 Z
  M361 320 L248 496 L394 610 H532 L500 662 H365 L220 500 L382 252 Z
" fill="#fff"/>
<path fill-rule="evenodd" d="
  M414 266 H688 L856 500 L668 760 H548 L710 504 L610 388 H386 Z
  M473 348 H646 L770 502 L625 690 H604 L681 504 L574 430 H420 Z
" fill="#fff"/>
<path d="M326 458 H388 V396 H468 V458 H530 V538 H468 V600 H388 V538 H326 Z" fill="#fff"/>
<circle cx="590" cy="500" r="42" fill="#fff"/>
<circle cx="690" cy="500" r="42" fill="#fff"/>
'''


def glyph_brand_precision(kind):
    if kind not in PRECISION_BRAND_KINDS:
        return None

    if kind == 'gamehub':
        mask = svg_mask(GAMEHUB_MARK, viewbox=(0, 0, 1024, 1024))
        return [glass(mask, '#f7f9fc', .92, .098, 'inside', .004)]

    if kind == 'gmail':
        # Use the real M-envelope silhouette instead of assembling four stroked
        # lines.  A slightly larger target fixes the previous 7.9% coverage and
        # makes Gmail unmistakable from generic Mail at launcher scale.
        mask = path_mask(GMAIL_D, viewbox=(0, 0, 24, 24), target=(154, 218, 870, 806), fill_rule='evenodd')
        return [glass(mask, '#ea4335', .92, .092, 'inside', .004)]

    if kind == 'amazon':
        # Full app-scale Amazon mark (letterform + smile/arrow).  The prior
        # smile-only override read as a random scratch at 48–64 px.
        mask = path_mask(AMAZON_D, viewbox=(0, 0, 448, 512), target=(172, 132, 852, 884), fill_rule='evenodd')
        return [glass(mask, '#17191c', .92, .086, 'inside', .004)]

    if kind == 'paypal':
        # PayPal was optically heavier than neighboring marks.  Keep the source
        # silhouette intact and reduce only its target box.
        mask = path_mask(PAYPAL_D, viewbox=(0, 0, 384, 512), target=(286, 190, 738, 826), fill_rule='evenodd')
        return [glass(mask, '#ffffff', .90, .086, 'inside', .004)]

    if kind == 'strava':
        # Strava needs more mass at launcher scale; enlarge without changing the
        # actual source silhouette.
        mask = path_mask(STRAVA_D, viewbox=(0, 0, 384, 512), target=(226, 126, 798, 886), fill_rule='evenodd')
        return [glass(mask, '#ffffff', .90, .088, 'inside', .004)]

    return None
