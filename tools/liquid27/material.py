from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance
import math

# Apple documents a 1024x1024 iPhone/iPad/Mac icon canvas. We author in that
# coordinate space and bake to the 512px Android asset with Lanczos.
DESIGN = 1024.0
WORK = 1024
OUT = 512
K = WORK / DESIGN
C = DESIGN / 2

FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def sx(v: float) -> int:
    return int(round(v * K))


def sbox(b):
    return tuple(sx(v) for v in b)


def spts(points):
    return [(sx(x), sx(y)) for x, y in points]


def rgb(value):
    if isinstance(value, (tuple, list)):
        return tuple(int(v) for v in value[:3])
    value = value.lstrip('#')
    if len(value) == 3:
        value = ''.join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def luminance(c):
    r, g, b = rgb(c)
    return .2126 * r + .7152 * g + .0722 * b


def blank_mask():
    return Image.new('L', (WORK, WORK), 0)


def rr(box, radius):
    m = blank_mask()
    ImageDraw.Draw(m).rounded_rectangle(sbox(box), radius=sx(radius), fill=255)
    return m


def ellipse(box):
    m = blank_mask()
    ImageDraw.Draw(m).ellipse(sbox(box), fill=255)
    return m


def poly(points):
    m = blank_mask()
    ImageDraw.Draw(m).polygon(spts(points), fill=255)
    return m


def line(points, width):
    m = blank_mask()
    ImageDraw.Draw(m).line(spts(points), fill=255, width=max(1, sx(width)), joint='curve')
    return m


def arc(box, start, end, width):
    m = blank_mask()
    ImageDraw.Draw(m).arc(sbox(box), start, end, fill=255, width=max(1, sx(width)))
    return m


def round_line(points, width):
    m = line(points, width)
    r = width / 2
    d = ImageDraw.Draw(m)
    for x, y in (points[0], points[-1]):
        d.ellipse(sbox((x-r, y-r, x+r, y+r)), fill=255)
    return m


def bezier(p0, p1, p2, p3, width, steps=64):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
        y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
        pts.append((x, y))
    return round_line(pts, width)


def union(*masks):
    out = blank_mask()
    for m in masks:
        out = ImageChops.lighter(out, m)
    return out


def sub(a, b):
    return ImageChops.subtract(a, b)


def inter(a, b):
    return ImageChops.multiply(a, b)


def shifted(mask, dx=0, dy=0):
    out = blank_mask()
    dx, dy = sx(dx), sx(dy)
    src = (max(0, -dx), max(0, -dy), min(WORK, WORK - dx), min(WORK, WORK - dy))
    if src[2] > src[0] and src[3] > src[1]:
        out.paste(mask.crop(src), (max(0, dx), max(0, dy)))
    return out


def rotate(mask, degrees, center=(C, C)):
    return mask.rotate(degrees, center=(sx(center[0]), sx(center[1])), resample=Image.Resampling.BICUBIC)


# The system applies the enclosure dynamically. Android cannot, so this is only
# the final crop, not a decorative frame.
ENCL = rr((0, 0, 1024, 1024), 228)


def _vertical_gradient(colors):
    colors = [rgb(c) for c in colors]
    if len(colors) == 1:
        colors = [mix(colors[0], (255,255,255), .12), colors[0], mix(colors[0], (0,0,0), .09)]
    if len(colors) == 2:
        colors = [colors[0], mix(colors[0], colors[1], .5), colors[1]]
    half = WORK // 2
    top = ImageOps.colorize(Image.linear_gradient('L').resize((WORK, half)), colors[0], colors[1]).convert('RGBA')
    bottom = ImageOps.colorize(Image.linear_gradient('L').resize((WORK, WORK-half)), colors[1], colors[-1]).convert('RGBA')
    im = Image.new('RGBA', (WORK, WORK), (0,0,0,0))
    im.paste(top, (0,0)); im.paste(bottom, (0,half))
    return im


def _ambient_pools(im):
    glow = Image.radial_gradient('L').resize((int(WORK*.95), int(WORK*.95)), Image.Resampling.BICUBIC)
    glow = ImageOps.invert(glow).point(lambda v: int(v*.055))
    gm = Image.new('L', (WORK,WORK), 0); gm.paste(glow, (-int(WORK*.18), -int(WORK*.28)))
    white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(gm); im.alpha_composite(white)
    shade = Image.radial_gradient('L').resize((int(WORK*1.05), int(WORK*1.05)), Image.Resampling.BICUBIC)
    shade = ImageOps.invert(shade).point(lambda v: int(v*.035))
    sm = Image.new('L', (WORK,WORK), 0); sm.paste(shade, (int(WORK*.30), int(WORK*.25)))
    black = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); black.putalpha(sm); im.alpha_composite(black)
    return im


def background(spec):
    kind = spec.get('type', 'auto')
    cols = spec.get('colors') or [spec.get('color', '#7a7a80')]
    im = _vertical_gradient(cols)
    if kind == 'radial' and len(cols) > 1:
        pm = Image.new('L', (WORK,WORK), 0)
        d = ImageDraw.Draw(pm)
        d.ellipse((int(WORK*.42), -int(WORK*.10), int(WORK*1.08), int(WORK*.58)), fill=128)
        pm = pm.filter(ImageFilter.GaussianBlur(int(WORK*.14)))
        tint = Image.new('RGBA', (WORK,WORK), (*rgb(cols[-1]), 0)); tint.putalpha(pm); im.alpha_composite(tint)
    im = _ambient_pools(im)
    im.putalpha(ENCL)
    return im


def _max_filter(mask, px):
    n = max(3, sx(px) * 2 + 1)
    if n % 2 == 0:
        n += 1
    return mask.filter(ImageFilter.MaxFilter(n))


def _min_filter(mask, px):
    n = max(3, sx(px) * 2 + 1)
    if n % 2 == 0:
        n += 1
    return mask.filter(ImageFilter.MinFilter(n))


def inner_edge(mask, px=2.2):
    return sub(mask, _min_filter(mask, px))


def outer_edge(mask, px=2.0):
    return sub(_max_filter(mask, px), mask)


def top_facing_edge(mask, px=2.2):
    return sub(mask, shifted(mask, 0, px))


def bottom_facing_edge(mask, px=1.5):
    return sub(mask, shifted(mask, 0, -px))


def _vertical_weight(top=True):
    g = Image.linear_gradient('L').resize((WORK, WORK))
    return ImageOps.invert(g) if top else g


def finish_enclosure(canvas):
    grad = Image.linear_gradient('L').resize((WORK, WORK))
    grad = ImageOps.invert(grad).point(lambda v: int((v/255.0)**3 * 20))
    grad = inter(grad, ENCL)
    white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(grad); canvas.alpha_composite(white)
    top = inter(top_facing_edge(ENCL, 3.6), _vertical_weight(True)).point(lambda v: int(v*.34))
    hi = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); hi.putalpha(top); canvas.alpha_composite(hi)
    lo_field = Image.linear_gradient('L').resize((WORK,WORK)).point(lambda v: int((v/255.0)**3 * 13))
    lo_field = inter(lo_field, ENCL)
    black = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); black.putalpha(lo_field); canvas.alpha_composite(black)
    low = inter(bottom_facing_edge(ENCL, 2.3), _vertical_weight(False)).point(lambda v: int(v*.10))
    dk = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); dk.putalpha(low); canvas.alpha_composite(dk)
    canvas.putalpha(ENCL)


def _masked_source_alpha(image, mask, factor=1.0):
    """Clip by mask without turning transparent source pixels opaque."""
    source_alpha = image.getchannel('A')
    gate = mask.point(lambda v: int(v * max(0.0, min(1.0, factor))))
    image.putalpha(inter(source_alpha, gate))
    return image


def _lens_refract(under, mask, strength=.045, offset=(0,0), blur=0):
    bb = mask.getbbox()
    if not bb or strength <= 0:
        return _masked_source_alpha(under.copy(), mask, 1.0)
    cx = (bb[0]+bb[2])/2
    cy = (bb[1]+bb[3])/2
    scale = 1.0 + min(.18, max(0.0, strength))
    a = 1/scale
    e = 1/scale
    c = cx - cx*a - sx(offset[0])
    f = cy - cy*e - sx(offset[1])
    refr = under.transform((WORK,WORK), Image.Transform.AFFINE, (a,0,c,0,e,f), resample=Image.Resampling.BICUBIC)
    if blur:
        refr = refr.filter(ImageFilter.GaussianBlur(max(.1, sx(blur))))
    return _masked_source_alpha(refr, mask, .92)


def _apply_blend(canvas, layer, mode):
    alpha = layer.getchannel('A')
    if mode == 'screen':
        canvas.paste(ImageChops.screen(canvas, layer), (0,0), alpha)
    elif mode == 'multiply':
        canvas.paste(ImageChops.multiply(canvas, layer), (0,0), alpha)
    elif mode == 'plus_lighter':
        canvas.paste(ImageChops.add(canvas, layer, scale=1.0, offset=0), (0,0), alpha)
    else:
        canvas.alpha_composite(layer)


def _surface_sheen(mask, strength=.18):
    y = Image.linear_gradient('L').resize((WORK,WORK))
    y = ImageOps.invert(y).point(lambda v: int(((v/255.0)**2.4) * 255 * strength))
    return inter(mask, y).filter(ImageFilter.GaussianBlur(max(1, sx(1.0))))


def _reflection_field(mask, strength=.22):
    """Broad and narrow reflected-light bands; not a uniform white overlay."""
    field = blank_mask()
    d = ImageDraw.Draw(field)
    s = max(0.0, min(1.0, strength))
    d.polygon([(-180, 230), (20, -80), (980, 500), (780, 760)], fill=int(255 * .34 * s))
    d.polygon([(360, -120), (520, -120), (1040, 360), (1040, 500)], fill=int(255 * .25 * s))
    d.ellipse((590, -180, 1110, 330), fill=int(255 * .20 * s))
    field = field.filter(ImageFilter.GaussianBlur(max(1, sx(46))))
    return inter(field, mask)


def _clear_dark_reflection(mask, strength=.12):
    field = blank_mask()
    d = ImageDraw.Draw(field)
    d.ellipse((500, 520, 1180, 1180), fill=int(255 * max(0.0, min(1.0, strength))))
    field = field.filter(ImageFilter.GaussianBlur(max(1, sx(90))))
    return inter(field, mask)


def composite_layer(canvas, mask, *, fill='#ffffff', material='glass', opacity=.78,
                    refraction=.065, refract_offset=(0,0), blur=0, specular='automatic',
                    shadow=.035, blend='normal', shadow_offset=2.0, shadow_blur=5.0):
    under = canvas.copy()
    color = rgb(fill)
    # Clear pack starts from a genuinely translucent enclosure; color pack is opaque in the center.
    clear_context = under.getchannel('A').getpixel((WORK // 2, WORK // 2)) < 220

    if shadow and material != 'ink':
        sm = shifted(mask, 0, shadow_offset).filter(ImageFilter.GaussianBlur(max(1, sx(shadow_blur))))
        sm = sm.point(lambda v: int(v * min(.11, shadow)))
        black = Image.new('RGBA', (WORK,WORK), (0,0,0,255)); black.putalpha(sm); canvas.alpha_composite(black)

    layer_img = Image.new('RGBA', (WORK,WORK), (0,0,0,0))
    if material == 'glass':
        refr = _lens_refract(under, mask, max(.02, refraction), refract_offset, blur)
        refr = ImageEnhance.Contrast(refr).enhance(1.04 if clear_context else 1.035)
        refr = ImageEnhance.Color(refr).enhance(1.02 if clear_context else 1.06)
        layer_img.alpha_composite(refr)

        if refraction > .02:
            edge_band = inner_edge(mask, 12.0 if clear_context else 10.0)
            strong = _lens_refract(
                under,
                edge_band,
                min(.19 if clear_context else .16, refraction * (2.05 if clear_context else 1.75)),
                (refract_offset[0]-1.8, refract_offset[1]-1.2),
                blur,
            )
            strong = ImageEnhance.Contrast(strong).enhance(1.10 if clear_context else 1.08)
            strong = ImageEnhance.Color(strong).enhance(1.04 if clear_context else 1.12)
            strong = _masked_source_alpha(strong, edge_band, .82 if clear_context else .72)
            layer_img.alpha_composite(strong)

        luma = luminance(color)
        if clear_context:
            material_alpha = opacity * (.27 if luma >= 228 else .34)
            material_alpha = max(.07, min(.42, material_alpha))
        else:
            material_alpha = opacity * (.46 if luma >= 228 else .62)
            material_alpha = max(.24, min(.76, material_alpha))

        tint = Image.new('RGBA', (WORK,WORK), (*color,0))
        tint.putalpha(mask.point(lambda v: int(v * material_alpha)))
        layer_img.alpha_composite(tint)

        sheen_strength = (.21 if luma > 210 else .16) if clear_context else (.115 if luma > 210 else .085)
        sheen = _surface_sheen(mask, sheen_strength)
        white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(sheen); layer_img.alpha_composite(white)

        if clear_context:
            reflect = _reflection_field(mask, .95)
            cool = Image.new('RGBA', (WORK,WORK), (236,246,255,0)); cool.putalpha(reflect); layer_img.alpha_composite(cool)
            dark = _clear_dark_reflection(mask, .10)
            dk2 = Image.new('RGBA', (WORK,WORK), (74,82,96,0)); dk2.putalpha(dark); layer_img.alpha_composite(dk2)

        mode = specular
        if mode == 'automatic':
            mode = 'inside' if luma >= 150 else 'outside'
        if mode != 'off':
            edge = top_facing_edge(mask, 4.4 if clear_context else 3.8) if mode == 'inside' else outer_edge(mask, 3.1 if clear_context else 2.6)
            edge = inter(edge, _vertical_weight(True)).point(
                lambda v: int(v * (1.0 if clear_context else (.92 if luma > 180 else .78)))
            )
            hi = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); hi.putalpha(edge); layer_img.alpha_composite(hi)

            rim_strength = .62 if clear_context else .42
            rim = inter(inner_edge(mask, 2.4 if clear_context else 2.1), _vertical_weight(True)).point(lambda v: int(v * rim_strength))
            rim_color = mix(color, (255,255,255), .72 if clear_context else .58)
            ri = Image.new('RGBA', (WORK,WORK), (*rim_color,0)); ri.putalpha(rim); layer_img.alpha_composite(ri)

            hair = outer_edge(mask, 1.2).point(lambda v: int(v * (.38 if clear_context else .26)))
            hc = mix(color, (255,255,255), .62 if clear_context else .46)
            ho = Image.new('RGBA', (WORK,WORK), (*hc,0)); ho.putalpha(hair); layer_img.alpha_composite(ho)

            low = inter(bottom_facing_edge(mask, 2.0), _vertical_weight(False)).point(lambda v: int(v * (.12 if clear_context else .17)))
            dk = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); dk.putalpha(low); layer_img.alpha_composite(dk)
    else:
        alpha = mask.point(lambda v: int(v * max(.0, min(1.0, opacity))))
        tint = Image.new('RGBA', (WORK,WORK), (*color,0)); tint.putalpha(alpha); layer_img.alpha_composite(tint)

    _apply_blend(canvas, layer_img, blend)


def text_mask(text, size=260, yoff=0, bold=True):
    font = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, sx(size))
    m = blank_mask()
    d = ImageDraw.Draw(m)
    box = d.textbbox((0,0), text, font=font)
    x = (WORK-(box[2]-box[0]))/2-box[0]
    y = (WORK-(box[3]-box[1]))/2-box[1]+sx(yoff)
    d.text((x,y), text, font=font, fill=255)
    return m


def layer(mask, fill='#fff', opacity=.88, refraction=.045, specular='automatic', shadow=.05,
          material='glass', blend='normal', offset=(0,0), blur=0, shadow_offset=3.0, shadow_blur=7.0):
    return dict(
        mask=mask,
        fill=fill,
        opacity=opacity,
        refraction=refraction,
        specular=specular,
        shadow=shadow,
        material=material,
        blend=blend,
        refract_offset=offset,
        blur=blur,
        shadow_offset=shadow_offset,
        shadow_blur=shadow_blur,
    )
