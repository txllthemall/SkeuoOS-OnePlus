from __future__ import annotations

import generate_liquid27 as gen
from liquid27.glyphs_vector_complete import glyph_vector_complete, COMPLETE_VECTOR_KINDS

# The main generator contains the reviewed reference/brand paths.  This driver
# closes the last gap: every remaining catalog kind must resolve through the
# SVG2048 completion module before any historical fallback can be reached.
_original_base_layers = gen.base_layers


def release_base_layers(kind):
    completed = glyph_vector_complete(kind)
    if completed:
        return completed
    return _original_base_layers(kind)


gen.base_layers = release_base_layers
gen.ALL_VECTOR_KINDS = set(gen.ALL_VECTOR_KINDS) | set(COMPLETE_VECTOR_KINDS)


if __name__ == '__main__':
    gen.main()
