"""Fusion 360 script: build the 1U rear exhaust fan bar for the MacBook Pro tray.

Run inside Fusion via the MCP execute tool. Creates a new unsaved design
document containing a single body, "Rear Fan Bar".

v2 — mounts to the REAR EAR BACK PLATES, not the rack rails. The rear ears
extend 67 mm behind the rear rail (rear_depth 65 + thickness 2), so the bar
sits just behind the laptop's rear edge, screwed with M3 socket-head screws
into CNC Kitchen M3 x 3 short heat-set inserts in the Rear Ear v2 bosses
(built by build_rear_ear_v2.py).

Design intent (all values in mm):
- Back plates span x = 95.3..110.3 per side (rod line at +/-102.82); the bar
  is 222 wide so its tabs cover the plates while 4x Noctua NF-A4x20 5V fans
  (40x40x20, 32 mm screw pitch) nest between them, exhausting rearward.
- Bar front face lands on the ear bosses' 3 mm pads; total stack behind the
  rear rail = 69 (ear) + 3 (pad) + 4 (bar) + 20 (fan) = 96 mm.
"""

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion API lengths are in cm

# Overall bar
BAR_WIDTH = 222.0
BAR_Y_MIN = 0.4
BAR_Y_MAX = 44.05
PLATE_THICKNESS = 4.0

# Mounting into Rear Ear v2 insert bosses (M3 socket-head screws)
BOSS_X = 102.82          # rod line: rail hole span/2 - 15.44
BOSS_ROWS = (15.0, 29.45)  # symmetric about U mid-height 22.225, clear of rod bores
SCREW_CLEAR_DIA = 3.4
HEAD_CBORE_DIA = 6.5
HEAD_CBORE_DEPTH = 2.0

# Fans: Noctua NF-A4x20 5V
FAN_CENTERS_X = (-72.0, -24.0, 24.0, 72.0)
FAN_CENTER_Y = 22.225
FAN_OPENING_DIA = 39.0
FAN_SCREW_PITCH = 32.0
FAN_SCREW_DIA = 3.6


def run(_context: str):
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    extrudes = root.features.extrudeFeatures

    def point(x_mm, y_mm, z_mm=0.0):
        return adsk.core.Point3D.create(x_mm * MM, y_mm * MM, z_mm * MM)

    def all_profiles(sketch):
        collection = adsk.core.ObjectCollection.create()
        for i in range(sketch.profiles.count):
            collection.add(sketch.profiles.item(i))
        return collection

    # 1. Base plate
    plate_sketch = root.sketches.add(root.xYConstructionPlane)
    plate_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        point(-BAR_WIDTH / 2, BAR_Y_MIN), point(BAR_WIDTH / 2, BAR_Y_MAX))
    plate = extrudes.addSimple(
        plate_sketch.profiles.item(0),
        adsk.core.ValueInput.createByReal(PLATE_THICKNESS * MM),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    body = plate.bodies.item(0)
    body.name = "Rear Fan Bar"

    # 2. Fan openings + fan screw holes + M3 mounting holes (all through-cuts)
    cut_sketch = root.sketches.add(root.xYConstructionPlane)
    circles = cut_sketch.sketchCurves.sketchCircles
    for fan_x in FAN_CENTERS_X:
        circles.addByCenterRadius(point(fan_x, FAN_CENTER_Y), FAN_OPENING_DIA / 2 * MM)
        for dx in (-FAN_SCREW_PITCH / 2, FAN_SCREW_PITCH / 2):
            for dy in (-FAN_SCREW_PITCH / 2, FAN_SCREW_PITCH / 2):
                circles.addByCenterRadius(
                    point(fan_x + dx, FAN_CENTER_Y + dy), FAN_SCREW_DIA / 2 * MM)
    for hole_x in (-BOSS_X, BOSS_X):
        for hole_y in BOSS_ROWS:
            circles.addByCenterRadius(point(hole_x, hole_y), SCREW_CLEAR_DIA / 2 * MM)
    through_cut = extrudes.createInput(
        all_profiles(cut_sketch), adsk.fusion.FeatureOperations.CutFeatureOperation)
    through_cut.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(PLATE_THICKNESS * MM))
    extrudes.add(through_cut)

    # 3. Counterbores for the M3 screw heads, cut from the rear face
    planes = root.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        root.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(PLATE_THICKNESS * MM))
    rear_plane = planes.add(plane_input)
    cbore_sketch = root.sketches.add(rear_plane)
    for hole_x in (-BOSS_X, BOSS_X):
        for hole_y in BOSS_ROWS:
            cbore_sketch.sketchCurves.sketchCircles.addByCenterRadius(
                point(hole_x, hole_y), HEAD_CBORE_DIA / 2 * MM)
    cbore_cut = extrudes.createInput(
        all_profiles(cbore_sketch), adsk.fusion.FeatureOperations.CutFeatureOperation)
    cbore_cut.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(-HEAD_CBORE_DEPTH * MM))
    extrudes.add(cbore_cut)

    app.activeViewport.fit()
    print("Created document '%s' with body '%s' (%d faces)" % (
        doc.name, body.name, body.faces.count))
