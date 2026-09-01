from __future__ import annotations

from .material import layer
from .vector import circle_mask, path_mask, paths_mask, stroked_path_mask, svg_mask
from .glyphs_vector import (
    CAMERA_BODY_D,
    TELEGRAM_PLANE_D,
    DISCORD_HALF_D,
    YOUTUBE_D,
    CHATGPT_ARM_D,
)

# Production ownership is explicit in geometry.py. These are the reviewed
# launcher-scale overrides; they are not fallbacks and never depend on import
# order.
TUNED_KINDS = {'camera', 'telegram', 'discord', 'youtube', 'spotify', 'chatgpt'}


def gl(mask, fill='#fff', opacity=.84, refraction=.085, specular='outside', shadow=.020,
       material='glass', blend='normal', offset=(0, -2)):
    return layer(mask, fill, opacity, refraction, specular, shadow, material, blend, offset, 0, 2.0, 5.0)


def glyph_vector_tuned(kind):
    """Launcher-scale vector geometry that has explicit optical corrections."""
    if kind not in TUNED_KINDS:
        return None

    if kind == 'camera':
        body = path_mask(CAMERA_BODY_D, viewbox=(0, 1.5, 16, 13), target=(120, 190, 904, 836))
        return [
            gl(body, '#f7f8fa', .84, .065, 'inside', .018),
            gl(circle_mask(512, 516, 194), '#303844', .78, .088, 'outside', .022),
            gl(circle_mask(512, 516, 140), '#1679eb', .78, .116, 'outside', .008),
            gl(circle_mask(482, 482, 69), '#b5e6ff', .38, .132, 'inside', .002),
        ]

    if kind == 'telegram':
        # The paper plane is intrinsically right-heavy. A mathematical bbox
        # center looks visually off at 48-64 px, so placement is corrected in
        # vector space. The +10 px adjustment here is the QA follow-up after
        # the previous correction overshot slightly to the left.
        plane = path_mask(
            TELEGRAM_PLANE_D,
            viewbox=(112, 157, 258, 218),
            target=(115, 205, 805, 820),
        )
        return [gl(plane, '#fff', .88, .105, 'outside', .018)]

    if kind == 'discord':
        logo = paths_mask(
            [(DISCORD_HALF_D, None), (DISCORD_HALF_D, 'matrix(-1 0 0 1 512 0)')],
            viewbox=(54, 94, 404, 320),
            target=(166, 224, 858, 800),
        )
        return [gl(logo, '#fff', .86, .094, 'outside', .018)]

    if kind == 'youtube':
        logo = path_mask(
            YOUTUBE_D,
            viewbox=(64, 114, 384, 284),
            target=(150, 280, 874, 744),
            fill_rule='evenodd',
        )
        return [gl(logo, '#fff', .88, .094, 'outside', .018)]

    if kind == 'spotify':
        p1 = stroked_path_mask('M258 382 C385 327 574 342 758 408', width=54)
        p2 = stroked_path_mask('M292 505 C412 458 575 470 724 528', width=48)
        p3 = stroked_path_mask('M333 624 C436 584 562 590 684 638', width=42)
        return [
            layer(p1, '#0b0d0e', .98, 0, 'off', 0, 'ink'),
            layer(p2, '#0b0d0e', .98, 0, 'off', 0, 'ink'),
            layer(p3, '#0b0d0e', .98, 0, 'off', 0, 'ink'),
        ]

    if kind == 'chatgpt':
        fragment = '<defs><path id="arm2" d="%s" fill="#fff"/></defs>' % CHATGPT_ARM_D
        fragment += '<use href="#arm2"/>'
        for deg in (60, 120, 180, 240, 300):
            fragment += f'<use href="#arm2" transform="rotate({deg} 256 256)"/>'
        logo = svg_mask(
            fragment,
            viewbox=(82, 80, 348, 352),
            target=(170, 170, 854, 854),
        )
        return [gl(logo, '#f2faf6', .76, .110, 'outside', .008, blend='plus_lighter')]

    raise AssertionError(f'Unhandled tuned kind: {kind}')
