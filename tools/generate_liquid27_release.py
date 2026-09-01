from __future__ import annotations

import generate_liquid27 as gen
from liquid27.glyphs_vector_complete import glyph_vector_complete, COMPLETE_VECTOR_KINDS
from liquid27.glyphs_brand_fixes import glyph_brand_fix, FIXED_BRAND_KINDS

# Release order is explicit: verified brand corrections first, then the complete
# SVG coverage module, then the already-reviewed reference/home/curated stack.
_original_base_layers = gen.base_layers


def release_base_layers(kind):
    fixed = glyph_brand_fix(kind)
    if fixed:
        return fixed
    completed = glyph_vector_complete(kind)
    if completed:
        return completed
    return _original_base_layers(kind)


gen.base_layers = release_base_layers
gen.ALL_VECTOR_KINDS = set(gen.ALL_VECTOR_KINDS) | set(COMPLETE_VECTOR_KINDS) | set(FIXED_BRAND_KINDS)


if __name__ == '__main__':
    gen.main()
