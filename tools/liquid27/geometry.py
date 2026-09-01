from __future__ import annotations

"""Single production geometry registry.

Every catalog kind has exactly one production owner. Historical modules below
are vector libraries, never a fallback chain and never import-order overrides.
"""

from .catalog import ICON_SPECS
from .material import layer
from .vector import circle_mask, path_mask, rounded_rect_mask, stroked_path_mask, svg_mask
from .glyphs_vector import glyph_vector, VECTOR_KINDS
from .glyphs_vector_tuned import glyph_vector_tuned, TUNED_KINDS
from .glyphs_vector_home import (
    glyph_vector_home,
    HOME_VECTOR_KINDS,
    GMAIL_D,
    SOUNDCLOUD_D,
    CLOUD_D,
    SUN_D,
)
from .glyphs_brand_curated import (
    glyph_brand_curated,
    BRAND_CURATED_KINDS,
    GOOGLE_PLAY_LEFT_D,
    GOOGLE_PLAY_TOP_D,
    GOOGLE_PLAY_BOTTOM_D,
    GOOGLE_PLAY_TIP_D,
)
from .glyphs_vector_complete import (
    glyph_vector_complete,
    COMPLETE_VECTOR_KINDS,
    AMAZON_D,
    PAYPAL_D,
    STRAVA_D,
)
from .brand_assets import KASPI_MARK


def _glass(mask, fill='#fff', opacity=.88, refraction=.088, specular='outside', shadow=.010):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -2), 0, 1.2, 3.0)


# Only concrete launcher-scale fixes live here. They preserve source geometry
# that already passed visual review and correct the known outliers.
OVERRIDE_KINDS = {
    'gamehub', 'playstore', 'weather', 'revanced', 'soundcloud', 'drive', 'appstore',
    'gmail', 'kaspi', 'amazon', 'paypal', 'strava',
}


def _gamehub():
    """Filled GameSir/GameHub controller mark; never a nested wireframe."""
    left = svg_mask('''
      <path d="M278 234 H366 L158 512 L226 654 H642 L594 726 H188 L88 512 Z" fill="#fff"/>
    ''')
    right = svg_mask('''
      <path d="M430 300 H792 L934 512 L748 790 H654 L838 512 L746 370 H382 Z" fill="#fff"/>
    ''')
    plus_h = rounded_rect_mask(292, 474, 156, 62, 18)
    plus_v = rounded_rect_mask(339, 427, 62, 156, 18)
    dot1 = circle_mask(596, 506, 43)
    dot2 = circle_mask(714, 506, 43)
    return [
        _glass(left, '#f7f9fc', .91, .096, 'inside', .004),
        _glass(right, '#f7f9fc', .91, .096, 'inside', .004),
        _glass(plus_h, '#f7f9fc', .92, .090, 'inside', .002),
        _glass(plus_v, '#f7f9fc', .92, .090, 'inside', .002),
        _glass(dot1, '#f7f9fc', .92, .090, 'inside', .002),
        _glass(dot2, '#f7f9fc', .92, .090, 'inside', .002),
    ]


def _playstore():
    # QA follow-up: the previous fit sat just over the +5% right-offset gate.
    # Keep scale unchanged and nudge the complete four-part mark left in vector space.
    target = (238, 226, 886, 798)
    return [
        _glass(path_mask(GOOGLE_PLAY_LEFT_D, viewbox=(0, 0, 24, 24), target=target), '#34a853', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_TOP_D, viewbox=(0, 0, 24, 24), target=target), '#fbbc04', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_BOTTOM_D, viewbox=(0, 0, 24, 24), target=target), '#ea4335', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_TIP_D, viewbox=(0, 0, 24, 24), target=target), '#4285f4', .90, .082),
    ]


def _gmail():
    # Preserve the reviewed full M-envelope silhouette and launcher-scale mass.
    mask = path_mask(GMAIL_D, viewbox=(0, 0, 24, 24), target=(154, 218, 870, 806), fill_rule='evenodd')
    return [_glass(mask, '#ea4335', .92, .092, 'inside', .004)]


def _kaspi():
    # Verified Kaspi emblem that produced the accepted preview, not the old
    # invented person/card semantic substitute.
    mask = svg_mask(KASPI_MARK, viewbox=(0, 0, 192, 192), target=(210, 192, 814, 824))
    return [_glass(mask, '#ffffff', .91, .090, 'inside', .006)]


def _amazon():
    # Full a + smile/arrow mark: readable at launcher scale, unlike smile-only.
    mask = path_mask(AMAZON_D, viewbox=(0, 0, 448, 512), target=(172, 132, 852, 884), fill_rule='evenodd')
    return [_glass(mask, '#17191c', .92, .086, 'inside', .004)]


def _paypal():
    # Preserve the reviewed reduced visual mass.
    mask = path_mask(PAYPAL_D, viewbox=(0, 0, 384, 512), target=(286, 190, 738, 826), fill_rule='evenodd')
    return [_glass(mask, '#ffffff', .90, .086, 'inside', .004)]


def _strava():
    # Preserve the reviewed larger launcher-scale chevrons.
    mask = path_mask(STRAVA_D, viewbox=(0, 0, 384, 512), target=(226, 126, 798, 886), fill_rule='evenodd')
    return [_glass(mask, '#ffffff', .90, .088, 'inside', .004)]


def _weather():
    sun = path_mask(SUN_D, viewbox=(0, 0, 16, 16), target=(410, 82, 850, 522))
    cloud = path_mask(CLOUD_D, viewbox=(0, 0, 16, 16), target=(190, 205, 850, 730))
    return [
        _glass(sun, '#ffd21a', .82, .095, 'outside', .006),
        _glass(cloud, '#fff', .84, .100, 'outside', .016),
    ]


def _revanced():
    mark = svg_mask('''
      <g transform="translate(54 0)">
        <path d="M382 300 L746 512 L382 724 Z" fill="#fff"/>
        <rect x="254" y="330" width="52" height="364" rx="26" fill="#fff"/>
        <rect x="320" y="330" width="22" height="150" rx="11" fill="#fff" opacity=".65"/>
      </g>
    ''')
    return [_glass(mark, '#ff5262', .84, .094, 'outside', .012)]


def _soundcloud():
    mark = path_mask(SOUNDCLOUD_D, viewbox=(0, 0, 24, 24), target=(115, 242, 909, 782))
    return [_glass(mark, '#fff', .86, .092, 'outside', .014)]


def _drive():
    green = svg_mask('<path d="M410 216 H560 L806 642 H656 Z" fill="#fff"/>')
    yellow = svg_mask('<path d="M410 216 L164 642 L240 774 L486 348 Z" fill="#fff"/>')
    blue = svg_mask('<path d="M240 774 L164 642 H656 L806 642 L730 774 Z" fill="#fff"/>')
    return [
        _glass(green, '#34a853', .88, .080),
        _glass(yellow, '#fbbc04', .88, .080),
        _glass(blue, '#4285f4', .88, .080),
    ]


def _appstore():
    a1 = stroked_path_mask('M330 734 L503 402', width=74)
    a2 = stroked_path_mask('M521 402 L694 734', width=74)
    cross = stroked_path_mask('M370 646 L660 646', width=70)
    return [
        _glass(a1, '#fff', .88, .096, 'outside', .010),
        _glass(a2, '#fff', .88, .096, 'outside', .010),
        _glass(cross, '#fff', .88, .096, 'outside', .010),
    ]


OVERRIDES = {
    'gamehub': _gamehub,
    'playstore': _playstore,
    'gmail': _gmail,
    'kaspi': _kaspi,
    'amazon': _amazon,
    'paypal': _paypal,
    'strava': _strava,
    'weather': _weather,
    'revanced': _revanced,
    'soundcloud': _soundcloud,
    'drive': _drive,
    'appstore': _appstore,
}

OWN_OVERRIDE = set(OVERRIDE_KINDS)
OWN_TUNED = set(TUNED_KINDS) - OWN_OVERRIDE
OWN_CURATED = set(BRAND_CURATED_KINDS) - OWN_OVERRIDE - OWN_TUNED
OWN_HOME = set(HOME_VECTOR_KINDS) - OWN_OVERRIDE - OWN_TUNED - OWN_CURATED
OWN_REFERENCE = set(VECTOR_KINDS) - OWN_OVERRIDE - OWN_TUNED - OWN_CURATED - OWN_HOME
OWN_COMPLETE = set(COMPLETE_VECTOR_KINDS) - OWN_OVERRIDE - OWN_TUNED - OWN_CURATED - OWN_HOME - OWN_REFERENCE

OWNER_SETS = {
    'override': OWN_OVERRIDE,
    'tuned': OWN_TUNED,
    'curated': OWN_CURATED,
    'home': OWN_HOME,
    'reference': OWN_REFERENCE,
    'complete': OWN_COMPLETE,
}

OWNER_BY_KIND = {}
for owner, kinds in OWNER_SETS.items():
    for kind in kinds:
        if kind in OWNER_BY_KIND:
            raise RuntimeError(f'duplicate production geometry owner for {kind}: {OWNER_BY_KIND[kind]} and {owner}')
        OWNER_BY_KIND[kind] = owner

CATALOG_KINDS = {kind for _, kind, _ in ICON_SPECS.values()}
PRODUCTION_KINDS = set(OWNER_BY_KIND)
_missing = sorted(CATALOG_KINDS - PRODUCTION_KINDS)
_extra = sorted(PRODUCTION_KINDS - CATALOG_KINDS)
if _missing or _extra:
    raise RuntimeError(f'production geometry registry mismatch: missing={_missing}, extra={_extra}')


def duplicate_production_kinds():
    seen = set()
    duplicates = set()
    for kinds in OWNER_SETS.values():
        for kind in kinds:
            if kind in seen:
                duplicates.add(kind)
            seen.add(kind)
    return duplicates


def geometry_owner(kind: str) -> str:
    try:
        return OWNER_BY_KIND[kind]
    except KeyError as exc:
        raise RuntimeError(f'No production geometry owner for {kind}') from exc


def glyph(kind: str):
    owner = geometry_owner(kind)
    if owner == 'override':
        layers = OVERRIDES[kind]()
    elif owner == 'tuned':
        layers = glyph_vector_tuned(kind)
    elif owner == 'curated':
        layers = glyph_brand_curated(kind)
    elif owner == 'home':
        layers = glyph_vector_home(kind)
    elif owner == 'reference':
        layers = glyph_vector(kind)
    elif owner == 'complete':
        layers = glyph_vector_complete(kind)
    else:
        raise AssertionError(owner)
    if not layers:
        raise RuntimeError(f'Production geometry owner {owner} returned no layers for {kind}')
    return layers
