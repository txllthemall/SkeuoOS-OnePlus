from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
import math

# Apple documents a 1024x1024 iPhone/iPad/Mac icon canvas. We author in that
# coordinate space, rasterize at 1536x1536, then Lanczos-bake to the 512px Android asset.
DESIGN = 1024.0
WORK = 1536
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


def scale_mask(mask, factor, center=(C, C)):
    if abs(factor - 1.0) < 1e-6:
        return mask
    if not mask.getbbox():
        return mask
    cx, cy = sx(center[0]), sx(center[1])
    w = max(1, int(WORK * factor)); h = max(1, int(WORK * factor))
    scaled = mask.resize((w, h), Image.Resampling.BICUBIC)
    out = blank_mask(); x = cx - w // 2; y = cy - h // 2
    if w <= WORK and h <= WORK:
        out.paste(scaled, (x, y))
    else:
        out = scaled.crop((-x, -y, -x + WORK, -y + WORK))
    return out


# The system normally applies the enclosure mask. Android needs a flattened crop.
# This is deliberately not a decorative border, chrome ring, or baked bevel.
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
    im = Image.new('RGBA', (WORK, WORK), (0,0,0,0)); im.paste(top, (0,0)); im.paste(bottom, (0,half))
    return im


def _ambient_pools(im):
    # Broad, low-amplitude lighting changes field density without drawing a frame.
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
        pm = Image.new('L', (WORK,WORK), 0); d = ImageDraw.Draw(pm)
        d.ellipse((int(WORK*.42), -int(WORK*.10), int(WORK*1.08), int(WORK*.58)), fill=128)
        pm = pm.filter(ImageFilter.GaussianBlur(int(WORK*.14)))
        tint = Image.new('RGBA', (WORK,WORK), (*rgb(cols[-1]), 0)); tint.putalpha(pm); im.alpha_composite(tint)
    im = _ambient_pools(im); im.putalpha(ENCL)
    return im


def finish_enclosure(canvas):
    """Subtle system-like enclosure lighting. No stroke, bevel, or chrome."""
    grad = ImageOps.invert(Image.linear_gradient('L').resize((WORK,WORK)))
    grad = grad.point(lambda v: int((v/255.0)**3 * 18)); grad = inter(grad, ENCL)
    white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(grad); canvas.alpha_composite(white)
    lo = Image.linear_gradient('L').resize((WORK,WORK)).point(lambda v: int((v/255.0)**3 * 12)); lo = inter(lo, ENCL)
    black = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); black.putalpha(lo); canvas.alpha_composite(black)
    canvas.putalpha(ENCL)


def _lens_refract(under, mask, strength=.045, offset=(0,0), blur=0):
    """Static lens bake using pixels already composited beneath this layer."""
    bb = mask.getbbox()
    if not bb or strength <= 0:
        out = under.copy(); out.putalpha(mask); return out
    cx = (bb[0]+bb[2])/2; cy = (bb[1]+bb[3])/2
    scale = 1.0 + min(.18, max(0.0, strength)); a = 1/scale; e = 1/scale
    c = cx - cx*a - sx(offset[0]); f = cy - cy*e - sx(offset[1])
    refr = under.transform((WORK,WORK), Image.Transform.AFFINE, (a,0,c,0,e,f), resample=Image.Resampling.BICUBIC)
    if blur: refr = refr.filter(ImageFilter.GaussianBlur(max(.1, sx(blur))))
    refr.putalpha(mask.point(lambda v: int(v*.92)))
    return refr


def _max_filter(mask, px):
    n = max(3, sx(px)*2+1); n = n if n%2 else n+1
    return mask.filter(ImageFilter.MaxFilter(n))


def _min_filter(mask, px):
    n = max(3, sx(px)*2+1); n = n if n%2 else n+1
    return mask.filter(ImageFilter.MinFilter(n))


def inner_edge(mask, px=2.2): return sub(mask, _min_filter(mask, px))
def outer_edge(mask, px=2.0): return sub(_max_filter(mask, px), mask)
def top_facing_edge(mask, px=2.2): return sub(mask, shifted(mask, 0, px))
def bottom_facing_edge(mask, px=1.5): return sub(mask, shifted(mask, 0, -px))

def _vertical_weight(top=True):
    g = Image.linear_gradient('L').resize((WORK,WORK)); return ImageOps.invert(g) if top else g


def _apply_blend(canvas, layer, mode):
    alpha = layer.getchannel('A')
    if mode == 'screen': canvas.paste(ImageChops.screen(canvas, layer), (0,0), alpha)
    elif mode == 'multiply': canvas.paste(ImageChops.multiply(canvas, layer), (0,0), alpha)
    elif mode == 'plus_lighter': canvas.paste(ImageChops.add(canvas, layer, scale=1.0, offset=0), (0,0), alpha)
    elif mode == 'plus_darker':
        inv = ImageChops.invert(ImageChops.add(ImageChops.invert(canvas.convert('RGB')), ImageChops.invert(layer.convert('RGB'))).convert('RGB')).convert('RGBA'); inv.putalpha(alpha); canvas.alpha_composite(inv)
    else: canvas.alpha_composite(layer)


def composite_layer(canvas, mask, *, fill='#ffffff', material='glass', opacity=.88,
                    refraction=.045, refract_offset=(0,0), blur=0, specular='automatic',
                    shadow=.05, blend='normal', shadow_offset=3.0, shadow_blur=7.0):
    under = canvas.copy()
    if shadow and material != 'ink':
        sm = shifted(mask, 0, shadow_offset).filter(ImageFilter.GaussianBlur(max(1, sx(shadow_blur))))
        sm = sm.point(lambda v: int(v*min(.18, shadow)))
        black = Image.new('RGBA', (WORK,WORK), (0,0,0,255)); black.putalpha(sm); canvas.alpha_composite(black)

    layer_img = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); color = rgb(fill)
    if material == 'glass':
        layer_img.alpha_composite(_lens_refract(under, mask, refraction, refract_offset, blur))
        # Near-white layers stay visibly glassy rather than becoming opaque stickers.
        eff_opacity = opacity * (.82 if luminance(color) >= 228 else 1.0)
        tint_alpha = mask.point(lambda v: int(v*max(0.0, min(1.0, eff_opacity))))
        tint = Image.new('RGBA', (WORK,WORK), (*color,0)); tint.putalpha(tint_alpha); layer_img.alpha_composite(tint)
        mode = specular
        if mode == 'automatic': mode = 'inside' if luminance(color) >= 135 else 'outside'
        if mode != 'off':
            edge = top_facing_edge(mask, 2.1) if mode == 'inside' else outer_edge(mask, 1.8)
            edge = inter(edge, _vertical_weight(True)).point(lambda v: int(v*.88))
            hi = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); hi.putalpha(edge); layer_img.alpha_composite(hi)
            low = inter(bottom_facing_edge(mask, 1.1), _vertical_weight(False)).point(lambda v: int(v*.16))
            dk = Image.new('RGBA', (WORK,WORK), (0,0,0,0)); dk.putalpha(low); layer_img.alpha_composite(dk)
    elif material in ('solid','ink'):
        alpha = mask.point(lambda v: int(v*max(0.0, min(1.0, opacity))))
        tint = Image.new('RGBA', (WORK,WORK), (*color,0)); tint.putalpha(alpha); layer_img.alpha_composite(tint)
        if material == 'solid' and specular != 'off':
            hi = inter(top_facing_edge(mask, 1.5), _vertical_weight(True)).point(lambda v: int(v*.30))
            white = Image.new('RGBA', (WORK,WORK), (255,255,255,0)); white.putalpha(hi); layer_img.alpha_composite(white)
    _apply_blend(canvas, layer_img, blend)


def text_mask(text, size=260, yoff=0, bold=True):
    font = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, sx(size))
    m = blank_mask(); d = ImageDraw.Draw(m); box = d.textbbox((0,0), text, font=font)
    x = (WORK-(box[2]-box[0]))/2-box[0]; y = (WORK-(box[3]-box[1]))/2-box[1]+sx(yoff)
    d.text((x,y), text, font=font, fill=255); return m


def layer(mask, fill='#fff', opacity=.88, refraction=.045, specular='automatic',
          shadow=.05, material='glass', blend='normal', offset=(0,0), blur=0,
          shadow_offset=3.0, shadow_blur=7.0):
    return dict(mask=mask, fill=fill, opacity=opacity, refraction=refraction,
                specular=specular, shadow=shadow, material=material, blend=blend,
                refract_offset=offset, blur=blur, shadow_offset=shadow_offset,
                shadow_blur=shadow_blur)
