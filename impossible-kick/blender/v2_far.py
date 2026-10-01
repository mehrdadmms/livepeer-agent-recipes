# v2 additions, exec()'d at the end of scene_far.py (scene.py namespace): football-mad street (murals, fan flags),
# rooftop kids, pigeons, goalkeeper, crossbar/net ending, confetti, crowd reaction.
rr2 = random.Random(2088)
SKIN = simple('v2skin', (0.42, 0.27, 0.18), 0.6)
HAIR = simple('v2hair', (0.03, 0.025, 0.02), 0.8)

# ---------------------------------------------------------------- crowd reacts to the goal (emission ramps up, then settles high)
_cm = bpy.data.materials['crowd']
_em = [n for n in _cm.node_tree.nodes if n.type == 'EMISSION'][0]
for f_, v_ in ((0, 2.2), (600, 2.2), (612, 3.2), (622, 4.6), (645, 3.4), (719, 3.6)):
    _em.inputs[1].default_value = v_; _em.inputs[1].keyframe_insert('default_value', frame=f_)

# ---------------------------------------------------------------- helpers
def flag(name, img, center, size, rot_z=0.0, wave=0.07):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(TEX+img)
    nt.links.new(t.outputs[0], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.85; bs.inputs['Sheen Weight'].default_value = 0.4
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=8, y_segments=6, size=0.5, calc_uvs=True)
    for v in bm.verts: v.co = Vector((v.co.x*size[0], v.co.y*size[1], 0))
    ob = _mesh_obj(name, bm, m); ob.location = center; ob.rotation_euler = (math.pi/2, 0, rot_z)
    for p_ in ob.data.polygons: p_.use_smooth = True
    wv = ob.modifiers.new('wave', 'WAVE'); wv.height = wave; wv.width = 0.5; wv.narrowness = 2.5; wv.speed = 0.10; wv.time_offset = rr2.uniform(0, 40); wv.use_normal = True
    return ob

def person(name, base, height, kit, legs_col, skin=None, arms_up=0.0, parent=None):
    """crude standing figure; returns root empty (origin at feet). arms_up: 0 hanging .. 1 raised"""
    root = bpy.data.objects.new(name, None); sc.collection.objects.link(root); root.location = base
    h = height
    def part(ob): ob.parent = root; return ob
    part(cyl(name+'_legL', (-0.09*h/1.7, 0, h*0.24), 0.05*h/1.7, h*0.48, legs_col, seg=8))
    part(cyl(name+'_legR', (0.09*h/1.7, 0, h*0.24), 0.05*h/1.7, h*0.48, legs_col, seg=8))
    part(cyl(name+'_torso', (0, 0, h*0.66), 0.13*h/1.7, h*0.36, kit, seg=10, r2=0.15*h/1.7))
    part(sphere(name+'_head', (0, 0, h*0.92), 0.085*h/1.7, skin or SKIN, seg=10))
    part(sphere(name+'_hair', (0, 0.01, h*0.945), 0.08*h/1.7, HAIR, seg=8, scale=(1, 1, 0.75)))
    arms = []
    for s_ in (-1, 1):
        a = part(cyl(name+f'_arm{s_}', (s_*0.19*h/1.7, 0, h*0.68), 0.035*h/1.7, h*0.34, kit, seg=8))
        arms.append((a, s_))
    return root, arms
def raise_arms(arms, f_from, f_to, up=1.0):
    for a, s_ in arms:
        a.rotation_euler = (0, math.radians(s_*8), 0); a.keyframe_insert('rotation_euler', frame=f_from)
        a.rotation_euler = (0, math.radians(s_*(8+150*up)), 0); a.keyframe_insert('rotation_euler', frame=f_to)

def bird(name, pos, vel, f_start, n=10):
    """pigeon that sits still, then bursts away when the can gets near (f_start), wings flapping"""
    root = bpy.data.objects.new(name, None); sc.collection.objects.link(root)
    body = sphere(name+'_b', (0, 0, 0), 0.11, simple('pigeon', (0.32, 0.34, 0.4), 0.8), seg=10, scale=(0.5, 1.0, 0.55)); body.parent = root
    hd = sphere(name+'_h', (0, 0.11, 0.04), 0.045, simple('pigeonh', (0.2, 0.25, 0.3), 0.7), seg=8); hd.parent = root
    wings = []
    for s_ in (-1, 1):
        w = box(name+f'_w{s_}', (s_*0.13, 0, 0.02), (0.22, 0.09, 0.012), simple('pigeonw', (0.36, 0.38, 0.44), 0.8)); w.parent = root; wings.append((w, s_))
    root.location = pos; root.keyframe_insert('location', frame=f_start-1)
    dur = 60
    root.location = Vector(pos)+Vector(vel)*(dur/24.0)+Vector((0, 0, 1.2)); root.keyframe_insert('location', frame=f_start+dur)
    root.rotation_euler = (0, 0, math.atan2(-vel[0], vel[1])); root.keyframe_insert('rotation_euler', frame=f_start-1)
    for k in range(0, dur, 3):
        for w, s_ in wings:
            w.rotation_euler = (0, math.radians(s_*(-45 if (k//3) % 2 else 40)), 0); w.keyframe_insert('rotation_euler', frame=f_start+k)
    for w, s_ in wings:
        w.rotation_euler = (0, math.radians(s_*70), 0); w.keyframe_insert('rotation_euler', frame=f_start-1)   # folded before the burst
    return root

# ---------------------------------------------------------------- pigeons on an alley sill (near miss on the climb) and one more flock on the kids' roof
pa = P(92)
box('sill_pigeons', (1.32, pa.y, pa.z-0.9), (0.3, 3.0, 0.08), M['concrete'])
for k in range(7):
    bird(f'pigA{k}', (1.30-0.05*(k % 2), pa.y-1.2+k*0.4, pa.z-0.78), (-1.5-rr2.random()*2, 2.5+rr2.random()*3, 0.4), int(T(92))-14)

# ---------------------------------------------------------------- rooftop kids playing football (near miss on the way to the window building)
y0 = P(104).y
_ps = [Vector(CAN(f)) for f in np.arange(T(104)-30, T(104)+30, 0.5)]
zmin = min([p.z for p in _ps if y0-1.7 <= p.y <= y0+1.7] or [P(104).z])
rtop = max(zmin-2.1, 4.0)
box('kidhouse', (0, y0, rtop/2), (7.4, 3.6, rtop), M['plaster'])
box('kidroof', (0, y0, rtop+0.1), (7.6, 3.8, 0.2), M['concrete'])
for (px, py, sx, sy) in ((0, -1.8, 7.6, 0.2), (0, 1.8, 7.6, 0.2), (-3.7, 0, 0.2, 3.8), (3.7, 0, 0.2, 3.8)):
    box('kidpar', (px, y0+py, rtop+0.55), (sx, sy, 0.7), M['concrete'])
zt = rtop+0.2
kitc = [simple('kit_r', (0.7, 0.12, 0.1), 0.8), simple('kit_b', (0.12, 0.25, 0.6), 0.8), simple('kit_y', (0.85, 0.7, 0.15), 0.8), simple('kit_w', (0.85, 0.85, 0.82), 0.8)]
jeans = simple('kidshort', (0.1, 0.12, 0.2), 0.9)
for k, (kx, ky) in enumerate(((-2.2, -0.6), (-1.2, 0.5), (0.2, -0.3), (1.3, 0.6), (2.3, -0.5), (-0.4, 1.1))):
    kroot, karms = person(f'kid{k}', (kx, y0+ky, zt), 1.25, kitc[k % 4], jeans)
    kroot.rotation_euler = (0, 0, rr2.uniform(0, 6.28))
    tt = int(T(104))
    raise_arms(karms, tt-30, tt-8, up=0.9)                      # they spot the can and cheer
    kroot.location = (kx, y0+ky, zt); kroot.keyframe_insert('location', frame=tt-30)
    kroot.location = (kx, y0+ky, zt+0.12); kroot.keyframe_insert('location', frame=tt-20)      # little jump
    kroot.location = (kx, y0+ky, zt); kroot.keyframe_insert('location', frame=tt-12)
    kroot.location = (kx, y0+ky, zt+0.15); kroot.keyframe_insert('location', frame=tt-4)
    kroot.location = (kx, y0+ky, zt); kroot.keyframe_insert('location', frame=tt+4)
# their ball + two bag goals
bl = sphere('kidball', (0.6, y0+0.1, zt+0.11), 0.11, simple('ball', (0.92, 0.92, 0.9), 0.5), seg=14)
for gxx in (-3.2, 3.2):
    for gyy in (-0.4, 0.4): cyl('bagpost', (gxx, y0+gyy, zt+0.15), 0.07, 0.3, simple('bagp', (0.15, 0.2, 0.3), 0.9), seg=10)
# fan flags on the roof line
line_pts = [(-3.7+t*7.4, y0-1.9, zt+1.7-0.15*math.sin(math.pi*t)) for t in np.linspace(0, 1, 12)]
crv = bpy.data.curves.new('kidline', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.008
sp = crv.splines.new('POLY'); sp.points.add(len(line_pts)-1)
for p_, q_ in zip(sp.points, line_pts): p_.co = (*q_, 1)
co = bpy.data.objects.new('kidline', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
for k, x_ in enumerate((-2.6, -0.9, 0.9, 2.6)):
    flag(f'kidflag{k}', 'flag_a.png' if k % 2 == 0 else 'flag_b.png', (x_, y0-1.9, zt+1.25), (0.55, 0.36))
for k in range(6):   # pigeons on the roof parapet, they burst as the can flies over
    bird(f'pigB{k}', (-3.3+k*0.35, y0+1.8, rtop+0.95), (rr2.uniform(-2, 2), 2+rr2.random()*3, 0.5), int(T(104))-16)

# ---------------------------------------------------------------- football street: murals + fan flags (market, old y 38-112)
mural_y = [(-1, 58, 'mural1', 9.0), (1, 70, 'mural2', 9.0), (-1, 86, 'mural3', 9.0), (1, 98, 'mural4', 9.0), (-1, 46, 'mural2', 8.0), (1, 52, 'mural3', 8.0)]
for k, (side, yy, name, wdt) in enumerate(mural_y):
    hgt = wdt*1365/1024
    if side < 0: decal(f'mur{k}', name+'.png', (yy, 4.0+hgt/2), (wdt, hgt), 0.0, wall_x=-7.5, sgn=1, rough=0.9)
    else: decal(f'mur{k}', name+'_r.png', (yy, 4.0+hgt/2), (wdt, hgt), 0.0, wall_x=7.5, sgn=-1, rough=0.9)
# strung fan flags across the street (two kinds), a few hung low as near misses for the can
for k, yy in enumerate(np.arange(44, 108, 4.5)):
    zc = 5.0+0.4*math.sin(k*1.3)
    pts = [(-7.2+t*14.4, yy, zc-0.7*math.sin(math.pi*t)) for t in np.linspace(0, 1, 16)]
    crv = bpy.data.curves.new('ffl', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.008
    sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p_, q_ in zip(sp.points, pts): p_.co = (*q_, 1)
    co = bpy.data.objects.new('ffl', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
    for j in range(6):
        t = (j+0.7)/7.4; x_ = -7.2+t*14.4
        flag(f'fflag{k}_{j}', 'flag_a.png' if (j+k) % 2 == 0 else 'flag_b.png', (x_, yy, zc-0.7*math.sin(math.pi*t)-0.42), (0.7, 0.45), rr2.uniform(-0.2, 0.2))
for old_f in (117, 122, 127, 132):        # low hanging banners right on the flight line
    p_ = P(old_f); zc = p_.z+1.55
    for x_ in (-7.0, 7.0): pass
    pts = [(-7.2+t*14.4, p_.y, zc-0.5*math.sin(math.pi*t)) for t in np.linspace(0, 1, 16)]
    crv = bpy.data.curves.new('nmfl', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.01
    sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p2, q2 in zip(sp.points, pts): p2.co = (*q2, 1)
    co = bpy.data.objects.new('nmfl', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
    tx = (p_.x+rr2.choice((-0.55, 0.55))); t = (tx+7.2)/14.4
    flag(f'nmflag{old_f}', 'flag_a.png' if old_f % 2 else 'flag_b.png', (tx, p_.y, zc-0.5*math.sin(math.pi*t)-0.6), (1.1, 0.7))

# ---------------------------------------------------------------- goalkeeper: dives the right way but late (ending B)
gk_kit = simple('gk_kit', (0.95, 0.45, 0.05), 0.7); gk_short = simple('gk_short', (0.03, 0.03, 0.04), 0.8)
gk, gk_arms = person('keeper', (-0.30, GY-0.35, 0.0), 1.85, gk_kit, gk_short)
for a, s_ in gk_arms:
    a.rotation_euler = (0, math.radians(s_*30), 0)
    gl = sphere(a.name+'_glove', (0, 0, -0.2), 0.055, simple('glove', (0.6, 0.95, 0.1), 0.6), seg=8); gl.parent = a
GKK = ((0, (-0.30, 0.0, 0.0), 0), (596, (-0.30, 0.0, -0.06), 0), (600, (-0.28, 0.0, 0.06), 4), (603, (-0.22, 0.02, 0.35), 25),
       (607, (0.05, 0.04, 0.60), 50), (612, (0.45, 0.06, 0.70), 76), (618, (0.72, 0.16, 0.45), 85), (624, (0.85, 0.30, 0.18), 89), (719, (0.85, 0.30, 0.16), 89))
for f_, (dx, dy, dz), ry in GKK:
    gk.location = (dx, GY-0.35+dy, dz); gk.rotation_euler = (0, math.radians(ry), 0); gk.keyframe_insert('location', frame=f_); gk.keyframe_insert('rotation_euler', frame=f_)
for a, s_ in gk_arms:   # arms reach up/out during the dive
    for f_, ang in ((0, 30), (598, 40), (603, 150), (612, 170), (719, 170)):
        a.rotation_euler = (0, math.radians(s_*ang), 0); a.keyframe_insert('rotation_euler', frame=f_)
set_interp(gk, 'LINEAR')

# ---------------------------------------------------------------- confetti + crowd flash dots after the goal
conf_cols = [(0.9, 0.15, 0.1), (0.95, 0.85, 0.2), (0.15, 0.3, 0.8), (0.95, 0.95, 0.92), (0.2, 0.7, 0.3)]
cmats = [simple(f'conf{i}', c, 0.6, emit=c, estr=0.8) for i, c in enumerate(conf_cols)]
for k in range(220):
    x = rr2.uniform(-24, 24); y = rr2.uniform(312, 336); z0 = rr2.uniform(9, 20)
    ob = box(f'conf{k}', (x, y, z0), (0.16, 0.10, 0.006), cmats[k % 5])
    ob.scale = (0.001,)*3; ob.keyframe_insert('scale', frame=619)
    ob.scale = (1, 1, 1); ob.keyframe_insert('scale', frame=622)
    for f_ in (622, 660, 700, 719):
        dt = (f_-622)/24.0
        ob.location = (x+2.0*math.sin(dt*2.2+k), y-1.5*dt+0.6*math.cos(dt*1.7+k), z0-2.6*dt); ob.rotation_euler = (dt*6+k, dt*4, dt*5)
        ob.keyframe_insert('location', frame=f_); ob.keyframe_insert('rotation_euler', frame=f_)
    set_interp(ob, 'LINEAR')
# phone flashes / flares in the stands behind the goal, blinking after the goal
flash = emission('flashdot', (1.0, 0.97, 0.9), 40)
for k in range(90):
    ang = rr2.uniform(-0.9, 0.9); rad = rr2.uniform(0, 1)
    x = ang*40; y = 330+rr2.uniform(0, 16); z = 6+rr2.uniform(0, 12)
    ob = sphere(f'fl{k}', (x, y, z), 0.14, flash, seg=6)
    ob.scale = (0.001,)*3; ob.keyframe_insert('scale', frame=621)
    for f_ in range(622, 719, 6):
        ob.scale = ((1.0 if rr2.random() < 0.5 else 0.001),)*3; ob.keyframe_insert('scale', frame=f_)
    set_interp(ob, 'LINEAR')
