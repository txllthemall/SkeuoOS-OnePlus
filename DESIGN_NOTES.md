# SkeuoOS Liquid27 v4 — design notes

This version is a clean-room, static Android interpretation of Apple's current iOS 27 app-icon material system. It does **not** bundle or extract Apple app-icon artwork, and it does not reuse the v2 iOS 6 archive.

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
4. **Sharper iOS 27 material.** Apple's 2026 Icon Composer guidance describes a new sharper rendering, crisp specular highlights and a vertical light angle from above. The WWDC26 group lab also recommends reviewing/reducing translucency for legibility when bringing iOS 26 icons forward.
5. **Directional specular.** The renderer supports `automatic`, `inside`, `outside`, and `off`. Highlights are generated from directional mask edges, not a uniform white outline.
6. **Real under-layer sampling.** Static refraction samples pixels already composited beneath a layer. A stronger edge band creates lens-like bending near material boundaries. This is not a generic white overlay or blur.
7. **Restrained translucency.** The material tint remains saturated while enough of the actual lower layer is transmitted for the glass to read as material instead of a pastel sticker.
8. **Restrained shadows.** Shadows only separate z-layers. There is no floating-button shadow treatment on the enclosure.
9. **Optical consistency.** QA measures foreground bounds, occupied area, center offset, luminance and contrast and produces full, neutral, wallpaper and OnePlus-scale previews.
10. **Vector-like source geometry.** V4 geometry is built from masks, curves, paths and primitives on Apple's documented 1024×1024 icon canvas, then baked to 512×512 with Lanczos. No old raster glyph is scaled up.

## Curated v4 geometry

The most visible icons use a new `glyphs_v4.py` layer set rather than the v3 glyph shortcuts. Current curated set includes Phone, Messages, Camera, Photos, Settings, Mail, Gmail, Maps, Clock, Weather, Notes, Calendar, App Store, Calculator, Recorder, Telegram, Discord, YouTube, ReVanced, Chrome, Spotify, Instagram, SoundCloud, Kaspi, 2GIS, ChatGPT, GameHub and Play Store. Existing Android component mappings are retained; less-common icons can still use the semantic fallback geometry while the curated set expands.

## v3 failures explicitly removed

- shared metallic frame / bevel
- pseudo-skeuomorphic button shell
- large outer shadow
- universal vertical gradient used as fake depth
- white-overlay “glass”
- tiny glyphs floating inside oversized containers
- letters used as a shortcut for core brands where a semantic mark can be constructed
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
- high-resolution render followed by Lanczos 512×512 output
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

1. full contact sheet
2. light neutral
3. dark neutral
4. color-rich wallpaper field
5. OnePlus/Home-Screen-scale layout
