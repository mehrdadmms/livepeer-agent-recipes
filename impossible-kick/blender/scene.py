"""The impossible kick - builds the whole scene headless.
usage: blender -b -P blender/scene.py -- [--part kick|all] [--save blender/scene.blend]
Coordinates: metres, +Y is the direction of the kick and of the whole flight, +Z up.
"""
import bpy, bmesh, math, random, os, sys
import numpy as np
from mathutils import Vector, Euler, Matrix, Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from lib import _mesh_obj

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
PART = argv[argv.index('--part')+1] if '--part' in argv else 'all'
SAVE = argv[argv.index('--save')+1] if '--save' in argv else None
random.seed(8); rng = np.random.default_rng(8)

FPS, F0, F1 = 24, 0, 719
HOOK = 96      # v2: strike lands at exactly 4.000 s
OLD_HOOK = 72  # v1 timing; old frame numbers are mapped through T()

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS; sc.frame_start = F0; sc.frame_end = F1
sc.render.resolution_x = 540; sc.render.resolution_y = 960

# ------------------------------------------------------------------ can flight path (frame -> metres)
CAN_KEYS_OLD = [
 (72,(0.0,0.30,0.075)),(74,(-0.10,0.95,1.9)),(77,(-0.35,1.9,4.6)),(80,(-0.65,3.0,7.2)),(83,(-0.5,4.3,9.8)),
 (86,(-0.1,5.7,12.3)),(89,(0.3,7.2,14.9)),(92,(0.4,8.8,17.6)),(96,(0.2,12.5,21.5)),(100,(0.0,19,22.0)),
 (103,(0.0,24,16.5)),(105,(0.0,28,11.5)),(107,(0.0,31.0,8.6)),(108.5,(0.05,32.5,7.8)),(110,(0.1,34.4,7.35)),
 (111.5,(0.4,36.6,7.5)),(113,(0.6,40,7.0)),(114,(0.9,42,5.0)),(118,(0.7,52,3.4)),(124,(-0.4,68,2.9)),
 (130,(0.4,88,2.6)),(134,(0.0,102,3.0)),(138,(0,116,8)),(144,(0,140,27)),(150,(0,170,41)),(154,(0,192,38)),
 (160,(0.6,226,27)),(166,(1.6,258,15)),(172,(2.6,288,6.5)),]
# old (v1, 8 s) frame -> v2 frame. The route is the same but flown 3-4x slower so near misses can be read.
T_KNOTS = [(0, 0), (72, 96), (100, 168), (107, 222), (113, 246), (138, 372), (154, 480), (160, 520), (166, 548), (172, 575), (300, 575+128*3)]
def T(f):
    for (a0, b0), (a1, b1) in zip(T_KNOTS[:-1], T_KNOTS[1:]):
        if f <= a1: return b0 + (f-a0)*(b1-b0)/(a1-a0)
    return T_KNOTS[-1][1]
CAN_KEYS = [(T(f), p) for f, p in CAN_KEYS_OLD]
# ---- ending B: dipping shot hits the underside of the crossbar (ring), drops into the net, bulge pocket holds the can
GX, GY = 3.66, 310.0                       # goal half-width, goal line y
POCKET_X, POCKET_Z = 1.8, 0.95             # where the net bulges (matches scene_far net shape key)
BULGE_KEYS = [(0, 0.0), (617, 0.0), (620.5, 1.0), (624, 0.72), (628, 0.55), (634, 0.70), (650, 0.60), (719, 0.60)]
def bulge(f):
    for (a0, b0), (a1, b1) in zip(BULGE_KEYS[:-1], BULGE_KEYS[1:]):
        if f <= a1: return b0 + (f-a0)*(b1-b0)/(a1-a0)
    return BULGE_KEYS[-1][1]
NET_BACK_Y = GY+0.80+1.20*(1-POCKET_Z/2.44)
def pocket_pos(f): return (POCKET_X, NET_BACK_Y+0.95*bulge(f)-0.13, POCKET_Z-0.05*min(1, max(0, (f-620)/60.0)))
CAN_KEYS += [(590, (2.0, 300.0, 3.9)), (598, (1.75, 306.5, 3.05)), (604, (1.6, 309.3, 2.56)), (606, (1.65, 309.92, 2.42)), (608, (1.72, 310.1, 2.22)),
             (612, (1.78, 310.55, 1.6)), (616, (1.80, 311.0, 1.15)), (618, (1.81, NET_BACK_Y-0.05, 0.98))]
CAN_KEYS += [(f, pocket_pos(f)) for f in (621, 624, 628, 634, 642, 655, 680, 719)]
CAN = hermite_path(CAN_KEYS)
def can_pos(f):
    f = max(HOOK, f); return Vector(CAN(f))

# ------------------------------------------------------------------ juggling (0-4 s): analytic can motion
G = 9.81
CR = 0.033
JUG_SEGS = [(-9, 0.34, 5, 0.34), (5, 0.34, 19, 0.34), (19, 0.34, 33, 0.34), (33, 0.34, 47, 0.34), (47, 0.34, 60, 0.34)]
FLICK_T0, FLICK_T1, FLICK_Z0, FLICK_Z1 = 60, 95.3, 0.34, 0.061
TAP_FRAMES = [-9, 5, 19, 33, 47]
def _v0(t0, z0, t1, z1):
    T = (t1-t0)/FPS; return (z1-z0+0.5*G*T*T)/T
V_FLICK = _v0(FLICK_T0, FLICK_Z0, FLICK_T1, FLICK_Z1)
def jug_z(f):
    for (t0, z0, t1, z1) in JUG_SEGS:
        if f < t1: dt = (f-t0)/FPS; return z0 + _v0(t0, z0, t1, z1)*dt - 0.5*G*dt*dt
    if f < FLICK_T1: dt = (f-FLICK_T0)/FPS; return FLICK_Z0 + V_FLICK*dt - 0.5*G*dt*dt
    vd = V_FLICK - G*(FLICK_T1-FLICK_T0)/FPS; dt = (f-FLICK_T1)/FPS      # bounce, restitution 0.38
    return max(FLICK_Z1, FLICK_Z1 + 0.38*(-vd)*dt - 0.5*G*dt*dt)
def jug_xy(f):
    u = min(1.0, max(0.0, (f-FLICK_T0)/(FLICK_T1-FLICK_T0)))
    bx = 0.05+0.035*math.sin(f*0.23); by = 0.03+0.03*math.cos(f*0.31)
    return (bx*(1-u)+0.0*u, by*(1-u)+0.30*u)
def jug_pos(f):
    x, y = jug_xy(f); return Vector((x, y, jug_z(f)))

# ------------------------------------------------------------------ world / lighting
def build_world():
    w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI+'belfast_sunset_puresky_2k.hdr')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(-37))
    tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Generated'], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.55
    nt.links.new(env.outputs[0], bg.inputs[0])
    o = nt.nodes.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], o.inputs[0])
    for f_, v_ in ((0, 0.55), (250, 0.55), (470, 0.5), (570, 0.22), (719, 0.22)):
        bg.inputs['Strength'].default_value = v_; bg.inputs['Strength'].keyframe_insert('default_value', frame=f_)

def light(kind, name, loc, energy, color=(1,1,1), size=0.2, rot=None, spot=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == 'SUN': pass
    elif kind == 'AREA': ld.size = size
    elif kind == 'POINT': ld.shadow_soft_size = size
    elif kind == 'SPOT': ld.shadow_soft_size = size; ld.spot_size = math.radians(spot or 60); ld.spot_blend = 0.4
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob); ob.location = loc
    if rot: ob.rotation_euler = rot
    return ob

def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

# ------------------------------------------------------------------ materials
M = {}
def make_materials():
    M['cobble'] = pbr('cobble', 'cobblestone_floor_04', tile=1.4, rough_mul=1.0, nstr=1.5, dirt=0.6, damp=0.3, moss=0.5)
    M['brick'] = pbr('brick', 'brick_wall_005', tile=2.4, dirt=0.85, nstr=1.6, streak=0.85, damp=0.9, damp_h=1.3, moss=0.25)
    M['plaster'] = pbr('plaster', 'beige_wall_001', tile=2.5, tint=(0.75, 0.62, 0.5, 1), tint_amt=0.6, dirt=0.95, streak=0.8, damp=0.8, damp_h=1.1)
    M['concrete'] = pbr('concrete', 'concrete_wall_008', tile=3.0, dirt=0.9, streak=0.6, damp=0.7, damp_h=0.7)
    M['tin'] = pbr('tin', 'corrugated_iron_02', tile=2.0, metal=1.0, dirt=0.7)
    M['rust'] = pbr('rust', 'rusty_metal_02', tile=1.5, metal=1.0, dirt=0.3)
    M['wood'] = pbr('wood', 'worn_planks', tile=1.2, dirt=0.5)
    M['asphalt'] = pbr('asphalt', 'asphalt_02', tile=3.0, dirt=0.5)
    M['grass'] = pbr('grass', 'grass_path_2', tile=3.0, dirt=0.1)
    M['glass_dark'] = simple('glass_dark', (0.02, 0.03, 0.05), rough=0.05, metal=0.0, extra={'Coat Weight': 0.0})
    M['frame'] = simple('frame', (0.15, 0.22, 0.2), rough=0.55)
    M['frame2'] = simple('frame2', (0.35, 0.14, 0.1), rough=0.6)
    M['pants'] = simple('pants', (0.02, 0.03, 0.07), rough=0.85, extra={'Sheen Weight': 0.1})
    nt = M['pants'].node_tree; bs = nt.nodes['Principled BSDF']
    tcn = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900; nz.inputs['Detail'].default_value = 2
    nt.links.new(tcn.outputs['Object'], nz.inputs[0]); bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; bp.inputs['Distance'].default_value = 0.002
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], bs.inputs['Normal'])
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 14; nz2.inputs['Detail'].default_value = 4
    nt.links.new(tcn.outputs['Object'], nz2.inputs[0])
    M['black'] = simple('black', (0.015, 0.015, 0.015), rough=0.7)
    M['bag'] = simple('bag', (0.01, 0.01, 0.012), rough=0.25)
    M['cardboard'] = simple('cardboard', (0.42, 0.3, 0.18), rough=0.9)
    M['warm'] = emission('warm', (1.0, 0.62, 0.28), 60)
    M['warm_lo'] = emission('warm_lo', (1.0, 0.7, 0.4), 12)
    # facade: lit-window atlas x plaster PBR, per-building random offset + tint (world-space tri-planar)
    m = bpy.data.materials.new('facade'); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    pos = nt.nodes.new('ShaderNodeNewGeometry'); oi = nt.nodes.new('ShaderNodeObjectInfo')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1/13.0,)*3
    offs = nt.nodes.new('ShaderNodeVectorMath'); offs.operation = 'MULTIPLY'; offs.inputs[1].default_value = (7.3, 5.1, 3.7)
    rv = nt.nodes.new('ShaderNodeCombineXYZ')
    for i in range(3): nt.links.new(oi.outputs['Random'], rv.inputs[i])
    nt.links.new(rv.outputs[0], offs.inputs[0]); nt.links.new(offs.outputs[0], mp.inputs['Location'])
    nt.links.new(pos.outputs['Position'], mp.inputs[0])
    d = nt.nodes.new('ShaderNodeTexImage'); d.image = bpy.data.images.load(TEX+'facade_diff.png'); d.projection = 'BOX'; d.projection_blend = 0.05
    e = nt.nodes.new('ShaderNodeTexImage'); e.image = bpy.data.images.load(TEX+'facade_emit.png'); e.projection = 'BOX'; e.projection_blend = 0.05
    for n in (d, e): nt.links.new(mp.outputs[0], n.inputs[0])
    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1/3.0,)*3; nt.links.new(pos.outputs['Position'], mp2.inputs[0])
    pd = nt.nodes.new('ShaderNodeTexImage'); pd.image = bpy.data.images.load(TEX+'beige_wall_001_diff_1k.jpg'); pd.projection = 'BOX'; pd.projection_blend = 0.1
    pn = nt.nodes.new('ShaderNodeTexImage'); pn.image = bpy.data.images.load(TEX+'beige_wall_001_nor_1k.jpg'); pn.image.colorspace_settings.name = 'Non-Color'; pn.projection = 'BOX'; pn.projection_blend = 0.1
    for n in (pd, pn): nt.links.new(mp2.outputs[0], n.inputs[0])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(pn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    c1 = mix(nt, d.outputs[0], pd.outputs[0], 1.0, 'MULTIPLY')
    tintv = nt.nodes.new('ShaderNodeMapRange'); tintv.inputs[3].default_value = 0.45; tintv.inputs[4].default_value = 1.15
    nt.links.new(oi.outputs['Random'], tintv.inputs[0])
    tcol = nt.nodes.new('ShaderNodeCombineColor'); 
    for i in range(3): pass
    nt.links.new(tintv.outputs[0], tcol.inputs[0]); nt.links.new(tintv.outputs[0], tcol.inputs[1]); nt.links.new(tintv.outputs[0], tcol.inputs[2])
    c2 = mix(nt, c1, tcol.outputs[0], 1.0, 'MULTIPLY')
    nt.links.new(c2, bs.inputs['Base Color']); nt.links.new(e.outputs[0], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = 2.6; bs.inputs['Roughness'].default_value = 0.9
    M['facade'] = m

# ------------------------------------------------------------------ the can
def build_can():
    Rb, H = 0.033, 0.122
    N, R = 72, 44
    prof = []   # (z, r) bottom -> top
    for j in range(R+1):
        t = j/R; z = t*H
        if z < 0.006: r = Rb*0.80 + (z/0.006)*Rb*0.10
        elif z < 0.010: r = Rb*0.90 + (z-0.006)/0.004*Rb*0.10
        elif z < H-0.022: r = Rb
        elif z < H-0.006: r = Rb - (z-(H-0.022))/0.016*0.0055
        else: r = Rb - 0.0055 - (z-(H-0.006))/0.006*0.0012
        prof.append((z, r))
    # base dents (already beaten up) + the kick dent as a shape key
    dents = [(0.6*math.pi, 0.075, 0.020, 0.0035), (1.4*math.pi, 0.050, 0.016, 0.0028), (0.15*math.pi, 0.095, 0.012, 0.0022)]
    kick_dent = (math.radians(255), 0.045, 0.024, 0.0105)   # (angle, z, radius, depth): facing the incoming boot (-Y side is 270deg)
    bm = bmesh.new(); grid = []
    for j in range(R+1):
        row = []
        for i in range(N+1):
            a = 2*math.pi*i/N; z, r = prof[j]
            rr = r
            for (da, dz, dr, dd) in dents:
                dist = math.hypot(min(abs(a-da), 2*math.pi-abs(a-da))*Rb, z-dz)
                rr -= dd*math.exp(-(dist/dr)**2)
            rr += 0.0003*math.sin(a*9+z*140)  # slight crumple
            row.append(bm.verts.new((rr*math.cos(a), rr*math.sin(a), z)))
        grid.append(row)
    uvl = bm.loops.layers.uv.new('UV')
    for j in range(R):
        for i in range(N):
            f = bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i])); f.smooth = True
            zc = (prof[j][0]+prof[j+1][0])/2
            f.material_index = 0 if 0.011 < zc < 0.106 else 1
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i+1, j), (i+1, j+1), (i, j+1))):
                lp[uvl].uv = (ii/N, (prof[jj][0]-0.011)/(0.106-0.011))
    # lid (concave) + base
    for top in (True, False):
        row = grid[-1] if top else grid[0]; z = H if top else 0.0
        cz = z + (-0.0035 if top else 0.004)
        c = bm.verts.new((0, 0, cz))
        for i in range(N):
            f = bm.faces.new((row[i+1], row[i], c) if top else (row[i], row[i+1], c)); f.smooth = True; f.material_index = 1
    me = bpy.data.meshes.new('can'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('can', me); sc.collection.objects.link(ob)
    # materials: printed label, bare aluminium
    lab = bpy.data.materials.new('can_label'); lab.use_nodes = True; nt = lab.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(TEX+'can_label.png'); t.extension = 'REPEAT'
    tc = nt.nodes.new('ShaderNodeUVMap'); nt.links.new(tc.outputs[0], t.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 6
    nt.links.new(nt.nodes.new('ShaderNodeNewGeometry').outputs['Position'], nz.inputs[0]) if False else None
    scuff = mix(nt, t.outputs[0], (0.55, 0.55, 0.57, 1), 0.0)
    nt.links.new(t.outputs[0], bs.inputs['Base Color'])
    bs.inputs['Metallic'].default_value = 0.35; bs.inputs['Roughness'].default_value = 0.28
    bs.inputs['Coat Weight'].default_value = 0.6; bs.inputs['Coat Roughness'].default_value = 0.08
    alu = bpy.data.materials.new('can_alu'); alu.use_nodes = True; b2 = alu.node_tree.nodes['Principled BSDF']
    b2.inputs['Base Color'].default_value = (0.72, 0.72, 0.74, 1); b2.inputs['Metallic'].default_value = 1.0; b2.inputs['Roughness'].default_value = 0.22
    ob.data.materials.append(lab); ob.data.materials.append(alu)
    # kick dent shape key
    ob.shape_key_add(name='Basis')
    sk = ob.shape_key_add(name='kick_dent')
    da, dz, dr, dd = kick_dent
    for k, v in enumerate(me.vertices):
        a = math.atan2(v.co.y, v.co.x) % (2*math.pi); z = v.co.z
        dist = math.hypot(min(abs(a-da), 2*math.pi-abs(a-da))*Rb, z-dz)
        pull = dd*math.exp(-(dist/dr)**2)
        rr = math.hypot(v.co.x, v.co.y)
        if rr > 1e-6:
            s = (rr-pull)/rr; sk.data[k].co = Vector((v.co.x*s, v.co.y*s, z))
    sk.value = 0
    ob.rotation_mode = 'XYZ'
    return ob

# ------------------------------------------------------------------ helpers for the alley
def wall_windows(x_face, sgn, y0, y1, zs, wall_mat_name):
    """windows on an alley wall; sgn=+1 wall on +x side (window faces -x)."""
    n = 0
    for y in np.arange(y0, y1, 3.1):
        for z in zs:
            if random.random() < 0.15: continue
            cx = x_face
            w, h = 0.9, 1.5
            box(f'win_g{n}', (cx-sgn*0.01, y, z), (0.04, w, h), M['glass_dark'])
            fr = M['frame'] if random.random() < 0.6 else M['frame2']
            box(f'win_fT{n}', (cx-sgn*0.05, y, z+h/2+0.05), (0.1, w+0.2, 0.1), fr)
            box(f'win_fB{n}', (cx-sgn*0.12, y, z-h/2-0.05), (0.25, w+0.3, 0.09), M['concrete'])   # sill
            box(f'win_fL{n}', (cx-sgn*0.05, y-w/2-0.05, z), (0.1, 0.1, h+0.2), fr)
            box(f'win_fR{n}', (cx-sgn*0.05, y+w/2+0.05, z), (0.1, 0.1, h+0.2), fr)
            box(f'win_bar{n}', (cx-sgn*0.04, y, z), (0.05, 0.04, h), fr)
            # some lit windows, some with open shutters
            if random.random() < 0.3:
                g = box(f'win_lit{n}', (cx-sgn*0.005, y, z), (0.03, w*0.9, h*0.9), M['warm_lo'])
            if random.random() < 0.5:
                sh = box(f'shutter{n}', (cx-sgn*0.45, y+w/2+0.35, z), (0.04, 0.5, h+0.1), M['frame2'], rot=(0, 0, sgn*math.radians(random.uniform(30, 80))))
            n += 1

def cloth(name, center, size, color, nseg=10, sway=0.05, wave=0.03, rot=(0, 0, 0)):
    ob = grid_plane(name, size, nseg, nseg, simple(f'cl_{name}', color, rough=0.9, extra={'Sheen Weight': 0.6}), center=center, rot=rot)
    for p in ob.data.polygons: p.use_smooth = True
    wv = ob.modifiers.new('wave', 'WAVE'); wv.height = wave; wv.width = 0.35; wv.narrowness = 3; wv.speed = 0.09
    wv.time_offset = random.uniform(0, 40); wv.use_normal = True
    return ob

# ------------------------------------------------------------------ the alley
def build_alley():
    Ly0, Ly1 = -9.0, 14.0
    # ground
    g = box('ground', (0, (Ly0+Ly1)/2, -0.5), (3.0, Ly1-Ly0, 1.0), M['cobble'])
    box('gutterL', (-1.32, (Ly0+Ly1)/2, -0.02), (0.2, Ly1-Ly0, 0.05), M['concrete'])
    box('gutterR', (1.32, (Ly0+Ly1)/2, -0.02), (0.2, Ly1-Ly0, 0.05), M['concrete'])
    # walls (left = brick, right = plaster) - tall so the alley reads as a canyon
    left = box('wallL', (-1.5-3.5, (Ly0+Ly1)/2, 6.5), (7, Ly1-Ly0, 13.0), M['brick'])
    right = box('wallR', (1.5+3.5, (Ly0+Ly1)/2, 7.25), (7, Ly1-Ly0, 14.5), M['plaster'])
    for ob in (left, right):
        b = ob.modifiers.new('bv', 'BEVEL'); b.width = 0.05; b.segments = 1
    # skirting wear on walls, drain pipes, cables, AC units
    box('skirtL', (-1.46, (Ly0+Ly1)/2, 0.25), (0.08, Ly1-Ly0, 0.5), M['concrete'])
    box('skirtR', (1.46, (Ly0+Ly1)/2, 0.25), (0.08, Ly1-Ly0, 0.5), M['concrete'])
    wall_windows(-1.5, -1, -8, 13, [3.2, 6.6, 10.0], 'brick')
    wall_windows(1.5, +1, -7, 13, [3.6, 7.1, 10.6], 'plaster')
    for k, y in enumerate((-2.6, 3.9, 10.7)):
        cyl(f'pipeL{k}', (-1.42, y, 6.5), 0.055, 13.0, M['rust'], seg=12)
        cyl(f'pipeR{k}', (1.42, y+1.2, 7.0), 0.05, 14.0, M['tin'], seg=12)
    for k, (y, z) in enumerate(((-3.6, 4.8), (6.3, 8.4))):
        box(f'ac{k}', (1.38, y, z), (0.5, 0.75, 0.45), M['concrete'], bevel=0.03)
        cyl(f'acfan{k}', (1.1, y, z), 0.17, 0.05, M['black'], seg=24, rot=(0, math.pi/2, 0))
    # cables across the alley
    for k, (y, z0, z1) in enumerate(((-4.5, 7.0, 7.8), (0.4, 6.5, 6.9), (11.5, 11.8, 12.3))):
        pts = [(-1.5+t*3.0, y, (z0+(z1-z0)*t) - 0.25*math.sin(math.pi*t)) for t in np.linspace(0, 1, 14)]
        crv = bpy.data.curves.new(f'cable{k}', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.006; crv.bevel_resolution = 2
        sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p, q in zip(sp.points, pts): p.co = (*q, 1)
        co = bpy.data.objects.new(f'cable{k}', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
    # ---- clutter at ground level
    for k, (x, y) in enumerate(((1.15, 1.4), (1.2, 2.2), (1.05, -2.8), (-1.2, -1.6), (-1.15, 3.5), (1.0, 6.5))):
        s = random.uniform(0.35, 0.5)
        box(f'crate{k}', (x, y, s/2), (s, s*1.3, s), M['wood'], bevel=0.015, rot=(0, 0, random.uniform(-0.3, 0.3)))
        if k in (1, 4): box(f'crate_top{k}', (x+0.03, y, s*1.5), (s*0.9, s*1.2, s), M['wood'], bevel=0.015, rot=(0, 0, random.uniform(-0.3, 0.3)))
    for k, (x, y) in enumerate(((1.1, 3.2), (-1.05, 2.4), (1.15, -2.3))):
        o = sphere(f'bag{k}', (x, y, 0.32), 0.34, M['bag'], seg=16, scale=(1, 0.9, 1.0))
        o.rotation_euler = (0, 0, random.uniform(0, 3))
        d = o.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new(f'bagn{k}', 'CLOUDS'); tx.noise_scale = 0.5; d.texture = tx; d.strength = 0.09
    bin_ = cyl('bin', (-1.15, -3.0, 0.5), 0.3, 1.0, M['tin'], seg=20)
    cyl('binlid', (-1.15, -3.0, 1.03), 0.32, 0.06, M['black'], seg=20)
    for k in range(3):
        cyl(f'rail{k}', (0.0, 0, 0), 0.01, 0.01, M['black'])   # placeholder removed below
    # paper, cigarette butts, bottle caps, leaves near the kick spot
    for k in range(60):
        x = random.uniform(-1.3, 1.3); y = random.uniform(-2.5, 4.5)
        kind = random.random()
        if kind < 0.4:
            o = box(f'paper{k}', (x, y, 0.004), (random.uniform(0.04, 0.12), random.uniform(0.04, 0.1), 0.004), simple('paper', (0.7, 0.68, 0.6), 0.9), rot=(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(0, 6.28)))
        elif kind < 0.7:
            cyl(f'butt{k}', (x, y, 0.004), 0.004, 0.03, simple('butt', (0.8, 0.75, 0.6), 0.8), seg=8, rot=(math.pi/2, 0, random.uniform(0, 6.28)))
        else:
            cyl(f'cap{k}', (x, y, 0.004), 0.013, 0.005, M['rust'], seg=12)
    # puddle: mirror-like patch reflecting the warm lamp
    pm = bpy.data.materials.new('puddle'); pm.use_nodes = True; b = pm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.02, 0.02, 0.022, 1); b.inputs['Roughness'].default_value = 0.03
    pud = grid_plane('puddle', (0.55, 1.1), 6, 6, pm, center=(0.10, 1.3, 0.008))
    bm = bmesh.new(); bm.from_mesh(pud.data)
    for v in bm.verts: v.co.x *= 1+0.2*math.sin(v.co.y*3); v.co.y += 0.15*math.sin(v.co.x*5)
    bm.to_mesh(pud.data); bm.free()
    # bicycle leaning on the left wall (simple tubes)
    frame = M['frame']
    for (p0, p1) in (((-1.05, -5.2, 0.35), (-1.05, -4.7, 0.35)), ):
        pass
    # wall lamp (warm sodium/tungsten practical) on the left wall behind the kick + bracket
    box('lamp_bracket', (-1.4, 1.8, 3.1), (0.18, 0.05, 0.05), M['black'])
    sphere('lamp_bulb', (-1.32, 1.8, 3.0), 0.09, emission('bulb', (1.0, 0.62, 0.3), 40), seg=16)
    cyl('lamp_shade', (-1.32, 1.8, 3.12), 0.15, 0.08, M['rust'], seg=20, r2=0.05)
    light('POINT', 'lampL', (-1.25, 1.8, 2.9), 350, (1.0, 0.6, 0.3), size=0.08)
    light('POINT', 'lampL2', (-1.2, -4.5, 3.4), 200, (1.0, 0.65, 0.35), size=0.08)
    # cool skylight + rim from the alley mouth
    light('AREA', 'rim', (0.6, 8.0, 1.6), 1800, (0.55, 0.7, 1.0), size=2.5, rot=(math.radians(90), 0, math.radians(180)))
    light('AREA', 'fill', (1.4, -4.0, 3.0), 220, (0.6, 0.72, 1.0), size=3)
    aim(sc.objects['fill'], (0, 0.3, 0.1))
    # ---- obstacles hung along the can's route
    P = lambda f: Vector(CAN(T(f)))
    # cat on a ledge (near miss)
    pc = P(79.6); ledge_z = pc.z - 0.62
    box('ledge', (-1.28, pc.y, ledge_z), (0.42, 1.0, 0.09), M['concrete'], bevel=0.01)
    cat = build_cat((-1.14, pc.y, ledge_z+0.045))
    # hanging lamp on a cable
    pl = P(84.0)
    lamp_pos = Vector((pl.x+0.55, pl.y, pl.z+0.05))
    swing = bpy.data.objects.new('lamp_swing', None); sc.collection.objects.link(swing); swing.location = (1.5, lamp_pos.y, lamp_pos.z+0.9)
    crv = bpy.data.curves.new('lampcable', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.006
    sp = crv.splines.new('POLY'); sp.points.add(1); sp.points[0].co = (0, 0, 0, 1); sp.points[1].co = (-(1.5-lamp_pos.x), 0, -0.9, 1)
    co = bpy.data.objects.new('lampcable', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co); co.parent = swing
    shade = cyl('lampshade', (0, 0, 0), 0.17, 0.18, M['rust'], seg=24, r2=0.05); shade.parent = swing
    shade.location = (-(1.5-lamp_pos.x), 0, -0.98)
    bulb = sphere('lampbulb', (0, 0, 0), 0.07, emission('bulb2', (1.0, 0.7, 0.35), 80), seg=16); bulb.parent = swing; bulb.location = (-(1.5-lamp_pos.x), 0, -1.02)
    lg = light('POINT', 'lamp_hang', (0, 0, 0), 500, (1.0, 0.65, 0.3), size=0.07); lg.parent = swing; lg.location = (-(1.5-lamp_pos.x), 0, -1.05)
    for f, a in ((70, 0), (84, 0), (86, 9), (89, -7), (93, 5), (98, -3), (105, 1), (120, 0)):
        swing.rotation_euler = (math.radians(a*0.3), math.radians(a), 0); swing.keyframe_insert('rotation_euler', frame=int(T(f)))
    # laundry lines
    for (fp, ycol) in ((75.6, None), (85.7, None), (87.6, None)):
        pp = P(fp)
        zl = pp.z + 0.55; y = pp.y
        pts = [(-1.5+t*3.0, y, zl - 0.18*math.sin(math.pi*t)) for t in np.linspace(0, 1, 16)]
        crv = bpy.data.curves.new('line', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.004
        sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p, q in zip(sp.points, pts): p.co = (*q, 1)
        co = bpy.data.objects.new('line', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
        cols = [(0.6, 0.12, 0.1), (0.85, 0.85, 0.8), (0.1, 0.25, 0.45), (0.9, 0.7, 0.2), (0.3, 0.45, 0.25), (0.75, 0.75, 0.78)]
        xs = [pp.x-1.15, pp.x-0.62, pp.x+0.68, pp.x+1.2]
        for k, x in enumerate(xs):
            if not (-1.35 < x < 1.35): continue
            t = (x+1.5)/3.0; zt = zl - 0.18*math.sin(math.pi*t) - 0.02
            wdt, hgt = random.uniform(0.4, 0.6), random.uniform(0.55, 0.85)
            cloth(f'sh{fp}_{k}', (x, y, zt-hgt/2), (wdt, hgt), random.choice(cols), nseg=8, wave=0.035, rot=(math.pi/2, 0, math.pi/2+random.uniform(-0.25, 0.25)))
    # a wall-to-wall banner / bedsheet higher up (passes at the camera during the climb)
    return cat

def build_cat(pos):
    # tabby cat (procedural fallback if no generated mesh is present)
    mat = simple('fur', (0.16, 0.11, 0.07), rough=0.95, extra={'Sheen Weight': 0.8})
    cm = MOD+'cat_lo.glb'
    if os.path.exists(cm):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=cm)
        new = [o for o in bpy.data.objects if o not in before]
        root = [o for o in new if o.type == 'MESH'][0]
        return root
    body = sphere('cat_body', (pos[0], pos[1], pos[2]+0.16), 0.13, mat, scale=(0.9, 1.3, 1.25))
    sphere('cat_head', (pos[0], pos[1]+0.05, pos[2]+0.36), 0.075, mat)
    for s in (-1, 1):
        cy = cyl(f'cat_ear{s}', (pos[0]+s*0.04, pos[1]+0.05, pos[2]+0.44), 0.025, 0.05, mat, seg=4)
    sphere('cat_eyeL', (pos[0]-0.03, pos[1]-0.03, pos[2]+0.375), 0.012, emission('eye', (0.9, 0.9, 0.3), 3))
    sphere('cat_eyeR', (pos[0]+0.03, pos[1]-0.03, pos[2]+0.375), 0.012, emission('eye', (0.9, 0.9, 0.3), 3))
    cyl('cat_tail', (pos[0]+0.02, pos[1]+0.22, pos[2]+0.1), 0.02, 0.4, mat, seg=8, rot=(math.radians(80), 0, 0))
    return body


def decal(name, img, center, size, rot_z=0.0, wall_x=-1.5, sgn=1, rough=0.85):
    """flat alpha decal glued to the left/right wall face (faces the alley centre)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(TEX+img); t.extension = 'CLIP'
    nt.links.new(t.outputs[0], bs.inputs['Base Color']); nt.links.new(t.outputs[1], bs.inputs['Alpha'])
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Specular IOR Level'].default_value = 0.2
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    uvl = bm.loops.layers.uv.new('UV')
    for f in bm.faces:
        for lp in f.loops:
            v = lp.vert.co; lp[uvl].uv = (v.x+0.5, v.y+0.5)
    for v in bm.verts: v.co = Vector((v.co.x*size[0], v.co.y*size[1], 0))
    ob = _mesh_obj(name, bm, m)
    # plane local XY -> wall plane (Y = along alley, Z = up): rotate so normal points to the alley centre
    ob.rotation_euler = (math.radians(90), 0, math.radians(90 if wall_x < 0 else -90) + rot_z)
    ob.location = (wall_x + sgn*0.006, center[0], center[1])
    return ob

def dress_kick():
    """wear, grime and clutter in the low-angle kick view (left brick wall behind the can)."""
    rr = random.Random(81)
    decal('tag', 'graffiti_tag.png', (0.45, 1.05), (1.1, 0.55), 0.06)
    decal('poster1', 'poster1.png', (-0.55, 1.75), (0.42, 0.62), -0.05)
    decal('poster2', 'poster2.png', (1.25, 1.35), (0.40, 0.60), 0.08)
    decal('poster3', 'poster3.png', (-0.15, 1.95), (0.30, 0.45), 0.2)
    # bins, crates, sacks piled against the wall
    binm = simple('binplastic', (0.07, 0.075, 0.08), rough=0.7)
    for k, (y, r_) in enumerate(((1.75, 0.29), (-1.6, 0.27))):
        c = cyl(f'wbin{k}', (-1.2, y, 0.55), r_, 1.1, binm, seg=24)
        bv = c.modifiers.new('bv', 'BEVEL'); bv.width = 0.01
        cyl(f'wbinlid{k}', (-1.2, y, 1.12), r_+0.015, 0.05, M['black'], seg=24)
        box(f'wbinband{k}', (-1.2+r_*0.98, y, 0.7), (0.02, 0.24, 0.18), simple('binlabel', (0.75, 0.7, 0.55), 0.7))
    box('crateS0', (-1.22, -0.55, 0.16), (0.42, 0.55, 0.32), M['wood'], bevel=0.015, rot=(0, 0, 0.12))
    box('crateS1', (-1.2, -0.52, 0.47), (0.4, 0.5, 0.30), M['wood'], bevel=0.015, rot=(0, 0, -0.2))
    box('cardbox0', (-1.15, 1.1, 0.22), (0.4, 0.5, 0.44), M['cardboard'], bevel=0.01, rot=(0, 0, 0.35))
    box('cardbox1', (-1.0, 0.75, 0.10), (0.35, 0.45, 0.2), M['cardboard'], bevel=0.01, rot=(0, 0, -0.5))
    sack = simple('sack', (0.55, 0.5, 0.4), 0.95)
    o = sphere('sack0', (-1.1, -1.0, 0.22), 0.28, sack, seg=16, scale=(0.9, 1.1, 0.8))
    d = o.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new('sackn', 'CLOUDS'); tx.noise_scale = 0.3; d.texture = tx; d.strength = 0.08
    # drain pipe + bracket clamps + a leaking joint (wet stain handled by damp)
    cyl('pipeKick', (-1.44, 0.15, 3.0), 0.045, 6.0, simple('pipegreen', (0.09, 0.075, 0.06), 0.6, metal=0.3), seg=12)
    for z in (0.5, 1.5, 2.5): box(f'clamp{z}', (-1.43, 0.15, z), (0.03, 0.07, 0.05), M['black'])
    # cable run along the wall + a slack drop across the alley above the kick
    def cable(pts, r=0.008):
        crv = bpy.data.curves.new('kc', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = r; crv.bevel_resolution = 2
        sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p, q in zip(sp.points, pts): p.co = (*q, 1)
        co = bpy.data.objects.new('kc', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
    cable([(-1.47, -1.5+t*3.6, 2.35+0.06*math.sin(t*20)-0.5*t*(1-t)*2) for t in np.linspace(0, 1, 40)], 0.012)
    cable([(-1.47, -1.5+t*3.6, 2.5+0.05*math.sin(t*17+1)-0.4*t*(1-t)*2) for t in np.linspace(0, 1, 40)], 0.007)
    cable([(-1.46, 0.3, 2.4)]+[(-1.46+t*2.9, 0.3+0.4*t, 2.4+1.2*t-0.35*math.sin(math.pi*t)) for t in np.linspace(0, 1, 20)][1:], 0.007)
    # laundry line low across the alley at the kick (a few real pieces hanging)
    yl = 1.9; zl = 3.4
    pts = [(-1.5+t*3.0, yl, zl-0.14*math.sin(math.pi*t)) for t in np.linspace(0, 1, 16)]
    cable(pts, 0.004)
    for k, (x, col) in enumerate(((-0.9, (0.6, 0.14, 0.1)), (-0.15, (0.82, 0.8, 0.72)), (0.55, (0.12, 0.25, 0.45)), (1.0, (0.85, 0.7, 0.2)))):
        t = (x+1.5)/3.0; zt = zl-0.14*math.sin(math.pi*t)-0.02
        cloth(f'klaundry{k}', (x, yl, zt-0.32), (0.4, 0.62), col, nseg=8, wave=0.03, rot=(math.pi/2, 0, math.pi/2+rr.uniform(-0.25, 0.25)))
    # litter: crushed cups, bottle, cigarette packet, leaves, gum blobs
    cup = simple('cup', (0.75, 0.72, 0.68), 0.7)
    for k in range(9):
        x, y = rr.uniform(-1.2, 1.0), rr.uniform(-1.4, 2.0)
        if abs(x) < 0.2 and abs(y-0.3) < 0.25: continue
        cyl(f'cup{k}', (x, y, 0.035), 0.03, 0.08, cup if k % 3 else simple('cupred', (0.6, 0.1, 0.08), 0.6), seg=12, r2=0.022, rot=(rr.uniform(1.2, 1.6), 0, rr.uniform(0, 6)))
    cyl('pbottle', (0.45, 0.95, 0.03), 0.035, 0.22, simple('pet', (0.75, 0.85, 0.88), 0.15, extra={'Alpha': 0.5}), seg=12, rot=(math.pi/2, 0, 0.7))
    box('pack', (-0.5, 0.65, 0.008), (0.055, 0.085, 0.016), simple('pack', (0.75, 0.75, 0.7), 0.6), rot=(0, 0, 0.5))
    leaf = simple('leaf', (0.22, 0.15, 0.05), 0.9)
    for k in range(50):
        x, y = rr.uniform(-1.3, 1.3), rr.uniform(-1.6, 2.4)
        box(f'leaf{k}', (x, y, 0.004), (rr.uniform(0.03, 0.08), rr.uniform(0.02, 0.05), 0.003), leaf, rot=(0, 0, rr.uniform(0, 6.28)))
    # puddles (dirty mirror) - foreground and mid
    pm2 = bpy.data.materials.new('puddle2'); pm2.use_nodes = True; nt = pm2.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.035, 0.03, 0.028, 1); b.inputs['Roughness'].default_value = 0.02
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 40; nz.inputs['Detail'].default_value = 3
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.03; nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    for k, (cx, cy, sx, sy) in enumerate(((0.32, 0.62, 0.34, 0.5), (-0.55, -0.7, 0.4, 0.3), (0.5, -0.4, 0.28, 0.22))):
        pud = grid_plane(f'kpud{k}', (sx, sy), 8, 8, pm2, center=(cx, cy, 0.006))
        bm = bmesh.new(); bm.from_mesh(pud.data)
        for v in bm.verts:
            r_ = math.hypot(v.co.x/(sx/2+1e-6), v.co.y/(sy/2+1e-6))
            ang = math.atan2(v.co.y, v.co.x); w = 1+0.22*math.sin(ang*3+k)+0.12*math.sin(ang*7)
            v.co.x *= 1.0/(1+0.0); v.co.x *= w*1.0; v.co.y *= w
        bm.to_mesh(pud.data); bm.free()
    # sun raking in from the alley mouth (low, warm) + dusty air near the kick
    kk = light('AREA', 'kickkey', (0.35, 3.2, 0.55), 450, (1.0, 0.62, 0.32), size=0.6); aim(kk, (0.0, 0.3, 0.1))
    sun = light('SUN', 'lowsun', (0, 20, 20), 2.5, (1.0, 0.72, 0.42))
    sun.data.angle = math.radians(1.2)
    sun.rotation_euler = Vector((0.28, -1.0, -0.22)).to_track_quat('-Z', 'Y').to_euler()

# ------------------------------------------------------------------ kicker: boot, sock, trousers
def build_kicker():
    bootglb = MOD+'boot_lo.glb'
    def load_boot(tag, mirror=False):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=bootglb)
        new = [o for o in bpy.data.objects if o not in before]
        ob = [o for o in new if o.type == 'MESH'][0]
        for o in new:
            if o is not ob and o.type == 'EMPTY': bpy.data.objects.remove(o)
        ob.parent = None; ob.name = f'boot_{tag}'
        # centre on origin, toe -> +Y, sole at z=0 (model: length along Y, toe at -Y)
        ob.rotation_euler = (0, 0, math.pi); bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        vs = np.array([v.co for v in ob.data.vertices]); mn, mx = vs.min(0), vs.max(0)
        sc_ = 0.295/(mx[1]-mn[1])
        ob.data.transform(Matrix.Translation((-(mx[0]+mn[0])/2, -(mx[1]+mn[1])/2, -mn[2])))
        ob.data.transform(Matrix.Scale(sc_, 4))
        for p in ob.data.polygons: p.use_smooth = True
        for m in ob.data.materials:
            if m and m.node_tree:
                for n in m.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        for l in list(n.inputs['Metallic'].links): m.node_tree.links.remove(l)
                        for l in list(n.inputs['Roughness'].links): m.node_tree.links.remove(l)
                        n.inputs['Metallic'].default_value = 0.0; n.inputs['Roughness'].default_value = 0.5
                        bc = n.inputs['Base Color']
                        if bc.links:
                            src = bc.links[0].from_socket; mm = m.node_tree.nodes.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'
                            mm.inputs[0].default_value = 1.0; mm.inputs[7].default_value = (0.30, 0.27, 0.25, 1)
                            m.node_tree.links.new(src, mm.inputs[6]); m.node_tree.links.new(mm.outputs[2], bc)
        return ob, (mx-mn)*sc_
    kick, dims = load_boot('kick'); plant, _ = load_boot('plant')
    print('boot dims', tuple(dims))
    length = dims[1]
    # keyframes for kicking boot (origin = sole centre): juggling taps, flick, step back, wind-up, strike at HOOK
    can_y, cr = 0.30, 0.033
    phi_c = math.radians(-14)
    def pose(f, y, z, phi, x=0.06): key_obj(kick, f, loc=(x, y, z), rot=(phi, 0, 0.0))
    ty = can_y - cr*0.95 - (length/2*math.cos(phi_c))
    for tc in TAP_FRAMES:                       # instep taps: foot lifts under the can, drops back between taps
        cx_, cy_ = jug_xy(tc)
        pose(tc-3, cy_-0.16, 0.06, math.radians(-8), x=0.05+cx_*0.5)
        pose(tc, cy_-0.075, 0.17, math.radians(-30), x=0.02+cx_)
        pose(tc+4, cy_-0.14, 0.09, math.radians(-14), x=0.05+cx_*0.5)
    cx_, cy_ = jug_xy(FLICK_T0)
    pose(56, cy_-0.28, 0.03, math.radians(8)); pose(60, cy_-0.06, 0.15, math.radians(-42), x=0.02+cx_)     # scoop + flick
    pose(64, cy_+0.12, 0.55, math.radians(-55)); pose(70, -0.10, 0.30, math.radians(-20)); pose(76, -0.25, 0.05, math.radians(-8))
    pose(82, -0.20, 0.03, math.radians(-10)); pose(88, -0.45, 0.15, math.radians(-38))                  # step back, wind-up
    pose(92, -0.62, 0.24, math.radians(-58)); pose(94.5, -0.36, 0.09, math.radians(-30))
    pose(HOOK, ty, 0.055, phi_c)
    pose(HOOK+1, ty+0.28, 0.12, math.radians(-4)); pose(HOOK+3, ty+0.55, 0.22, math.radians(8)); pose(HOOK+7, ty+0.95, 0.42, math.radians(20)); pose(HOOK+14, ty+1.4, 0.7, math.radians(30))
    set_interp(kick, 'BEZIER')
    # plant foot (static, slight weight shifts)
    plant.location = (-0.26, -0.30, 0.0); plant.rotation_euler = (0, 0, math.radians(-6))
    for f_, dy_ in ((0, 0.0), (30, 0.015), (56, -0.01), (76, 0.02), (90, 0.0), (HOOK, -0.01)):
        key_obj(plant, f_, loc=(-0.26, -0.30+dy_, 0.0))
    # legs: tapered trousers, stretched from ankle to hip (out of frame)
    for tag, boot, hip in (('kick', kick, (0.06, -0.10, 1.0)), ('plant', plant, (-0.22, -0.30, 1.0))):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.068, radius2=0.115, depth=1.0)
        for v in bm.verts: v.co = Vector((v.co.x, v.co.z+0.5, -v.co.y))   # along +Y from 0..1... y = z+0.5
        leg = _mesh_obj(f'leg_{tag}', bm, M['pants'])
        for p in leg.data.polygons: p.use_smooth = True
        leg.location = (0, 0, 0)
        bpy.context.view_layer.update()
        # ankle empty parented to the boot
        ank = bpy.data.objects.new(f'ankle_{tag}', None); sc.collection.objects.link(ank); ank.parent = boot; ank.location = (0, -0.045, 0.145)
        hp = bpy.data.objects.new(f'hip_{tag}', None); sc.collection.objects.link(hp); hp.location = hip
        leg.parent = ank; leg.location = (0, 0, 0)
        # Stretch-To: the tube's local +Y goes from the ankle to the hip empty
        c = leg.constraints.new('STRETCH_TO'); c.target = hp; c.rest_length = 1.0; c.volume = 'NO_VOLUME'
    # upper body (hoodie, hood up, seen from the side/behind: no hero face) + arms swaying for balance
    hood = simple('hoodie', (0.045, 0.05, 0.065), 0.9)
    torso = cyl('torso', (-0.08, -0.12, 1.28), 0.19, 0.62, hood, seg=20, r2=0.22)
    sphere('shoulders', (-0.08, -0.12, 1.56), 0.23, hood, seg=16, scale=(1.0, 0.75, 0.6))
    hd = sphere('hood_head', (-0.08, -0.14, 1.78), 0.13, hood, seg=16, scale=(0.95, 1.05, 1.1))
    sphere('hood_back', (-0.08, -0.22, 1.76), 0.12, hood, seg=12)
    for side in (-1, 1):
        arm = cyl(f'arm{side}', (-0.08+side*0.30, -0.12, 1.28), 0.055, 0.62, hood, seg=10)
        arm.rotation_euler = (0, math.radians(side*-14), 0)
        for f_, a_ in ((0, 0), (24, 6), (48, -5), (72, 12), (96, -8)):
            arm.rotation_euler = (math.radians(a_*side*0.4), math.radians(side*(-14-a_)), 0); arm.keyframe_insert('rotation_euler', frame=f_)
    return kick, plant

# ------------------------------------------------------------------ dust, chips and impact debris at the hook frame
def build_impact():
    dust = bpy.data.materials.new('dust'); dust.use_nodes = True; nt = dust.node_tree; nt.nodes.clear()
    vs = nt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Color'].default_value = (0.62, 0.55, 0.46, 1); vs.inputs['Density'].default_value = 5.0
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 8
    nt.links.new(nt.nodes.new('ShaderNodeNewGeometry').outputs['Position'], nz.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value = 0.35; mr.inputs[2].default_value = 0.75; mr.inputs[4].default_value = 1.0
    nt.links.new(nz.outputs['Fac'], mr.inputs[0])
    mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 1.6
    nt.links.new(mr.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], vs.inputs['Density'])
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(vs.outputs[0], o.inputs['Volume'])
    ctr = Vector((0, 0.30, 0.03))
    for k in range(14):   # dust puffs (volumetric blobs that swell and thin out)
        ang = random.uniform(0, 2*math.pi); sp = random.uniform(0.6, 2.0)
        p = bpy.data.objects.new(f'puff{k}', None)
        b = bpy.data.meshes.new(f'puffm{k}'); bmm = bmesh.new(); bmesh.ops.create_icosphere(bmm, subdivisions=3, radius=1.0); bmm.to_mesh(b); bmm.free()
        ob = bpy.data.objects.new(f'puff{k}', b); sc.collection.objects.link(ob); ob.data.materials.append(dust)
        ob.display_type = 'WIRE'
        r0 = random.uniform(0.04, 0.08)
        key_obj(ob, HOOK-1, loc=ctr, scale=(0.001,)*3)
        key_obj(ob, HOOK, loc=ctr, scale=(r0,)*3)
        end = ctr + Vector((math.cos(ang)*sp*0.25, math.sin(ang)*sp*0.25*0.7+0.1, 0.03+random.uniform(0.02, 0.2)))
        r1 = random.uniform(0.25, 0.5)
        key_obj(ob, HOOK+8, loc=end, scale=(r1,)*3)
        key_obj(ob, HOOK+24, loc=end+Vector((0, 0.3, 0.15)), scale=(r1*1.4, r1*1.4, r1*1.1))
        key_obj(ob, HOOK+25, scale=(0.001,)*3)
    # chips of grit and can paint
    gm = simple('grit', (0.35, 0.3, 0.26), rough=0.9)
    chip = simple('chip', (0.8, 0.15, 0.1), rough=0.4, metal=0.4)
    for k in range(90):
        ang = random.uniform(0, 2*math.pi); up = random.uniform(0.2, 1.0); sp = random.uniform(2, 7)*(0.4 if k < 60 else 0.8)
        s = random.uniform(0.003, 0.009)
        ob = box(f'grit{k}', ctr, (s, s*random.uniform(0.6, 1.4), s*0.6), gm if k < 70 else chip, rot=(random.random(), random.random(), random.random()))
        v = Vector((math.cos(ang)*sp*0.5, math.sin(ang)*sp*0.5+sp*0.3, up*sp*0.7))
        for f in range(HOOK-1, HOOK+28, 2):
            t = (f-HOOK)/24.0
            if t < 0: pos = ctr
            else:
                pos = ctr + v*t + Vector((0, 0, -4.9*t*t))
                if pos.z < 0.004: pos.z = 0.004; v = Vector((v.x*0.5, v.y*0.5, 0)); ctr2 = None
            key_obj(ob, f, loc=pos, scale=(1, 1, 1) if f > HOOK-1 else (0.001,)*3)
        set_interp(ob, 'LINEAR')

def animate_can(can):
    prev = Euler((0, 0, 0))
    # pre-kick: upright, tiny settle wobble
    for f in range(F0, 72):
        wob = 0.012*math.sin(f*0.55)*math.exp(-f/12.0) if f < 40 else 0
        can.location = (0, 0.30, 0.0); can.rotation_euler = (wob, wob*0.7, 0.4)
        can.keyframe_insert('location', frame=f); can.keyframe_insert('rotation_euler', frame=f)
    ang_t, ang_s = 0.0, 0.0
    fr = 71
    prevdir = Vector((0, 0.5, 1)).normalized()
    for f in range(72, F1+1):
        p = can_pos(f)
        if f > 178:   # in the net: falls and settles
            pass
        v = can_pos(f+0.5)-can_pos(f-0.5) if f > 72 else Vector((0, 0.5, 1))
        d = v.normalized() if v.length > 1e-6 else prevdir
        rate = 46.0*math.exp(-max(0, f-72)/90.0)   # deg/frame end-over-end
        if f >= 181:
            rate *= max(0.0, 1-(f-181)/6.0)
        ang_t += math.radians(rate); ang_s += math.radians(22.0*(1 if f < 181 else 0.3))
        # local frame: z along the can axis; tumble about the axis perpendicular to travel
        yaw = math.atan2(-d.x, d.y)
        R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(ang_t + 0.9, 3, 'X') @ Matrix.Rotation(ang_s, 3, 'Z')
        if f == 72: R = Matrix.Rotation(0.4, 3, 'Z')
        e = R.to_euler('XYZ', prev); prev = e
        can.location = p if f > 72 else Vector((0, 0.30, 0.0)); can.rotation_euler = e
        can.keyframe_insert('location', frame=f); can.keyframe_insert('rotation_euler', frame=f)
        if f == 72:
            can.location = Vector((0, 0.30, 0.0))
        prevdir = d
    # settled orientation: lying at rest in the net -> keep tumbling decays; fine.
    set_interp(can, 'LINEAR')
    sk = can.data.shape_keys.key_blocks['kick_dent']
    sk.value = 0; sk.keyframe_insert('value', frame=71); sk.value = 1.0; sk.keyframe_insert('value', frame=73)
    # let the can get its z offset: the can origin is at its base; recentre origin at the middle of the can
    can.data.transform(Matrix.Translation((0, 0, -0.061)))
    # ground contact before the kick: raise by half height
    for f in range(F0, 72):
        pass

# ------------------------------------------------------------------ camera
def build_camera(can):
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36.0; cd.lens = 24.0
    cd.clip_start = 0.02; cd.clip_end = 3000
    cd.dof.use_dof = True
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    fo = bpy.data.objects.new('focus', None); sc.collection.objects.link(fo); cd.dof.focus_object = fo
    # (focus object follows the can after the hook)
    def noise(f, seed, amp, freq=1.0):
        return amp*(math.sin(f*0.31*freq+seed)+0.6*math.sin(f*0.77*freq+seed*2.3)+0.35*math.sin(f*1.71*freq+seed*4.1))
    prev = Euler((0, 0, 0)); dsm = Vector((0, 0.5, 1)).normalized(); rollsm = 0.0; prevyaw = None
    poses = []
    HOLD = [Vector((0, 0, 0))]
    for f in range(F0, F1+1):
        # --- kick shot: ~ knee-to-ground level, three-quarter side, slow push-in with breathing
        t = f/72.0
        c0 = Vector((0.68-0.10*smooth(t)+noise(f, 1, 0.004), 0.10+0.06*smooth(t)+noise(f, 2, 0.004), 0.10-0.01*smooth(t)+noise(f, 3, 0.003)))
        tgt0 = Vector((0.0, 0.17+0.03*smooth(t), 0.27))
        # reaction to the hit (jolt)
        jolt = math.exp(-max(0, f-72)/2.5) if f >= 72 else 0.0
        if f < 72:
            pos, tgt, roll = c0, tgt0, math.radians(-1.5)+noise(f, 5, 0.003)
            dist = (c0-Vector((0, 0.3, 0.06))).length
        else:
            p = can_pos(f); v = can_pos(f+0.5)-can_pos(f-0.5); d = v.normalized()
            dsm = (dsm*0.55+d*0.45).normalized()
            back = 0.55 if f < 100 else 0.75
            e3 = smooth((f-168)/6.0)
            dsm = (dsm*(1-e3)+Vector((0.03, 1.0, -0.12)).normalized()*e3).normalized()
            e3 = smooth((f-168)/6.0)
            chase = p - dsm*back + Vector((-0.4*e3, 0, 0.16*(1-e3)-0.42*e3))
            w = smooth((f-75)/13.0)
            w2 = smooth((f-72.5)/9.0)
            pos = c0*(1-w) + chase*w
            tgt = tgt0*(1-w2) + (p + dsm*0.35)*w2
            # bank into turns
            yawv = math.atan2(d.x, d.y)
            yr = 0 if prevyaw is None else (yawv-prevyaw)
            prevyaw = yawv
            rollsm = rollsm*0.7 + (-yr*7.0)*0.3
            roll = (rollsm*w + noise(f, 6, 0.012)*w + (math.radians(-1.5)*(1-w)))*(1-e3)
            dist = (pos-p).length
        # shake grows with speed
        spd = 0 if f < 72 else min(1.0, (can_pos(f+1)-can_pos(f)).length/2.0)
        sh = 0.006+0.03*spd
        pos = pos + Vector((noise(f, 11, sh, 1.3), noise(f, 12, sh, 1.1), noise(f, 13, sh, 1.7)))
        if f >= 72: pos += Vector((0.015*jolt*math.sin(f*2.1), 0.02*jolt, -0.02*jolt))
        tgt = tgt + Vector((noise(f, 21, sh*0.6), noise(f, 22, sh*0.6), noise(f, 23, sh*0.5)))
        if f > 181:
            pos = HOLD[0] + Vector((0.004*(f-181), 0.02*(1-math.exp(-(f-181)/4.0)), -0.003*(f-181))) + Vector((noise(f, 31, 0.006), noise(f, 32, 0.006), noise(f, 33, 0.005)))
            tgt = tgt*0.6 + can_pos(f)*0.4
        elif f == 181:
            HOLD[0] = Vector(pos)
        q = (tgt-pos).to_track_quat('-Z', 'Y')
        e_ = q.to_euler('XYZ', prev)
        # apply roll about camera's own axis
        rq = q @ Quaternion((0, 0, 1), roll)
        e_ = rq.to_euler('XYZ', prev); prev = e_
        cam.location = pos; cam.rotation_euler = e_
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        # focus + aperture
        fo.location = (0, 0.3, 0.06) if f < 72 else can_pos(f)
        if f > 174: fo.location = Vector((3.4, 311.4, 1.4))*smooth((f-174)/10.0)+can_pos(f)*(1-smooth((f-174)/10.0))
        fo.keyframe_insert('location', frame=f)
        cd.dof.aperture_fstop = 3.2 if f < 72 else 3.5
        cd.dof.keyframe_insert('aperture_fstop', frame=f)
        cd.lens = 24.0 if f < 72 else 20.0 + 0.0
        cd.keyframe_insert('lens', frame=f)
    set_interp(cam, 'LINEAR')
    for ob in (fo,): set_interp(ob, 'LINEAR')
    return cam

# ------------------------------------------------------------------ render settings (EEVEE draft defaults; render.py overrides)
def render_settings():
    r = sc.render
    r.engine = 'BLENDER_EEVEE'
    r.use_motion_blur = True; r.motion_blur_shutter = 0.30
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception as ex: print('look', ex)
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v2_anim.py')).read())   # v2: overrides animate_can / build_camera
build_world(); make_materials(); render_settings()
can = build_can(); can.location = (0, 0.3, 0)
build_alley()
dress_kick()
kick, plant = build_kicker()
build_impact()
animate_can(can)
if PART != 'kick':
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scene_far.py')).read())
cam = build_camera(can)
if SAVE:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(SAVE))
    print('saved', SAVE)
# optional in-process draft: --draft <out_dir> <f1,f2,...> [w h]   (EEVEE, 12 samples) so one queued Blender process builds AND checks
if '--draft' in argv:
    _i = argv.index('--draft'); _out = argv[_i+1]; _fr = [int(x) for x in argv[_i+2].split(',')]
    _w = int(argv[_i+3]) if len(argv) > _i+3 and argv[_i+3].isdigit() else 270
    _h = int(argv[_i+4]) if len(argv) > _i+4 and argv[_i+4].isdigit() else 480
    os.makedirs(_out, exist_ok=True)
    sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 12
    sc.render.resolution_x = _w; sc.render.resolution_y = _h; sc.render.resolution_percentage = 100
    for _f in _fr:
        sc.frame_set(_f); sc.render.filepath = f'{_out}/d_{_f:03d}.png'
        bpy.ops.render.render(write_still=True)
# optional in-process previs render: --previs <out_dir>   (EEVEE 12 samples, 540x960, resumes: existing PNGs are skipped)
if '--previs' in argv:
    import time as _t
    _out = argv[argv.index('--previs')+1]; os.makedirs(_out, exist_ok=True)
    sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 12
    sc.render.resolution_x = 540; sc.render.resolution_y = 960; sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.30
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    for _f in range(F0, F1+1):
        _p = f'{_out}/f_{_f:04d}.png'
        if os.path.exists(_p): continue
        _t0 = _t.time(); sc.frame_set(_f); sc.render.filepath = _p
        bpy.ops.render.render(write_still=True)
        print(f'FRAME {_f} {_t.time()-_t0:.1f}s', flush=True)
