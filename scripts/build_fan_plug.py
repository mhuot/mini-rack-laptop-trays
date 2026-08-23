"""Fusion 360 script: blanking plug for unused fan bar openings.

Run inside Fusion via the MCP execute tool. Creates a new unsaved
direct-modeling document with one printable body.

For running two fans instead of four, the empty openings must be blocked
or the running fans pull backflow through them. The plug press-fits into
a bar opening from the rear (fan side). The flange seats on the bar's
rear face, and duct suction pushes the plug tighter rather than out.
Print flange-down, no supports. To remove, drive an M3 screw a couple
turns into the center pilot and pull.
"""

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion API lengths are in cm

FLANGE_DIA = 43.0
FLANGE_THICK = 1.6
BODY_DIA = 38.7          # press fit in the bar's 39.0 opening
BODY_DEPTH = 4.0         # fills the plate thickness, flush with the duct side
PULLER_PILOT_DIA = 2.5   # M3 screw threads in as a puller


def run(_context: str):
    app = adsk.core.Application.get()
    temp_mgr = adsk.fusion.TemporaryBRepManager.get()

    def cyl(z0_mm, z1_mm, dia_mm):
        return temp_mgr.createCylinderOrCone(
            adsk.core.Point3D.create(0, 0, z0_mm * MM), dia_mm / 2 * MM,
            adsk.core.Point3D.create(0, 0, z1_mm * MM), dia_mm / 2 * MM)

    plug = cyl(0.0, FLANGE_THICK, FLANGE_DIA)
    body = cyl(FLANGE_THICK, FLANGE_THICK + BODY_DEPTH, BODY_DIA)
    temp_mgr.booleanOperation(plug, body,
                              adsk.fusion.BooleanTypes.UnionBooleanType)
    pilot = cyl(-0.1, FLANGE_THICK + BODY_DEPTH + 0.1, PULLER_PILOT_DIA)
    temp_mgr.booleanOperation(plug, pilot,
                              adsk.fusion.BooleanTypes.DifferenceBooleanType)

    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    added = design.rootComponent.bRepBodies.add(plug)
    added.name = "Fan Plug"

    exp = design.exportManager
    stl = exp.createSTLExportOptions(
        added, "/Users/mhuot/mini-rack/exports/fan_plug.stl")
    stl.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    exp.execute(stl)
    step = exp.createSTEPExportOptions("/Users/mhuot/mini-rack/cad/fan_plug.step")
    exp.execute(step)
    f3d = exp.createFusionArchiveExportOptions(
        "/Users/mhuot/mini-rack/cad/fan_plug.f3d")
    exp.execute(f3d)

    app.activeViewport.fit()
    print("Fan plug built and exported (STL + STEP + F3D)")
