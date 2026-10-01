# ---- v3: Victorian seaside amusement pier, pier-head pavilions, 30 m Ferris wheel, wet sand beach
PIER_HW = 2.5                     # narrow pier half width (rails sit here)
HEAD_Y0, HEAD_Y1, HEAD_HW = 16.0, 52.0, 22.0
PY0 = -28.0
WHEEL_X, WHEEL_Y, WHEEL_R = 5.0, 28.0, 15.0
WHEEL_HUB_Z = DECK + 1.9 + WHEEL_R


def vbox(bm, cx, cy, cz, w, d, h, yaw=0.0):
    m = Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((w, d, h, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def vbeam(bm, p0, p1, r, seg=6):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if d.length < 1e-6:
        return
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length,
                          matrix=Matrix.Translation((p0 + p1) / 2) @ rot)


def vsphere(bm, p, r, sc=(1, 1, 1), seg=10, rings=6):
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0,
                              matrix=Matrix.Translation(p) @ Matrix.Diagonal((r * sc[0], r * sc[1], r * sc[2], 1)))


def emis_mat(name, col, strength):
    m, nt = new_mat(name)
    em = N(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = col + (1.0,)
    em.inputs["Strength"].default_value = strength
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, em.outputs[0], out.inputs["Surface"])
    return m


def rail_run(bm, a, b, h=1.0):
    a, b = Vector(a), Vector(b)
    d = b - a
    L_ = d.length
    u = d / L_
    ang = math.atan2(d.y, d.x)
    n = max(1, int(round(L_ / 1.5)))
    for i in range(n + 1):
        p = a + u * (L_ * i / n)
        vbox(bm, p.x, p.y, DECK + h / 2, 0.09, 0.09, h, ang)
        vsphere(bm, (p.x, p.y, DECK + h + 0.06), 0.07, seg=8, rings=5)
    c = (a + b) / 2
    for z, t in ((h, 0.065), (0.55, 0.04), (0.10, 0.04)):
        vbox(bm, c.x, c.y, DECK + z, L_, t, t, ang)
    s = 0.12
    while s < L_ - 0.05:
        p = a + u * s
        vbox(bm, p.x, p.y, DECK + 0.54, 0.022, 0.022, 0.86, ang)
        s += 0.14


def build_pier_v3():
    wood = wood_material()
    cream = simple_mat("IronCream", (0.80, 0.73, 0.56), 0.42, bump=0.4)
    dkiron = simple_mat("PileIron", (0.05, 0.055, 0.05), 0.6, metallic=0.5, bump=0.6)
    lampg = emis_mat("LampGlass", (1.0, 0.72, 0.36), 9.0)
    # ---- deck boards (narrow pier then the wide pier head)
    bm = bmesh.new()
    y = PY0
    while y < HEAD_Y1:
        bw = rnd.uniform(0.13, 0.17)
        y2 = min(y + bw, HEAD_Y1)
        hw = PIER_HW if y < HEAD_Y0 else HEAD_HW
        zoff = rnd.uniform(-0.006, 0.010)
        x0, x1 = -hw + rnd.uniform(-0.02, 0.02), hw + rnd.uniform(-0.02, 0.02)
        th = 0.05
        vs = [bm.verts.new(v) for v in [
            (x0, y, DECK + zoff), (x1, y, DECK + zoff), (x1, y2, DECK + zoff), (x0, y2, DECK + zoff),
            (x0, y, DECK + zoff - th), (x1, y, DECK + zoff - th), (x1, y2, DECK + zoff - th), (x0, y2, DECK + zoff - th)]]
        for fi in [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
            bm.faces.new([vs[i] for i in fi])
        y = y2 + rnd.uniform(0.008, 0.02)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    deck = mesh_obj("Deck", bm, [C_ABOVE], smooth=False)
    deck.data.materials.append(wood)
    deck.modifiers.new("Bevel", "BEVEL").width = 0.006
    # ---- substructure: stringers, head slab, cross beams
    bm = bmesh.new()
    for x in (-2.0, -1.0, 0.0, 1.0, 2.0):
        vbox(bm, x, (PY0 + HEAD_Y0) / 2, DECK - 0.22, 0.16, HEAD_Y0 - PY0, 0.28)
    vbox(bm, 0, (HEAD_Y0 + HEAD_Y1) / 2, DECK - 0.30, 2 * HEAD_HW, HEAD_Y1 - HEAD_Y0, 0.36)
    yy = PY0 + 1.0
    while yy < HEAD_Y0:
        vbox(bm, 0, yy, DECK - 0.42, 4.8, 0.18, 0.22)
        yy += 4.0
    sub = mesh_obj("PierSub", bm, [C_ABOVE], smooth=False)
    sub.data.materials.append(wood)
    # ---- iron piles (down to z=-8) with X bracing near the waterline
    bm = bmesh.new()
    yy = PY0 + 1.0
    while yy < HEAD_Y0:
        for x in (-2.2, 0.0, 2.2):
            vbeam(bm, (x, yy, -6.0), (x, yy, DECK - 0.05), 0.17, 10)
        vbeam(bm, (-2.2, yy, 0.9), (0.0, yy, -1.6), 0.045)
        vbeam(bm, (0.0, yy, 0.9), (-2.2, yy, -1.6), 0.045)
        vbeam(bm, (2.2, yy, 0.9), (0.0, yy, -1.6), 0.045)
        vbeam(bm, (0.0, yy, 0.9), (2.2, yy, -1.6), 0.045)
        yy += 4.0
    for gx in range(-20, 21, 5):
        for gy in np.arange(HEAD_Y0 + 2.0, HEAD_Y1, 5.0):
            vbeam(bm, (gx, gy, -4.0), (gx, gy, DECK - 0.1), 0.19, 10)
    piles = mesh_obj("Piles", bm, [C_ABOVE, C_UNDER], smooth=True)
    piles.data.materials.append(dkiron)
    # ---- ornate cream iron railings on both sides + round the pier head
    bm = bmesh.new()
    rail_run(bm, (-PIER_HW, PY0), (-PIER_HW, HEAD_Y0))
    rail_run(bm, (PIER_HW, PY0), (PIER_HW, HEAD_Y0))
    rail_run(bm, (-HEAD_HW, HEAD_Y0), (-PIER_HW, HEAD_Y0))
    rail_run(bm, (PIER_HW, HEAD_Y0), (HEAD_HW, HEAD_Y0))
    rail_run(bm, (-HEAD_HW, HEAD_Y0), (-HEAD_HW, HEAD_Y1))
    rail_run(bm, (HEAD_HW, HEAD_Y0), (HEAD_HW, HEAD_Y1))
    rail_run(bm, (-HEAD_HW, HEAD_Y1), (HEAD_HW, HEAD_Y1))
    rails = mesh_obj("Rail", bm, [C_ABOVE], smooth=False)
    rails.data.materials.append(cream)
    # ---- lamp posts (both sides of the deck, round the head)
    bp = bmesh.new()
    bg = bmesh.new()
    posts = [(s * PIER_HW, yy) for yy in np.arange(PY0 + 4.0, HEAD_Y0 - 1.0, 7.0) for s in (-1, 1)]
    posts += [(s * (HEAD_HW - 0.2), yy) for yy in np.arange(HEAD_Y0 + 6.0, HEAD_Y1 - 2.0, 9.0) for s in (-1, 1)]
    for (x, yy) in posts:
        inward = -1.0 if x > 0 else 1.0
        vbox(bp, x, yy, DECK + 0.25, 0.32, 0.32, 0.5)
        vbeam(bp, (x, yy, DECK), (x, yy, DECK + 4.3), 0.06, 8)
        vbeam(bp, (x, yy, DECK + 4.2), (x + inward * 0.45, yy, DECK + 4.5), 0.04, 6)
        vsphere(bp, (x, yy, DECK + 1.2), 0.11, seg=8, rings=5)
        vsphere(bg, (x + inward * 0.45, yy, DECK + 4.75), 0.24, (1, 1, 1.25))
        vbeam(bp, (x + inward * 0.45, yy, DECK + 4.95), (x + inward * 0.45, yy, DECK + 5.15), 0.12, 8)
    lp = mesh_obj("LampPost", bp, [C_ABOVE], smooth=True)
    lp.data.materials.append(cream)
    lg = mesh_obj("LampGlobes", bg, [C_ABOVE], smooth=True)
    lg.data.materials.append(lampg)
    build_wheel()
    build_pavilions(cream)
    return deck


def build_wheel():
    paint = simple_mat("WheelPaint", (0.62, 0.60, 0.55), 0.5, bump=0.3)
    red = simple_mat("CabinRed", (0.50, 0.08, 0.06), 0.45)
    blue = simple_mat("CabinBlue", (0.10, 0.22, 0.45), 0.45)
    bulbm = emis_mat("WheelBulb", (1.0, 0.85, 0.55), 14.0)
    hub = bpy.data.objects.new("WheelHub", None)
    hub.location = (WHEEL_X, WHEEL_Y, WHEEL_HUB_Z)
    link(hub, C_ABOVE)
    hub.rotation_euler = (0, 0, 0)
    hub.keyframe_insert("rotation_euler", frame=1)
    hub.rotation_euler = (0, 0.42, 0)
    hub.keyframe_insert("rotation_euler", frame=NF)
    R, NS, dy = WHEEL_R, 48, 0.65
    bm = bmesh.new()
    bb = bmesh.new()
    for side in (-1, 1):
        yv = side * dy
        for i in range(NS):
            a0, a1 = 2 * math.pi * i / NS, 2 * math.pi * (i + 1) / NS
            p0 = (R * math.cos(a0), yv, R * math.sin(a0))
            p1 = (R * math.cos(a1), yv, R * math.sin(a1))
            vbeam(bm, p0, p1, 0.16)
            if i % 2 == 0:
                vsphere(bb, p0, 0.17, seg=6, rings=4)
            q0 = (0.72 * R * math.cos(a0), yv, 0.72 * R * math.sin(a0))
            q1 = (0.72 * R * math.cos(a1), yv, 0.72 * R * math.sin(a1))
            vbeam(bm, q0, q1, 0.07)
        for i in range(24):
            a = 2 * math.pi * i / 24
            vbeam(bm, (0, yv, 0), (R * math.cos(a), yv, R * math.sin(a)), 0.045)
    for i in range(NS):
        a = 2 * math.pi * i / NS
        a2 = 2 * math.pi * (i + 0.5) / NS
        vbeam(bm, (R * math.cos(a), -dy, R * math.sin(a)), (R * math.cos(a2), dy, R * math.sin(a2)), 0.045)
    vbeam(bm, (0, -1.4, 0), (0, 1.4, 0), 0.75, 16)
    wr = mesh_obj("WheelRim", bm, [C_ABOVE], smooth=False)
    wr.data.materials.append(paint)
    wr.parent = hub
    wb = mesh_obj("WheelBulbs", bb, [C_ABOVE], smooth=False)
    wb.data.materials.append(bulbm)
    wb.parent = hub
    # cabins: hang from the rim, counter-rotate so they stay upright
    for k in range(16):
        a = 2 * math.pi * k / 16
        bc = bmesh.new()
        vbox(bc, 0, 0, -0.95, 1.7, 1.3, 1.25)
        vbox(bc, 0, 0, -0.25, 0.08, 0.08, 0.5)
        vbox(bc, 0, 0, -1.65, 1.9, 1.5, 0.12)
        cab = mesh_obj(f"Cabin{k}", bc, [C_ABOVE], smooth=False)
        cab.data.materials.append(red if k % 2 == 0 else blue)
        cab.parent = hub
        cab.location = (R * math.cos(a), 0, R * math.sin(a))
        cab.rotation_euler = (0, 0, 0)
        cab.keyframe_insert("rotation_euler", frame=1)
        cab.rotation_euler = (0, -0.42, 0)
        cab.keyframe_insert("rotation_euler", frame=NF)
    # A-frame legs + platform
    bl = bmesh.new()
    for sy in (-1.3, 1.3):
        for sx in (-1, 1):
            vbeam(bl, (WHEEL_X, WHEEL_Y + sy, WHEEL_HUB_Z), (WHEEL_X + sx * 8.5, WHEEL_Y + sy * 1.6, DECK), 0.28, 8)
    vbox(bl, WHEEL_X, WHEEL_Y, DECK + 0.3, 20, 6, 0.6)
    lg_ = mesh_obj("WheelLegs", bl, [C_ABOVE], smooth=False)
    lg_.data.materials.append(paint)
    # animation interpolation -> LINEAR
    for ob in [hub] + [bpy.data.objects[f"Cabin{k}"] for k in range(16)]:
        for lay in ob.animation_data.action.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"


def build_pavilions(cream):
    wall = simple_mat("PavWall", (0.82, 0.75, 0.60), 0.7, bump=0.5)
    roof = simple_mat("PavRoof", (0.42, 0.09, 0.07), 0.6)
    dome = simple_mat("PavDome", (0.16, 0.42, 0.36), 0.42, metallic=0.4)
    winm = emis_mat("PavWindow", (1.0, 0.62, 0.25), 5.0)
    bw, br, bd, bn = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()

    def pav(cx, cy, w, d, h, dome_r, turret=False):
        vbox(bw, cx, cy, DECK + h / 2, w, d, h)
        vbox(br, cx, cy, DECK + h + 0.15, w + 0.8, d + 0.8, 0.3)
        vbox(br, cx, cy, DECK + h + 0.5, w * 0.9, d * 0.9, 0.4)
        zc = DECK + h + 0.7
        vbeam(bd, (cx, cy, zc - 0.1), (cx, cy, zc + dome_r * 0.25), dome_r * 0.92, 20)
        vsphere(bd, (cx, cy, zc + dome_r * 0.2), dome_r, (1, 1, 1.05), seg=24, rings=12)
        vbeam(bd, (cx, cy, zc + dome_r * 1.2), (cx, cy, zc + dome_r * 1.2 + 2.6), 0.07, 6)
        vsphere(bd, (cx, cy, zc + dome_r * 1.2 + 0.5), 0.2, seg=8, rings=5)
        fy = cy - d / 2 - 0.02
        nx = max(1, int(w / 2.3))
        for i in range(nx):
            x = cx - w / 2 + (i + 0.5) * w / nx
            for zz in ((1.6, 3.9) if h > 5.5 else (1.6,)):
                vbox(bn, x, fy, DECK + zz, 1.0, 0.04, 1.7)
    pav(-12.0, 44.0, 16.0, 14.0, 7.0, 4.3)
    pav(-20.0, 37.0, 3.6, 3.6, 10.0, 2.0)
    pav(-4.0, 37.0, 3.6, 3.6, 10.0, 2.0)
    pav(17.0, 41.0, 10.0, 12.0, 6.0, 3.4)
    pav(3.0, 49.0, 24.0, 4.0, 5.0, 2.6)
    for nm, b, m in (("PavWalls", bw, wall), ("PavRoofs", br, roof), ("PavDomes", bd, dome), ("PavWindows", bn, winm)):
        o = mesh_obj(nm, b, [C_ABOVE], smooth=(nm == "PavDomes"))
        o.data.materials.append(m)


def build_beach():
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=12, y_segments=160, size=1.0, matrix=Matrix.Diagonal((300, 160, 1, 1)))
    for v in bm.verts:
        y = v.co.y - 80.0
        t = smoothstep(-10.0, -1.0, y)
        v.co.y = y
        v.co.z = 0.07 - 1.5 * t + 0.03 * math.sin(v.co.x * 0.7) * math.cos(y * 0.9) * (1 - t)
    ob = mesh_obj("Beach", bm, [C_ABOVE], smooth=True)
    m, nt = new_mat("WetSand")
    col, rough, nor = pbr_maps(nt, "sandy_gravel_02", scale=0.18, strength=0.6)
    tt = N(nt, "ShaderNodeMix")
    tt.data_type = "RGBA"
    tt.blend_type = "MULTIPLY"
    tt.inputs[0].default_value = 1
    tt.inputs[7].default_value = (0.55, 0.42, 0.32, 1)
    L(nt, col, tt.inputs[6])
    bs = principled(nt)
    L(nt, tt.outputs[2], bs.inputs["Base Color"])
    L(nt, MATH(nt, "MINIMUM", rough, 0.22), bs.inputs["Roughness"])
    L(nt, nor, bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    ob.visible_shadow = True
    return ob
