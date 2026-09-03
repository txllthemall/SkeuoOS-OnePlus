from __future__ import annotations

import io

import cairosvg
from PIL import Image, ImageChops

# Official GitHub mark geometry from primer/octicons, updated for the 2026
# GitHub brand mark. Source: primer/octicons/icons/mark-github-24.svg (MIT).
#
# The Octicon path represents the light field around a negative-space Octocat.
# For V3 the semantic glyph must be the Octocat volume itself, not that outer
# field. We therefore subtract the official mark from its own outer circular
# field. This recovers the exact Octocat negative-space silhouette without
# hand-redrawing or approximating the cat.
GITHUB_MARK_2026_D = "M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.336 1.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943"


def _svg_mask(fragment: str, px: int) -> Image.Image:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">{fragment}</svg>'''
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=px, output_height=px)
    rgba = Image.open(io.BytesIO(png)).convert("RGBA")
    return rgba.getchannel("A")


def github_octocat_mask(size: int, *, scale: float = 0.656, offset_y: float = -0.008) -> Image.Image:
    """Return the semantic Octocat body as a positive V3 relief mask.

    This deliberately differs from the legacy Clear foreground union, which
    treats the white field of the GitHub mark as foreground and therefore
    turns the Octocat into a hole. V3 needs the Octocat itself to carry height,
    thickness and optical mass.
    """
    glyph_px = max(8, int(round(size * scale)))

    # Render the exact official mark and its exact outer circle in the same
    # 24x24 coordinate system. The 2026 mark's outer disc spans x=.5..23.5,
    # y=1..24, centered at (12,12.5) with radius 11.5.
    mark = _svg_mask(f'<path fill="#fff" d="{GITHUB_MARK_2026_D}"/>', glyph_px)
    disc = _svg_mask('<circle cx="12" cy="12.5" r="11.5" fill="#fff"/>', glyph_px)

    octocat = ImageChops.subtract(disc, mark)

    # Preserve antialiasing but suppress tiny numerical remnants outside the
    # semantic negative-space glyph.
    octocat = octocat.point(lambda v: 0 if v < 3 else v)

    canvas = Image.new("L", (size, size), 0)
    x = (size - glyph_px) // 2
    y = (size - glyph_px) // 2 + int(round(size * offset_y))
    canvas.paste(octocat, (x, y))
    return canvas
