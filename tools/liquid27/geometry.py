from __future__ import annotations

"""Single production geometry registry.

All release rendering resolves a catalog kind through this module exactly once.
The older glyph modules are treated as vector libraries only; there is no
fallback chain and no import-order-dependent override.
"""

from .catalog import ICON_SPECS
from .material import layer
from .vector import circle_mask, path_mask, rounded_rect_mask, stroked_path_mask, svg_mask
from .glyphs_vector import glyph_vector, VECTOR_KINDS
from .glyphs_vector_tuned import glyph_vector_tuned, TUNED_KINDS
from .glyphs_vector_home import (
    glyph_vector_home,
    HOME_VECTOR_KINDS,
    GOOGLE_PLAY_LEFT_D,
    GOOGLE_PLAY_TOP_D,
    GOOGLE_PLAY_BOTTOM_D,
    GOOGLE_PLAY_D,
    SOUNDCLOUD_D,
    CLOUD_D,
    SUN_D,
)
from .glyphs_brand_curated import (
    glyph_brand_curated,
    BRAND_CURATED_KINDS,
    GOOGLE_PLAY_TIP_D,
)
from .glyphs_vector_complete import glyph_vector_complete, COMPLETE_VECTOR_KINDS


def _glass(mask, fill='#fff', opacity=.88, refraction=.088, specular='outside', shadow=.010):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -2), 0, 1.2, 3.0)


# These are the only production overrides. They exist because launcher-scale QA
# demonstrated a concrete geometry/optical problem in the library definition.
OVERRIDE_KINDS = {
    'gamehub', 'playstore', 'weather', 'revanced', 'soundcloud', 'drive', 'appstore',
}


def _gamehub():
    """GameSir/GameHub app-scale mark from the current official icon.

    The mark is two FILLED angular bracket surfaces plus a plus and two circular
    controls. There are deliberately no nested rails, outlines or stroked
    wireframe shells.
    """
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
    # Google Play is intrinsically left-heavy. Shift the source-vector fit to
    # the right before Cairo rasterisation, preserving the four material faces.
    target = (246, 226, 894, 798)
    return [
        _glass(path_mask(GOOGLE_PLAY_LEFT_D, viewbox=(0, 0, 24, 24), target=target), '#34a853', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_TOP_D, viewbox=(0, 0, 24, 24), target=target), '#fbbc04', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_BOTTOM_D, viewbox=(0, 0, 24, 24), target=target), '#ea4335', .90, .082),
        _glass(path_mask(GOOGLE_PLAY_TIP_D, viewbox=(0, 0, 24, 24), target=target), '#4285f4', .90, .082),
    ]


def _weather():
    # The previous composition was bottom-heavy. Move both semantic layers up
    # at vector-fit time without changing their silhouette.
    sun = path_mask(SUN_D, viewbox=(0, 0, 16, 16), target=(410, 82, 850, 522))
    cloud = path_mask(CLOUD_D, viewbox=(0, 0, 16, 16), target=(190, 205, 850, 730))
    return [
        _glass(sun, '#ffd21a', .82, .095, 'outside', .006),
        _glass(cloud, '#fff', .84, .100, 'outside', .016),
    ]


def _revanced():
    # Preserve the ReVanced play/rail semantics, but correct the left-heavy mass.
    mark = svg_mask('''
      <g transform="translate(54 0)">
        <path d="M382 300 L746 512 L382 724 Z" fill="#fff"/>
        <rect x="254" y="330" width="52" height="364" rx="26" fill="#fff"/>
        <rect x="320" y="330" width="22" height="150" rx="11" fill="#fff" opacity=".65"/>
      </g>
    ''')
    return [_glass(mark, '#ff5262', .84, .094, 'outside', .012)]


def _soundcloud():
    # Launcher coverage was 5.1%; enlarge the genuine SoundCloud path instead
    # of thickening individual bars or inventing a replacement glyph.
    mark = path_mask(SOUNDCLOUD_D, viewbox=(0, 0, 24, 24), target=(115, 242, 909, 782))
    return [_glass(mark, '#fff', .86, .092, 'outside', .014)]


def _drive():
    # Same three Google Drive faces, shifted slightly upward for optical mass.
    green = svg_mask('<path d="M410 216 H560 L806 642 H656 Z" fill="#fff"/>')
    yellow = svg_mask('<path d="M410 216 L164 642 L240 774 L486 348 Z" fill="#fff"/>')
    blue = svg_mask('<path d="M240 774 L164 642 H656 L806 642 L730 774 Z" fill="#fff"/>')
    return [
        _glass(green, '#34a853', .88, .080),
        _glass(yellow, '#fbbc04', .88, .080),
        _glass(blue, '#4285f4', .88, .080),
    ]


def _appstore():
    # Keep the familiar construction but increase launcher-scale visual mass.
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
    'weather': _weather,
    'revanced': _revanced,
    'soundcloud': _soundcloud,
    'drive': _drive,
    'appstore': _appstore,
}

# Derive mutually-exclusive production ownership. Raw library sets are allowed
# to overlap historically; production ownership is not.
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
    # Ownership construction above makes duplicates impossible; expose this for QA.
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
