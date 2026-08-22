"""Fusion 360 script: build Rear Ear v2 = existing Rear Ear + fan bar bosses.

Run inside Fusion via the MCP execute tool with the 'MacBook Pro Rear Ear'
document open. Copies the proven 'Rear Ear' and 'Back Plate' bodies unchanged,
fuses them, and adds two bosses on the back plate's rear face sized for CNC
Kitchen M3 x 3 SHORT heat-set inserts (hole diameter 4.0, depth 3.2). The
result lands in a new unsaved direct-modeling document as one printable body.

Boss positions (ear coordinates, mm): x = -7.5 (rod line), y = 14.0 and
30.45 — symmetric about the 1U mid-height (22.225) and clear of the 8 mm rod
sockets at y 6.22 / 38.23. Pads are diameter 9 x 3 tall on the plate rear
face (z = 69..72); insert pockets are blind, leaving 1.8 mm of plate in
front so nothing pokes the laptop's rear edge.
"""

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion API lengths are in cm

SOURCE_DOC = "MacBook Pro Rear Ear"
SOURCE_BODIES = ("Rear Ear", "Back Plate")

BOSS_X = -7.5
BOSS_ROWS = (15.0, 29.45)
PAD_DIA = 9.0
PAD_Z_START = 69.0
PAD_Z_END = 72.0
INSERT_HOLE_DIA = 4.0
INSERT_HOLE_DEPTH = 3.2


def run(_context: str):
    app = adsk.core.Application.get()

    source_doc = None
    for doc in app.documents:
        if doc.name.startswith(SOURCE_DOC):
            source_doc = doc
            break
    if source_doc is None:
        raise RuntimeError("Document '%s' is not open" % SOURCE_DOC)
    source_doc.activate()
    source_design = adsk.fusion.Design.cast(app.activeProduct)
    source_root = source_design.rootComponent

    temp_mgr = adsk.fusion.TemporaryBRepManager.get()

    combined = None
    for body_name in SOURCE_BODIES:
        source_body = source_root.bRepBodies.itemByName(body_name)
        if source_body is None:
            raise RuntimeError("Body '%s' not found" % body_name)
        copy = temp_mgr.copy(source_body)
        if combined is None:
            combined = copy
        else:
            temp_mgr.booleanOperation(
                combined, copy, adsk.fusion.BooleanTypes.UnionBooleanType)

    def cylinder(x_mm, y_mm, z0_mm, z1_mm, dia_mm):
        return temp_mgr.createCylinderOrCone(
            adsk.core.Point3D.create(x_mm * MM, y_mm * MM, z0_mm * MM),
            dia_mm / 2 * MM,
            adsk.core.Point3D.create(x_mm * MM, y_mm * MM, z1_mm * MM),
            dia_mm / 2 * MM)

    for boss_y in BOSS_ROWS:
        pad = cylinder(BOSS_X, boss_y, PAD_Z_START, PAD_Z_END, PAD_DIA)
        temp_mgr.booleanOperation(
            combined, pad, adsk.fusion.BooleanTypes.UnionBooleanType)
    for boss_y in BOSS_ROWS:
        pocket = cylinder(BOSS_X, boss_y, PAD_Z_END - INSERT_HOLE_DEPTH,
                          PAD_Z_END + 0.1, INSERT_HOLE_DIA)
        temp_mgr.booleanOperation(
            combined, pocket, adsk.fusion.BooleanTypes.DifferenceBooleanType)

    new_doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    new_design = adsk.fusion.Design.cast(app.activeProduct)
    new_design.designType = adsk.fusion.DesignTypes.DirectDesignType
    new_body = new_design.rootComponent.bRepBodies.add(combined)
    new_body.name = "Rear Ear v2"

    app.activeViewport.fit()
    bb = new_body.boundingBox
    print("Created document '%s' with body '%s': %.2f x %.2f x %.2f mm, %d faces" % (
        new_doc.name, new_body.name,
        (bb.maxPoint.x - bb.minPoint.x) * 10,
        (bb.maxPoint.y - bb.minPoint.y) * 10,
        (bb.maxPoint.z - bb.minPoint.z) * 10,
        new_body.faces.count))
