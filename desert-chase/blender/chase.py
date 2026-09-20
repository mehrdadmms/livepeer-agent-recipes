"""Two-car desert chase previs. Run: blender -b -P chase.py -- <outdir> [preview|final]"""
import bpy, math, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/chase"
MODE = argv[1] if len(argv) > 1 else "preview"
os.makedirs(OUT, exist_ok=True)

FPS, SECONDS = 24, 20
BPM = float(os.environ.get('BPM', '140')); BEAT0 = float(os.environ.get('BEAT0', '0'))
BEAT = 60.0 / BPM
def bt(n): return BEAT0 + n * BEAT        # time of beat n (0 = first beat)
END = FPS * SECONDS
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, END
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

# ---------- materials ----------
def mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, alpha=1.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k in ("Coat Weight", "Clearcoat"):
        if k in b.inputs:
            b.inputs[k].default_value = coat
            break
    if emit:
        k = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[k].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        k = "Transmission Weight" if "Transmission Weight" in b.inputs else "Transmission"
        b.inputs[k].default_value = 0.9
    return m

M = {
    "red": mat("CarRed", (0.55, 0.02, 0.01), 0.25, 0.4, coat=1.0),
    "black": mat("CarBlack", (0.015, 0.015, 0.018), 0.3, 0.15, coat=1.0),
    "glass": mat("Glass", (0.02, 0.03, 0.04), 0.05, 0.0, alpha=0.3),
    "tire": mat("Tire", (0.02, 0.02, 0.02), 0.85),
    "rim": mat("Rim", (0.6, 0.6, 0.62), 0.25, 1.0),
    "head": mat("Head", (1, 1, 1), 0.1, emit=(1, 0.92, 0.8), strength=40),
    "tail": mat("Tail", (0.5, 0, 0), 0.2, emit=(1, 0.02, 0.01), strength=25),
    "asphalt": mat("Asphalt", (0.045, 0.043, 0.042), 0.8),
    "paint": mat("Lines", (0.9, 0.75, 0.3), 0.6),
    "sand": mat("Sand", (0.66, 0.53, 0.38), 0.95),
    "rock": mat("Rock", (0.45, 0.2, 0.1), 0.9),
    "dust": mat("Dust", (0.7, 0.5, 0.33), 1.0),
    "grey": mat("PepperGrey", (0.2, 0.21, 0.22), 0.28, 0.65, coat=1.0),
    "stripe": mat("Stripe", (0.01, 0.01, 0.01), 0.15, 0.2, coat=1.0),
    "blue": mat("BaysideBlue", (0.015, 0.07, 0.42), 0.22, 0.55, coat=1.0),
    "bronze": mat("Bronze", (0.3, 0.2, 0.09), 0.3, 1.0),
    "white": mat("EdgeWhite", (0.85, 0.85, 0.82), 0.6),
    "sage": mat("Sage", (0.2, 0.24, 0.16), 0.9),
    "range": mat("Range", (0.32, 0.3, 0.3), 0.95),
}

# sand & rock get noise bump for texture
for key, scale in (("sand", 8.0), ("rock", 1.5)):
    nt = M[key].node_tree
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])

def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

def cube(name, size, loc, m, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 4
    bpy.ops.object.shade_smooth()
    assign(o, m)
    if parent: o.parent = parent
    return o

# ---------- road path (S-curve through the desert) ----------
pts = [(0, -60, 0), (0, 40, 0), (35, 130, 0), (90, 200, 0), (110, 290, 0),
       (80, 380, 0), (30, 460, 0), (20, 560, 0), (40, 660, 0), (75, 760, 0), (60, 860, 0), (30, 960, 0), (45, 1060, 0), (85, 1160, 0), (70, 1260, 0)]
cd = bpy.data.curves.new("RoadPath", "CURVE"); cd.dimensions = '3D'; cd.resolution_u = 48
sp = cd.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
for bp, p in zip(sp.bezier_points, pts):
    bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
path = bpy.data.objects.new("RoadPath", cd); sc.collection.objects.link(path)
cd.path_duration = END
cd.use_path = True
# sample path points for placing scenery
tmp = path.copy(); tmp.data = cd.copy(); sc.collection.objects.link(tmp)
bpy.context.view_layer.objects.active = tmp
dg = bpy.context.evaluated_depsgraph_get()
mesh = tmp.evaluated_get(dg).to_mesh()
samples = [tmp.matrix_world @ v.co for v in mesh.vertices]
length = sum((samples[i + 1] - samples[i]).length for i in range(len(samples) - 1))
tmp.evaluated_get(dg).to_mesh_clear(); bpy.data.objects.remove(tmp)
print("path length", length)

def along_curve(o, axis='POS_Y'):
    m = o.modifiers.new("curve", "CURVE"); m.object = path; m.deform_axis = axis

# road strip + markings built straight from the sampled path
def strip(name, x0, x1, z, m, dash=None):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    run = 0.0; prev = None; rows = []
    for i, p in enumerate(samples):
        q = samples[min(i + 1, len(samples) - 1)] if i < len(samples) - 1 else p + (p - samples[i - 1])
        t = (q - p).normalized(); n = Vector((t.y, -t.x, 0))
        if prev is not None: run += (p - prev).length
        prev = p
        rows.append((run, bm.verts.new(p + n * x0 + Vector((0, 0, z))), bm.verts.new(p + n * x1 + Vector((0, 0, z)))))
    for (r0, a0, b0), (r1, a1, b1) in zip(rows, rows[1:]):
        if dash and (r0 % dash[0]) > dash[1]: continue
        bm.faces.new((a0, b0, b1, a1))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); assign(o, m)
    return o
strip("Road", -5.5, 5.5, 0.02, M["asphalt"])
strip("LineL", -5.2, -5.05, 0.03, M["white"]); strip("LineR", 5.05, 5.2, 0.03, M["white"])
strip("YellowA", -0.28, -0.14, 0.03, M["paint"]); strip("YellowB", 0.14, 0.28, 0.03, M["paint"])

# ground
bpy.ops.mesh.primitive_plane_add(size=6000, location=(50, 300, 0))
g = bpy.context.object; g.name = "Ground"; assign(g, M["sand"])

# mesas / rocks placed away from the road
import random
random.seed(7)
def rock(loc, s, h):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1, location=loc)
    r = bpy.context.object; r.scale = (s, s * random.uniform(0.7, 1.3), h)
    tex = bpy.data.textures.new("rn", 'CLOUDS'); tex.noise_scale = 0.6
    d = r.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = 0.35
    bpy.ops.object.shade_smooth(); assign(r, M["rock"])
    r.rotation_euler.z = random.uniform(0, 6.28)
for i in range(0, len(samples), 6):
    p = samples[i]
    for side in (-1, 1):
        if random.random() < 0.55:
            off = side * random.uniform(26, 75)
            rock((p.x + off, p.y + random.uniform(-10, 10), 0), random.uniform(3, 9), random.uniform(2, 8))
# sagebrush: linked duplicates scattered off the tarmac
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, -100))
bush = bpy.context.object; bush.name = "Sage"; bush.scale = (0.7, 0.7, 0.45); assign(bush, M["sage"])
tex = bpy.data.textures.new("bn", 'CLOUDS'); tex.noise_scale = 0.3
d = bush.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = 0.5
for i in range(0, len(samples)):
    p = samples[i]
    for _ in range(4):
        off = random.choice((-1, 1)) * random.uniform(7.5, 90)
        b = bush.copy(); sc.collection.objects.link(b)
        sz = random.uniform(0.5, 1.4)
        b.location = (p.x + off, p.y + random.uniform(-8, 8), 0.1); b.scale = (0.7 * sz, 0.7 * sz, 0.45 * sz)
        b.rotation_euler.z = random.uniform(0, 6.28)
# far mountain ranges
for (x, y, sx, sy, h) in [(-900, 900, 600, 250, 160), (700, 1300, 700, 260, 200), (0, 1900, 1200, 300, 260),
                          (-1100, -100, 300, 700, 140), (1100, 300, 300, 800, 180)]:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1, location=(x, y, 0))
    r = bpy.context.object; r.scale = (sx, sy, h)
    tex = bpy.data.textures.new("rg", 'CLOUDS'); tex.noise_scale = 0.25
    dd = r.modifiers.new("disp", "DISPLACE"); dd.texture = tex; dd.strength = 0.35
    bpy.ops.object.shade_smooth(); assign(r, M["range"])
# mid-distance rust buttes
for (x, y, s, h) in [(-300, 500, 70, 45), (350, 700, 90, 55), (300, 200, 60, 35)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=2, location=(x, y, h / 2))
    m_ = bpy.context.object; m_.scale = (s, s * 0.7, h / 2)
    tex = bpy.data.textures.new("mn", 'CLOUDS'); tex.noise_scale = 0.3
    bpy.ops.object.transform_apply(scale=True); b_ = m_.modifiers.new('bev', 'BEVEL'); b_.width = 3; b_.segments = 3; b_.limit_method = 'ANGLE'
    d = m_.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = 0.0
    bpy.ops.object.shade_smooth(); assign(m_, M["rock"])

# ---------- cars ----------
def car(name, body_mat, kind):
    root = bpy.data.objects.new(name, None); sc.collection.objects.link(root)
    if kind == "fastback":   # '67 fastback stand-in (lead): long hood, set-back cabin
        L, W, H, cab = 4.7, 1.85, 0.62, (2.1, 1.5, 0.5, -0.55)
    else:                    # chaser stand-in: taller boxy coupe
        L, W, H, cab = 4.6, 1.79, 0.72, (2.2, 1.55, 0.5, -0.25)
    z0 = 0.42
    cube(name + "_body", (W, L, H), (0, 0, z0 + H / 2), body_mat, 0.07, root)
    cube(name + "_nose", (W * 0.96, 0.9, H * 0.55), (0, L / 2 - 0.1, z0 + H * 0.3), body_mat, 0.15, root)
    cube(name + "_cabin", (cab[1], cab[0], cab[2]), (0, cab[3], z0 + H + cab[2] / 2 - 0.05), M["glass"], 0.12, root)
    cube(name + "_roof", (cab[1] * 0.92, cab[0] * 0.7, 0.06), (0, cab[3] - 0.1, z0 + H + cab[2] - 0.03), body_mat, 0.03, root)
    for x in (-1, 1):
        cube(name + "_hl", (0.45, 0.06, 0.12), (x * (W / 2 - 0.35), L / 2 + 0.33, z0 + H * 0.5), M["head"], 0.02, root)
        cube(name + "_tl", (0.5, 0.06, 0.1), (x * (W / 2 - 0.35), -L / 2 - 0.01, z0 + H * 0.72), M["tail"], 0.02, root)
    if kind == "fastback":
        for x in (-0.28, 0.28):
            cube(name + "_stripe", (0.26, L * 0.99, 0.02), (x, 0, z0 + H + 0.005), M["stripe"], 0.0, root)
            cube(name + "_rstripe", (0.24, cab[0] * 0.72, 0.02), (x, cab[3] - 0.1, z0 + H + cab[2] - 0.0), M["stripe"], 0.0, root)
    else:
        cube(name + "_wing", (W * 0.9, 0.3, 0.04), (0, -L / 2 + 0.2, z0 + H + 0.3), body_mat, 0.01, root)
        for x in (-0.55, 0.55):
            cube(name + "_post", (0.05, 0.12, 0.3), (x, -L / 2 + 0.2, z0 + H + 0.15), body_mat, 0.0, root)
    rim_m = M["bronze"] if kind != "fastback" else M["rim"]
    wheels = []
    for x in (-1, 1):
        for y in (-1, 1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.36, depth=0.3,
                                                location=(x * (W / 2 - 0.08), y * (L / 2 - 0.85), 0.36),
                                                rotation=(0, math.pi / 2, 0))
            w = bpy.context.object; w.name = name + "_wheel"; bpy.ops.object.shade_smooth()
            assign(w, M["tire"]); w.parent = root
            bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.22, depth=0.32,
                                                location=w.location, rotation=(0, math.pi / 2, 0))
            r = bpy.context.object; assign(r, rim_m); r.parent = w
            r.matrix_parent_inverse = w.matrix_world.inverted()
            wheels.append(w)
    return root, wheels

def rig(name, keys, lane_keys=None):
    """Empty that rides the road path. keys: [(frame, offset_factor)]"""
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    c = e.constraints.new('FOLLOW_PATH'); c.target = path
    c.use_fixed_location = True; c.use_curve_follow = True; c.forward_axis = 'FORWARD_Y'
    for f, v in keys:
        c.offset_factor = v; c.keyframe_insert("offset_factor", frame=f)
    return e

def lane(obj, keys, yaw_scale=0.06):
    """Lateral weave: keys [(frame, x)]. Adds a little yaw toward the direction of the move."""
    prev = None
    for f, x in keys:
        obj.location.x = x; obj.keyframe_insert("location", index=0, frame=f)
        yaw = 0 if prev is None else -(x - prev) * yaw_scale
        obj.rotation_euler.z = yaw; obj.keyframe_insert("rotation_euler", index=2, frame=f)
        prev = x

# ---------- motion: integrated speed profiles + simple vehicle dynamics ----------
T = [i / FPS for i in range(END)]              # t for frame i+1
dt = 1.0 / FPS
def g(t, c, w): return math.exp(-((t - c) / w) ** 2)
def v_lead(t):  return 40 + 0.25 * t - 5 * g(t, 6.5, 0.5) - 6 * g(t, 11.8, 0.5) + 3 * g(t, 13.5, 0.6) - 6 * g(t, 15.9, 0.5) + 4 * g(t, 18.3, 0.7)
def v_chase(t): return 40.7 + 0.25 * t - 4 * g(t, 6.9, 0.5) - 3 * g(t, 12.2, 0.5) + 2 * g(t, 14.6, 0.5) - 7 * g(t, 16.4, 0.45) + 1 * g(t, 18.8, 0.6)
def integrate(v, s0):
    out, sv = [], s0
    for t in T: out.append(sv); sv += v(t) * dt
    return out
lead_m0, chase_m0 = 60.0, 36.0
S_lead, S_chase = integrate(v_lead, lead_m0), integrate(v_chase, chase_m0)

# road heading/curvature lookup by distance
cum = [0.0]
for i in range(1, len(samples)): cum.append(cum[-1] + (samples[i] - samples[i - 1]).length)
head = [math.atan2(samples[min(i + 1, len(samples) - 1)].y - samples[max(i - 1, 0)].y,
                   samples[min(i + 1, len(samples) - 1)].x - samples[max(i - 1, 0)].x) for i in range(len(samples))]
def curvature(sd):
    import bisect
    i = min(max(bisect.bisect(cum, sd), 2), len(cum) - 3)
    dth = (head[i + 1] - head[i - 1] + math.pi) % (2 * math.pi) - math.pi
    return dth / max(cum[i + 1] - cum[i - 1], 1e-3)      # +ve = left turn

def smooth_keys(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (t0, x0), (t1, x1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0); u = u * u * (3 - 2 * u)
            return x0 + (x1 - x0) * u
    return keys[-1][1]

random.seed(11)
def wobble(t, amp, freqs, seed):
    r = random.Random(seed); out = 0.0
    for f in freqs: out += amp * math.sin(2 * math.pi * f * t + r.uniform(0, 6.28)) / len(freqs)
    return out

def length_(): return length
def f2o(m): return m / length

LAT = {}
def drive(rig_obj, body, wheels, S, v, lanes, seed):
    c = rig_obj.constraints[0]
    X = [smooth_keys(lanes, t) for t in T]
    LAT[body.name] = X
    for i, t in enumerate(T):
        f = i + 1
        c.offset_factor = f2o(S[i]); c.keyframe_insert("offset_factor", frame=f)
        xm, x0, xp = X[max(i - 1, 0)], X[i], X[min(i + 1, END - 1)]
        vx = (xp - xm) / (2 * dt); ax = (xp - 2 * x0 + xm) / dt ** 2
        vt = v(t); acc = (v(t + dt) - v(t - dt)) / (2 * dt)
        k = curvature(S[i])
        a_left = vt * vt * k - ax                       # lateral accel toward the left
        slip = max(-0.14, min(0.14, 0.0022 * a_left))   # rear steps out: nose points further into the turn
        body.location.x = x0 + wobble(t, 0.05, (0.3, 0.7), seed)
        body.location.z = abs(wobble(t, 0.03, (2.1, 3.7, 5.3), seed + 1)) + 0.012 * (i % 7 == 0)
        body.rotation_euler.z = -math.atan2(vx, vt) + slip
        body.rotation_euler.y = max(-0.07, min(0.07, 0.0045 * a_left)) + wobble(t, 0.006, (1.5, 2.9), seed + 2)
        body.rotation_euler.x = max(-0.05, min(0.05, 0.004 * acc)) + wobble(t, 0.005, (1.2, 2.3), seed + 3)
        body.keyframe_insert("location", frame=f); body.keyframe_insert("rotation_euler", frame=f)
        for w in wheels:
            w.rotation_euler = (-(S[i] - S[0]) / 0.36, math.pi / 2, 0); w.keyframe_insert("rotation_euler", index=0, frame=f)

lead_rig = rig("LeadRig", [(1, f2o(lead_m0))])
chase_rig = rig("ChaseRig", [(1, f2o(chase_m0))])
lead, lw = car("LeadCar", M["grey"], "fastback"); lead.parent = lead_rig
chaser, cw = car("ChaseCar", M["blue"], "coupe"); chaser.parent = chase_rig
LEAD_LANES = [(0, 2.2), (3, 2.3), (5, -1.6), (6.5, -2.0), (8, 1.6), (10, 2.2), (12, -1.0), (13.5, -2.2), (15.2, -0.8), (16.5, -2.3), (18, 1.5), (20, 2.0)]
CHASE_LANES = [(0, 2.0), (4, 2.0), (5.6, -1.8), (7, -1.4), (8.6, 1.4), (10.3, 2.0), (12.4, -1.4), (13.8, 1.2), (15, -1.8), (16, -1.9), (17, 1.3), (18.5, -1.0), (20, -1.5)]
drive(lead_rig, lead, lw, S_lead, v_lead, LEAD_LANES, 100)
drive(chase_rig, chaser, cw, S_chase, v_chase, CHASE_LANES, 200)
gaps = [a_ - b_ for a_, b_ in zip(S_lead, S_chase)]
print("gap min/max", round(min(gaps), 1), round(max(gaps), 1), "path", round(length), "end", round(S_lead[-1]))

# dust trail: particle emitters behind each car
def dust(root, y):
    bpy.ops.mesh.primitive_plane_add(size=1.8, location=(0, y, 0.15))
    em = bpy.context.object; em.parent = root; em.name = root.name + "_dust"
    em.hide_render = False
    ps = em.modifiers.new("dust", "PARTICLE_SYSTEM").particle_system.settings
    ps.count = 1500; ps.frame_start = 1; ps.frame_end = END; ps.lifetime = 30
    ps.normal_factor = 0.8; ps.factor_random = 1.2; ps.effector_weights.gravity = -0.02
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.6, location=(0, 0, -50))
    puff = bpy.context.object; puff.name = "puff"; assign(puff, M["dust"])
    ps.render_type = 'OBJECT'; ps.instance_object = puff; ps.particle_size = 1.0; ps.size_random = 0.7
    em.show_instancer_for_render = False
    # dust material slightly transparent-ish via low alpha

# ---------- cameras (3 shots, cut via markers) ----------
def camera(name, parent, loc, rot_deg, lens):
    cam = bpy.data.cameras.new(name); cam.lens = lens
    cam.dof.use_dof = False
    o = bpy.data.objects.new(name, cam); sc.collection.objects.link(o)
    o.parent = parent; o.location = loc; o.rotation_euler = [math.radians(a) for a in rot_deg]
    return o

from mathutils import Euler
def look_rot(pos, target, roll_deg):
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat('-Z', 'Y')
    q = q @ Euler((0, 0, math.radians(roll_deg))).to_quaternion()
    return q.to_euler()

def beat_env(t):
    """0..1 kick that fires on every beat and decays fast (drives zoom punch + shake spikes)."""
    if t < BEAT0: return 0.0
    ph = ((t - BEAT0) % BEAT) / BEAT
    return math.exp(-ph * 9)

SHOTS = []   # (start_frame, cam)
def shot(name, parent, b0, b1, lens, fn, shake=1.0, lat=None, punch=1.0):
    """fn(u, t) -> (local_pos, local_target, roll_deg). u = 0..1 through the shot."""
    cam = camera(name, parent, (0, 0, 0), (0, 0, 0), lens)
    f0 = max(1, round(bt(b0) * FPS) + 1); f1 = min(END, round(bt(b1) * FPS) + 1)
    for f in range(max(1, f0 - 1), min(END, f1 + 1) + 1):
        t = (f - 1) / FPS; u = min(max((f - f0) / max(f1 - f0, 1), 0), 1)
        pos, tgt, roll = fn(u, t)
        if lat is not None:
            li = lat[min(f - 1, END - 1)]; pos = (pos[0] + li, pos[1], pos[2]); tgt = (tgt[0] + li, tgt[1], tgt[2])
        k = beat_env(t) * punch
        amp = shake * (1 + 2.2 * k)
        pos = Vector(pos) + Vector((wobble(t, 0.05 * amp, (3.1, 4.7, 6.3), f0), wobble(t, 0.04 * amp, (2.5, 5.2), f0 + 1), wobble(t, 0.06 * amp, (3.7, 5.9, 7.7), f0 + 2)))
        roll += wobble(t, 0.8 * amp, (1.3, 2.9), f0 + 3)
        tgt = Vector(tgt) + Vector((wobble(t, 0.12 * amp, (1.7, 4.1), f0 + 4), 0, wobble(t, 0.1 * amp, (2.3, 5.3), f0 + 5)))
        cam.location = pos; cam.rotation_euler = look_rot(pos, tgt, roll)
        cam.data.lens = lens * (1 - 0.14 * k)                       # zoom punch on the beat
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
    SHOTS.append((f0, cam))
    return cam

# a rig that rides between the two cars, for the orbit / drone shots
S_mid = [(a_ + b_) / 2 for a_, b_ in zip(S_lead, S_chase)]
mid_rig = rig("MidRig", [(1, f2o(S_mid[0]))])
for i in range(END):
    mid_rig.constraints[0].offset_factor = f2o(S_mid[i]); mid_rig.constraints[0].keyframe_insert("offset_factor", frame=i + 1)
def lead_off(i): return (S_lead[i] - S_mid[i])      # lead car's y in mid-rig space
def sm(u): return u * u * (3 - 2 * u)
def fi(t): return min(END - 1, max(0, int(round(t * FPS))))

LAT_MID = [(a_ + b_) / 2 for a_, b_ in zip(LAT["LeadCar"], LAT["ChaseCar"])]
DROP1, DROP2, CHASE = 8, 16, 24          # beat indices of the two drops and the chase start
# build-up (0 -> drop 1): slow high establishing drone, cars approaching, almost no shake
shot("00_Establish_Drone", mid_rig, -2, DROP1, 26,
     lambda u, t: ((-25 + 12 * sm(u), 70 - 45 * sm(u), 38 - 20 * sm(u)), (0, 0, 0), -4 + 6 * u), shake=0.25, lat=LAT_MID, punch=0.2)
# drop 1: NFS chase cam behind the lead car, swaying side to side with a dutch tilt
shot("01_ChaseCam_Lead", lead_rig, DROP1, DROP2, 22,
     lambda u, t: ((1.8 * math.sin(2 * math.pi * 0.75 * u), -7.8 + 1.8 * u, 1.7 - 0.3 * u), (0, 6, 0.8), -7 * math.sin(2 * math.pi * 0.75 * u)), lat=LAT["LeadCar"])
# drop 2: hard cut behind the chaser, low and aggressive, swinging the other way
shot("02_ChaseCam_Chaser", chase_rig, DROP2, CHASE, 22,
     lambda u, t: ((-1.6 * math.sin(2 * math.pi * 0.75 * u), -7.2 + 1.6 * u, 1.3), (0, 12, 0.9), 7 * math.sin(2 * math.pi * 0.75 * u)), lat=LAT["ChaseCar"])
# chase: new angle every bar (4 beats)
def orbit(u, t):
    th = math.radians(-150 + 220 * sm(u)); Rx = 12 - 4 * math.sin(math.pi * u); Ry = 24 - 3 * math.sin(math.pi * u); h = 2.8 - 1.2 * math.sin(math.pi * u)
    return ((Rx * math.sin(th), Ry * math.cos(th), h), (0, 0, 0.8), 10 * math.sin(2 * math.pi * u))
shot("03_Swirl_Orbit", mid_rig, CHASE, CHASE + 4, 20, orbit, lat=LAT_MID)
shot("04_FrontTrack_LookBack", lead_rig, CHASE + 4, CHASE + 8, 30,
     lambda u, t: ((1.8 - 1.2 * u, 11 - 2 * u, 0.55), (0, -9, 1.0), 3 * math.sin(math.pi * u)), lat=LAT["LeadCar"])
shot("05_SideTrack_Pass", chase_rig, CHASE + 8, CHASE + 12, 24,
     lambda u, t: ((-7 + 1.5 * u, 3 + 4 * u, 1.0), (0, 5, 0.8), -4 + 6 * u), lat=LAT["ChaseCar"])
shot("06_Bumper_LookBack", lead, CHASE + 12, CHASE + 16, 26,
     lambda u, t: ((0, -3.4, 1.05), (0, -20, 1.2), 0), shake=0.7)
nb = int((SECONDS - BEAT0) / BEAT) + 1
def finale(u, t):
    th = math.radians(20 + 270 * sm(u)); Rx = 9 + 14 * u; Ry = 22 + 10 * u; h = 1.4 + 6 * u
    return ((Rx * math.sin(th), Ry * math.cos(th), h), (0, 0, 0.8), -8 * math.sin(2 * math.pi * u))
shot("07_Swirl_Finale", mid_rig, CHASE + 16, nb, 20, finale, lat=LAT_MID)

for f, cam in SHOTS:
    mk = sc.timeline_markers.new(cam.name, frame=f); mk.camera = cam
sc.camera = SHOTS[0][1]
print("shots", [(f, c.name) for f, c in SHOTS], "beats", nb)

def all_fcurves():
    for a in bpy.data.actions:
        if hasattr(a, "layers") and len(a.layers):
            for L in a.layers:
                for st in L.strips:
                    for cb in st.channelbags:
                        yield from cb.fcurves
        elif hasattr(a, "fcurves"):
            yield from a.fcurves
n = 0
for fc in all_fcurves():
    n += len(fc.keyframe_points)
print("linearized keys", n)

# ---------- light & world ----------
world = bpy.data.worlds.new("Sky"); sc.world = world; world.use_nodes = True
nt = world.node_tree; bg = nt.nodes["Background"]
sky = nt.nodes.new("ShaderNodeTexSky")
for t in ("NISHITA", "SINGLE_SCATTERING", "MULTIPLE_SCATTERING"):
    try:
        sky.sky_type = t; break
    except TypeError:
        pass
try:
    sky.sun_elevation = math.radians(9); sky.sun_rotation = math.radians(200)
    sky.air_density = 1.2; sky.dust_density = 3.0
except AttributeError:
    pass
nt.links.new(sky.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.35
sun = bpy.data.lights.new("Sun", "SUN"); sun.energy = 4.5; sun.color = (1, 0.72, 0.45); sun.angle = math.radians(1.5)
so = bpy.data.objects.new("Sun", sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(81), 0, math.radians(200 - 180))

# ---------- render ----------
ENGINE = os.environ.get("ENGINE", "EEVEE")
sc.render.engine = 'CYCLES'
try:    # GPU for Cycles: Metal on macOS, else whatever the machine offers; EEVEE (the default below) does not need this
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try: prefs.compute_device_type = dev; break
        except TypeError: pass
    prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print("cycles GPU setup skipped:", e)
sc.cycles.samples = 16 if MODE == "preview" else 64
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = (1280, 720)
sc.render.resolution_percentage = 75 if MODE == "preview" else 100
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except TypeError: pass
sc.render.image_settings.file_format = 'PNG'
if ENGINE == "EEVEE":
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = 16
    try: sc.eevee.use_shadows = True; sc.eevee.use_raytracing = True
    except AttributeError: pass
    sc.render.resolution_percentage = 100

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "chase.blend"))
if MODE == "stills":
    for f in (30, 120, 200):
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"still_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
elif MODE in ("preview", "final"):
    sc.render.filepath = os.path.join(OUT, "frames", "f_")
    bpy.ops.render.render(animation=True)
