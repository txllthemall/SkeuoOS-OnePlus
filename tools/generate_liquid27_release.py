from __future__ import annotations

import generate_liquid27 as gen
from liquid27.glyphs_vector_complete import glyph_vector_complete, COMPLETE_VECTOR_KINDS
from liquid27.glyphs_brand_fixes import glyph_brand_fix, FIXED_BRAND_KINDS
from liquid27.glyphs_brand_precision import glyph_brand_precision, PRECISION_BRAND_KINDS

# Release order is explicit: precision traces first, then verified brand fixes,
# then full SVG coverage, then the already-reviewed reference/home/curated stack.
_original_base_layers = gen.base_layers


def release_base_layers(kind):
    precise = glyph_brand_precision(kind)
    if precise:
        return precise
    fixed = glyph_brand_fix(kind)
    if fixed:
        return fixed
    completed = glyph_vector_complete(kind)
    if completed:
        return completed
    return _original_base_layers(kind)


gen.base_layers = release_base_layers
gen.ALL_VECTOR_KINDS = (
    set(gen.ALL_VECTOR_KINDS)
    | set(COMPLETE_VECTOR_KINDS)
    | set(FIXED_BRAND_KINDS)
    | set(PRECISION_BRAND_KINDS)
)


if __name__ == '__main__':
    gen.main()
