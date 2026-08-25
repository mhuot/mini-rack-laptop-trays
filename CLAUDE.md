# Working in this repo

## Terminology

Every part has exactly one name. They drifted once — the same part went by
one name in the README and another in the print plate filenames, and a
second part disagreed with itself between the prose and the CAD — and were
settled in a single pass. Use the left column and nothing else, in prose,
comments, identifiers, and filenames alike.

<!-- terminology-check: ignore -->

| Use | Not | Why this one |
|---|---|---|
| **ear**, front ear, rear ear | bracket | The printed parts that bolt to the rack rails. |
| **fan plate** | fan bar, the bar | The Fusion body is named `Rear Fan Plate`, and it is a flat 4 mm slab. |
| **rack rail** | a bare "rail" for the cabinet | The cabinet's mounting rails. Always qualified, because... |
| **duct rail** | capture rail, ear rail, a bare "rail" | ...the ears also carry rails, the ones the duct panels slide into. Matches the Fusion feature named `Duct rail`. |
| **fan opening** | fan bore | The 39 mm hole in the fan plate. Keeps *bore* meaning one thing: the rod, screw, and insert holes. |
| **duct panel** | — | "sheet" is fine as a material description ("a 37 g sheet"), not as the part's name. |

Two places keep a retired word on purpose:

- `docs/index.html` — "A front ear and a rear ear, which is what I call the
  brackets" is a gloss. It hands the reader the vocabulary rather than
  drifting from it. Don't mechanically substitute it away.
- `scripts/build_rack_mockup.py` — `Brackets for Speaker Stand v2` is the
  exact name of a legacy Fusion document that `grab_bodies()` opens.
  Renaming the file would not rename the document inside Fusion.

<!-- terminology-check: resume -->

Run `python scripts/check_terminology.py` before you commit. It greps for
the retired names, exits nonzero on a hit, and knows about both exceptions
above. When you retire a name, add a rule to it; when you need a genuine
exemption, add it to `ALLOWED` **with a note saying why** — an unexplained
exemption is how the drift started.

## Which scripts run where

This matters before you offer to regenerate anything:

- **Fusion 360 only** — `build_rear_ear_v2.py`, `build_rear_fan_plate.py`,
  `build_duct_panel.py`, `build_fan_plug.py`, `build_rack_mockup.py`,
  `add_duct_rails.py`, `export_front_ear.py`, `fix_insert_pockets.py`,
  `fix_laptop_relief.py`. They `import adsk` and need the Fusion documents
  open. You cannot run these; say so rather than guessing at their output.
- **Locally** — `build_print_plate.py` (trimesh, numpy),
  `check_rear_assembly.py` (+ scipy), `build_depth_diagram.py`
  (+ matplotlib), `whiten_renders.py` (numpy, scipy, Pillow),
  `build_web_assets.py` (trimesh, numpy, Pillow). Use a throwaway venv;
  nothing is installed system-wide.
- **Standard library only** — `check_terminology.py`.

Fusion API note: all Fusion API lengths are centimeters. The scripts define
`MM = 0.1` and work in millimeters throughout.

## Generated assets

`docs/images/laptop-depth.png` renders text into the image, so a
terminology change means regenerating it (`build_depth_diagram.py`, runs
locally). The other renders are text-free Fusion output.

Regenerating a 3MF or STL on a different trimesh version rewrites float
formatting across the whole file, which buries a real change in noise. If
the mesh itself didn't change, restore it with `git checkout -- exports/`
rather than committing the churn.
