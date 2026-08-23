"""Assemble a one-tray print plate as a 3MF for PrusaSlicer.

Loads the exported STLs, orients each part print-side down, bakes the
mirrored copies (left/right ears), arranges everything on a 250 x 210 bed,
and writes a vanilla 3MF that PrusaSlicer opens as separate objects:

    python scripts/build_print_plate.py            # heat-set rear ears
    python scripts/build_print_plate.py --variant nuttrap
    python scripts/build_print_plate.py --variant selftap

Requires: trimesh, numpy (pip install trimesh numpy).
"""

import argparse
import zipfile
from pathlib import Path

import numpy as np
import trimesh

EXPORTS = Path("exports")
REAR_EAR_FILES = {
    "heatset": "rear_ear_v2.stl",
    "selftap": "rear_ear_v2_selftap.stl",
    "nuttrap": "rear_ear_v2_nuttrap.stl",
}

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0"
  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def mirrored(mesh):
    """Bake an X-mirrored copy with corrected face winding."""
    copy = mesh.copy()
    copy.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    if copy.volume < 0:  # older trimesh doesn't fix winding on reflections
        copy.invert()
    return copy


def place(mesh, x_center, y_center):
    """Drop the mesh so it sits on z=0 centered at (x_center, y_center)."""
    lo, hi = mesh.bounds
    mesh.apply_translation([x_center - (lo[0] + hi[0]) / 2,
                            y_center - (lo[1] + hi[1]) / 2,
                            -lo[2]])
    return mesh


def build_parts(variant):
    """Two plates. The duct set is what you reprint when the fan layout
    changes; the brackets are print-once and independent of it."""
    front = trimesh.load_mesh(EXPORTS / "front_ear.stl")
    rear = trimesh.load_mesh(EXPORTS / REAR_EAR_FILES[variant])
    plate = trimesh.load_mesh(EXPORTS / "rear_fan_bar.stl")
    plug = trimesh.load_mesh(EXPORTS / "fan_plug.stl")
    panel = trimesh.load_mesh(EXPORTS / "duct_panel.stl")

    duct = [
        ("duct_panel_top", place(panel.copy(), 112.0, 46.0)),
        ("duct_panel_bottom", place(panel.copy(), 112.0, 124.0)),
        ("rear_fan_plate", place(plate, 125.0, 188.0)),
    ]
    brackets = [
        ("rear_ear_R", place(rear.copy(), 35.0, 37.0)),
        ("rear_ear_L", place(mirrored(rear), 75.0, 37.0)),
        ("front_ear_R", place(front.copy(), 115.0, 37.0)),
        ("front_ear_L", place(mirrored(front), 155.0, 37.0)),
        ("fan_plug_1", place(plug.copy(), 40.0, 95.0)),
        ("fan_plug_2", place(plug.copy(), 95.0, 95.0)),
    ]
    return {"duct": duct, f"brackets_{variant}": brackets}


def write_3mf(parts, out_path):
    objects_xml = []
    items_xml = []
    for index, (name, mesh) in enumerate(parts, start=1):
        vertices = "".join(
            '<vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(v)
            for v in mesh.vertices)
        triangles = "".join(
            '<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f)
            for f in mesh.faces)
        objects_xml.append(
            '<object id="%d" name="%s" type="model"><mesh>'
            '<vertices>%s</vertices><triangles>%s</triangles>'
            '</mesh></object>' % (index, name, vertices, triangles))
        items_xml.append('<item objectid="%d"/>' % index)

    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<resources>%s</resources><build>%s</build></model>'
        % ("".join(objects_xml), "".join(items_xml)))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELS)
        archive.writestr("3D/3dmodel.model", model)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(REAR_EAR_FILES),
                        default="heatset", help="rear ear variant to plate")
    args = parser.parse_args()

    for plate_name, parts in build_parts(args.variant).items():
        boxes = []
        for name, mesh in parts:
            assert mesh.volume > 0, f"{name} has inverted winding"
            lo, hi = mesh.bounds
            boxes.append((name, lo, hi))
            print(f"  {name:20s} {hi[0]-lo[0]:6.1f} x {hi[1]-lo[1]:5.1f} x "
                  f"{hi[2]-lo[2]:5.1f} at x {lo[0]:.0f}..{hi[0]:.0f} "
                  f"y {lo[1]:.0f}..{hi[1]:.0f}")
        for i, (n1, lo1, hi1) in enumerate(boxes):
            for n2, lo2, hi2 in boxes[i + 1:]:
                if (lo1[0] < hi2[0] and lo2[0] < hi1[0]
                        and lo1[1] < hi2[1] and lo2[1] < hi1[1]):
                    raise SystemExit(f"{n1} overlaps {n2} on plate {plate_name}")
        far = max(hi[:2].max() for _, _, hi in boxes)
        near = min(lo[:2].min() for _, lo, _ in boxes)
        if near < 0 or far > 250:
            raise SystemExit(f"plate {plate_name} runs off the bed "
                             f"({near:.0f} to {far:.0f})")

        out_path = EXPORTS / f"print_plate_{plate_name}.3mf"
        write_3mf(parts, out_path)
        print(f"wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)\n")


if __name__ == "__main__":
    main()
