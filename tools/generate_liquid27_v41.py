from __future__ import annotations

from PIL import Image

import generate_liquid27 as gen
from liquid27.clear_material import clearify_layers, clear_background, finish_clear_enclosure
from liquid27.material import WORK, OUT, background, composite_layer, finish_enclosure, ENCL


def layers_for(kind, variant='color'):
    layers = gen.base_layers(kind)
    return clearify_layers(layers, kind) if variant == 'clear' else layers


def render(name, bgspec, kind, variant='color'):
    canvas = Image.new('RGBA', (WORK, WORK), (0, 0, 0, 0))
    if variant == 'clear':
        canvas.alpha_composite(clear_background(name))
        layers = clearify_layers(gen.base_layers(kind), name)
    else:
        canvas.alpha_composite(background(bgspec))
        layers = gen.base_layers(kind)

    for lay in layers:
        composite_layer(canvas, **lay)

    if variant == 'clear':
        finish_clear_enclosure(canvas, name)
    else:
        finish_enclosure(canvas)
        canvas.putalpha(ENCL)

    return canvas.resize((OUT, OUT), Image.Resampling.LANCZOS)


# Keep all existing catalog, preview and QA plumbing. Only swap the material path.
gen.layers_for = layers_for
gen.render = render


if __name__ == '__main__':
    gen.main()
