from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from liquid_glass_v3.sources import github_octocat_mask

OUT = Path(__file__).resolve().parents[2] / "build" / "liquid-glass-v7"
SIZE = 1024


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mask = np.asarray(github_octocat_mask(SIZE).convert("L"), dtype=np.uint8)
    _, bw = cv2.threshold(mask, 8, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError("GitHub contour not found")

    contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.00135 * perimeter, True)[:, 0, :]

    # Normalize to centered Blender XY coordinates, preserving the raster source
    # as the geometry authority. Y is flipped because image coordinates grow down.
    pts = []
    for x, y in approx:
        px = (float(x) / (SIZE - 1.0) - 0.5) * 2.0
        py = -(float(y) / (SIZE - 1.0) - 0.5) * 2.0
        pts.append([px, py])

    payload = {
        "source": "official GitHub Octocat negative-space mask from Primer Octicons",
        "size": SIZE,
        "points": pts,
        "area_px": float(cv2.contourArea(contour)),
        "perimeter_px": float(perimeter),
    }
    (OUT / "github_contour.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"prepared {len(pts)} contour vertices")


if __name__ == "__main__":
    main()
