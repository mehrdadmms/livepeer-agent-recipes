# ---- v3: drowned classical forum (colonnades, arches, statues, temple with pediment and steps, flagstone plaza)
SB = SEABED
TEMPLE_Y = 75.6           # front edge of the stylobate (top of the steps)
FLOOR_T = SB + 1.6        # temple floor height
COL_H = 9.6
CELLA_Y0 = 84.0           # cella front wall (the window plane, YF in build_ending)
LANTERNS = []


def _M(x, y, z, yaw=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")


def add_column(bm, cx, cy, z0, h, r, broken=0.0, rng=rnd, cap=True):
    """fluted tapered column with base and capital; broken>0 leaves a jagged stump"""
    nseg = 24
    base_h = 0.35
    vbox(bm, cx, cy, z0 + base_h / 2, r * 2.5, r * 2.5, base_h)
    cap_h = 0.65 if cap and broken == 0 else 0.0
    top = z0 + h - cap_h
    zs = np.linspace(z0 + base_h, top, 7)
    rings = []
    for k, z in enumerate(zs):
        t = k / 6.0
        rr = r * (1.0 - 0.14 * t + 0.03 * math.sin(t * math.pi))
        ring = []
        for i in range(nseg):
            a = 2 * math.pi * i / nseg
            fl = 1.0 - 0.055 * abs(math.cos(6 * a))
            zz = z
            if broken > 0 and k == 6:
                zz = z - broken * rng.uniform(0.0, 1.0) * (0.5 + 0.5 * math.cos(a - 1.0))
            ring.append(bm.verts.new((cx + rr * fl * math.cos(a), cy + rr * fl * math.sin(a), zz)))
        rings.append(ring)
    for k in range(6):
        for i in range(nseg):
            j = (i + 1) % nseg
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if broken > 0:
        bm.faces.new(rings[6][::-1])
    if cap_h > 0:
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r * 0.88, radius2=r * 1.3, depth=0.32,
                              matrix=Matrix.Translation((cx, cy, top + 0.16)))
        vbox(bm, cx, cy, top + 0.32 + 0.14, r * 2.9, r * 2.9, 0.28)


def add_arch(bm, cx, cy, z0, span, pier_w, h_spring, thick=2.2, gaps=()):
    ri = span / 2
    ro = ri + 1.3
    for s in (-1, 1):
        px = cx + s * (ri + pier_w / 2)
        vbox(bm, px, cy, z0 + h_spring / 2, pier_w, thick, h_spring)
        vbox(bm, px, cy, z0 + 0.2, pier_w + 0.4, thick + 0.4, 0.4)
    zc = z0 + h_spring
    n = 20
    for i in range(n):
        if i in gaps:
            continue
        th = math.pi * (i + 0.5) / n
        rm = (ri + ro) / 2
        arc = math.pi * rm / n * 1.04
        m = Matrix.Translation((cx + rm * math.cos(th), cy, zc + rm * math.sin(th))) @ Matrix.Rotation(-th, 4, "Y") @ \
            Matrix.Diagonal(((ro - ri) * (1.12 if i == n // 2 else 1.0), thick, arc, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    vbox(bm, cx, cy, zc + ro + 0.4, span + 2 * pier_w + 0.6, thick + 0.3, 0.8)


def add_statue(bm, x, y, z0, yaw, sc=1.0, arm_up=True):
    vbox(bm, x, y, z0 + 0.15, 1.9, 1.9, 0.3)
    vbox(bm, x, y, z0 + 1.2, 1.4, 1.4, 1.9)
    vbox(bm, x, y, z0 + 2.25, 1.75, 1.75, 0.22)
    zb = z0 + 2.36
    M = _M(x, y, zb, yaw)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.46 * sc, radius2=0.26 * sc, depth=1.55 * sc,
                          matrix=M @ Matrix.Translation((0, 0, 0.78 * sc)))
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=1.0,
                              matrix=M @ Matrix.Translation((0, 0, 1.95 * sc)) @ Matrix.Diagonal((0.30 * sc, 0.19 * sc, 0.42 * sc, 1)))
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0,
                              matrix=M @ Matrix.Translation((0, 0, 2.52 * sc)) @ Matrix.Diagonal((0.15 * sc, 0.16 * sc, 0.19 * sc, 1)))
    # arms: one raised holding a wreath, one down
    def arm(p0, p1):
        a, b = M @ Vector(p0), M @ Vector(p1)
        vbeam(bm, a, b, 0.07 * sc, 8)
    arm((0.30 * sc, 0, 2.2 * sc), (0.55 * sc, 0.12 * sc, 3.05 * sc) if arm_up else (0.5 * sc, 0.2 * sc, 1.5 * sc))
    arm((-0.30 * sc, 0, 2.2 * sc), (-0.42 * sc, 0.25 * sc, 1.55 * sc))
    if arm_up:
        bmesh.ops.create_torus(bm, major_segments=14, minor_segments=6, major_radius=0.17 * sc, minor_radius=0.03 * sc,
                               matrix=M @ Matrix.Translation((0.58 * sc, 0.12 * sc, 3.15 * sc)) @ Matrix.Rotation(math.pi / 2, 4, "X")) \
            if hasattr(bmesh.ops, "create_torus") else None


def add_lantern(bmg, bmb, x, y, z):
    vsphere(bmg, (x, y, z), 0.2, (1, 1, 1.25), seg=10, rings=7)
    vbeam(bmb, (x, y, z + 0.22), (x, y, z + 0.5), 0.03, 6)
    vbeam(bmb, (x, y, z - 0.26), (x, y, z - 0.2), 0.12, 8)
    vbeam(bmb, (x, y, z + 0.22), (x, y, z + 0.27), 0.14, 8)
    LANTERNS.append((x, y, z))


def build_forum():
    rg = random.Random(21)
    stone = ground_material("ForumStone", "concrete_wall_006", 0.32, (0.66, 0.76, 0.80, 1), 0.40, 0.55)
    stone_dk = ground_material("ForumStoneDark", "concrete_wall_006", 0.32, (0.44, 0.55, 0.60, 1), 0.55, 0.6)
    slab_m = ground_material("ForumSlab", "concrete_wall_006", 0.24, (0.50, 0.60, 0.62, 1), 0.5, 0.7)
    sand = ground_material("Seabed", "sandy_gravel_02", 0.12, (0.50, 0.62, 0.60, 1), 0.3, 0.75)
    ground_material("SunkenFacade", "concrete_wall_006", 0.3, (0.60, 0.70, 0.74, 1), 0.45, 0.6)
    ground_material("DressConcrete", "concrete_wall_006", 0.3, (0.60, 0.70, 0.74, 1), 0.45, 0.6)
    bronze = metal_mat("DressIron", (0.50, 0.32, 0.12), 0.45, 0.9)
    lant_g = emis_mat("LanternGlow", (1.0, 0.62, 0.22), 14.0)
    door_g = emis_mat("DoorGlow", (1.0, 0.45, 0.10), 2.2)
    # ---- seabed + flagstone plaza
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=260.0)
    sb = mesh_obj("Seabed", bm, [C_UNDER], loc=(0, 60, SB - 0.05), smooth=False)
    sb.data.materials.append(sand)
    bm = bmesh.new()
    for gx in np.arange(-26.0, 26.1, 3.2):
        for gy in np.arange(0.0, 104.0, 3.2):
            if rg.random() < 0.07 and abs(gx) > 6:
                continue
            h = 0.26
            dz = rg.uniform(-0.05, 0.09)
            tilt_ok = rg.random() < 0.15
            m = Matrix.Translation((gx + rg.uniform(-0.03, 0.03), gy + rg.uniform(-0.03, 0.03), SB + dz)) @ \
                Matrix.Rotation(rg.uniform(-0.012, 0.012), 4, "Z") @ \
                (Matrix.Rotation(rg.uniform(-0.05, 0.05), 4, "X") if tilt_ok else Matrix.Identity(4)) @ \
                Matrix.Diagonal((3.08, 3.08, h, 1))
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    plaza = mesh_obj("Roads", bm, [C_UNDER], smooth=False)
    plaza.data.materials.append(slab_m)
    # ---- stone structures
    bs_ = bmesh.new()    # light marble
    bd_ = bmesh.new()    # darker / lower
    bg_ = bmesh.new()    # lantern glass
    bb_ = bmesh.new()    # bronze fittings
    bgl = bmesh.new()    # door glow cards
    tops = []
    # colonnades along the avenue (x = +-8), some broken
    for sx in (-1, 1):
        ys = np.arange(12.0, 72.0, 4.4)
        intact = []
        for i, y in enumerate(ys):
            brk = rg.random() < 0.22 and i not in (0, len(ys) - 1)
            if brk:
                hh = rg.uniform(2.5, 6.5)
                add_column(bs_, sx * 8.0, y, SB + 0.1, hh, 0.68, broken=1.4, rng=rg)
                # fallen drums
                for k in range(3):
                    dx, dy = rg.uniform(-2.5, 2.5), rg.uniform(-1.5, 1.5)
                    ang = rg.uniform(0, 3.14)
                    bmesh.ops.create_cone(bd_, cap_ends=True, segments=16, radius1=0.62, radius2=0.6, depth=rg.uniform(0.9, 1.4),
                                          matrix=Matrix.Translation((sx * 8.0 + dx + sx * 1.2, y + dy, SB + 0.65)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "Y"))
                tops.append((sx * 8.0, y, SB + 0.1 + hh))
            else:
                add_column(bs_, sx * 8.0, y, SB + 0.1, COL_H, 0.7)
                if i % 2 == 0:
                    add_lantern(bg_, bb_, sx * 8.0 - sx * 1.0, y, SB + 5.6)
            intact.append(not brk)
        for i in range(len(ys) - 1):
            if intact[i] and intact[i + 1]:
                ym = (ys[i] + ys[i + 1]) / 2
                vbox(bs_, sx * 8.0, ym, SB + 0.1 + COL_H + 0.45, 1.5, 4.4 - 0.1, 0.9)
                vbox(bs_, sx * 8.0, ym, SB + 0.1 + COL_H + 1.1, 1.75, 4.4 - 0.1, 0.45)
    # gate pair the camera swims between
    for sx in (-1, 1):
        add_column(bs_, sx * 2.8, 44.0, SB + 0.1, 10.0, 0.75)
    vbox(bs_, 0, 44.0, SB + 10.1 + 0.45, 6.6, 1.7, 0.9)
    add_lantern(bg_, bb_, -2.0, 44.0, SB + 6.0)
    add_lantern(bg_, bb_, 2.0, 44.0, SB + 6.0)
    # arch over the avenue
    add_arch(bs_, 0.0, 56.0, SB + 0.1, 8.4, 2.0, 7.4, gaps=(3,))
    # free-standing colonnade (three columns + lintel), left of the path
    for k in range(4):
        add_column(bs_, -15.5 + k * 3.6, 26.0, SB + 0.1, 9.0 if k != 3 else 4.5, 0.68, broken=(0 if k != 3 else 1.2), rng=rg)
    vbox(bs_, -15.5 + 3.6, 26.0, SB + 9.1 + 0.45, 11.2, 1.5, 0.9)
    add_lantern(bg_, bb_, -15.5 + 3.6, 24.9, SB + 5.0)
    # right: ruined free arch + pair
    add_arch(bs_, 15.0, 38.0, SB + 0.1, 5.2, 1.6, 5.4, gaps=(2, 14, 15))
    for k in range(3):
        add_column(bs_, 16.0 + k * 3.6, 62.0, SB + 0.1, rg.choice([9.0, 6.0, 3.5]), 0.66, broken=(1.0 if k else 0.0), rng=rg)
    # statues on plinths (one right beside the dive line)
    add_statue(bs_, -3.6, 34.0, SB + 0.1, 0.6, 1.0, True)
    add_statue(bs_, 4.0, 63.0, SB + 0.1, math.pi - 0.5, 1.1, False)
    add_statue(bs_, -12.5, 50.0, SB + 0.1, 0.3, 0.9, True)
    add_statue(bs_, 12.5, 22.0, SB + 0.1, -0.4, 1.0, False)
    for (sx, sy) in ((-3.6, 34.0), (4.0, 63.0), (-12.5, 50.0), (12.5, 22.0)):
        tops.append((sx, sy, SB + 2.6))
    # scattered broken drums and blocks in the plaza
    for i in range(36):
        x, y = rg.uniform(-18, 18), rg.uniform(8, 92)
        if abs(x) < 2.2:
            x += 4.5 * (1 if x >= 0 else -1)
        bmesh.ops.create_cone(bd_, cap_ends=True, segments=14, radius1=0.6, radius2=0.56, depth=rg.uniform(0.7, 1.5),
                              matrix=Matrix.Translation((x, y, SB + 0.55)) @ Matrix.Rotation(rg.uniform(0, 3.14), 4, "Z") @ Matrix.Rotation(rg.choice([0, math.pi / 2]), 4, "Y"))
        if i % 3 == 0:
            vbox(bd_, x + 1.2, y + 0.6, SB + 0.35, rg.uniform(0.8, 1.8), rg.uniform(0.8, 1.6), 0.6, rg.uniform(0, 3))
    # ---- the temple
    # steps
    for k in range(4):
        yk = TEMPLE_Y - (3 - k) * 2.2
        hk = 0.4 * (k + 1)
        vbox(bs_, 0, (yk + 97.0) / 2, SB + hk / 2, 30.0 + (3 - k) * 2.4, 97.0 - yk, hk)
    FL = SB + 1.6
    # portico front row (6 columns), side peristyle, entablature, ceiling
    front_x = [-11.0, -6.6, -2.2, 2.2, 6.6, 11.0]
    for x in front_x:
        add_column(bs_, x, 78.0, FL, COL_H, 0.85)
    for sx in (-1, 1):
        for y in (82.5, 87.5, 92.5):
            add_column(bs_, sx * 11.0, y, FL, COL_H, 0.85)
    ztop = FL + COL_H
    vbox(bs_, 0, 78.0, ztop + 0.45, 26.4, 1.9, 0.9)
    vbox(bs_, 0, 78.0, ztop + 1.25, 27.0, 2.1, 0.7)
    for sx in (-1, 1):
        vbox(bs_, sx * 11.0, 87.5, ztop + 0.45, 1.9, 16.0, 0.9)
    for x in front_x:
        vbox(bs_, x, 81.2, ztop + 0.3, 1.0, 6.6, 0.6)
    vbox(bd_, 0, 81.2, ztop + 0.05, 25.0, 6.6, 0.3)
    # pediment (triangular prism) and gable roof
    PH = 4.2
    zb = ztop + 1.6
    for (ya, yb) in ((77.0, 78.4),):
        vs = [bs_.verts.new(v) for v in [(-13.4, ya, zb), (13.4, ya, zb), (0.0, ya, zb + PH),
                                         (-13.4, yb, zb), (13.4, yb, zb), (0.0, yb, zb + PH)]]
        for fi in [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]:
            bs_.faces.new([vs[i] for i in fi])
    # recessed tympanum (darker, warm-lit)
    vs = [bd_.verts.new(v) for v in [(-10.5, 78.42, zb + 0.15), (10.5, 78.42, zb + 0.15), (0.0, 78.42, zb + PH - 0.85)]]
    bd_.faces.new(vs[::-1])
    al = math.atan2(PH, 13.4)
    for sx in (-1, 1):
        m = Matrix.Translation((sx * 6.7, 87.0, zb + PH / 2 + 0.25)) @ Matrix.Rotation(sx * al, 4, "Y") @ Matrix.Diagonal((14.4, 22.0, 0.55, 1))
        bmesh.ops.create_cube(bd_, size=1.0, matrix=m)
    # cella: walls up to the roof, front wall at CELLA_Y0
    # (the EndBuilding box from build_ending is the cella; here only the side and back walls + doorway frames)
    for sx in (-1, 1):
        vbox(bs_, sx * 8.4, 91.0, FL + COL_H / 2 + 0.3, 0.8, 14.0, COL_H + 0.6)
    vbox(bs_, 0, 98.0, FL + COL_H / 2, 17.6, 0.8, COL_H)
    # doorways left and right of the window (warm glow cards + bronze frames)
    for sx in (-1, 1):
        dx = sx * 4.9
        vbox(bb_, dx, CELLA_Y0 - 0.1, FL + 2.3, 2.3, 0.22, 0.25)
        vbox(bb_, dx - 0.95, CELLA_Y0 - 0.1, FL + 1.1, 0.2, 0.22, 2.3)
        vbox(bb_, dx + 0.95, CELLA_Y0 - 0.1, FL + 1.1, 0.2, 0.22, 2.3)
        vs = [bgl.verts.new(v) for v in [(dx - 0.85, CELLA_Y0 - 0.06, FL), (dx + 0.85, CELLA_Y0 - 0.06, FL),
                                          (dx + 0.85, CELLA_Y0 - 0.06, FL + 2.2), (dx - 0.85, CELLA_Y0 - 0.06, FL + 2.2)]]
        bgl.faces.new(vs)
    # lanterns on the portico columns + flanking the steps
    for x in front_x:
        add_lantern(bg_, bb_, x, 76.6, FL + 5.2)
    for sx in (-1, 1):
        add_lantern(bg_, bb_, sx * 15.5, 70.0, SB + 2.0)
    # ---- build objects
    bmesh.ops.recalc_face_normals(bs_, faces=bs_.faces[:])
    bmesh.ops.recalc_face_normals(bd_, faces=bd_.faces[:])
    objs = []
    for nm, b, m, smooth in (("Buildings", bs_, stone, True), ("Rubble", bd_, stone_dk, False),
                             ("LampHeads", bg_, lant_g, True), ("LampPosts", bb_, bronze, False),
                             ("DoorCards", bgl, door_g, False)):
        o = mesh_obj(nm, b, [C_UNDER], smooth=smooth)
        o.data.materials.append(m)
        if nm == "Buildings":
            bv = o.modifiers.new("Bevel", "BEVEL")
            bv.width = 0.05
            bv.segments = 1
            bv.limit_method = "ANGLE"
        objs.append(o)
    for nm in ("Buildings", "Rubble", "LampHeads", "LampPosts", "DoorCards"):
        pass
    # point lights at lanterns (only those useful to the camera), warm
    pick = [l for l in LANTERNS if l[1] > 70] + [l for l in LANTERNS if l[1] <= 70][::2]
    for (x, y, z) in pick[:26]:
        ld = bpy.data.lights.new("Lamp", "POINT")
        ld.energy = 900
        ld.color = (1.0, 0.58, 0.22)
        ld.shadow_soft_size = 0.3
        ld.use_shadow = False
        lo = bpy.data.objects.new("Lamp", ld)
        lo.location = (x, y, z)
        link(lo, C_UNDER)
    return tops
