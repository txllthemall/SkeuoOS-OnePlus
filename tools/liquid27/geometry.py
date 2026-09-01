from __future__ import annotations

"""Single production geometry registry."""

from .catalog import ICON_SPECS
from .material import layer
from .vector import circle_mask, path_mask, rounded_rect_mask, stroked_path_mask, svg_mask
from .glyphs_vector import glyph_vector, VECTOR_KINDS
from .glyphs_vector_tuned import glyph_vector_tuned, TUNED_KINDS
from .glyphs_vector_home import glyph_vector_home, HOME_VECTOR_KINDS, GMAIL_D, SOUNDCLOUD_D, CLOUD_D, SUN_D
from .glyphs_brand_curated import glyph_brand_curated, BRAND_CURATED_KINDS, GOOGLE_PLAY_LEFT_D, GOOGLE_PLAY_TOP_D, GOOGLE_PLAY_BOTTOM_D, GOOGLE_PLAY_TIP_D
from .glyphs_vector_complete import glyph_vector_complete, COMPLETE_VECTOR_KINDS, AMAZON_D, PAYPAL_D, STRAVA_D
from .brand_assets import KASPI_MARK


def _glass(mask, fill='#fff', opacity=.88, refraction=.088, specular='outside', shadow=.010):
    return layer(mask, fill, opacity, refraction, specular, shadow, 'glass', 'normal', (0, -2), 0, 1.2, 3.0)


OVERRIDE_KINDS = {
    'gamehub', 'playstore', 'weather', 'revanced', 'twogis', 'soundcloud', 'drive', 'appstore',
    'gmail', 'kaspi', 'amazon', 'paypal', 'strava',
}


def _gamehub():
    left = svg_mask('<path d="M278 234 H366 L158 512 L226 654 H642 L594 726 H188 L88 512 Z" fill="#fff"/>')
    right = svg_mask('<path d="M430 300 H792 L934 512 L748 790 H654 L838 512 L746 370 H382 Z" fill="#fff"/>')
    plus_h = rounded_rect_mask(292, 474, 156, 62, 18)
    plus_v = rounded_rect_mask(339, 427, 62, 156, 18)
    dot1 = circle_mask(596, 506, 43); dot2 = circle_mask(714, 506, 43)
    return [_glass(left,'#fff',.91,.096,'inside',.004), _glass(right,'#fff',.91,.096,'inside',.004), _glass(plus_h,'#fff',.92,.090,'inside',.002), _glass(plus_v,'#fff',.92,.090,'inside',.002), _glass(dot1,'#fff',.92,.090,'inside',.002), _glass(dot2,'#fff',.92,.090,'inside',.002)]


def _playstore():
    target = (238, 226, 886, 798)
    return [
        _glass(path_mask(GOOGLE_PLAY_LEFT_D, viewbox=(0,0,24,24), target=target),'#34a853',.90,.082),
        _glass(path_mask(GOOGLE_PLAY_TOP_D, viewbox=(0,0,24,24), target=target),'#fbbc04',.90,.082),
        _glass(path_mask(GOOGLE_PLAY_BOTTOM_D, viewbox=(0,0,24,24), target=target),'#ea4335',.90,.082),
        _glass(path_mask(GOOGLE_PLAY_TIP_D, viewbox=(0,0,24,24), target=target),'#4285f4',.90,.082),
    ]


def _gmail():
    return [_glass(path_mask(GMAIL_D, viewbox=(0,0,24,24), target=(154,218,870,806), fill_rule='evenodd'),'#ea4335',.92,.092,'inside',.004)]


def _kaspi():
    return [_glass(svg_mask(KASPI_MARK, viewbox=(0,0,192,192), target=(210,192,814,824)),'#fff',.91,.090,'inside',.006)]


def _amazon():
    return [_glass(path_mask(AMAZON_D, viewbox=(0,0,448,512), target=(172,132,852,884), fill_rule='evenodd'),'#17191c',.92,.086,'inside',.004)]


def _paypal():
    return [_glass(path_mask(PAYPAL_D, viewbox=(0,0,384,512), target=(286,190,738,826), fill_rule='evenodd'),'#fff',.90,.086,'inside',.004)]


def _strava():
    return [_glass(path_mask(STRAVA_D, viewbox=(0,0,384,512), target=(226,126,798,886), fill_rule='evenodd'),'#fff',.90,.088,'inside',.004)]


def _weather():
    sun = path_mask(SUN_D, viewbox=(0,0,16,16), target=(410,82,850,522))
    cloud = path_mask(CLOUD_D, viewbox=(0,0,16,16), target=(190,205,850,730))
    return [_glass(sun,'#ffd21a',.82,.095,'outside',.006), _glass(cloud,'#fff',.84,.100,'outside',.016)]


def _revanced():
    """Exact current ReVanced brand geometry from revanced-branding SVG."""
    fragment = '''
      <path fill-rule="evenodd" d="M128,0C198.645,0 256,57.355 256,128C256,198.645 198.645,256 128,256C57.355,256 0,198.645 0,128C0,57.355 57.355,0 128,0ZM128,11.52C63.713,11.52 11.52,63.713 11.52,128C11.52,192.287 63.713,244.48 128,244.48C192.287,244.48 244.48,192.287 244.48,128C244.48,63.713 192.287,11.52 128,11.52Z" fill="#fff"/>
      <g transform="matrix(1,0,0,1,0,-0.0493818)"><path d="M172.397,86.408C172.871,85.326 172.767,84.078 172.12,83.089C171.474,82.1 170.372,81.504 169.191,81.504H164.658C163.666,81.504 162.768,82.091 162.369,82.999L130.289,156.064C129.89,156.972 128.992,157.559 128,157.559C127.008,157.559 126.11,156.972 125.711,156.064L93.631,82.999C93.232,82.091 92.334,81.504 91.342,81.504H86.809C85.628,81.504 84.526,82.1 83.879,83.089C83.233,84.078 83.129,85.326 83.603,86.408L121.322,172.499C121.88,173.772 123.138,174.595 124.528,174.595H131.472C132.862,174.595 134.12,173.772 134.678,172.499Z" fill="#fff"/></g>
      <g transform="matrix(-1.54007,0,0,-1.54007,327.925,209.689)"><path d="M128.129,54.017C128.477,53.414 129.12,53.043 129.816,53.043C130.512,53.043 131.155,53.414 131.503,54.017L146.703,80.344C147.051,80.947 147.051,81.689 146.703,82.292C146.355,82.894 145.712,83.266 145.016,83.266H114.616C113.92,83.266 113.277,82.894 112.929,82.292C112.581,81.689 112.581,80.947 112.929,80.344Z" fill="#fff"/></g>
    '''
    mark = svg_mask(fragment, viewbox=(0,0,256,256), target=(180,180,844,844))
    return [_glass(mark,'#fff',.92,.116,'inside',.003)]


# Official 2GIS corporate logo geometry (2020+ public wordmark source). Paths are
# preserved exactly; only the square-launcher fit and Clear material are ours.
_TWOGIS_S = 'M45610.17 5701.03l2193.56 0c-277.44,-2135 -1836.72,-3257.22 -4003.95,-3257.22 -2193.5,0 -3660.28,1163.3 -3660.28,3161.42 0,2271.83 1889.61,2778.16 2893.89,2983.52 1295,260.01 2563.56,287.4 2563.56,1436.95 0,780.1 -634.28,1163.3 -1532.83,1163.3 -1110,0 -1849.94,-574.8 -2035,-1614.86l-2167.12 0c132.11,2244.44 1704.67,3448.77 4017.17,3448.77 2140.67,0 3898.11,-1012.72 3898.11,-3202.45 0,-2353.99 -2021.72,-2778.22 -3435.67,-2997.21 -964.67,-150.52 -2021.78,-287.4 -2021.78,-1341.21 0,-739.02 541.78,-1190.63 1453.56,-1190.63 1057.17,0 1691.39,615.89 1836.78,1409.62z'
_TWOGIS_G = 'M30321.31 9245.63l2708.95 0c-422.89,1067.56 -1374.34,1573.83 -2471.12,1573.83 -1929.22,0 -2827.78,-1546.45 -2827.78,-3079.26 0,-1546.51 845.67,-3120.34 2814.61,-3120.34 1202.5,0 2101,574.8 2444.61,1601.22l2233.18 0.01c-383.17,-2312.85 -2338.89,-3640.37 -4651.34,-3640.37 -2854.28,0 -4995.01,2011.75 -4995.01,5186.87 0,3216.14 2325.67,5118.46 4981.73,5118.46 2616.45,0 4664.62,-1765.44 4664.62,-4529.96l0 -807.49 -4902.45 0 0 1697.03z'
_TWOGIS_2 = 'M20833.51 2580.71c-2378.56,0 -4136.06,1546.45 -4122.84,4119.37l2140.72 0c-26.45,-1122.22 660.67,-2148.64 1876.39,-2148.64 1057.17,0 1678.22,766.41 1678.22,1642.25 0,875.9 -621.06,1368.6 -1770.72,1902.38 -1572.5,725.32 -2695.67,1190.63 -3845.34,1601.22l0 3010.84 8007.85 0 0 -2025.51 -5497.47 0c935.05,-293.44 1637.52,-612.24 2470.54,-990.3 1783.89,-821.12 2801.39,-1847.6 2801.39,-3599.34 0.01,-2148.7 -1532.83,-3503.54 -3766.05,-3503.54z'
_TWOGIS_MARK = 'M11081.41 9218.29c-2695.72,13.7 -3131.78,1697.02 -3277.11,3120.34l-66.06 629.52 -541.83 0 -66.06 -629.52c-145.33,-1423.32 -594.61,-3106.65 -3197.84,-3120.34 -436.06,-930.68 -621.06,-1683.39 -621.06,-2531.9 0,-2121.25 1678.22,-4105.74 4162.45,-4105.74 2484.28,0 4136.06,1970.73 4136.06,4119.49 0.01,834.76 -79.27,1587.47 -528.55,2518.15zm-3633.89 -9210.56c-4096.39,0 -7452.84,3476.21 -7452.84,7732.41 0,4270.01 3356.45,7746.16 7452.84,7746.16 4136,0 7479.23,-3476.15 7479.23,-7746.16 0,-4256.19 -3343.23,-7732.41 -7479.23,-7732.41z'


def _twogis():
    target = (100, 350, 924, 616)
    vb = (0,0,47809.1,15478.6)
    mark = path_mask(_TWOGIS_MARK, viewbox=vb, target=target)
    two = path_mask(_TWOGIS_2, viewbox=vb, target=target)
    g = path_mask(_TWOGIS_G, viewbox=vb, target=target)
    i = svg_mask('<polygon points="38659.51,2785.98 36584.84,2785.98 36584.84,12708.11 38659.51,12708.11" fill="#fff"/>', viewbox=vb, target=target)
    s = path_mask(_TWOGIS_S, viewbox=vb, target=target)
    return [_glass(mark,'#fff',.92,.110,'inside',.002), _glass(two,'#fff',.92,.110,'inside',.002), _glass(g,'#fff',.92,.110,'inside',.002), _glass(i,'#fff',.92,.110,'inside',.002), _glass(s,'#fff',.92,.110,'inside',.002)]


def _soundcloud():
    return [_glass(path_mask(SOUNDCLOUD_D, viewbox=(0,0,24,24), target=(115,242,909,782)),'#fff',.86,.092,'outside',.014)]


def _drive():
    green=svg_mask('<path d="M410 216 H560 L806 642 H656 Z" fill="#fff"/>'); yellow=svg_mask('<path d="M410 216 L164 642 L240 774 L486 348 Z" fill="#fff"/>'); blue=svg_mask('<path d="M240 774 L164 642 H656 L806 642 L730 774 Z" fill="#fff"/>')
    return [_glass(green,'#34a853',.88,.080), _glass(yellow,'#fbbc04',.88,.080), _glass(blue,'#4285f4',.88,.080)]


def _appstore():
    a1=stroked_path_mask('M330 734 L503 402',width=74); a2=stroked_path_mask('M521 402 L694 734',width=74); cross=stroked_path_mask('M370 646 L660 646',width=70)
    return [_glass(a1,'#fff',.88,.096,'outside',.010), _glass(a2,'#fff',.88,.096,'outside',.010), _glass(cross,'#fff',.88,.096,'outside',.010)]


OVERRIDES={'gamehub':_gamehub,'playstore':_playstore,'gmail':_gmail,'kaspi':_kaspi,'amazon':_amazon,'paypal':_paypal,'strava':_strava,'weather':_weather,'revanced':_revanced,'twogis':_twogis,'soundcloud':_soundcloud,'drive':_drive,'appstore':_appstore}
OWN_OVERRIDE=set(OVERRIDE_KINDS)
OWN_TUNED=set(TUNED_KINDS)-OWN_OVERRIDE
OWN_CURATED=set(BRAND_CURATED_KINDS)-OWN_OVERRIDE-OWN_TUNED
OWN_HOME=set(HOME_VECTOR_KINDS)-OWN_OVERRIDE-OWN_TUNED-OWN_CURATED
OWN_REFERENCE=set(VECTOR_KINDS)-OWN_OVERRIDE-OWN_TUNED-OWN_CURATED-OWN_HOME
OWN_COMPLETE=set(COMPLETE_VECTOR_KINDS)-OWN_OVERRIDE-OWN_TUNED-OWN_CURATED-OWN_HOME-OWN_REFERENCE
OWNER_SETS={'override':OWN_OVERRIDE,'tuned':OWN_TUNED,'curated':OWN_CURATED,'home':OWN_HOME,'reference':OWN_REFERENCE,'complete':OWN_COMPLETE}
OWNER_BY_KIND={}
for owner,kinds in OWNER_SETS.items():
    for kind in kinds:
        if kind in OWNER_BY_KIND: raise RuntimeError(f'duplicate production geometry owner for {kind}: {OWNER_BY_KIND[kind]} and {owner}')
        OWNER_BY_KIND[kind]=owner
CATALOG_KINDS={kind for _,kind,_ in ICON_SPECS.values()}; PRODUCTION_KINDS=set(OWNER_BY_KIND)
_missing=sorted(CATALOG_KINDS-PRODUCTION_KINDS); _extra=sorted(PRODUCTION_KINDS-CATALOG_KINDS)
if _missing or _extra: raise RuntimeError(f'production geometry registry mismatch: missing={_missing}, extra={_extra}')


def duplicate_production_kinds():
    seen=set(); duplicates=set()
    for kinds in OWNER_SETS.values():
        for kind in kinds:
            if kind in seen: duplicates.add(kind)
            seen.add(kind)
    return duplicates


def geometry_owner(kind: str) -> str:
    try: return OWNER_BY_KIND[kind]
    except KeyError as exc: raise RuntimeError(f'No production geometry owner for {kind}') from exc


def glyph(kind: str):
    owner=geometry_owner(kind)
    if owner=='override': layers=OVERRIDES[kind]()
    elif owner=='tuned': layers=glyph_vector_tuned(kind)
    elif owner=='curated': layers=glyph_brand_curated(kind)
    elif owner=='home': layers=glyph_vector_home(kind)
    elif owner=='reference': layers=glyph_vector(kind)
    elif owner=='complete': layers=glyph_vector_complete(kind)
    else: raise AssertionError(owner)
    if not layers: raise RuntimeError(f'Production geometry owner {owner} returned no layers for {kind}')
    return layers
