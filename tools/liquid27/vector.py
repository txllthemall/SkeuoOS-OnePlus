from __future__ import annotations

from io import BytesIO
from typing import Iterable

import cairosvg
from PIL import Image

from .material import WORK

# Geometry is authored as real SVG paths in the Apple 1024-unit design space.
# Cairo rasterizes every path at 2048 px before it is downsampled into the
# material renderer.  We never rotate or scale a previously-rasterized glyph.
VECTOR_RASTER = 2048
DESIGN = 1024.0


def _render(fragment: str, *, viewbox=(0.0, 0.0, DESIGN, DESIGN), target=None) -> Image.Image:
    vx, vy, vw, vh = [float(x) for x in viewbox]
    if target is None:
        target = (0.0, 0.0, DESIGN, DESIGN)
    x0, y0, x1, y1 = [float(x) for x in target]
    tw, th = x1 - x0, y1 - y0
    scale = min(tw / vw, th / vh)
    ox = x0 + (tw - vw * scale) / 2.0 - vx * scale
    oy = y0 + (th - vh * scale) / 2.0 - vy * scale

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{VECTOR_RASTER}" height="{VECTOR_RASTER}" viewBox="0 0 {DESIGN:g} {DESIGN:g}">
      <g transform="translate({ox:.8f} {oy:.8f}) scale({scale:.8f})">
        {fragment}
      </g>
    </svg>'''
    png = cairosvg.svg2png(
        bytestring=svg.encode('utf-8'),
        output_width=VECTOR_RASTER,
        output_height=VECTOR_RASTER,
    )
    alpha = Image.open(BytesIO(png)).convert('RGBA').getchannel('A')
    if alpha.size != (WORK, WORK):
        alpha = alpha.resize((WORK, WORK), Image.Resampling.LANCZOS)
    return alpha


def path_mask(d: str, *, viewbox=(0, 0, 24, 24), target=(190, 190, 834, 834),
              fill_rule='nonzero', transform: str | None = None) -> Image.Image:
    tf = f' transform="{transform}"' if transform else ''
    fragment = f'<path d="{d}" fill="#fff" fill-rule="{fill_rule}" clip-rule="{fill_rule}"{tf}/>'
    return _render(fragment, viewbox=viewbox, target=target)


def paths_mask(paths: Iterable[tuple[str, str | None]], *, viewbox=(0, 0, 24, 24),
               target=(190, 190, 834, 834), fill_rule='nonzero') -> Image.Image:
    items = []
    for d, transform in paths:
        tf = f' transform="{transform}"' if transform else ''
        items.append(f'<path d="{d}" fill="#fff" fill-rule="{fill_rule}" clip-rule="{fill_rule}"{tf}/>')
    return _render(''.join(items), viewbox=viewbox, target=target)


def svg_mask(fragment: str, *, viewbox=(0, 0, 1024, 1024), target=None) -> Image.Image:
    return _render(fragment, viewbox=viewbox, target=target)


def circle_mask(cx: float, cy: float, r: float) -> Image.Image:
    return _render(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff"/>')


def ellipse_mask(cx: float, cy: float, rx: float, ry: float, *, rotate=0.0) -> Image.Image:
    tf = '' if not rotate else f' transform="rotate({rotate} {cx} {cy})"'
    return _render(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#fff"{tf}/>')


def rounded_rect_mask(x: float, y: float, w: float, h: float, r: float) -> Image.Image:
    return _render(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" fill="#fff"/>')


def stroked_path_mask(d: str, *, viewbox=(0, 0, 1024, 1024), target=None,
                      width=48.0, linecap='round', linejoin='round') -> Image.Image:
    fragment = (
        f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{width}" '
        f'stroke-linecap="{linecap}" stroke-linejoin="{linejoin}"/>'
    )
    return _render(fragment, viewbox=viewbox, target=target)
