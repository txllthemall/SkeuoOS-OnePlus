from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from .surface import SurfaceMaps


def wallpaper(kind: str, size: tuple[int, int]) -> Image.Image:
    w, h = size
    im = Image.new("RGB", size, (96, 80, 102))
    d = ImageDraw.Draw(im)
    if kind == "dark":
        d.rectangle((0, 0, w, h), fill=(22, 24, 28))
        d.ellipse((int(w*0.56), int(h*0.08), int(w*1.02), int(h*0.56)), fill=(58, 62, 72))
    elif kind == "bright":
        d.rectangle((0, 0, w, h), fill=(238, 238, 234))
        d.ellipse((-int(w*0.08), int(h*0.12), int(w*0.52), int(h*0.72)), fill=(211, 207, 199))
    elif kind == "warm":
        d.rectangle((0, 0, w, h), fill=(126, 83, 63))
        d.ellipse((-int(w*0.12), -int(h*0.02), int(w*0.62), int(h*0.66)), fill=(186, 128, 83))
    elif kind == "blue":
        d.rectangle((0, 0, w, h), fill=(52, 70, 126))
        d.ellipse((int(w*0.38), -int(h*0.08), int(w*1.08), int(h*0.68)), fill=(77, 122, 178))
    elif kind == "midtone":
        d.rectangle((0, 0, w, h), fill=(111, 91, 111))
        d.ellipse((-int(w*0.12), -int(h*0.08), int(w*0.64), int(h*0.66)), fill=(168, 121, 132))
        d.ellipse((int(w*0.54), int(h*0.42), int(w*1.06), int(h*0.98)), fill=(72, 60, 90))
    elif kind == "highcontrast":
        d.rectangle((0, 0, w, h), fill=(34, 34, 36))
        step = max(18, w // 18)
        for x in range(-h, w + h, step * 2):
            d.line((x, 0, x + h, h), fill=(245, 245, 245), width=max(2, w // 180))
        for y in range(step, h, step * 2):
            d.line((0, y, w, y), fill=(180, 180, 180), width=max(1, w // 240))
    else:
        d.rectangle((0, 0, w, h), fill=(96, 80, 102))
    return im


def composite_center(bg: Image.Image, icon: Image.Image, px: int) -> Image.Image:
    out = bg.convert("RGB").copy()
    ic = icon.resize((px, px), Image.Resampling.LANCZOS)
    x = (out.width - px) // 2
    y = (out.height - px) // 2
    out.paste(ic, (x, y), ic)
    return out


def make_material_lab(icon: Image.Image, cell: int = 420) -> Image.Image:
    kinds = ["warm", "midtone", "blue", "dark", "bright", "highcontrast"]
    board = Image.new("RGB", (cell * 3, cell * 2), (0, 0, 0))
    for i, kind in enumerate(kinds):
        bg = wallpaper(kind, (cell, cell))
        view = composite_center(bg, icon, int(cell * 0.58))
        board.paste(view, ((i % 3) * cell, (i // 3) * cell))
    return board


def map_to_gray(a: np.ndarray) -> Image.Image:
    a = np.asarray(a, dtype=np.float32)
    lo = float(np.percentile(a, 1.0))
    hi = float(np.percentile(a, 99.0))
    if hi <= lo + 1e-8:
        norm = np.zeros_like(a)
    else:
        norm = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return Image.fromarray((norm * 255.0).astype(np.uint8), "L").convert("RGB")


def normal_map_image(normals: np.ndarray) -> Image.Image:
    rgb = np.clip((normals * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def render_map_sheet(maps: SurfaceMaps) -> Image.Image:
    panels = [
        map_to_gray(maps.front_height),
        normal_map_image(maps.normals),
        map_to_gray(maps.thickness),
        map_to_gray(maps.curvature),
        map_to_gray(maps.local_radius),
        map_to_gray(maps.glyph_profile),
    ]
    size = panels[0].size[0]
    board = Image.new("RGB", (size * 3, size * 2), (0, 0, 0))
    for i, p in enumerate(panels):
        board.paste(p, ((i % 3) * size, (i // 3) * size))
    return board


def difference_heatmap(old: Image.Image, new: Image.Image, bg: Image.Image) -> Image.Image:
    a = composite_center(bg, old, min(bg.size)//2).convert("RGB")
    b = composite_center(bg, new, min(bg.size)//2).convert("RGB")
    aa = np.asarray(a, dtype=np.float32)
    bb = np.asarray(b, dtype=np.float32)
    delta = np.linalg.norm(bb - aa, axis=2)
    hi = max(float(np.percentile(delta, 99.0)), 1e-6)
    x = np.clip(delta / hi, 0.0, 1.0)
    heat = np.zeros((*x.shape, 3), dtype=np.float32)
    heat[..., 0] = np.clip(2.0 * x, 0.0, 1.0)
    heat[..., 1] = np.clip(2.0 * (x - 0.25), 0.0, 1.0)
    heat[..., 2] = np.clip(2.0 * (x - 0.65), 0.0, 1.0)
    return Image.fromarray((heat * 255.0).astype(np.uint8), "RGB")


def diagnostics_dict(icon: Image.Image, maps: SurfaceMaps) -> dict:
    rgba = np.asarray(icon.convert("RGBA"), dtype=np.float32)
    alpha = rgba[..., 3] / 255.0
    cm = maps.container_mask > 0.5
    gm = maps.glyph_mask > 0.5
    edge = (maps.container_profile < 0.55) & cm
    core = (maps.container_profile > 0.92) & cm & (~gm)
    glyph_core = (maps.glyph_profile > 0.70) & gm
    return {
        "alpha_mean": float(alpha[cm].mean()) if np.any(cm) else 0.0,
        "container_core_alpha_mean": float(alpha[core].mean()) if np.any(core) else 0.0,
        "container_edge_alpha_mean": float(alpha[edge].mean()) if np.any(edge) else 0.0,
        "glyph_core_alpha_mean": float(alpha[glyph_core].mean()) if np.any(glyph_core) else 0.0,
        "max_slope": float(np.max(maps.slope)),
        "max_thickness": float(np.max(maps.thickness)),
        "glyph_radius_p95": float(np.percentile(maps.local_radius[gm], 95.0)) if np.any(gm) else 0.0,
    }


def save_diagnostics_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
