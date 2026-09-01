# SkeuoOS Liquid27 v4 — design notes

This version is a static Android interpretation of Apple's current iOS 27 app-icon material system. It does **not** bundle or extract Apple app-icon artwork, and it does not reuse the v2 iOS 6 archive.

## Official sources used as source of truth

Reviewed on 2026-08-31:

- Apple Human Interface Guidelines — App icons: https://developer.apple.com/design/human-interface-guidelines/app-icons
- Creating your app icon using Icon Composer: https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer
- Icon Composer 2026 product/documentation page: https://developer.apple.com/icon-composer/
- Adopting Liquid Glass — App icons: https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- Apple Design Resources — current iOS/iPadOS app-icon grids: https://developer.apple.com/design/resources/
- WWDC26 — Icon Composer for Beginners Group Lab: https://developer.apple.com/videos/play/wwdc2026/8012/
- WWDC26 Design guide: https://developer.apple.com/wwdc26/guides/design/
- SF Symbols guidance for simple, legible symbol geometry: https://developer.apple.com/sf-symbols/

## Design invariants taken from Apple guidance

1. **Layer-first construction.** A background plus one or more meaningful foreground layers is the primary model. Layers are ordered back-to-front; material properties belong to layers/groups rather than being painted onto a flattened bitmap.
2. **Simple, bold, overlapping shapes.** Launcher-scale readability is a first-class target. Excessive complexity is avoided because overlap/refraction becomes noisy at small sizes.
3. **No decorative outer shell.** Apple applies the enclosure and platform crop. Android needs a flattened crop, but v4 does not add a metallic ring, bevel, pseudo-chrome shell, or large common drop shadow.
4. **Sharper iOS 27 material.** Apple's 2026 Icon Composer guidance describes a sharper rendering, crisp specular highlights and a vertical light angle from above. The WWDC26 group lab also recommends reviewing/reducing translucency for legibility when bringing iOS 26 icons forward.
5. **Directional specular.** The renderer supports `automatic`, `inside`, `outside`, and `off`. Highlights are generated from directional mask edges, not a uniform white outline.
6. **Real under-layer sampling.** Static refraction samples pixels already composited beneath a layer. A stronger edge band creates lens-like bending near material boundaries. This is not a generic white overlay or blur.
7. **Restrained translucency.** The material tint remains saturated while enough of the actual lower layer is transmitted for the glass to read as material instead of a pastel sticker.
8. **Restrained shadows.** Shadows only separate z-layers. There is no floating-button shadow treatment on the enclosure.
9. **Optical consistency.** QA measures foreground bounds, occupied area, center offset, luminance and contrast and produces full, neutral, wallpaper and OnePlus-scale previews.
10. **Continuous vector source geometry.** The reference glyph set is authored as SVG paths/primitives. Cairo rasterizes those paths at 2048 px, then the mask is downsampled into the material renderer and finally baked to 512×512 with Lanczos. No reference glyph is created by rotating a bitmap mask, joining Pillow polygons, or sampling a Bézier into a thick polyline.

## SVG2048 reference geometry

The geometry gate currently covers 12 reference icons:

- Phone
- Messages
- Camera
- Photos
- Settings
- Mail
- Telegram
- Discord
- YouTube
- Spotify
- Instagram
- ChatGPT

`tools/liquid27/vector.py` is the vector rasterization boundary and `tools/liquid27/glyphs_vector.py` contains the reference geometry. `tools/generate_liquid27.py` always prefers this path for the reference set. `tools/qa_liquid27.py` fails CI if fewer than 12 generated icons report the `svg2048` geometry engine.

The remaining catalog is still transitional and may use the older v4 semantic geometry until it is migrated. It is intentionally not described as finished.

## Geometry-source licensing

No Apple icon artwork is shipped.

For a small number of generic/system semantic silhouettes, the vector base comes from **Bootstrap Icons**, MIT licensed. For selected brand silhouettes, geometry is derived from **SuperTinyIcons**, MIT licensed, and **Simple Icons**, CC0. Their trademark policies still apply to the respective brands. Material, layout, refraction, color treatment and Android packaging are SkeuoOS work.

These sources are used specifically to avoid the previous failure mode where recognisable shapes were approximated with hand-entered rectangles, triangles and sampled bitmap curves.

## v3 / early-v4 failures explicitly removed from the reference set

- shared metallic frame / bevel
- pseudo-skeuomorphic button shell
- large outer shadow
- universal vertical gradient used as fake depth
- white-overlay “glass”
- tiny glyphs floating inside oversized containers
- low-point-count polygon approximations of recognisable brand marks
- bitmap rotation of already-rasterized masks
- sampled Bézier-as-thick-line handset geometry
- zagnut / iOS 6 fallback artwork and importer

## Static Android approximations

Apple's native renderer is dynamic. A PNG icon pack cannot reproduce all of it.

### Implemented as a static bake

- independent foreground layer materials
- background / foreground z hierarchy
- per-layer translucency
- real under-layer sampling for refraction
- stronger lens-like refraction at layer boundaries
- refraction strength and directional offset
- automatic / inside / outside / off specular modes
- vertical-light directional specular response
- restrained per-layer shadow
- normal, screen, multiply and additive-style blend paths where useful
- SVG reference masks rasterized at 2048 px
- Lanczos 512×512 output
- launcher-safe alpha enclosure and safe-area-oriented artwork

### Not possible in a static OxygenOS PNG

- device-motion-driven highlight movement
- real-time environment lighting
- live wallpaper-dependent refraction after placement on the Home Screen
- Apple's runtime Default / Dark / Clear / Tinted switching from one `.icon` source
- system HDR icon rendering
- platform-specific dynamic enclosure adaptation

V4 therefore targets **Default appearance at Home Screen size** and bakes a conservative static snapshot of the material. Dynamic effects are documented rather than replaced by heavy decorative chrome.

## QA policy

`tools/generate_liquid27.py` writes `build/liquid27-v4/qa.json` and `qa.tsv`. `tools/qa_liquid27.py` checks generated resources and preview outputs.

Preview contexts:

1. `preview_vector_reference.png` — the 12 SVG2048 geometry references
2. full contact sheet
3. light neutral
4. dark neutral
5. color-rich wallpaper field
6. OnePlus/Home-Screen-scale layout
