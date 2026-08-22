"""Fusion 360 script: build the 1U rear exhaust fan bar for the MacBook Pro tray.

Run inside Fusion via the MCP execute tool. Creates a new unsaved design
document containing a single body, "Rear Fan Bar".

Design intent (all values in mm):
- Spans the rear rails of a 10-inch mini rack (hole span 236.525 mm c-c),
  mounted on the BACK face of the rear rails using the same 1U hole rows as
  the existing MacBook Pro rear ears (y = 6.35 and 38.1 within the U).
- Holds 4x Noctua NF-A4x20 5V fans (40x40x20, 32 mm screw pitch) exhausting
  rearward, centered on the 1U so they sweep the air channels above and
  below the racked MacBook.
- Plate thickness 4 mm; total protrusion behind the rear rail = 24 mm.
"""

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion API lengths are in cm

# Overall bar
BAR_WIDTH = 252.0
BAR_Y_MIN = 0.4
BAR_Y_MAX = 44.05
PLATE_THICKNESS = 4.0

# Rack mounting. Rows 6.35/38.1 match the existing ear hole rows (usable only
# if the rail is through-hole and a longer sandwich screw is used); row 22.225
# is the free middle hole of the 1U and is the primary mount for this bar.
RAIL_HOLE_SPAN = 236.525
RAIL_HOLE_ROWS = (6.35, 22.225, 38.1)
RAIL_HOLE_DIA = 4.8
RAIL_CBORE_DIA = 10.0
RAIL_CBORE_DEPTH = 2.5

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

    # 2. Fan openings + fan screw holes + rail holes (all through-cuts)
    cut_sketch = root.sketches.add(root.xYConstructionPlane)
    circles = cut_sketch.sketchCurves.sketchCircles
    for fan_x in FAN_CENTERS_X:
        circles.addByCenterRadius(point(fan_x, FAN_CENTER_Y), FAN_OPENING_DIA / 2 * MM)
        for dx in (-FAN_SCREW_PITCH / 2, FAN_SCREW_PITCH / 2):
            for dy in (-FAN_SCREW_PITCH / 2, FAN_SCREW_PITCH / 2):
                circles.addByCenterRadius(
                    point(fan_x + dx, FAN_CENTER_Y + dy), FAN_SCREW_DIA / 2 * MM)
    for hole_x in (-RAIL_HOLE_SPAN / 2, RAIL_HOLE_SPAN / 2):
        for hole_y in RAIL_HOLE_ROWS:
            circles.addByCenterRadius(point(hole_x, hole_y), RAIL_HOLE_DIA / 2 * MM)
    through_cut = extrudes.createInput(
        all_profiles(cut_sketch), adsk.fusion.FeatureOperations.CutFeatureOperation)
    through_cut.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(PLATE_THICKNESS * MM))
    extrudes.add(through_cut)

    # 3. Counterbores for rail screws, cut from the rear face
    planes = root.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        root.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(PLATE_THICKNESS * MM))
    rear_plane = planes.add(plane_input)
    cbore_sketch = root.sketches.add(rear_plane)
    for hole_x in (-RAIL_HOLE_SPAN / 2, RAIL_HOLE_SPAN / 2):
        for hole_y in RAIL_HOLE_ROWS:
            cbore_sketch.sketchCurves.sketchCircles.addByCenterRadius(
                point(hole_x, hole_y), RAIL_CBORE_DIA / 2 * MM)
    cbore_cut = extrudes.createInput(
        all_profiles(cbore_sketch), adsk.fusion.FeatureOperations.CutFeatureOperation)
    cbore_cut.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(-RAIL_CBORE_DEPTH * MM))
    extrudes.add(cbore_cut)

    app.activeViewport.fit()
    print("Created document '%s' with body '%s' (%d faces)" % (
        doc.name, body.name, body.faces.count))
