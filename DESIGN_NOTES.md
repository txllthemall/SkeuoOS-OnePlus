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

## Design invariants

1. **Layer-first construction.** Background and meaningful foreground layers remain independent until the final static bake.
2. **Simple, bold, optically balanced shapes.** Home Screen readability matters more than detail visible only at 512 px.
3. **No decorative outer shell.** No metallic ring, bevel, pseudo-chrome frame, or common floating-button shadow.
4. **Sharper material response.** Specular response is directional from above and edge-aware rather than a uniform white stroke.
5. **Per-layer material.** Refraction, opacity, shadow and specular are properties of each material layer, not a global overlay.
6. **Real under-layer sampling.** Color mode samples already-composited pixels below a glass layer for the static refraction approximation.
7. **Restrained shadows.** Shadows exist only to separate z-layers.
8. **Continuous vector source geometry.** Reference glyphs are SVG paths/primitives rasterized by Cairo at 2048 px, then downsampled into the 1024 material renderer and finally baked to 512×512 with Lanczos.
9. **One geometry system, two appearance presets.** Color and Clear share component mappings and glyph geometry. Only material/background treatment changes.

## Two installable APKs

### SkeuoOS Liquid27

- product flavor: `color`
- package id: `io.github.txllthemall.skeuoos`
- keeps the existing package id so it upgrades the previous normal pack
- colored backgrounds and brand-aware glass layers
- higher opacity for maximum daily readability

### SkeuoOS Liquid27 Clear

- product flavor: `clear`
- package id: `io.github.txllthemall.skeuoos.clear`
- can be installed next to the Color build
- same glyph masks and Android component mappings as Color
- brand color is intentionally removed from the material pass
- enclosure and glyphs retain partial PNG alpha so the actual OxygenOS wallpaper remains visible through the icon
- stronger neutral glass/specular treatment and much lower enclosure opacity

The Clear APK can transmit the real wallpaper through alpha, but a static PNG cannot *refract* wallpaper pixels it does not know at build time. The clear renderer therefore does not fake wallpaper-dependent distortion with a painted gradient.

## Gmail is Gmail, not generic Mail

`skeuo_gmail` is permanently mapped to the dedicated `gmail` geometry kind. It does not reuse `mail`.

The Color build uses an original multicolor glass **M** construction with separate blue, red, yellow and green vector strokes over a glass card. The Clear build uses the exact same M geometry, converted by the shared Clear material preset to neutral translucent glass. CI explicitly checks that Gmail is mapped to `gmail` and that its composition is not identical to generic Mail.

## SVG2048 geometry

`tools/liquid27/vector.py` is the vector rasterization boundary. Geometry is assembled in:

- `glyphs_vector.py` — first reference set
- `glyphs_vector_tuned.py` — optical tuning overrides
- `glyphs_vector_home.py` — expanded Home Screen set

The generator preference order is SVG tuning → expanded SVG geometry → base SVG geometry → transitional older v4 geometry. The long-term goal is to eliminate the transitional path entirely.

Current SVG/Home Screen coverage includes the core reference set plus Gmail, Maps, Google Maps, Clock, Weather, Notes, Calendar, Google Calendar, App Store, ReVanced, Chrome, Recorder, SoundCloud, Kaspi, 2GIS, GameHub, Play Store and Google Photos.

## Geometry-source licensing

No Apple icon artwork is shipped.

For a small number of generic/system semantic silhouettes, vector bases may come from **Bootstrap Icons** under MIT. Selected brand silhouettes may use **SuperTinyIcons** under MIT and **Simple Icons** under CC0 where appropriate. Trademark rights remain with the respective brands. Material, layout, refraction treatment, Android packaging, variant system and original geometry authored in this repository are SkeuoOS work.

## Removed failure modes

- shared metallic frame / bevel
- pseudo-skeuomorphic button shell
- large outer shadow
- universal gradient used as fake depth
- white-overlay “glass”
- tiny glyphs floating inside oversized containers
- low-point-count polygon approximations of recognisable marks
- bitmap rotation of already-rasterized masks for reference geometry
- sampled Bézier-as-thick-line handset geometry
- zagnut / iOS 6 fallback artwork and importer
- Gmail being treated as generic email

## Static Android limitations

Not possible in a static OxygenOS PNG:

- motion-driven highlight movement
- real-time environment lighting
- live wallpaper-dependent refraction/distortion
- Apple's runtime Default / Dark / Clear / Tinted switching from one `.icon` source
- system HDR icon rendering
- platform dynamic enclosure adaptation

## QA policy

`tools/generate_liquid27.py --variant all` generates both resource sets under:

- `app/src/color/res/`
- `app/src/clear/res/`

Preview and QA output is separated under:

- `build/liquid27-v4/color/`
- `build/liquid27-v4/clear/`

`tools/qa_liquid27.py --variant all` checks both appearances, SVG geometry coverage, optical centering, foreground coverage, contrast and alpha behavior. Clear fails QA if it becomes effectively opaque or effectively invisible. `tools/check_pack.py` verifies that every drawable referenced by the shared OnePlus/OxygenOS mappings exists in **both** flavor resource sets.
