# SkeuoOS Liquid27 v4 — design notes

This version is a clean-room, static Android interpretation of Apple's current iOS 27 app-icon design system. It does **not** bundle or extract Apple app-icon artwork and it does not reuse the v2 iOS 6 archive.

## Official sources used as source of truth

Accessed 2026-08-31:

- Apple Human Interface Guidelines — App icons: https://developer.apple.com/design/human-interface-guidelines/app-icons
- Creating your app icon using Icon Composer: https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer
- Icon Composer: https://developer.apple.com/icon-composer/
- Adopting Liquid Glass — App icons: https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- Liquid Glass overview/design principles: https://developer.apple.com/documentation/technologyoverviews/liquid-glass
- Apple Design Resources — iOS 27 / iPadOS 27 App Icon Template: https://developer.apple.com/design/resources/
- WWDC26 — Icon Composer for Beginners Group Lab: https://developer.apple.com/videos/play/wwdc2026/8012/
- WWDC26 Platforms State of the Union: https://developer.apple.com/videos/play/wwdc2026/112/
- SF Symbols 8 beta overview: https://developer.apple.com/sf-symbols/

## Design invariants taken from Apple guidance

1. **Layer-first construction.** A background plus one or more meaningful foreground layers is the primary model. Layers are ordered in z, and material properties belong to layers/groups rather than to a flattened painting.
2. **Simple, bold, overlapping shapes.** The smallest Home Screen presentation is a first-class target. Excessive complexity is rejected because refraction and overlap become noisy at small sizes.
3. **No decorative outer shell.** Apple applies the enclosure and platform crop. The Android bake contains only an alpha enclosure for launcher portability — no metallic ring, bevel, pseudo-chrome, or common embossed frame.
4. **iOS 27 is sharper than the first Liquid Glass release.** WWDC26 guidance calls for reviewing specular placement, shadows and refraction and explicitly notes reduced translucency for sharper, more legible icons.
5. **Directional specular.** The renderer supports `automatic`, `inside`, `outside`, and `off`. Highlights are generated from top-facing mask edges, not from a uniform white outline.
6. **Real under-layer sampling.** Static refraction samples the actual already-composited pixels behind the foreground mask, then applies a weak convex affine displacement. It is not a generic blur or white overlay.
7. **Restrained shadows.** Shadows only separate layers. There is no large floating-button shadow on the enclosure.
8. **Optical consistency.** A QA report measures foreground bounding box, occupied area, center offset, luminance and contrast for every icon and checks multiple previews including the full contact sheet and Home Screen scale.
9. **Vector-like source geometry.** Glyphs are constructed from masks/primitives at a 1536-unit design coordinate space, rasterized at 1024×1024, then downsampled to 512×512 using Lanczos. No legacy raster glyphs are enlarged.

## v3 failures explicitly removed

- shared metallic frame / bevel
- pseudo-skeuomorphic button shell
- large outer shadow
- universal top-to-bottom gradient as the source of depth
- white-overlay “glass”
- tiny glyphs floating inside oversized containers
- text initials used as a shortcut for brands where a semantic shape can be constructed
- zagnut / iOS 6 fallback artwork

## Static Android approximations

Apple's native icon renderer is dynamic. A PNG icon pack cannot reproduce all of it.

### Implemented as a static bake

- independent layer materials
- background / foreground z hierarchy
- per-layer translucency
- per-layer blur parameter
- real under-layer sampling for refraction
- refraction strength and directional offset
- automatic / inside / outside / off specular modes
- restrained per-layer shadow
- normal, screen and multiply blend paths
- supersampling and Lanczos downsampling
- launcher-safe alpha enclosure and safe-area-oriented artwork

### Not possible in a static OxygenOS PNG

- device-motion-driven highlight movement
- real-time environment lighting
- live background-dependent refraction after the icon is placed on the Home Screen
- Apple's runtime Default / Dark / Clear / Tinted appearance switching from one `.icon` source
- system HDR icon rendering
- platform-specific dynamic enclosure adaptation

For these reasons v4 targets the **Default appearance at Home Screen size** and bakes a conservative snapshot of the material. Dynamic behaviors are documented rather than faked with heavy decorative effects.

## QA policy

`tools/generate_liquid27.py` writes `build/liquid27-v4/qa.json` and `qa.tsv`. `tools/qa_liquid27.py` checks:

- all generated icons are represented
- foreground occupied area is not extreme
- optical center stays within tolerance
- contrast anomalies are surfaced
- all preview contexts exist

Preview contexts:

1. full 66-icon contact sheet
2. light neutral
3. dark neutral
4. colorful photographic-style field
5. OnePlus/Home-Screen-scale layout
