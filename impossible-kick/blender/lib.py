import bpy, bmesh, math, random, os
import numpy as np
from mathutils import Vector, Euler, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TEX = ROOT + '/assets/textures/'
MOD = ROOT + '/assets/models/'
HDRI = ROOT + '/assets/hdri/'
_mats = {}

def _img(nt, path, cs='sRGB', box=True, blend=0.2):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = cs
    if box:
        n.projection = 'BOX'; n.projection_blend = blend
    return n

def mix(nt, a, b, fac, blend='MIX'):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend
    m.inputs[0].default_value = fac if not hasattr(fac, 'node') else 0
    if hasattr(fac, 'node'): nt.links.new(fac, m.inputs[0])
    for i, v in ((6, a), (7, b)):
        if hasattr(v, 'node'): nt.links.new(v, m.inputs[i])
        else: m.inputs[i].default_value = v
    return m.outputs[2]

def pbr(name, tex, tile=2.0, tint=None, tint_amt=0.0, rough_mul=1.0, nstr=1.0, dirt=0.35, color=None,
        metal=0.0, uvmap=False, disp=0.0, streak=0.0, damp=0.0, damp_h=0.9, moss=0.0):
    """Poly Haven PBR set (1k) mapped triplanar in WORLD metres. tile = metres per texture repeat."""
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    if uvmap: vec = nt.nodes.new('ShaderNodeUVMap').outputs[0]
    else:
        pos = nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']
        mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1/tile,)*3
        nt.links.new(pos, mp.inputs[0]); vec = mp.outputs[0]
    def T(suffix, cs):
        p = TEX + f'{tex}_{suffix}_1k.jpg'
        if not os.path.exists(p): return None
        n = _img(nt, p, cs, box=not uvmap); nt.links.new(vec, n.inputs[0]); return n
    d = T('diff', 'sRGB'); arm = T('arm', 'Non-Color'); nor = T('nor', 'Non-Color')
    col = d.outputs[0] if d else (color or (0.5, 0.5, 0.5, 1))
    if tint is not None and tint_amt > 0: col = mix(nt, col, tint, tint_amt, 'MULTIPLY' if d else 'MIX')
    # grime: large-scale noise darkens & roughens
    ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.9; ns.inputs['Detail'].default_value = 8
    if not uvmap:
        pos2 = nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']; nt.links.new(pos2, ns.inputs[0])
    ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs[1].default_value = 0.35; ramp.inputs[2].default_value = 0.7
    nt.links.new(ns.outputs['Fac'], ramp.inputs[0])
    if dirt > 0:
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = dirt
        nt.links.new(ramp.outputs[0], mul.inputs[0])
        col = mix(nt, col, (0.09, 0.075, 0.06, 1), mul.outputs[0])
    # ---- wear: vertical rain streaks, rising damp, moss/dirt pockets
    dampf = None
    if not uvmap:
        gp = nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']
        if streak > 0:
            mps = nt.nodes.new('ShaderNodeMapping'); mps.inputs['Scale'].default_value = (2.2, 2.2, 0.28)
            nt.links.new(gp, mps.inputs[0])
            nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6
            nt.links.new(mps.outputs[0], nz.inputs[0])
            mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value = 0.42; mr.inputs[2].default_value = 0.72
            nt.links.new(nz.outputs['Fac'], mr.inputs[0])
            mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = streak
            nt.links.new(mr.outputs[0], mm.inputs[0])
            col = mix(nt, col, (0.05, 0.045, 0.04, 1), mm.outputs[0])
        if damp > 0:
            sp_ = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(gp, sp_.inputs[0])
            mr2 = nt.nodes.new('ShaderNodeMapRange'); mr2.inputs[1].default_value = 0.05; mr2.inputs[2].default_value = damp_h
            mr2.inputs[3].default_value = 1.0; mr2.inputs[4].default_value = 0.0
            nt.links.new(sp_.outputs['Z'], mr2.inputs[0])
            nzd = nt.nodes.new('ShaderNodeTexNoise'); nzd.inputs['Scale'].default_value = 5.0; nzd.inputs['Detail'].default_value = 5
            nt.links.new(gp, nzd.inputs[0])
            addn = nt.nodes.new('ShaderNodeMath'); addn.operation = 'ADD'
            nt.links.new(mr2.outputs[0], addn.inputs[0]); nt.links.new(nzd.outputs['Fac'], addn.inputs[1]); addn.inputs[1].default_value = 0
            sub_ = nt.nodes.new('ShaderNodeMath'); sub_.operation = 'SUBTRACT'; sub_.inputs[1].default_value = 0.35
            nt.links.new(addn.outputs[0], sub_.inputs[0])
            cl = nt.nodes.new('ShaderNodeMath'); cl.operation = 'MULTIPLY'; cl.use_clamp = True; cl.inputs[1].default_value = damp
            nt.links.new(sub_.outputs[0], cl.inputs[0]); dampf = cl.outputs[0]
            col = mix(nt, col, (0.02, 0.018, 0.016, 1), dampf, 'MULTIPLY')
        if moss > 0:
            nzm = nt.nodes.new('ShaderNodeTexNoise'); nzm.inputs['Scale'].default_value = 7.0; nzm.inputs['Detail'].default_value = 7
            nt.links.new(gp, nzm.inputs[0])
            mrm = nt.nodes.new('ShaderNodeMapRange'); mrm.inputs[1].default_value = 0.58; mrm.inputs[2].default_value = 0.75
            nt.links.new(nzm.outputs['Fac'], mrm.inputs[0])
            mmm = nt.nodes.new('ShaderNodeMath'); mmm.operation = 'MULTIPLY'; mmm.inputs[1].default_value = moss
            nt.links.new(mrm.outputs[0], mmm.inputs[0])
            col = mix(nt, col, (0.07, 0.09, 0.03, 1), mmm.outputs[0])
    nt.links.new(col, bs.inputs['Base Color'])
    if arm:
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(arm.outputs[0], sep.inputs[0])
        r = nt.nodes.new('ShaderNodeMath'); r.operation = 'MULTIPLY'; r.inputs[1].default_value = rough_mul
        nt.links.new(sep.outputs[1], r.inputs[0])
        if dampf is not None:
            dr = nt.nodes.new('ShaderNodeMath'); dr.operation = 'MULTIPLY'; dr.inputs[1].default_value = 0.0
            dm = nt.nodes.new('ShaderNodeMath'); dm.operation = 'SUBTRACT'; dm.inputs[0].default_value = 1.0
            dm2 = nt.nodes.new('ShaderNodeMath'); dm2.operation = 'MULTIPLY'; dm2.inputs[1].default_value = 0.6
            nt.links.new(dampf, dm2.inputs[0]); nt.links.new(dm2.outputs[0], dm.inputs[1])
            r2 = nt.nodes.new('ShaderNodeMath'); r2.operation = 'MULTIPLY'
            nt.links.new(r.outputs[0], r2.inputs[0]); nt.links.new(dm.outputs[0], r2.inputs[1])
            nt.links.new(r2.outputs[0], bs.inputs['Roughness'])
        else:
            nt.links.new(r.outputs[0], bs.inputs['Roughness'])
        if metal > 0: nt.links.new(sep.outputs[2], bs.inputs['Metallic'])
    else:
        bs.inputs['Roughness'].default_value = 0.6 * rough_mul
    if nor:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(nor.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    _mats[name] = m; return m

def simple(name, color, rough=0.5, metal=0.0, emit=None, estr=0.0, alpha=None, extra=None):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color[:3], 1)
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    if emit is not None:
        bs.inputs['Emission Color'].default_value = (*emit[:3], 1); bs.inputs['Emission Strength'].default_value = estr
    if alpha is not None: bs.inputs['Alpha'].default_value = alpha
    if extra:
        for k, v in extra.items(): bs.inputs[k].default_value = v
    _mats[name] = m; return m

def emission(name, color, strength):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*color[:3], 1); e.inputs[1].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0])
    _mats[name] = m; return m

def _mesh_obj(name, bm, mat=None, coll=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    if mat: ob.data.materials.append(mat)
    return ob

def box(name, center, size, mat, bevel=0.0, rot=None):
    """Axis-aligned box in real metres (scale applied)."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x*size[0], v.co.y*size[1], v.co.z*size[2]))
    ob = _mesh_obj(name, bm, mat); ob.location = center
    if rot: ob.rotation_euler = rot
    if bevel > 0:
        b = ob.modifiers.new('bv', 'BEVEL'); b.width = bevel; b.segments = 2; b.limit_method = 'ANGLE'
    return ob

def cyl(name, center, r, h, mat, seg=24, rot=None, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=(r if r2 is None else r2), depth=h)
    ob = _mesh_obj(name, bm, mat); ob.location = center
    if rot: ob.rotation_euler = rot
    for p in ob.data.polygons: p.use_smooth = True
    return ob

def sphere(name, center, r, mat, seg=24, scale=(1,1,1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg//2), radius=r)
    for v in bm.verts: v.co = Vector((v.co.x*scale[0], v.co.y*scale[1], v.co.z*scale[2]))
    ob = _mesh_obj(name, bm, mat); ob.location = center
    for p in ob.data.polygons: p.use_smooth = True
    return ob

def quad_strip(name, pts_a, pts_b, mat, uv=None):
    """Loft between two equally long point lists (quads)."""
    bm = bmesh.new()
    va = [bm.verts.new(p) for p in pts_a]; vb = [bm.verts.new(p) for p in pts_b]
    for i in range(len(va)-1): bm.faces.new((va[i], va[i+1], vb[i+1], vb[i]))
    return _mesh_obj(name, bm, mat)

def grid_plane(name, size, nx, ny, mat, center=(0,0,0), rot=None):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x*2*size[0]/2*1.0, v.co.y*2*size[1]/2*1.0, 0))
    ob = _mesh_obj(name, bm, mat); ob.location = center
    if rot: ob.rotation_euler = rot
    return ob

def set_interp(ob, kind='LINEAR'):
    ad = ob.animation_data
    if not ad or not ad.action: return
    for layer in ad.action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    for kp in fc.keyframe_points: kp.interpolation = kind

def key_obj(ob, f, loc=None, rot=None, scale=None):
    if loc is not None: ob.location = loc; ob.keyframe_insert('location', frame=f)
    if rot is not None: ob.rotation_euler = rot; ob.keyframe_insert('rotation_euler', frame=f)
    if scale is not None: ob.scale = scale; ob.keyframe_insert('scale', frame=f)

def smooth(x): x = min(1.0, max(0.0, x)); return x*x*(3-2*x)

def hermite_path(keys):
    """keys: list of (frame, (x,y,z)); returns f -> position (Catmull-Rom in time, C1)."""
    fs = [k[0] for k in keys]; ps = [np.array(k[1], float) for k in keys]
    n = len(keys)
    tang = []
    for i in range(n):
        a = max(0, i-1); b = min(n-1, i+1)
        tang.append((ps[b]-ps[a])/(fs[b]-fs[a]))
    def P(f):
        f = min(max(f, fs[0]), fs[-1]-1e-9)
        i = max(j for j in range(n-1) if fs[j] <= f)
        h = fs[i+1]-fs[i]; t = (f-fs[i])/h
        h00 = 2*t**3-3*t**2+1; h10 = t**3-2*t**2+t; h01 = -2*t**3+3*t**2; h11 = t**3-t**2
        return h00*ps[i] + h10*h*tang[i] + h01*ps[i+1] + h11*h*tang[i+1]
    return P
