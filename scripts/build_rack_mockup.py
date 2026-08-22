"""Fusion 360 script: full mockup of the 10-inch rack with both laptop trays.

Run inside Fusion via the MCP execute tool with the 'MacBook Pro Front Ear',
'MacBook Pro Rear Ear', and 'Brackets for Speaker Stand v2' documents open.
Creates a new unsaved direct-modeling document containing:

- Simplified GeeekPi 4U 10-inch frame (posts, top/bottom slabs; rail-to-rail
  depth 200 mm, hole span 236.525 mm)
- U3: MacBook Pro 14 tray — front/rear ears (mirrored pairs, rear with insert
  bosses), 4x 8 mm rods, ducted fan bar, 4 fan placeholders, and the copied
  'REF MacBook Pro 14' body
- U2: identical tray for the Surface Laptop 13.8 with a new
  'REF Surface Laptop 13.8' body (301 x 220 x 17.5)

Global frame (mm): x = 0 at rack centerline, y = 0 at bottom of U1,
z = 0 at the front rail mounting face, +z rearward. Rod line at +/-102.82;
rear rail face at z = 200; back plates at z = 267..269; fan bar at 272..276.
"""

import adsk.core
import adsk.fusion

MM = 0.1  # Fusion API lengths are in cm

RU = 44.45
RAIL_DEPTH = 200.0
ROD_X = 102.82
EAR_OFFSET_X = 110.32   # ear local x=0 -> global (rod line 102.82 = local -7.5)
ROD_ROWS = (6.22, 38.23)
ROD_DIA = 8.0
# The front ear straddles the front rail: its thin 2 mm face plate sits ON
# the rail's front face (screw heads recessed in it), while the rod blocks
# (6 mm deeper) pass through the rack opening inboard of the rail. Only
# that 2 mm plate is proud of the rack; the laptop overhang is cantilevered.
EAR_PLATE = 2.0
FRONT_EAR_Z = -EAR_PLATE          # ear body: z -2..6
POST_X_INNER = 110.5              # rail plates sit outboard of the ear blocks
# Rods (243 mm, per the as-built trays) run from flush with the front
# ear's face (z=-2) to ~41 mm inside the rear ears' bores (z=241).
ROD_Z0, ROD_Z1 = -EAR_PLATE, -EAR_PLATE + 243.0

BAR_Z0, BAR_Z1 = 272.0, 276.0
FAN_CENTERS_X = (-72.0, -24.0, 24.0, 72.0)
DUCT_X = 94.8

SLOTS = [
    {"u_bottom": RU, "laptop": "surface", "label": "U2 Surface Laptop 13.8"},
    {"u_bottom": 2 * RU, "laptop": "macbook", "label": "U3 MacBook Pro 14"},
]

SURFACE_L, SURFACE_W, SURFACE_T = 301.0, 220.0, 17.5


def run(_context: str):
    app = adsk.core.Application.get()
    temp_mgr = adsk.fusion.TemporaryBRepManager.get()

    def find_doc(prefix):
        for doc in app.documents:
            if doc.name.startswith(prefix):
                return doc
        raise RuntimeError("Document '%s' is not open" % prefix)

    def grab_bodies(doc_prefix, body_names):
        doc = find_doc(doc_prefix)
        doc.activate()
        design = adsk.fusion.Design.cast(app.activeProduct)
        out = []
        for name in body_names:
            body = design.rootComponent.bRepBodies.itemByName(name)
            if body is None:
                raise RuntimeError("Body '%s' missing in '%s'" % (name, doc_prefix))
            out.append(temp_mgr.copy(body))
        return out

    front_ear_src = grab_bodies("MacBook Pro Front Ear", ["Front Ear"])[0]
    rear_parts = grab_bodies("MacBook Pro Rear Ear", ["Rear Ear", "Back Plate"])
    rear_ear_src = rear_parts[0]
    temp_mgr.booleanOperation(rear_ear_src, rear_parts[1],
                              adsk.fusion.BooleanTypes.UnionBooleanType)
    macbook_src = grab_bodies("Brackets for Speaker Stand v2",
                              ["REF MacBook Pro 14"])[0]

    def matrix(rows):
        m = adsk.core.Matrix3D.create()
        for r in range(3):
            for c in range(3):
                m.setCell(r, c, rows[r][c])
            m.setCell(r, 3, rows[r][3] * MM)
        return m

    def placed(source, m):
        copy = temp_mgr.copy(source)
        temp_mgr.transform(copy, m)
        return copy

    def box(x0, x1, y0, y1, z0, z1):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        center = adsk.core.Point3D.create(
            (x0 + x1) / 2 * MM, (y0 + y1) / 2 * MM, (z0 + z1) / 2 * MM)
        obb = adsk.core.OrientedBoundingBox3D.create(
            center,
            adsk.core.Vector3D.create(1, 0, 0),
            adsk.core.Vector3D.create(0, 1, 0),
            (x1 - x0) * MM, (y1 - y0) * MM, (z1 - z0) * MM)
        return temp_mgr.createBox(obb)

    def cyl_z(x, y, z0, z1, dia):
        return temp_mgr.createCylinderOrCone(
            adsk.core.Point3D.create(x * MM, y * MM, z0 * MM), dia / 2 * MM,
            adsk.core.Point3D.create(x * MM, y * MM, z1 * MM), dia / 2 * MM)

    bodies = []  # (name, temp brep body)

    # --- Rack frame (GeeekPi-style: corner extrusions, open frames, feet) ---
    FRAME_Y0, FRAME_Y1 = -12.0, 4 * RU + 12.0
    HOLE_ROWS_PER_U = (6.35, 22.225, 38.1)

    # Corner posts are full-depth extrusions like the real rack. The front
    # ears need no clearance behind the rail here: their plates sit in front
    # of the rail face and their rod blocks pass through the opening inboard
    # of the posts (|x| < POST_X_INNER).
    for side in (-1, 1):
        for z_range, tag in (((0.0, 20.0), "front"), ((180.0, 200.0), "rear")):
            post = box(side * POST_X_INNER, side * 127, FRAME_Y0, FRAME_Y1,
                       z_range[0], z_range[1])
            # Mounting hole strip drilled through the post face
            for u in range(4):
                for row in HOLE_ROWS_PER_U:
                    hole = cyl_z(side * (236.525 / 2), u * RU + row,
                                 z_range[0] - 1, z_range[1] + 1, 5.0)
                    temp_mgr.booleanOperation(
                        post, hole,
                        adsk.fusion.BooleanTypes.DifferenceBooleanType)
            bodies.append(("Frame %s post %+d" % (tag, side), post))

    for y_range, tag in (((FRAME_Y0, 0.0), "bottom"), ((4 * RU, FRAME_Y1), "top")):
        bodies.append(("Frame %s front rail" % tag,
                       box(-POST_X_INNER, POST_X_INNER, y_range[0], y_range[1], 0, 20)))
        bodies.append(("Frame %s rear rail" % tag,
                       box(-POST_X_INNER, POST_X_INNER, y_range[0], y_range[1], 180, 200)))
        for side in (-1, 1):
            bodies.append(("Frame %s side rail %+d" % (tag, side),
                           box(side * POST_X_INNER, side * 127, y_range[0], y_range[1],
                               20, 180)))

    # Side panels + top cover (the RackMate T0's sides and top are closed
    # with smoked acrylic)
    for side in (-1, 1):
        bodies.append(("Side panel %+d" % side,
                       box(side * 125, side * 127, 0, 4 * RU, 20, 180)))
    bodies.append(("Top panel",
                   box(-POST_X_INNER, POST_X_INNER, 4 * RU, 4 * RU + 3, 20, 180)))

    for side_x in (-1, 1):
        for foot_z in (10.0, 190.0):
            foot = temp_mgr.createCylinderOrCone(
                adsk.core.Point3D.create(side_x * 117 * MM, (FRAME_Y0 - 8) * MM,
                                         foot_z * MM),
                12.0 * MM,
                adsk.core.Point3D.create(side_x * 117 * MM, FRAME_Y0 * MM,
                                         foot_z * MM),
                12.0 * MM)
            bodies.append(("Frame foot", foot))

    # --- Per-slot tray assemblies ---
    for slot in SLOTS:
        y0 = slot["u_bottom"]
        label = slot["label"]

        # Front ears straddle the rail: local z 0..8 -> global -2..6
        for side, tx in (("R", EAR_OFFSET_X), ("L", -EAR_OFFSET_X)):
            sign = 1 if side == "R" else -1
            m = matrix([[sign, 0, 0, sign * EAR_OFFSET_X],
                        [0, 1, 0, y0],
                        [0, 0, 1, FRONT_EAR_Z]])
            bodies.append(("%s front ear %s" % (label, side),
                           placed(front_ear_src, m)))

        # Rear ears v2: local z 0..69 -> global 200..269, plus bosses
        for side in ("R", "L"):
            sign = 1 if side == "R" else -1
            m = matrix([[sign, 0, 0, sign * EAR_OFFSET_X],
                        [0, 1, 0, y0],
                        [0, 0, 1, RAIL_DEPTH]])
            ear = placed(rear_ear_src, m)
            # Full-height boss rib seals the plate-to-bar standoff gap
            rib = box(sign * ROD_X - 4.5, sign * ROD_X + 4.5,
                      y0 + 0.4, y0 + 44.05, 269.0, 272.0)
            temp_mgr.booleanOperation(
                ear, rib, adsk.fusion.BooleanTypes.UnionBooleanType)
            for row in (15.0, 29.45):
                pocket = cyl_z(sign * ROD_X, y0 + row, 268.8, 272.1, 4.0)
                temp_mgr.booleanOperation(
                    ear, pocket, adsk.fusion.BooleanTypes.DifferenceBooleanType)
            bodies.append(("%s rear ear v2 %s" % (label, side), ear))

        # Rods
        for side in (-1, 1):
            for row in ROD_ROWS:
                bodies.append(("%s rod" % label,
                               cyl_z(side * ROD_X, y0 + row, ROD_Z0, ROD_Z1,
                                     ROD_DIA)))

        # Ducted fan bar (visual: fan openings only, no small holes)
        bar = box(-111, 111, y0 + 0.4, y0 + 44.05, BAR_Z0, BAR_Z1)
        for fan_x in FAN_CENTERS_X:
            opening = cyl_z(fan_x, y0 + 22.225, BAR_Z0 - 1, BAR_Z1 + 1, 39.0)
            temp_mgr.booleanOperation(
                bar, opening, adsk.fusion.BooleanTypes.DifferenceBooleanType)
        duct_top = box(-DUCT_X, DUCT_X, y0 + 42.25, y0 + 44.05, 202.0, BAR_Z0)
        duct_bottom = box(-DUCT_X, DUCT_X, y0 + 0.4, y0 + 2.2, 202.0, BAR_Z0)
        temp_mgr.booleanOperation(bar, duct_top,
                                  adsk.fusion.BooleanTypes.UnionBooleanType)
        temp_mgr.booleanOperation(bar, duct_bottom,
                                  adsk.fusion.BooleanTypes.UnionBooleanType)
        bodies.append(("%s fan bar" % label, bar))

        # Fan placeholders: 40x40x20 frame with bore and hub
        for fan_x in FAN_CENTERS_X:
            fan = box(fan_x - 20, fan_x + 20, y0 + 2.225, y0 + 42.225,
                      276.0, 296.0)
            bore = cyl_z(fan_x, y0 + 22.225, 275.0, 297.0, 35.0)
            temp_mgr.booleanOperation(
                fan, bore, adsk.fusion.BooleanTypes.DifferenceBooleanType)
            hub = cyl_z(fan_x, y0 + 22.225, 278.0, 294.0, 14.0)
            temp_mgr.booleanOperation(
                fan, hub, adsk.fusion.BooleanTypes.UnionBooleanType)
            bodies.append(("%s fan" % label, fan))

        # Laptop
        if slot["laptop"] == "macbook":
            # Source lies flat: x=length(312.6), y=width(221.2), z=thick.
            # Map (lx,ly,lz) -> (ly, lz, lx): width across, thickness up,
            # length rearward; rear edge lands on the back plates at z=267.
            m = matrix([[0, 1, 0, -1.4],
                        [0, 0, 1, y0 + 5.42],
                        [1, 0, 0, 110.7]])
            bodies.append(("REF MacBook Pro 14 (U3)", placed(macbook_src, m)))
        else:
            bodies.append(("REF Surface Laptop 13.8 (U2)",
                           box(-SURFACE_W / 2, SURFACE_W / 2,
                               y0 + 10.22, y0 + 10.22 + SURFACE_T,
                               267.0 - SURFACE_L, 267.0)))

    # --- Emit into a new direct-modeling document ---
    # Design coordinates use y-up / z-rearward; Fusion's world is z-up with
    # the front view looking along +y, so rotate everything into world space:
    # (x, y, z) -> (-x, z, y), a proper rotation (det = +1).
    world = adsk.core.Matrix3D.create()
    world.setCell(0, 0, -1.0)
    world.setCell(1, 1, 0.0)
    world.setCell(2, 2, 0.0)
    world.setCell(1, 2, 1.0)
    world.setCell(2, 1, 1.0)

    new_doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    root = design.rootComponent

    # --- Appearances ---
    library = app.materialLibraries.itemByName("Fusion Appearance Library")

    def get_appearance(lib_name, local_name, rgb=None):
        existing = design.appearances.itemByName(local_name)
        if existing:
            return existing
        source = library.appearances.itemByName(lib_name)
        copied = design.appearances.addByCopy(source, local_name)
        if rgb is not None:
            # Appearances can carry several ColorProperties (e.g. anodized
            # metals tint via the second one) — set them all.
            for i in range(copied.appearanceProperties.count):
                prop = copied.appearanceProperties.item(i)
                if prop.name == "Color" and prop.objectType.endswith("ColorProperty"):
                    prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
        return copied

    aluminum = get_appearance("Aluminum - Anodized Glossy (Grey)", "Rack Aluminum",
                              rgb=(196, 199, 204))
    # Prusament Prusa Orange (#F75403)
    orange_print = get_appearance("Plastic - Matte (Black)", "PETG Orange",
                                  rgb=(247, 84, 3))
    steel = get_appearance("Stainless Steel - Satin", "Rod Steel")
    macbook_look = get_appearance("Paint - Enamel Glossy (Dark Grey)",
                                  "MacBook Space Black", rgb=(45, 45, 48))
    surface_look = get_appearance("Paint - Enamel Glossy (Black)",
                                  "Surface Black", rgb=(25, 25, 27))
    noctua = get_appearance("Plastic - Matte (Black)", "Noctua Brown",
                            rgb=(94, 61, 48))
    rubber = get_appearance("Plastic - Matte (Black)", "Rubber Foot",
                            rgb=(20, 20, 20))
    acrylic = get_appearance("Plastic - Translucent Matte (Gray)",
                             "Smoked Acrylic", rgb=(40, 40, 46))

    def pick_appearance(name):
        if "panel" in name:
            return acrylic
        if "foot" in name:
            return rubber
        if name.startswith("Frame"):
            return aluminum
        if "MacBook" in name and "REF" in name:
            return macbook_look
        if "Surface" in name and "REF" in name:
            return surface_look
        if name.endswith("rod"):
            return steel
        if name.endswith("fan"):
            return noctua
        return orange_print  # printed parts: ears, fan bars

    for name, body in bodies:
        temp_mgr.transform(body, world)
        added = root.bRepBodies.add(body)
        added.name = name
        added.appearance = pick_appearance(name)
        if "panel" in name.lower():
            added.opacity = 0.3  # smoked acrylic reads see-through in renders

    app.activeViewport.fit()
    print("Mockup created: %d bodies in document '%s'" % (
        root.bRepBodies.count, new_doc.name))
