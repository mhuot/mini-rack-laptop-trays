"""Assemble the README turntable GIF and the Pages viewer GLB.

Inputs are produced by running build_rack_mockup.py inside Fusion and then
exporting (a) one STL per body into a parts directory and (b) a sequence of
turntable PNG frames. This script runs locally:

    python scripts/build_web_assets.py --parts-dir <dir> --frames-dir <dir>

Requires: pillow, trimesh, numpy (pip install pillow trimesh numpy).

Color notes:
- The palette below is authored in sRGB to match the Fusion renders; glTF's
  baseColorFactor is linear, so values are converted with the sRGB EOTF
  before export. Skipping that conversion washes every color out.
- Fusion de-duplicates repeated body names ("... fan (1)"), so parts are
  classified by substring, not exact suffix.
"""

import argparse
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

GIF_PATH = Path("docs/images/rack-turntable.gif")
GLB_PATH = Path("docs/models/rack-mockup.glb")

# sRGB, matching the appearances in build_rack_mockup.py
PALETTE = {
    "frame": (196, 199, 204, 255),
    "foot": (25, 25, 25, 255),
    "rod": (215, 215, 220, 255),
    "macbook": (45, 45, 48, 255),
    "surface": (28, 28, 30, 255),
    "fan": (94, 61, 48, 255),
    "print": (247, 84, 3, 255),  # Prusament Prusa Orange
    "panel": (40, 40, 46, 90),   # smoked acrylic, alpha-blended
}

METALLIC = {"frame": 0.6, "rod": 0.6}
ROUGHNESS = {"rod": 0.35}


def classify(stem: str) -> str:
    """Map an exported body filename to a palette group."""
    lower = stem.lower()
    if "panel" in lower:
        return "panel"
    if "foot" in lower:
        return "foot"
    if lower.split("_", 1)[-1].startswith("frame"):
        return "frame"
    if "ref" in lower and "macbook" in lower:
        return "macbook"
    if "ref" in lower and "surface" in lower:
        return "surface"
    if "fan_bar" in lower:
        return "print"
    if "fan" in lower:
        return "fan"
    if "rod" in lower:
        return "rod"
    return "print"


def srgb_to_linear(rgba_255):
    """Convert 0-255 sRGB to linear floats per the sRGB EOTF (alpha passes through)."""
    srgb = np.array(rgba_255[:3], dtype=np.float64) / 255.0
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return np.append(linear, rgba_255[3] / 255.0)


def build_gif(frames_dir: Path) -> None:
    frames = []
    for frame_path in sorted(frames_dir.glob("frame_*.png")):
        image = Image.open(frame_path).convert("RGB")
        frames.append(image.quantize(colors=128, dither=Image.Dither.FLOYDSTEINBERG))
    if not frames:
        raise SystemExit(f"no frames found in {frames_dir}")
    frames[0].save(GIF_PATH, save_all=True, append_images=frames[1:],
                   duration=90, loop=0, optimize=True)
    print(f"GIF: {GIF_PATH} ({GIF_PATH.stat().st_size / 1e6:.2f} MB, {len(frames)} frames)")


def build_glb(parts_dir: Path) -> None:
    # Z-up (Fusion world) -> Y-up (glTF)
    z_to_y_up = np.array([
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, -1, 0, 0],
        [0, 0, 0, 1],
    ], dtype=np.float64)

    scene = trimesh.Scene()
    counts = {}
    for stl_path in sorted(parts_dir.glob("*.stl")):
        mesh = trimesh.load_mesh(stl_path)
        mesh.apply_transform(z_to_y_up)
        group = classify(stl_path.stem)
        counts[group] = counts.get(group, 0) + 1
        mesh.visual = trimesh.visual.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=srgb_to_linear(PALETTE[group]),
                metallicFactor=METALLIC.get(group, 0.1),
                roughnessFactor=ROUGHNESS.get(group, 0.6),
                alphaMode="BLEND" if group == "panel" else "OPAQUE",
            ))
        scene.add_geometry(mesh, node_name=stl_path.stem)
    if not counts:
        raise SystemExit(f"no part STLs found in {parts_dir}")
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    scene.export(GLB_PATH)
    print(f"GLB: {GLB_PATH} ({GLB_PATH.stat().st_size / 1e6:.2f} MB); groups: {counts}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-dir", type=Path, required=True,
                        help="directory of per-body STL exports")
    parser.add_argument("--frames-dir", type=Path, required=True,
                        help="directory of turntable frame PNGs")
    args = parser.parse_args()
    build_gif(args.frames_dir)
    build_glb(args.parts_dir)


if __name__ == "__main__":
    main()
