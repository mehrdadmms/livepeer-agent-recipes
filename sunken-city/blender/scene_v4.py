"""Sunken city hook - builds the whole scene from scratch, headless.

blender -b -P blender/scene.py -- [--save blender/scene.blend]

Timeline (24 fps, frames 1..192). HOOK frame = 84 (3.5 s): kid cannonballs into the sea,
splash reaches the lens, camera goes through the waterline and dives into the sunken city.
Coordinates: +Y = along the pier towards the sea/sun, Z up, water surface at z=0, pier deck z=1.5.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Euler, Matrix, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))) if False else \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
HOOK = 97   # 4.000 s = 0-indexed picture frame 96 (Blender frame 97)
HOOK_V1 = 84
SHIFT = HOOK - HOOK_V1
FPS = 24
NF = 576
DECK = 1.5
SEABED = -22.0
rnd = random.Random(7)
nrng = np.random.default_rng(7)

# ----------------------------------------------------------------------------- helpers
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, NF
scene.render.fps = FPS
scene.render.resolution_x, scene.render.resolution_y = 720, 1280
scene.render.resolution_percentage = 100


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


C_ABOVE = coll("Above")
C_UNDER = coll("Under")
C_MISC = coll("Misc")


def link(obj, *cols):
    for c in cols:
        c.objects.link(obj)
    return obj


def mesh_obj(name, bm, cols, loc=(0, 0, 0), smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    link(ob, *cols)
    return ob


def tex(path):
    im = bpy.data.images.load(os.path.join(A, "textures", path), check_existing=True)
    return im


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def MATH(nt, op, a, b=None, c=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def VMATH(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def pbr_maps(nt, name, scale=0.25, box=True, strength=1.0, tint=None, loc_out=None):
    """Poly Haven texture set with box projection in object space. returns (color, rough, normal) sockets"""
    tc = N(nt, "ShaderNodeTexCoord")
    mp = N(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    L(nt, tc.outputs["Object"], mp.inputs["Vector"])
    outs = []
    for kind, cs in (("diff", "sRGB"), ("rough", "Non-Color"), ("nor", "Non-Color")):
        t = N(nt, "ShaderNodeTexImage")
        t.image = tex(f"{name}_{kind}_2k.jpg")
        t.image.colorspace_settings.name = cs
        if box:
            t.projection = "BOX"
            t.projection_blend = 0.25
        t.interpolation = "Cubic"
        L(nt, mp.outputs[0], t.inputs["Vector"])
        outs.append(t.outputs["Color"])
    nm = N(nt, "ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = strength
    # box-projected normal maps are only approximate but fine for weathered surfaces
    L(nt, outs[2], nm.inputs["Color"])
    return outs[0], outs[1], nm.outputs["Normal"]


def principled(nt):
    return N(nt, "ShaderNodeBsdfPrincipled")


def set_in(node, name, val):
    sk = node.inputs[name]
    if isinstance(val, tuple) and len(val) == 3 and sk.type == "RGBA":
        val = val + (1.0,)
    sk.default_value = val


# ----------------------------------------------------------------------------- render setup
def setup_render():
    r = scene.render
    r.engine = "BLENDER_EEVEE"
    e = scene.eevee
    e.use_raytracing = True
    e.taa_render_samples = 48
    e.taa_samples = 16
    e.use_shadows = True
    e.shadow_pool_size = "1024"
    e.shadow_ray_count = 2
    e.shadow_step_count = 6
    e.use_volumetric_shadows = True
    e.volumetric_tile_size = "8"
    e.volumetric_samples = 64
    e.volumetric_sample_distribution = 0.8
    e.volumetric_shadow_samples = 32
    e.volumetric_ray_depth = 8
    e.use_volume_custom_range = True
    e.volumetric_start = 0.05
    e.volumetric_end = 70.0
    e.use_fast_gi = True
    e.fast_gi_method = "GLOBAL_ILLUMINATION"
    e.motion_blur_steps = 3
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.35
    r.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = 0.3
    scene.display_settings.display_device = "sRGB"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "16"


setup_render()

# ----------------------------------------------------------------------------- world (HDRI golden hour)
def build_world():
    w = bpy.data.worlds.new("World")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = N(nt, "ShaderNodeTexCoord")
    el_, az_ = math.radians(SUN_EL_DEG), math.radians(SUN_AZ_DEG)
    sv_ = (math.cos(az_) * math.cos(el_), math.sin(az_) * math.cos(el_), math.sin(el_))
    gen = VMATH(nt, "NORMALIZE", tc.outputs["Generated"])
    sp_ = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, gen, sp_.inputs[0])
    zz = sp_.outputs["Z"]
    dn = nt.nodes.new("ShaderNodeVectorMath")
    dn.operation = "DOT_PRODUCT"
    L(nt, gen, dn.inputs[0])
    dn.inputs[1].default_value = sv_
    cdot = dn.outputs["Value"]

    def mixc(f, c0, c1):
        m_ = N(nt, "ShaderNodeMix")
        m_.data_type = "RGBA"
        if isinstance(c0, tuple):
            m_.inputs[6].default_value = c0
        else:
            L(nt, c0, m_.inputs[6])
        if isinstance(c1, tuple):
            m_.inputs[7].default_value = c1
        else:
            L(nt, c1, m_.inputs[7])
        L(nt, f, m_.inputs[0])
        return m_.outputs[2]
    t1 = MATH(nt, "MINIMUM", MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", zz, 7.0), 0.0), 1.0)
    t2 = MATH(nt, "MINIMUM", MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", zz, 0.05), 1.9), 0.0), 1.0)
    c1_ = mixc(t1, (0.95, 0.34, 0.08, 1), (0.42, 0.30, 0.46, 1))
    c2_ = mixc(MATH(nt, "POWER", t2, 0.7), c1_, (0.012, 0.05, 0.27, 1))
    g_ = MATH(nt, "MINIMUM", MATH(nt, "MULTIPLY", MATH(nt, "POWER", MATH(nt, "MAXIMUM", cdot, 0.0), 10.0), 1.4), 1.0)
    c3_ = mixc(g_, c2_, (1.0, 0.50, 0.14, 1))
    dsc = MATH(nt, "GREATER_THAN", cdot, 0.99992)
    skycol = mixc(dsc, c3_, (60.0, 40.0, 18.0, 1))
    bg = N(nt, "ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    out = N(nt, "ShaderNodeOutputWorld")
    L(nt, skycol, bg.inputs["Color"])
    L(nt, bg.outputs[0], out.inputs["Surface"])
    # faint warm air haze (sun glow)
    vs = N(nt, "ShaderNodeVolumeScatter")
    vs.inputs["Density"].default_value = 0.0025
    vs.inputs["Color"].default_value = (1.0, 0.85, 0.7, 1)
    vs.inputs["Anisotropy"].default_value = 0.6
    # (world haze volume removed: it blacked out the frame; haze is faked in post)


SUN_AZ_DEG, SUN_EL_DEG = 83.0, 4.0
build_world()

# sun direction (HDRI sun is ~2 deg above the horizon, ahead of the pier, slightly left)
SUN_AZ = math.radians(88.0)  # direction the sun is IN (from origin), measured from +X towards +Y
sun_dir = Vector((math.cos(SUN_AZ), math.sin(SUN_AZ), math.sin(math.radians(4))))


def make_sun(name, col, strength, elev_deg, az_deg, cols, angle=0.6):
    ld = bpy.data.lights.new(name, "SUN")
    ld.color = col
    ld.energy = strength
    ld.angle = math.radians(angle)
    ob = bpy.data.objects.new(name, ld)
    d = Vector((math.cos(math.radians(az_deg)) * math.cos(math.radians(elev_deg)),
                math.sin(math.radians(az_deg)) * math.cos(math.radians(elev_deg)),
                math.sin(math.radians(elev_deg))))
    # sun lamp points along its -Z; we want light travelling FROM the direction d, so -Z -> -d
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    link(ob, C_MISC)
    return ob


sun_air = make_sun("SunAir", (1.0, 0.58, 0.28), 3.4, SUN_EL_DEG, SUN_AZ_DEG, None, angle=1.5)
sun_air.data.use_shadow = True
sun_under = make_sun("SunUnder", (0.55, 0.95, 0.95), 0.0, 72.0, 70.0, None, angle=1.0)
sun_under.data.use_shadow = False  # shadow pass cost 100+ s/frame; beams come from the shaft cards

# ----------------------------------------------------------------------------- sea surface
def build_sea():
    me = bpy.data.meshes.new("SeaMesh")
    ob = bpy.data.objects.new("Sea", me)
    link(ob, C_ABOVE, C_UNDER)
    # base plane consumed by the ocean modifier (GENERATE ignores it)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)
    bm.to_mesh(me)
    bm.free()
    om = ob.modifiers.new("Ocean", "OCEAN")
    om.geometry_mode = "GENERATE"
    om.repeat_x = 8
    om.repeat_y = 8
    om.resolution = 8
    om.spatial_size = 50
    om.wave_scale = 0.22
    om.choppiness = 1.0
    om.wind_velocity = 6.0
    om.wave_alignment = 0.4
    om.random_seed = 3
    om.use_foam = True
    om.foam_coverage = 0.3
    d = om.driver_add("time").driver
    d.type = "SCRIPTED"
    d.expression = "frame/24*0.9"
    ob.location = (0, 0, 0)
    # scale the generated 400m sheet to cover to the horizon
    ob.scale = (4, 4, 1)
    ob.location = (-800, -650, 0)

    m, nt = new_mat("Sea")
    tc = N(nt, "ShaderNodeTexCoord")
    geo = N(nt, "ShaderNodeNewGeometry")
    # front face: reflective sea seen from above
    top = principled(nt)
    set_in(top, "Base Color", (0.015, 0.06, 0.07))
    set_in(top, "Roughness", 0.04)
    set_in(top, "IOR", 1.33)
    set_in(top, "Specular IOR Level", 0.6)
    noise = N(nt, "ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    noise.noise_dimensions = "4D"
    dr = nt.nodes.new("ShaderNodeValue")
    drv = dr.outputs[0].driver_add("default_value").driver
    drv.type = "SCRIPTED"
    drv.expression = "frame/24*0.35"
    L(nt, dr.outputs[0], noise.inputs["W"])
    L(nt, tc.outputs["Object"], noise.inputs["Vector"])
    bump = N(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.5
    L(nt, noise.outputs["Fac"], bump.inputs["Height"])
    L(nt, bump.outputs[0], top.inputs["Normal"])
    # foam: from the ocean modifier's foam vertex colour if present -> keep subtle by using noise
    # back face (seen from below): bright translucent ceiling with Snell-window feel
    ceil = N(nt, "ShaderNodeEmission")
    cam = N(nt, "ShaderNodeCameraData")
    tr = N(nt, "ShaderNodeBsdfTranslucent")
    # ceiling colour: sunlit sky-water, attenuated with distance to match the volume
    dist = cam.outputs["View Distance"]
    e_r = MATH(nt, "POWER", 0.02, MATH(nt, "MULTIPLY", dist, 0.055))
    e_g = MATH(nt, "POWER", 0.55, MATH(nt, "MULTIPLY", dist, 0.055))
    e_b = MATH(nt, "POWER", 0.8, MATH(nt, "MULTIPLY", dist, 0.055))
    comb = N(nt, "ShaderNodeCombineColor")
    L(nt, MATH(nt, "MULTIPLY", e_r, 0.55), comb.inputs[0])
    L(nt, MATH(nt, "MULTIPLY", e_g, 1.5), comb.inputs[1])
    L(nt, MATH(nt, "MULTIPLY", e_b, 1.7), comb.inputs[2])
    # ripple modulation
    rip = N(nt, "ShaderNodeTexVoronoi")
    rip.feature = "DISTANCE_TO_EDGE"
    rip.inputs["Scale"].default_value = 0.35
    rip.voronoi_dimensions = "4D"
    L(nt, dr.outputs[0], rip.inputs["W"])
    L(nt, tc.outputs["Object"], rip.inputs["Vector"])
    ramp = N(nt, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = 0.35
    ramp.inputs["To Min"].default_value = 1.8
    ramp.inputs["To Max"].default_value = 0.7
    L(nt, rip.outputs["Distance"], ramp.inputs["Value"])
    sc = N(nt, "ShaderNodeVectorMath")
    sc.operation = "SCALE"
    L(nt, comb.outputs[0], sc.inputs[0])
    L(nt, ramp.outputs[0], sc.inputs[3])
    L(nt, sc.outputs[0], ceil.inputs["Color"])
    ceil.inputs["Strength"].default_value = 0.45
    mix = N(nt, "ShaderNodeMixShader")
    L(nt, geo.outputs["Backfacing"], mix.inputs[0])
    L(nt, top.outputs[0], mix.inputs[1])
    L(nt, ceil.outputs[0], mix.inputs[2])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, mix.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.use_smooth = True
    # shadows: let the sea not shadow the pier weirdly; it does not cast
    ob.visible_shadow = False
    return ob


sea = build_sea()

# ----------------------------------------------------------------------------- pier
def wood_material():
    m, nt = new_mat("PierWood")
    col, rough, nor = pbr_maps(nt, "weathered_planks", scale=0.45, strength=1.2)
    bs = principled(nt)
    # darker, wet, greyer wood + waterline slime
    tint = N(nt, "ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1.0
    tint.inputs[7].default_value = (0.75, 0.62, 0.5, 1)
    L(nt, col, tint.inputs[6])
    # dirt / wear noise in world space
    tc = N(nt, "ShaderNodeTexCoord")
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 8
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    ramp = N(nt, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.35
    ramp.inputs["From Max"].default_value = 0.7
    L(nt, nz.outputs["Fac"], ramp.inputs["Value"])
    dirt = N(nt, "ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.inputs[7].default_value = (0.03, 0.028, 0.025, 1)
    L(nt, ramp.outputs[0], dirt.inputs[0])
    L(nt, tint.outputs[2], dirt.inputs[6])
    # waterline slime: world z low
    wz = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], wz.inputs[0])
    geo = N(nt, "ShaderNodeNewGeometry")
    sepg = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo.outputs["Position"], sepg.inputs[0])
    zmask = N(nt, "ShaderNodeMapRange")
    zmask.inputs["From Min"].default_value = 1.1
    zmask.inputs["From Max"].default_value = 0.3
    L(nt, sepg.outputs["Z"], zmask.inputs["Value"])
    nzm = MATH(nt, "MULTIPLY", zmask.outputs[0], MATH(nt, "ADD", 0.5, nz.outputs["Fac"]))
    slime = N(nt, "ShaderNodeMix")
    slime.data_type = "RGBA"
    slime.inputs[7].default_value = (0.06, 0.13, 0.05, 1)
    L(nt, MATH(nt, "MINIMUM", nzm, 1.0), slime.inputs[0])
    L(nt, dirt.outputs[2], slime.inputs[6])
    L(nt, slime.outputs[2], bs.inputs["Base Color"])
    rr = MATH(nt, "MULTIPLY", rough, 1.0)
    L(nt, rr, bs.inputs["Roughness"])
    L(nt, nor, bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def metal_mat(name, col, rough=0.5, metallic=0.9):
    m, nt = new_mat(name)
    bs = principled(nt)
    set_in(bs, "Base Color", col)
    set_in(bs, "Metallic", metallic)
    set_in(bs, "Roughness", rough)
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 12
    nz.inputs["Detail"].default_value = 10
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nz.inputs["Vector"])
    rust = N(nt, "ShaderNodeMix")
    rust.data_type = "RGBA"
    rust.inputs[6].default_value = tuple(col) + (1.0,)
    rust.inputs[7].default_value = (0.25, 0.09, 0.03, 1)
    ramp = N(nt, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.4
    ramp.inputs["From Max"].default_value = 0.6
    L(nt, nz.outputs["Fac"], ramp.inputs["Value"])
    L(nt, ramp.outputs[0], rust.inputs[0])
    L(nt, rust.outputs[2], bs.inputs["Base Color"])
    L(nt, MATH(nt, "MULTIPLY", ramp.outputs[0], -0.0), bs.inputs["Metallic"]) if False else None
    bump = N(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    L(nt, nz.outputs["Fac"], bump.inputs["Height"])
    L(nt, bump.outputs[0], bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def simple_mat(name, col, rough=0.6, metallic=0.0, bump=0.0, sheen=0.0, sss=0.0):
    m, nt = new_mat(name)
    bs = principled(nt)
    set_in(bs, "Base Color", col)
    set_in(bs, "Roughness", rough)
    set_in(bs, "Metallic", metallic)
    if sheen:
        set_in(bs, "Sheen Weight", sheen)
        set_in(bs, "Sheen Roughness", 0.4)
    if sss:
        set_in(bs, "Subsurface Weight", sss)
        set_in(bs, "Subsurface Radius", (1.0, 0.35, 0.2))
        set_in(bs, "Subsurface Scale", 0.05)
    if bump:
        nz = N(nt, "ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 300
        nz.inputs["Detail"].default_value = 3
        L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nz.inputs["Vector"])
        bp = N(nt, "ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.002
        L(nt, nz.outputs["Fac"], bp.inputs["Height"])
        L(nt, bp.outputs[0], bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def build_pier():
    wood = wood_material()
    iron = metal_mat("Iron", (0.15, 0.14, 0.13), 0.6, 0.85)
    rope_m = simple_mat("Rope", (0.32, 0.26, 0.16), 0.9, bump=0.5)
    Y0, Y1 = -26.0, 1.05
    W = 3.2
    # --- deck planks (one mesh), boards run across the pier, uv jitter per board
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV")
    y = Y0
    while y < Y1:
        bw = rnd.uniform(0.13, 0.17)
        y2 = min(y + bw, Y1)
        zoff = rnd.uniform(-0.006, 0.010)
        tilt = rnd.uniform(-0.004, 0.004)
        x0, x1 = -W / 2 + rnd.uniform(-0.02, 0.02), W / 2 + rnd.uniform(-0.02, 0.02)
        th = 0.05
        vs = [bm.verts.new(v) for v in [
            (x0, y, DECK + zoff), (x1, y, DECK + zoff + tilt), (x1, y2, DECK + zoff + tilt), (x0, y2, DECK + zoff),
            (x0, y, DECK + zoff - th), (x1, y, DECK + zoff - th), (x1, y2, DECK + zoff - th), (x0, y2, DECK + zoff - th)]]
        faces = [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        u_off = rnd.random()
        for fi in faces:
            f = bm.faces.new([vs[i] for i in fi])
        y = y2 + rnd.uniform(0.008, 0.02)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.faces.ensure_lookup_table()
    # per-board texture offset via object-space noise is enough as box-mapping uses position
    deck = mesh_obj("Deck", bm, [C_ABOVE], smooth=False)
    deck.data.materials.append(wood)
    # bevel
    bv = deck.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.006
    bv.segments = 2
    # --- stringers + posts + crossbeams
    bm = bmesh.new()
    for x in (-1.4, -0.5, 0.5, 1.4):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x, (Y0 + Y1) / 2, DECK - 0.24)) @ Matrix.Diagonal((0.16, (Y1 - Y0), 0.26, 1)))
    stringers = mesh_obj("Stringers", bm, [C_ABOVE], smooth=False)
    stringers.data.materials.append(wood)
    bm = bmesh.new()
    y = Y0 + 1.0
    while y <= Y1 - 0.2:
        for x in (-1.45, 1.45):
            h = DECK + 0.05 + rnd.uniform(-0.05, 0.02)
            bot = -8.0
            r = rnd.uniform(0.14, 0.18)
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r * 0.95, depth=h - bot,
                                  matrix=Matrix.Translation((x + rnd.uniform(-0.03, 0.03), y + rnd.uniform(-.05, .05), (h + bot) / 2)))
        y += 3.0
    # end cluster
    for dx, dy in ((-1.5, 1.0), (1.5, 1.0), (0.0, 1.12)):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.17, radius2=0.16, depth=DECK + 0.6 + 8,
                              matrix=Matrix.Translation((dx, dy, (DECK + 0.6 - 8) / 2)))
    posts = mesh_obj("Posts", bm, [C_ABOVE], smooth=True)
    posts.data.materials.append(wood)
    # displace posts for organic feel
    tx = bpy.data.textures.new("PostNoise", "CLOUDS")
    tx.noise_scale = 0.35
    dm = posts.modifiers.new("Disp", "DISPLACE")
    dm.texture = tx
    dm.strength = 0.03
    dm.mid_level = 0.5
    # --- side rail (left) with rope, and bollards
    bm = bmesh.new()
    y = Y0
    while y < Y1 - 0.5:
        x = -1.55
        h = rnd.uniform(0.8, 0.9)
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x, y, DECK + h / 2)) @ Matrix.Diagonal((0.09, 0.09, h, 1)))
        y += 2.4
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((-1.55, (Y0 + Y1 - 0.5) / 2, DECK + 0.8)) @ Matrix.Diagonal((0.07, (Y1 - 0.5 - Y0), 0.07, 1)))
    rail = mesh_obj("Rail", bm, [C_ABOVE], smooth=False)
    rail.data.materials.append(wood)
    rail.modifiers.new("Bevel", "BEVEL").width = 0.008
    # bollards (iron)
    bm = bmesh.new()
    for y in (-6.4, -1.2):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.1, radius2=0.075, depth=0.42,
                              matrix=Matrix.Translation((1.35, y, DECK + 0.21)))
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.085,
                                  matrix=Matrix.Translation((1.35, y, DECK + 0.44)))
    boll = mesh_obj("Bollards", bm, [C_ABOVE])
    boll.data.materials.append(iron)
    # lamp post at the end
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.05, radius2=0.04, depth=2.8,
                          matrix=Matrix.Translation((1.3, -14.5, DECK + 1.4)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.16, radius2=0.03, depth=0.2,
                          matrix=Matrix.Translation((1.3, -14.5, DECK + 2.85)))
    lamp = mesh_obj("LampPost", bm, [C_ABOVE])
    lamp.data.materials.append(iron)
    # rope coil + hanging rope along rail
    bm = bmesh.new()
    ropepts = []
    y = Y0 + 2.0
    n = 60
    # coil
    cx, cy = 1.0, -3.6
    for i in range(0, 5 * 24):
        a = i / 24 * 2 * math.pi
        rr = 0.17 - i * 0.0004
        ropepts.append(Vector((cx + rr * math.cos(a), cy + rr * math.sin(a), DECK + 0.03 + i * 0.0006)))
    verts = []
    for i, p in enumerate(ropepts):
        ring = []
        for k in range(6):
            a = k / 6 * 2 * math.pi
            ring.append(bm.verts.new(p + Vector((math.cos(a) * 0.017, math.sin(a) * 0.017, 0))))
        verts.append(ring)
    for i in range(len(verts) - 1):
        for k in range(6):
            bm.faces.new((verts[i][k], verts[i][(k + 1) % 6], verts[i + 1][(k + 1) % 6], verts[i + 1][k]))
    rope = mesh_obj("Rope", bm, [C_ABOVE])
    rope.data.materials.append(rope_m)
    # crates / debris on deck
    bm = bmesh.new()
    for (x, y, sz, rot) in ((1.15, -9.2, 0.45, 0.4), (-1.1, -12.0, 0.38, -0.2), (0.9, -7.6, 0.3, 0.9)):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((x, y, DECK + sz / 2)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Diagonal((sz, sz * 1.3, sz, 1)))
    crates = mesh_obj("Crates", bm, [C_ABOVE], smooth=False)
    crates.data.materials.append(wood)
    crates.modifiers.new("Bevel", "BEVEL").width = 0.01
    return deck


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

build_pier_v3()

# ----------------------------------------------------------------------------- the kid (back view)
KID = {}


def smoothstep(a, b, x):
    t = min(1, max(0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def cap_mesh(name, r0, r1, length, seg=12, rings=8, cols=None, mat=None):
    """tapered capsule pointing DOWN (-Z) from origin, length along -Z"""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        t = (v.co.z + 1) / 2  # 0 bottom .. 1 top
        r = lerp(r1, r0, t)
        v.co = Vector((v.co.x * r, v.co.y * r * 0.95, -length * (1 - t)))
    ob = mesh_obj(name, bm, cols or [C_ABOVE, C_UNDER])
    if mat:
        ob.data.materials.append(mat)
    ob.modifiers.new("Sub", "SUBSURF").levels = 1
    return ob


def stripe_mat(name):
    m, nt = new_mat(name)
    bs = principled(nt)
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], sp.inputs[0])
    st = MATH(nt, "GREATER_THAN", MATH(nt, "SINE", MATH(nt, "MULTIPLY", sp.outputs["Z"], 60.0)), 0.0)
    cm = N(nt, "ShaderNodeMix")
    cm.data_type = "RGBA"
    cm.inputs[6].default_value = (0.03, 0.06, 0.20, 1)
    cm.inputs[7].default_value = (0.80, 0.80, 0.78, 1)
    L(nt, st, cm.inputs[0])
    L(nt, cm.outputs[2], bs.inputs["Base Color"])
    set_in(bs, "Roughness", 0.9)
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def build_kid():
    skin = simple_mat("Skin", (0.50, 0.30, 0.22), 0.55)
    hair = simple_mat("Hair", (0.50, 0.33, 0.10), 0.6)
    hood = stripe_mat("StripeTee")
    shorts = simple_mat("Shorts", (0.04, 0.10, 0.28), 0.85, bump=0.8)
    shoe = skin
    cols = [C_ABOVE, C_UNDER]
    root = bpy.data.objects.new("KidRoot", None)
    link(root, C_MISC)
    KID["root"] = root

    def part(name, parent, loc, mesh_ob=None):
        e = bpy.data.objects.new(name, None)
        e.parent = parent
        e.location = loc
        link(e, C_MISC)
        KID[name] = e
        if mesh_ob:
            mesh_ob.parent = e
        return e

    # pelvis mesh (shorts)
    pel = part("pelvis", root, (0, 0, 0))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0,
                              matrix=Matrix.Diagonal((0.105, 0.075, 0.085, 1)))
    ob = mesh_obj("pelvis_m", bm, cols)
    ob.data.materials.append(shorts)
    ob.parent = pel
    ob.location = (0, 0, -0.02)
    # torso
    tor = part("torso", pel, (0, 0, 0.02))
    t = cap_mesh("torso_m", 0.125, 0.15, 0.38, seg=16, rings=10, mat=hood)
    # cap_mesh points down; flip to go up
    t.rotation_euler = (math.pi, 0, 0)
    t.location = (0, 0, 0.0)
    t.scale = (1.0, 0.72, 1.0)
    t.parent = tor
    # hood bulge at back of neck
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0, matrix=Matrix.Diagonal((0.075, 0.05, 0.045, 1)))
    hb = mesh_obj("hood_m", bm, cols)
    hb.data.materials.append(hood)
    hb.parent = tor
    hb.location = (0, -0.06, 0.39)
    # head + hair
    head = part("head", tor, (0, 0.005, 0.44))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=1.0, matrix=Matrix.Diagonal((0.068, 0.082, 0.088, 1)))
    hm = mesh_obj("head_m", bm, cols)
    hm.data.materials.append(skin)
    hm.parent = head
    hm.location = (0, 0, 0.06)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=1.0, matrix=Matrix.Diagonal((0.085, 0.095, 0.10, 1)))
    hr = mesh_obj("hair_m", bm, cols)
    hr.data.materials.append(hair)
    hr.parent = head
    hr.location = (0, -0.012, 0.075)
    # ears
    for s in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0, matrix=Matrix.Diagonal((0.010, 0.022, 0.03, 1)))
        em = mesh_obj("ear_m", bm, cols)
        em.data.materials.append(skin)
        em.parent = head
        em.location = (0.07 * s, 0.0, 0.06)
    # arms
    for s, nm in ((-1, "L"), (1, "R")):
        sh = part(f"shoulder{nm}", tor, (0.15 * s, 0.0, 0.33))
        u = cap_mesh(f"uarm_m{nm}", 0.038, 0.032, 0.22, seg=10, rings=6, mat=hood)
        u.parent = sh
        el = part(f"elbow{nm}", sh, (0, 0, -0.22))
        f = cap_mesh(f"farm_m{nm}", 0.032, 0.026, 0.19, seg=10, rings=6, mat=hood)
        f.parent = el
        wr = part(f"wrist{nm}", el, (0, 0, -0.19))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0, matrix=Matrix.Diagonal((0.022, 0.014, 0.035, 1)))
        hd = mesh_obj(f"hand_m{nm}", bm, cols)
        hd.data.materials.append(skin)
        hd.parent = wr
        hd.location = (0, 0, -0.03)
    # legs
    for s, nm in ((-1, "L"), (1, "R")):
        hp = part(f"hip{nm}", pel, (0.058 * s, 0.0, -0.05))
        th = cap_mesh(f"thigh_m{nm}", 0.052, 0.038, 0.29, seg=12, rings=6, mat=skin)
        th.parent = hp
        # shorts leg
        sl = cap_mesh(f"shortleg_m{nm}", 0.068, 0.062, 0.17, seg=12, rings=6, mat=shorts)
        sl.parent = hp
        kn = part(f"knee{nm}", hp, (0, 0, -0.29))
        sn = cap_mesh(f"shin_m{nm}", 0.036, 0.026, 0.28, seg=12, rings=6, mat=skin)
        sn.parent = kn
        an = part(f"ankle{nm}", kn, (0, 0, -0.28))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0, matrix=Matrix.Diagonal((0.036, 0.095, 0.036, 1)))
        sh_m = mesh_obj(f"shoe_m{nm}", bm, cols)
        sh_m.data.materials.append(shoe)
        sh_m.parent = an
        sh_m.location = (0, 0.04, -0.03)
    return root


build_kid()

# ---- kid animation (analytic) ------------------------------------------------
TAKEOFF_V1 = 49
KY0 = -10.5
RUNV = 4.5
FLY_VY = 4.44
FLY_VH = 4.0
KX0, KX_T, FLY_VX = 0.3, 1.9, 2.3          # veer to the side rail, then vault it
KID_EX = 3.4
KID_ENTRY_Y = 1.85


def kid_state_v1(f):
    """returns dict with root pos and joint angles for frame f"""
    d = {}
    t_run = (f - 1) / 24.0
    ph = 2 * math.pi * (f - 1) / 16.0
    if f <= TAKEOFF_V1:
        y = KY0 + RUNV * t_run
        # slight acceleration into the run (starts already running)
        crouch = smoothstep(TAKEOFF_V1 - 5, TAKEOFF_V1 - 1, f) * (1 - smoothstep(TAKEOFF_V1 - 1, TAKEOFF_V1 + 1, f))
        bob = 0.03 * math.cos(2 * ph)
        z = DECK + 0.575 + bob - 0.06 * crouch
        d["pos"] = (KX0 + (KX_T - KX0) * smoothstep(TAKEOFF_V1 - 34, TAKEOFF_V1 - 3, f) + 0.04 * math.sin(ph), y, z)
        sw = 0.75 * (1 - 0.5 * crouch)
        d["hipL"] = 0.15 + sw * math.sin(ph)
        d["hipR"] = 0.15 - sw * math.sin(ph)
        d["kneeL"] = 0.25 + 0.95 * max(0.0, math.cos(ph)) ** 1.3
        d["kneeR"] = 0.25 + 0.95 * max(0.0, -math.cos(ph)) ** 1.3
        d["shL"] = -0.7 * math.sin(ph)
        d["shR"] = 0.7 * math.sin(ph)
        d["elL"] = 1.35 + 0.15 * math.cos(ph)
        d["elR"] = 1.35 - 0.15 * math.cos(ph)
        d["armAbd"] = 0.06
        d["lean"] = -0.20 - 0.12 * crouch
        d["twist"] = 0.14 * math.sin(ph)
        d["headp"] = 0.12
        d["pitch"] = 0.0
        return d
    ta = (f - TAKEOFF_V1) / 24.0
    if f <= HOOK_V1:
        z = DECK + 0.575 + FLY_VY * ta - 4.9 * ta * ta
        y = KY0 + RUNV * (TAKEOFF_V1 - 1) / 24.0 + FLY_VH * ta
        tuck = smoothstep(TAKEOFF_V1 + 1, TAKEOFF_V1 + 11, f)
        arms_up = smoothstep(TAKEOFF_V1, TAKEOFF_V1 + 3, f) * (1 - smoothstep(TAKEOFF_V1 + 5, TAKEOFF_V1 + 12, f))
        d["pos"] = (KX_T + FLY_VX * ta, y, z)
        d["hipL"] = lerp(0.6, 1.95, tuck)
        d["hipR"] = lerp(-0.2, 1.85, tuck)
        d["kneeL"] = lerp(0.3, 2.1, tuck)
        d["kneeR"] = lerp(0.6, 2.0, tuck)
        d["shL"] = lerp(-0.9, 1.15, tuck) + 2.4 * arms_up * 0.0
        d["shR"] = lerp(-0.7, 1.15, tuck)
        d["shL"] += arms_up * 2.6
        d["shR"] += arms_up * 2.6
        d["elL"] = lerp(0.8, 1.3, tuck)
        d["elR"] = lerp(0.8, 1.3, tuck)
        d["armAbd"] = lerp(0.35, 0.10, tuck)
        d["lean"] = -0.20 - 0.55 * tuck
        d["twist"] = 0.0
        d["headp"] = 0.10 + 0.45 * tuck
        d["pitch"] = -0.45 * smoothstep(TAKEOFF_V1, HOOK_V1, f)
        return d
    # underwater
    tt = (f - HOOK_V1)
    vz0, vy0 = -6.2, 3.3
    tau = 9.0
    z = 0.35 + vz0 * tau * (1 - math.exp(-tt / tau)) / 24.0 - 0.05 * tt / 24.0 * 0  # metres: v per second
    y_at = KY0 + RUNV * (TAKEOFF_V1 - 1) / 24.0 + FLY_VH * (HOOK_V1 - TAKEOFF_V1) / 24.0
    y = y_at + vy0 * tau * (1 - math.exp(-tt / tau)) / 24.0
    z = 0.35 + vz0 * tau * (1 - math.exp(-tt / tau)) / 24.0 - 0.28 * max(0, tt - 20) / 24.0
    rel = smoothstep(HOOK_V1 + 8, HOOK_V1 + 40, f)
    d["pos"] = (KID_EX + 0.12 * rel + 0.4 * tau * (1 - math.exp(-tt / tau)) / 24.0, y, z)
    d["hipL"] = lerp(1.95, 0.55, rel)
    d["hipR"] = lerp(1.85, 0.25, rel)
    d["kneeL"] = lerp(2.1, 0.9, rel)
    d["kneeR"] = lerp(2.0, 0.6, rel)
    d["shL"] = lerp(1.15, 2.3, rel)
    d["shR"] = lerp(1.15, 2.1, rel)
    d["elL"] = lerp(1.3, 0.3, rel)
    d["elR"] = lerp(1.3, 0.3, rel)
    d["armAbd"] = lerp(0.10, 0.6, rel)
    d["lean"] = lerp(-0.75, -0.25, rel)
    d["twist"] = 0.1 * rel * math.sin(tt * 0.12)
    d["headp"] = lerp(0.55, -0.1, rel)
    d["pitch"] = lerp(-0.45, -0.75, smoothstep(HOOK_V1, HOOK_V1 + 14, f)) + 0.0 * rel
    return d


_VC = {}


def _sm(arr, sigma=1.3):
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(arr, (r, r), mode="edge"), k, mode="valid")


def _vault_tables():
    if _VC:
        return _VC
    d62 = kid_state_v1(62 - SHIFT)
    frs = np.arange(62, HOOK + 1)

    def K(keys, smooth=1.3):
        ks = sorted(keys)
        return _sm(np.interp(frs, [k[0] for k in ks], [k[1] for k in ks]), smooth)
    P0 = d62["pos"]
    _VC["frs"] = frs
    _VC["x"] = K([(62, P0[0]), (65, 1.95), (67, 2.05), (69, 2.3), (72, 2.75), (75, 3.0), (HOOK, KID_EX)])
    _VC["y"] = K([(62, P0[1]), (66, -0.9), (70, -0.4), (75, 0.2), (HOOK, KID_ENTRY_Y)])
    z = np.interp(frs, [62, 64, 66, 68, 70, 72, 75], [P0[2], 2.75, 3.1, 3.2, 3.2, 3.18, 3.1])
    tb = (frs - 75) / 24.0
    vz = (0.55 - 3.1 + 4.9 * ((HOOK - 75) / 24.0) ** 2) / ((HOOK - 75) / 24.0)
    z = np.where(frs <= 75, z, 3.1 + vz * tb - 4.9 * tb * tb)
    _VC["z"] = _sm(z, 1.0)
    _VC["z"][-1] = 0.55
    _VC["roll"] = K([(62, 0), (64, -0.6), (66, -1.3), (68, -1.7), (70, -1.8), (75, -1.8), (79, -1.6), (85, -0.9), (91, -0.3), (HOOK, 0.0)])
    for nm in ("hipL", "hipR"):
        _VC[nm] = K([(62, d62[nm]), (64, 1.2), (66, 1.4), (70, 1.3), (73, 0.6), (76, 0.3), (85, 0.15), (HOOK, 0.05)])
    for nm in ("kneeL", "kneeR"):
        _VC[nm] = K([(62, d62[nm]), (64, 1.2), (66, 1.6), (70, 1.5), (73, 0.8), (76, 0.4), (85, 0.2), (HOOK, 0.08)])
    for nm in ("shL", "shR"):
        _VC[nm] = K([(62, d62[nm]), (66, 0.9), (69, 0.5), (72, 0.8), (75, 2.2), (82, 2.7), (HOOK, 2.9)])
    for nm in ("shLy", "shRy"):
        _VC[nm] = K([(62, 0), (66, -0.6), (69, -1.15), (72, -0.7), (75, 0.0), (HOOK, 0.0)])
    for nm in ("elL", "elR"):
        _VC[nm] = K([(62, d62[nm]), (66, 0.5), (69, 0.2), (75, 0.3), (HOOK, 0.2)])
    _VC["armAbd"] = K([(62, d62["armAbd"]), (75, 0.1), (82, 0.5), (HOOK, 0.3)])
    _VC["lean"] = K([(62, d62["lean"]), (66, -0.15), (70, 0.1), (75, 0.25), (85, 0.05), (HOOK, -0.05)])
    _VC["headp"] = K([(62, d62["headp"]), (70, 0.3), (HOOK, -0.05)])
    return _VC


def kid_vault(f):
    T = _vault_tables()
    i = int(f - 62)
    d = {"pos": (float(T["x"][i]), float(T["y"][i]), float(T["z"][i])), "twist": 0.0, "pitch": 0.0, "roll": float(T["roll"][i])}
    for nm in ("hipL", "hipR", "kneeL", "kneeR", "shL", "shR", "shLy", "shRy", "elL", "elR", "armAbd", "lean", "headp"):
        d[nm] = float(T[nm][i])
    return d


def kid_uw(f):
    d = {}
    tt = f - HOOK
    vz0, vy0, tau = -6.2, 1.0, 9.0
    z = 0.55 + vz0 * tau * (1 - math.exp(-tt / tau)) / 24.0 - 0.28 * max(0, tt - 20) / 24.0
    y = KID_ENTRY_Y + vy0 * tau * (1 - math.exp(-tt / tau)) / 24.0
    rel = smoothstep(HOOK + 8, HOOK + 40, f)
    d["pos"] = (KID_EX + 0.12 * rel + 0.4 * tau * (1 - math.exp(-tt / tau)) / 24.0, y, z)
    d["hipL"] = lerp(0.05, 0.55, rel)
    d["hipR"] = lerp(0.05, 0.25, rel)
    d["kneeL"] = lerp(0.08, 0.9, rel)
    d["kneeR"] = lerp(0.08, 0.6, rel)
    d["shL"] = lerp(2.9, 2.3, rel)
    d["shR"] = lerp(2.9, 2.1, rel)
    d["elL"] = lerp(0.2, 0.3, rel)
    d["elR"] = lerp(0.2, 0.3, rel)
    d["armAbd"] = lerp(0.3, 0.6, rel)
    d["lean"] = lerp(-0.05, -0.25, rel)
    d["twist"] = 0.1 * rel * math.sin(tt * 0.12)
    d["headp"] = lerp(0.0, -0.1, rel)
    d["pitch"] = lerp(0.0, -0.5, smoothstep(HOOK, HOOK + 14, f))
    d["roll"] = 0.0
    return d


def kid_state(f):
    if f <= 62:
        return kid_state_v1(f - SHIFT)
    if f <= HOOK:
        return kid_vault(f)
    return kid_uw(f)


TAKEOFF = 62


def animate_kid():
    for f in range(1, NF + 1):
        d = kid_state(f)
        r = KID["root"]
        r.location = d["pos"]
        r.keyframe_insert("location", frame=f)
        r.rotation_euler = (0, d.get("roll", 0.0), 0)
        r.keyframe_insert("rotation_euler", frame=f)
        KID["pelvis"].rotation_euler = (d["pitch"], 0, d["twist"] * -0.6)
        KID["pelvis"].keyframe_insert("rotation_euler", frame=f)
        KID["torso"].rotation_euler = (d["lean"], 0, d["twist"])
        KID["torso"].keyframe_insert("rotation_euler", frame=f)
        KID["head"].rotation_euler = (d["headp"] - d["lean"] * 0.4 - 0.1, 0, -d["twist"] * 0.6)
        KID["head"].keyframe_insert("rotation_euler", frame=f)
        for s, nm in ((-1, "L"), (1, "R")):
            KID[f"hip{nm}"].rotation_euler = (d[f"hip{nm}"], 0, 0.04 * s)
            KID[f"hip{nm}"].keyframe_insert("rotation_euler", frame=f)
            KID[f"knee{nm}"].rotation_euler = (-d[f"knee{nm}"], 0, 0)
            KID[f"knee{nm}"].keyframe_insert("rotation_euler", frame=f)
            KID[f"ankle{nm}"].rotation_euler = (0.5 + 0.2 * math.sin(f), 0, 0) if False else (0.35, 0, 0)
            KID[f"ankle{nm}"].keyframe_insert("rotation_euler", frame=f)
            KID[f"shoulder{nm}"].rotation_euler = (d[f"sh{nm}"], d.get(f"sh{nm}y", 0.0), d["armAbd"] * s)
            KID[f"shoulder{nm}"].keyframe_insert("rotation_euler", frame=f)
            KID[f"elbow{nm}"].rotation_euler = (d[f"el{nm}"], 0, 0)
            KID[f"elbow{nm}"].keyframe_insert("rotation_euler", frame=f)
    for ob in KID.values():
        ad = ob.animation_data
        if ad and ad.action:
            for lay in ad.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "LINEAR"


animate_kid()
KID_ENTRY_Y = 1.85
KID_ENTRY_X = KID_EX
print("kid entry", KID_ENTRY_X, KID_ENTRY_Y)
BEACH = build_beach()



# ============================================================================= PART 2
def keyed_bool(ob, prop, changes):
    """changes: list of (frame, value) ; constant interpolation"""
    for f, v in changes:
        setattr(ob, prop, v)
        ob.keyframe_insert(prop, frame=f)
    ad = ob.animation_data
    for lay in ad.action.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == prop:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "CONSTANT"


def hidden_until(ob, f):
    keyed_bool(ob, "hide_render", [(1, True), (f, False)])
    ob.hide_viewport = False


def visible_until(ob, f):
    keyed_bool(ob, "hide_render", [(1, False), (f, True)])


# ----------------------------------------------------------------------------- camera
def gauss_smooth(arr, sigma):
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(arr, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, i], k, mode="valid") for i in range(arr.shape[1])], 1)


def interp_keys(keys):
    fr = np.arange(1, NF + 1)
    ks = sorted(keys)
    kf = [k[0] for k in ks]
    out = np.stack([np.interp(fr, kf, [k[1][i] for k in ks]) for i in range(3)], 1)
    return out


def build_camera():
    cd = bpy.data.cameras.new("Cam")
    cd.lens = 18
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 1500
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.4
    cam = bpy.data.objects.new("Cam", cd)
    link(cam, C_MISC)
    scene.camera = cam

    # ---- base path (v2: 24 s). pre-hook = v1 keys shifted by SHIFT, then a long dive
    S_ = SHIFT
    pos_keys = [
        (1, (-0.1, -15.7, 1.95)), (14, (-0.1, -13.4, 1.95)), (40, (0.2, -8.6, 1.93)), (62, (0.6, -4.3, 1.98)),
        (68, (1.0, -3.0, 2.25)), (73, (1.5, -1.5, 2.90)), (78, (2.4, -0.2, 3.40)), (84, (3.0, 0.1, 3.20)),
        (90, (3.25, 0.1, 2.60)), (94, (3.3, 0.4, 1.90)), (97, (3.35, 0.8, 1.40)), (100, (3.4, 1.4, 0.5)),
        (104, (3.45, 2.0, -0.5)), (109, (3.5, 2.7, -1.3)), (120, (3.4, 3.4, -3.2)),
        (192, (3.4, 7.5, -9.0)), (288, (0.0, 10.5, -15.5)), (384, (0.0, 34.0, -16.4)),
        (480, (0.0, 66.0, -16.2)), (528, (0.0, 76.0, -16.0)), (576, (0.0, 79.6, -15.8)),
    ]
    pos = gauss_smooth(interp_keys(pos_keys), 3.5)
    # underwater street: gentle weave, stronger while speeding
    frr = np.arange(1, NF + 1)
    wv_ = np.clip((frr - 288) / 60.0, 0, 1) * np.clip((560 - frr) / 60.0, 0, 1)
    pos[:, 0] += 0.9 * np.sin(frr / 24.0 * 0.85) * wv_
    pos[:, 2] += 0.35 * np.sin(frr / 24.0 * 0.6 + 1.0) * wv_
    # aim points
    aim = np.zeros((NF, 3))
    for i, f in enumerate(range(1, NF + 1)):
        ks = kid_state(min(f, NF))
        kp = Vector(ks["pos"])
        if f <= 70 + S_:
            aim[i] = (kp.x * 1.0, kp.y + 0.2, kp.z + 0.72)
        else:
            aim[i] = (kp.x * 1.0, kp.y + 0.2, kp.z + 0.5)
    late = interp_keys([
        (84 + S_, (3.4, 1.85, 0.4)), (88 + S_, (3.5, 2.6, -0.3)), (92 + S_, (3.5, 3.5, -1.5)), (98 + S_, (3.4, 4.5, -3.6)),
        (150, (0.2, 15.0, -9.5)), (192, (0.2, 24.0, -13.5)), (288, (0, 32.0, -17.5)), (384, (0, 58.0, -18.0)),
        (440, (0, 80.0, -16.5)), (490, (0, 84.0, -15.8)), (576, (0, 84.0, -15.7)),
    ])
    kid_after = np.array([aim[i] for i in range(NF)])
    for i, f in enumerate(range(1, NF + 1)):
        if f > 80 + S_:
            w = smoothstep(80 + S_, 90 + S_, f)
            aim[i] = kid_after[i] * (1 - w) + late[i] * w if f < 92 + S_ else late[i]
    for i, f in enumerate(range(1, NF + 1)):
        if 92 + S_ < f <= 122 + S_:
            ks = kid_state(f)
            kp = Vector(ks["pos"])
            wk = smoothstep(92 + S_, 98 + S_, f) * (1 - smoothstep(104 + S_, 122 + S_, f))
            tgt = np.array([kp.x, kp.y, kp.z - 0.2])
            aim[i] = late[i] * (1 - wk) + tgt * wk
    aim = gauss_smooth(aim, 3.0)
    aim[110 + 0:] = gauss_smooth(aim, 8.0)[110:]  # smoother look-around in the long dive
    # ================= v4: FPV dive through the forum (frames 109..480) =================
    aim_old = aim.copy()
    BANK = np.zeros(NF)
    F0, F1 = 109, 480
    CX_, CY_, RO_ = 0.5, 63.5, 4.5          # toppled statue = orbit centre
    WIN_ = np.array([0.0, 84.0, -15.6])

    wp = [(124, (3.3, 5.6, -8.0)), (148, (1.8, 11.0, -18.6)), (162, (1.4, 16.8, -19.4)),
          (175, (1.4, 22.6, -19.5)), (188, (-1.4, 27.0, -19.7)), (201, (1.4, 31.4, -19.4)),
          (214, (-1.4, 35.8, -19.7)), (227, (1.4, 40.2, -19.5)), (240, (-1.4, 44.6, -19.6)),
          (252, (0.6, 49.0, -20.3)), (260, (2.4, 51.4, -21.0)), (272, (0.5, 56.0, -18.2)),
          (279, (CX_, CY_ - RO_, -19.0))]
    for k_ in range(1, 7):                  # clockwise half orbit, 30 deg steps
        a_ = math.radians(-90 - 30 * k_)
        wp.append((int(round(279 + 6.5 * k_)), (CX_ + RO_ * math.cos(a_), CY_ + RO_ * math.sin(a_), -19.0 - 0.7 * math.sin(k_ * 0.5))))
    wp += [(328, (4.5, 68.6, -19.6)), (337, (7.0, 70.6, -19.8)), (346, (8.6, 73.3, -19.5)), (352, (8.8, 75.8, -18.8)),
           (357, (8.8, 77.4, -18.0)), (365, (8.8, 80.0, -17.9)), (373, (6.0, 81.3, -18.0)), (386, (1.0, 81.6, -18.4)),
           (397, (-3.6, 80.6, -18.9)), (403, (-4.4, 78.4, -19.4)), (409, (-4.2, 75.5, -19.9)),
           (417, (-4.0, 72.5, -20.3)), (426, (-3.0, 68.5, -20.9)), (437, (-2.0, 63.5, -19.8)),
           (446, (0.0, 60.8, -17.8)), (454, (1.8, 61.8, -16.9)), (462, (1.0, 63.3, -16.5)), (470, (0.1, 64.8, -16.3))]
    wp.sort(key=lambda w: w[0])
    wfr = np.array([F0] + [w[0] for w in wp] + [F1], float)
    WP = np.array([pos[F0 - 1]] + [w[1] for w in wp] + [pos[F1 - 1]], float)
    Mv = np.zeros_like(WP)
    for i_ in range(len(WP)):
        if i_ == 0:
            Mv[i_] = pos[F0 - 1] - pos[F0 - 2]
        elif i_ == len(WP) - 1:
            Mv[i_] = pos[F1 - 1] - pos[F1 - 2]
        else:
            Mv[i_] = (WP[i_ + 1] - WP[i_ - 1]) / (wfr[i_ + 1] - wfr[i_ - 1])
    PP = np.zeros((F1 - F0 + 1, 3))
    for k_, f_ in enumerate(range(F0, F1 + 1)):
        i_ = int(min(max(np.searchsorted(wfr, f_, side="right") - 1, 0), len(WP) - 2))
        h_ = wfr[i_ + 1] - wfr[i_]
        t_ = (f_ - wfr[i_]) / h_
        PP[k_] = ((2 * t_**3 - 3 * t_**2 + 1) * WP[i_] + (t_**3 - 2 * t_**2 + t_) * h_ * Mv[i_] +
                  (-2 * t_**3 + 3 * t_**2) * WP[i_ + 1] + (t_**3 - t_**2) * h_ * Mv[i_ + 1])
    # drone wobble (small, off-axis, two frequencies)
    tt_ = np.arange(F0, F1 + 1) / 24.0
    ramp_ = np.clip((tt_ - 4.6) / 0.6, 0, 1) * np.clip((20.0 - tt_) / 0.6, 0, 1)
    PP[:, 0] += ramp_ * (0.05 * np.sin(tt_ * 11.0) + 0.03 * np.sin(tt_ * 19.0 + 1.3))
    PP[:, 2] += ramp_ * (0.05 * np.sin(tt_ * 9.0 + 0.7) + 0.03 * np.sin(tt_ * 17.0))
    pos[F0 - 1:F1] = PP
    # look direction: tangent (look-ahead), statue during the orbit, window at the end, old aim at the start
    n_ = len(PP)
    look_t = np.zeros((n_, 3))
    for k_ in range(n_):
        a0, a1 = max(0, k_ - 3), min(n_ - 1, k_ + 5)
        look_t[k_] = PP[a1] - PP[a0]
    yaw_t = np.unwrap(np.arctan2(look_t[:, 0], look_t[:, 1]))
    pit_t = np.arctan2(look_t[:, 2], np.hypot(look_t[:, 0], look_t[:, 1]))
    fr_k = np.arange(F0, F1 + 1)

    def ang_to(target, ref_yaw):
        d_ = target - PP
        y_ = np.arctan2(d_[:, 0], d_[:, 1])
        y_ = y_ + 2 * np.pi * np.round((ref_yaw - y_) / (2 * np.pi))
        return y_, np.arctan2(d_[:, 2], np.hypot(d_[:, 0], d_[:, 1]))
    yaw_c, pit_c = ang_to(np.array([CX_, CY_, SEABED + 1.0]), yaw_t)
    wc = np.array([smoothstep(279, 288, f) * (1 - smoothstep(312, 324, f)) for f in fr_k])
    yaw_w, pit_w = ang_to(WIN_, yaw_t)
    ww = np.array([smoothstep(452, 476, f) for f in fr_k])
    yaw_o, pit_o = ang_to(aim_old[F0 - 1:F1], yaw_t)
    wo = np.array([1 - smoothstep(114, 142, f) for f in fr_k])
    yt = yaw_t * (1 - wc) + yaw_c * wc
    pt = pit_t * (1 - wc) + pit_c * wc
    yt = yt * (1 - ww) + yaw_w * ww
    pt = pt * (1 - ww) + pit_w * ww
    yt = yt * (1 - wo) + yaw_o * wo
    pt = pt * (1 - wo) + pit_o * wo
    # spring (underdamped) so the camera lags, overshoots a touch and settles
    def spring(tgt, w0, zeta, x0, v0=0.0):
        x_, v_ = x0, v0
        out_ = np.zeros_like(tgt)
        dt_ = 1.0 / 24.0
        for k_ in range(len(tgt)):
            a_ = w0 * w0 * (tgt[k_] - x_) - 2 * zeta * w0 * v_
            v_ += a_ * dt_
            x_ += v_ * dt_
            out_[k_] = x_
        return out_
    yaw_s = spring(yt, 11.0, 0.62, yt[0])
    pit_s = spring(pt, 11.0, 0.65, pt[0])
    # bank from yaw rate x speed, clamped to 25 deg; spring for overshoot
    spd = np.linalg.norm(np.gradient(PP, axis=0), axis=1) * 24.0
    yr = np.gradient(yaw_s) * 24.0
    bank_t = np.clip(np.arctan(-yr * spd / 9.81) * 1.5, -math.radians(25), math.radians(25))
    bank_s = spring(bank_t, 9.0, 0.5, 0.0)
    bank_s = np.clip(bank_s, -math.radians(25), math.radians(25))
    barrel = np.array([2 * math.pi * smoothstep(356, 372, f) for f in fr_k])
    BANK[F0 - 1:F1] = bank_s + barrel
    dirs = np.stack([np.sin(yaw_s) * np.cos(pit_s), np.cos(yaw_s) * np.cos(pit_s), np.sin(pit_s)], 1)
    aim[F0 - 1:F1] = PP + dirs * 10.0
    CAM_SPEED = spd
    for a_ in range(0, n_, 24):
        print("SPEED f%d-%d %.1f m/s" % (F0 + a_, F0 + min(a_ + 23, n_ - 1), spd[a_:a_ + 24].mean()))
    print("FPV path ok: mean speed %.1f m/s, max %.1f m/s" % (spd[20:340].mean(), spd.max()))
    # ---- handheld
    rs = np.random.default_rng(11)
    fr = np.arange(1, NF + 1)

    def noise(freqs, amps):
        n = np.zeros(NF)
        for fq, am in zip(freqs, amps):
            n += am * np.sin(2 * np.pi * fq * fr / 24 + rs.uniform(0, 6.28))
        return n

    env = np.where(fr <= 62 + SHIFT, 1.0, np.where(fr <= 84 + SHIFT, 0.6, np.where(fr < 500, 0.45, 0.2)))
    step_hz = 3.0
    bob = 0.028 * np.cos(2 * np.pi * step_hz * fr / 24 * 1.0) * (fr <= 62 + SHIFT)
    dpos = np.stack([noise([0.6, 1.9], [0.012, 0.006]) * env, noise([0.7, 2.3], [0.010, 0.004]) * env,
                     (noise([0.8, 2.6], [0.014, 0.006]) + bob) * env], 1)
    yaw_n = np.deg2rad(noise([0.5, 1.7, 4.0], [0.9, 0.5, 0.18]) * env)
    pit_n = np.deg2rad(noise([0.6, 1.4, 3.0], [0.8, 0.45, 0.22]) * env + 0.9 * np.cos(2 * np.pi * step_hz * fr / 24) * (fr <= 62 + SHIFT))
    rol_n = np.deg2rad(noise([0.4, 1.1], [1.0, 0.5]) * env) + np.deg2rad(1.6) + BANK
    # splash impact kick + entry shock
    for i, f in enumerate(range(1, NF + 1)):
        t = f - HOOK
        if t >= 0:
            a = math.exp(-t / 6.0) * math.cos(t * 0.9)
            pit_n[i] += math.radians(5.0) * a
            rol_n[i] += math.radians(4.0) * a * math.sin(t * 0.7 + 1)
            dpos[i, 2] += -0.08 * a
            dpos[i, 1] += -0.06 * math.exp(-t / 4.0)
        t3 = f - 73
        if 0 <= t3 < 16:
            pit_n[i] += math.radians(5.0) * math.exp(-t3 / 5.0) * math.cos(t3 * 0.7)
            rol_n[i] += math.radians(-6.0) * math.exp(-t3 / 6.0) * math.sin(t3 * 0.6)
        # takeoff bounce
        t2 = f - TAKEOFF
        if 0 <= t2 < 14:
            pit_n[i] += math.radians(2.5) * math.exp(-t2 / 5.0) * math.cos(t2 * 0.8)
    # underwater: gentle swimmer sway instead of running bob
    pos = pos + dpos
    fdist = np.linalg.norm(aim - pos, axis=1)
    for i, f in enumerate(range(1, NF + 1)):
        p = Vector(pos[i])
        fwd = Vector(aim[i]) - p
        q = fwd.to_track_quat("-Z", "Y")
        # horizon roll: to_track_quat keeps Y up => zero roll; add noise
        e = q.to_euler("XYZ")
        qn = Euler((e.x + pit_n[i] * 0.0, 0, 0)).to_quaternion()
        adj = Quaternion((0, 0, 1), yaw_n[i]) @ q @ Quaternion((1, 0, 0), pit_n[i]) @ Quaternion((0, 0, 1), rol_n[i])
        cam.location = p
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = adj
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cd.dof.focus_distance = float(min(max(fdist[i], 1.2), 25.0))
        cd.dof.keyframe_insert("focus_distance", frame=f)
    for ad in (cam.animation_data,):
        for lay in ad.action.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
    return cam, pos


cam, CAMPOS = build_camera()

# ----------------------------------------------------------------------------- splash
def foam_mat(name, alpha_gain=1.0, fade=None):
    m, nt = new_mat(name)
    m.surface_render_method = "DITHERED"
    bs = principled(nt)
    set_in(bs, "Base Color", (0.93, 0.96, 0.97))
    set_in(bs, "Roughness", 0.55)
    set_in(bs, "Subsurface Weight", 0.5)
    set_in(bs, "Subsurface Radius", (0.8, 0.9, 1.0))
    set_in(bs, "Subsurface Scale", 0.3)
    set_in(bs, "Emission Color", (1.0, 0.75, 0.55, 1)) if False else None
    tc = N(nt, "ShaderNodeTexCoord")
    nz = N(nt, "ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 9.0
    nz.inputs["Detail"].default_value = 8
    nz.inputs["Roughness"].default_value = 0.7
    val = N(nt, "ShaderNodeValue")
    d = val.outputs[0].driver_add("default_value").driver
    d.type = "SCRIPTED"
    d.expression = "frame*0.09"
    L(nt, val.outputs[0], nz.inputs["W"])
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    rng = N(nt, "ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = 0.42
    rng.inputs["From Max"].default_value = 0.62
    L(nt, nz.outputs["Fac"], rng.inputs["Value"])
    a = MATH(nt, "MULTIPLY", rng.outputs[0], alpha_gain)
    fv = N(nt, "ShaderNodeValue")
    fd = fv.outputs[0].driver_add("default_value").driver
    fd.type = "SCRIPTED"
    fd.expression = fade or "1"
    a2 = MATH(nt, "MULTIPLY", a, fv.outputs[0])
    L(nt, MATH(nt, "MINIMUM", a2, 1.0), bs.inputs["Alpha"])
    bump = N(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    L(nt, nz.outputs["Fac"], bump.inputs["Height"])
    L(nt, bump.outputs[0], bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def drop_mat():
    m, nt = new_mat("Droplet")
    m.surface_render_method = "DITHERED"
    bs = principled(nt)
    set_in(bs, "Base Color", (0.9, 0.96, 0.98))
    set_in(bs, "Roughness", 0.12)
    set_in(bs, "Specular IOR Level", 1.0)
    set_in(bs, "Alpha", 0.55)
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def setup_particles(emitter, name, count, f0, f1, life, normal, rand, size, size_rand, inst, gravity=1.0,
                    damping=0.0, tangent=0.0, obj_factor=0.0, seed=1):
    mod = emitter.modifiers.new(name, "PARTICLE_SYSTEM")
    ps = emitter.particle_systems[-1]
    s = ps.settings
    s.count = count
    s.frame_start = f0
    s.frame_end = f1
    s.lifetime = life
    s.lifetime_random = 0.4
    s.emit_from = "FACE"
    s.use_emit_random = True
    s.normal_factor = normal
    s.factor_random = rand
    s.tangent_factor = tangent
    s.object_factor = obj_factor
    s.physics_type = "NEWTON"
    s.effector_weights.gravity = gravity
    s.drag_factor = 0.0
    s.damping = damping
    s.render_type = "OBJECT"
    s.instance_object = inst
    s.particle_size = size
    s.size_random = size_rand
    emitter.show_instancer_for_render = False
    s.show_unborn = False
    s.use_dead = False
    ps.seed = seed
    return ps


def build_splash():
    ey = KID_ENTRY_Y
    dm = drop_mat()
    # droplet instance object
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    drop = mesh_obj("DropProto", bm, [C_MISC])
    drop.data.materials.append(dm)
    drop.hide_render = True
    drop.hide_viewport = True
    # a water-kill plane so drops vanish when they fall back to the surface
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=8.0)
    kill = mesh_obj("SplashKill", bm, [C_ABOVE], loc=(KID_ENTRY_X, ey, 0.03), smooth=False)
    kill.modifiers.new("Col", "COLLISION")
    kill.collision.use_particle_kill = True
    kill.collision.permeability = 0.0
    for a in ("visible_camera", "visible_shadow", "visible_glossy", "visible_diffuse", "visible_transmission",
              "visible_volume_scatter"):
        setattr(kill, a, False)
    # crown emitter (open cone, normals out+up)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=28, radius1=0.12, radius2=0.42, depth=0.3,
                          matrix=Matrix.Translation((0, 0, 0.16)))
    crown = mesh_obj("CrownEmit", bm, [C_ABOVE], loc=(KID_ENTRY_X, ey, 0.0), smooth=False)
    crown.hide_render = False
    ps1 = setup_particles(crown, "Crown", 5200, HOOK - 1, HOOK + 5, 34, 6.2, 0.55, 0.025, 0.75, drop, gravity=1.0,
                          tangent=0.3, seed=3)
    # central jet
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=0.16)
    jet = mesh_obj("JetEmit", bm, [C_ABOVE], loc=(KID_ENTRY_X, ey, 0.05), smooth=False)
    ps2 = setup_particles(jet, "Jet", 1600, HOOK, HOOK + 3, 36, 8.2, 0.45, 0.032, 0.8, drop, gravity=1.0, seed=5)
    # foam column
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=1.0, radius2=0.72, depth=1.0,
                          matrix=Matrix.Translation((0, 0, 0.5)))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=14, use_grid_fill=True)
    col = mesh_obj("FoamColumn", bm, [C_ABOVE], loc=(KID_ENTRY_X, ey, 0.0))
    col.data.materials.append(foam_mat("FoamColumn", 1.6, "max(0,min(1,(112-frame)/16))"))
    tx = bpy.data.textures.new("SplashNoise", "CLOUDS")
    tx.noise_scale = 0.45
    tx.noise_depth = 3
    dsp = col.modifiers.new("Disp", "DISPLACE")
    dsp.texture = tx
    dsp.strength = 0.42
    dsp.mid_level = 0.5
    dsp.direction = "NORMAL"
    dsp.texture_coords = "LOCAL"
    col.scale = (0.001, 0.001, 0.001)
    for f, s, z in ((HOOK - 1, (0.2, 0.2, 0.05), 0), (HOOK + 1, (0.5, 0.5, 1.4), 0), (HOOK + 4, (0.75, 0.75, 2.5), 0),
                    (HOOK + 8, (1.0, 1.0, 2.1), 0), (HOOK + 14, (1.3, 1.3, 1.0), 0), (HOOK + 22, (1.6, 1.6, 0.3), 0),
                    (HOOK + 32, (1.8, 1.8, 0.05), 0)):
        col.scale = s
        col.keyframe_insert("scale", frame=f)
    hidden_until(col, HOOK - 1)
    # foam ring on the surface (shrinkwrapped to the wavy sea)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=90, y_segments=90, size=1.0)
    for v in bm.verts:
        pass
    ring = mesh_obj("FoamRing", bm, [C_ABOVE], loc=(KID_ENTRY_X, ey, 0.0))
    rm, nt = new_mat("FoamRing")
    rm.surface_render_method = "DITHERED"
    bs = principled(nt)
    set_in(bs, "Base Color", (0.9, 0.95, 0.96))
    set_in(bs, "Roughness", 0.6)
    tc = N(nt, "ShaderNodeTexCoord")
    gen = N(nt, "ShaderNodeVectorMath")
    gen.operation = "LENGTH"
    L(nt, tc.outputs["Object"], gen.inputs[0])
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 14
    nz.inputs["Detail"].default_value = 8
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    # radial mask: ring between 0.35 and 1.0 (object units, grid half-size 1)
    r_in = MATH(nt, "SMOOTH_MAX", 0.0, 0.0) if False else None
    rad = gen.outputs["Value"]
    mask = MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, MATH(nt, "MAXIMUM", MATH(nt, "SUBTRACT", rad, 0.55), 0.0)),
                MATH(nt, "MINIMUM", MATH(nt, "MULTIPLY", rad, 4.0), 1.0))
    mask = MATH(nt, "MULTIPLY", MATH(nt, "MAXIMUM", MATH(nt, "SUBTRACT", 1.0, MATH(nt, "MULTIPLY", rad, 1.0)), 0.0), 1.0)
    fv = N(nt, "ShaderNodeValue")
    fd = fv.outputs[0].driver_add("default_value").driver
    fd.type = "SCRIPTED"
    fd.expression = "max(0,min(1,(frame-83)/4))*max(0,min(1,(150-frame)/40))"
    thr = MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", nz.outputs["Fac"], mask), 0.18)
    a = MATH(nt, "MULTIPLY", MATH(nt, "MINIMUM", MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", thr, 4.0), 0.0), 1.0),
             fv.outputs[0])
    L(nt, a, bs.inputs["Alpha"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    ring.data.materials.append(rm)
    sw = ring.modifiers.new("Wrap", "SHRINKWRAP")
    sw.target = sea
    sw.wrap_method = "PROJECT"
    sw.use_project_z = True
    sw.use_negative_direction = True
    sw.use_positive_direction = True
    sw.offset = 0.04
    ring.scale = (0.3, 0.3, 1)
    for f, s in ((HOOK, 0.3), (HOOK + 10, 1.7), (HOOK + 30, 3.0), (HOOK + 60, 4.2)):
        ring.scale = (s, s, 1)
        ring.keyframe_insert("scale", frame=f)
    hidden_until(ring, HOOK)
    for o in (crown, jet):
        o.hide_render = False
    # underwater bubbles that trail the kid
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    bub = mesh_obj("BubbleProto", bm, [C_MISC])
    bm_, nt = new_mat("Bubble")
    bm_.surface_render_method = "DITHERED"
    fr = N(nt, "ShaderNodeLayerWeight")
    fr.inputs["Blend"].default_value = 0.35
    gl = N(nt, "ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.03
    gl.inputs["Color"].default_value = (0.9, 1.0, 1.0, 1)
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    L(nt, MATH(nt, "MULTIPLY", fr.outputs["Facing"], 0.0) if False else fr.outputs["Fresnel"], mx.inputs[0])
    L(nt, tr.outputs[0], mx.inputs[1])
    L(nt, gl.outputs[0], mx.inputs[2])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, mx.outputs[0], out.inputs["Surface"])
    bub.data.materials.append(bm_)
    bub.hide_render = True
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.32)
    be = mesh_obj("BubbleEmit", bm, [C_UNDER], loc=(0, 0, 0.1))
    be.parent = KID["root"]
    be.location = (0, 0, 0.0)
    # parenting the emitter to a keyed root keeps it moving with the kid
    ps3 = setup_particles(be, "Bubbles", 4200, HOOK, HOOK + 26, 130, 0.9, 0.9, 0.016, 0.85, bub, gravity=-0.05,
                          damping=0.5, obj_factor=0.15, seed=9)
    ps3.settings.use_emit_random = True
    # entry-column bubbles born at the surface, not attached to the kid
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.55)
    be2 = mesh_obj("BubbleEmit2", bm, [C_UNDER], loc=(KID_ENTRY_X, ey, -0.6))
    setup_particles(be2, "Bubbles2", 3600, HOOK, HOOK + 8, 120, 1.2, 0.9, 0.02, 0.85, bub, gravity=-0.05, damping=0.55,
                    seed=13)
    return col


build_splash()


# ============================================================================= PART 3 : the sunken city
def facade_material():
    m, nt = new_mat("SunkenFacade")
    tc = N(nt, "ShaderNodeTexCoord")
    geo = N(nt, "ShaderNodeNewGeometry")
    oi = N(nt, "ShaderNodeObjectInfo")
    P = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["Object"], P.inputs[0])
    Nn = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["Normal"], Nn.inputs[0])
    nx = MATH(nt, "ABSOLUTE", Nn.outputs["X"])
    ny = MATH(nt, "ABSOLUTE", Nn.outputs["Y"])
    nzv = MATH(nt, "ABSOLUTE", Nn.outputs["Z"])
    u = MATH(nt, "ADD", MATH(nt, "MULTIPLY", P.outputs["X"], ny), MATH(nt, "MULTIPLY", P.outputs["Y"], nx))
    # add per-object offset so grids differ
    off = 0.0
    u = MATH(nt, "ADD", u, off)
    v = MATH(nt, "ADD", P.outputs["Z"], 22.0)  # height above the seabed
    cw, ch = 3.4, 3.7
    cu = MATH(nt, "DIVIDE", u, cw)
    cv = MATH(nt, "DIVIDE", v, ch)
    fu = MATH(nt, "FRACT", cu)
    fv = MATH(nt, "FRACT", cv)
    wu = MATH(nt, "MULTIPLY", MATH(nt, "GREATER_THAN", fu, 0.2), MATH(nt, "LESS_THAN", fu, 0.78))
    wv = MATH(nt, "MULTIPLY", MATH(nt, "GREATER_THAN", fv, 0.28), MATH(nt, "LESS_THAN", fv, 0.78))
    side = MATH(nt, "LESS_THAN", nzv, 0.5)
    win = MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", wu, wv), side)
    # ground floor is a plinth without windows
    win = MATH(nt, "MULTIPLY", win, MATH(nt, "GREATER_THAN", v, 1.2))
    # cell ids -> random
    idv = N(nt, "ShaderNodeCombineXYZ")
    L(nt, MATH(nt, "FLOOR", cu), idv.inputs["X"])
    L(nt, MATH(nt, "FLOOR", cv), idv.inputs["Y"])
    L(nt, MATH(nt, "MULTIPLY", oi.outputs["Random"], 91.0), idv.inputs["Z"])
    wn = N(nt, "ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = "3D"
    L(nt, idv.outputs[0], wn.inputs["Vector"])
    wn2 = N(nt, "ShaderNodeTexWhiteNoise")
    wn2.noise_dimensions = "3D"
    L(nt, VMATH(nt, "ADD", idv.outputs[0], (17.3, 5.1, 3.9)), wn2.inputs["Vector"])
    lit = MATH(nt, "LESS_THAN", wn.outputs["Value"], 0.4)
    warm = N(nt, "ShaderNodeMix")
    warm.data_type = "RGBA"
    warm.inputs[6].default_value = (1.0, 0.22, 0.02, 1)
    warm.inputs[7].default_value = (1.0, 0.48, 0.08, 1)
    L(nt, wn2.outputs["Value"], warm.inputs[0])
    # wall: concrete with silt on top faces and algae
    col, rough, nor = pbr_maps(nt, "concrete_wall_006", scale=0.22, strength=0.9)
    nzz = N(nt, "ShaderNodeTexNoise")
    nzz.inputs["Scale"].default_value = 0.6
    nzz.inputs["Detail"].default_value = 9
    L(nt, tc.outputs["Object"], nzz.inputs["Vector"])
    tint = N(nt, "ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1.0
    tint.inputs[7].default_value = (0.30, 0.36, 0.34, 1)
    L(nt, col, tint.inputs[6])
    # algae/growth: stronger low down and by noise
    gm = N(nt, "ShaderNodeMapRange")
    gm.inputs["From Min"].default_value = 0.42
    gm.inputs["From Max"].default_value = 0.68
    L(nt, nzz.outputs["Fac"], gm.inputs["Value"])
    lowmask = N(nt, "ShaderNodeMapRange")
    lowmask.inputs["From Min"].default_value = 14.0
    lowmask.inputs["From Max"].default_value = 2.0
    L(nt, v, lowmask.inputs["Value"])
    grow = MATH(nt, "MULTIPLY", gm.outputs[0], MATH(nt, "ADD", 0.35, lowmask.outputs[0]))
    alg = N(nt, "ShaderNodeMix")
    alg.data_type = "RGBA"
    alg.inputs[7].default_value = (0.035, 0.09, 0.04, 1)
    L(nt, MATH(nt, "MINIMUM", grow, 0.85), alg.inputs[0])
    L(nt, tint.outputs[2], alg.inputs[6])
    # silt on upward facing world normal
    nw = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo.outputs["Normal"], nw.inputs[0])
    sm = N(nt, "ShaderNodeMapRange")
    sm.inputs["From Min"].default_value = 0.45
    sm.inputs["From Max"].default_value = 0.85
    L(nt, nw.outputs["Z"], sm.inputs["Value"])
    silt = N(nt, "ShaderNodeMix")
    silt.data_type = "RGBA"
    silt.inputs[7].default_value = (0.22, 0.21, 0.17, 1)
    L(nt, MATH(nt, "MULTIPLY", sm.outputs[0], 0.92), silt.inputs[0])
    L(nt, alg.outputs[2], silt.inputs[6])
    # window frames / sills (painted, proud of the recessed glass) and barnacle crust near the seabed
    wu_o = MATH(nt, "MULTIPLY", MATH(nt, "GREATER_THAN", fu, 0.13), MATH(nt, "LESS_THAN", fu, 0.85))
    wv_o = MATH(nt, "MULTIPLY", MATH(nt, "GREATER_THAN", fv, 0.21), MATH(nt, "LESS_THAN", fv, 0.87))
    frame = MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", wu_o, wv_o), MATH(nt, "SUBTRACT", 1.0, win))
    frame = MATH(nt, "MULTIPLY", frame, MATH(nt, "MULTIPLY", side, MATH(nt, "GREATER_THAN", v, 1.2)))
    pnt = N(nt, "ShaderNodeMix")
    pnt.data_type = "RGBA"
    pnt.inputs[7].default_value = (0.20, 0.22, 0.19, 1)
    L(nt, MATH(nt, "MULTIPLY", frame, 0.9), pnt.inputs[0])
    L(nt, silt.outputs[2], pnt.inputs[6])
    vor = N(nt, "ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.inputs["Scale"].default_value = 38.0
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    vm = N(nt, "ShaderNodeMapRange")
    vm.inputs["From Min"].default_value = 0.10
    vm.inputs["From Max"].default_value = 0.30
    vm.inputs["To Min"].default_value = 1.0
    vm.inputs["To Max"].default_value = 0.0
    L(nt, vor.outputs["Distance"], vm.inputs["Value"])
    bmask = MATH(nt, "MULTIPLY", vm.outputs[0], MATH(nt, "MULTIPLY", lowmask.outputs[0], gm.outputs[0]))
    bar = N(nt, "ShaderNodeMix")
    bar.data_type = "RGBA"
    bar.inputs[7].default_value = (0.42, 0.41, 0.35, 1)
    L(nt, MATH(nt, "MULTIPLY", bmask, 0.9), bar.inputs[0])
    L(nt, pnt.outputs[2], bar.inputs[6])
    hgt = MATH(nt, "ADD", MATH(nt, "MULTIPLY", frame, 0.35), MATH(nt, "MULTIPLY", bmask, 0.5))
    fb = N(nt, "ShaderNodeBump")
    fb.inputs["Strength"].default_value = 0.8
    fb.inputs["Distance"].default_value = 0.03
    L(nt, hgt, fb.inputs["Height"])
    L(nt, nor, fb.inputs["Normal"])
    wall = principled(nt)
    L(nt, bar.outputs[2], wall.inputs["Base Color"])
    L(nt, MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", rough, 1.0), MATH(nt, "MULTIPLY", sm.outputs[0], 0.9)), wall.inputs["Roughness"])
    L(nt, fb.outputs[0], wall.inputs["Normal"])
    # window
    glass = principled(nt)
    glass.inputs["Base Color"].default_value = (0.01, 0.02, 0.02, 1)
    glass.inputs["Roughness"].default_value = 0.08
    glass.inputs["Specular IOR Level"].default_value = 0.8
    glass.inputs["Emission Strength"].default_value = 0.0
    L(nt, warm.outputs[2], glass.inputs["Emission Color"])
    flick = MATH(nt, "MULTIPLY", lit, 1.5)
    L(nt, flick, glass.inputs["Emission Strength"])
    mix = N(nt, "ShaderNodeMixShader")
    L(nt, win, mix.inputs[0])
    L(nt, wall.outputs[0], mix.inputs[1])
    L(nt, glass.outputs[0], mix.inputs[2])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, mix.outputs[0], out.inputs["Surface"])
    return m


def ground_material(name, tex_name, scale, tint, silt_amount=0.6, rough_min=0.6):
    m, nt = new_mat(name)
    col, rough, nor = pbr_maps(nt, tex_name, scale=scale, strength=1.0)
    tcx = N(nt, "ShaderNodeTexCoord")
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 8
    L(nt, tcx.outputs["Object"], nz.inputs["Vector"])
    t = N(nt, "ShaderNodeMix")
    t.data_type = "RGBA"
    t.blend_type = "MULTIPLY"
    t.inputs[0].default_value = 1.0
    t.inputs[7].default_value = tint
    L(nt, col, t.inputs[6])
    silt = N(nt, "ShaderNodeMix")
    silt.data_type = "RGBA"
    silt.inputs[7].default_value = (0.20, 0.19, 0.15, 1)
    rr = N(nt, "ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = 0.35
    rr.inputs["From Max"].default_value = 0.6
    L(nt, nz.outputs["Fac"], rr.inputs["Value"])
    L(nt, MATH(nt, "MULTIPLY", rr.outputs[0], silt_amount), silt.inputs[0])
    L(nt, t.outputs[2], silt.inputs[6])
    bs = principled(nt)
    L(nt, silt.outputs[2], bs.inputs["Base Color"])
    L(nt, MATH(nt, "MAXIMUM", rough, rough_min), bs.inputs["Roughness"])
    L(nt, nor, bs.inputs["Normal"])
    # caustics: animated bright web on the street, fading with depth below the surface
    cv = N(nt, "ShaderNodeTexVoronoi")
    cv.feature = "DISTANCE_TO_EDGE"
    cv.voronoi_dimensions = "4D"
    cv.inputs["Scale"].default_value = 2.2
    cw_ = nt.nodes.new("ShaderNodeValue")
    cd_ = cw_.outputs[0].driver_add("default_value").driver
    cd_.type = "SCRIPTED"
    cd_.expression = "frame*0.045"
    L(nt, cw_.outputs[0], cv.inputs["W"])
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], cv.inputs["Vector"])
    cm2 = N(nt, "ShaderNodeMapRange")
    cm2.inputs["From Min"].default_value = 0.0
    cm2.inputs["From Max"].default_value = 0.09
    cm2.inputs["To Min"].default_value = 1.0
    cm2.inputs["To Max"].default_value = 0.0
    L(nt, cv.outputs["Distance"], cm2.inputs["Value"])
    ce = N(nt, "ShaderNodeVectorMath")
    ce.operation = "SCALE"
    ce.inputs[0].default_value = (0.35, 0.75, 0.75)
    L(nt, MATH(nt, "MULTIPLY", MATH(nt, "POWER", cm2.outputs[0], 1.5), 0.09), ce.inputs[3])
    L(nt, ce.outputs[0], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 1.0
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def box(bm, cx, cy, z0, w, d, h):
    return bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((cx, cy, z0 + h / 2)) @ Matrix.Diagonal((w, d, h, 1)))


LOTINFO = []


def build_city():
    facade = facade_material()
    sand = ground_material("Seabed", "sandy_gravel_02", 0.12, (0.20, 0.29, 0.31, 1), 0.5, 0.75)
    road = ground_material("Road", "asphalt_02", 0.2, (0.28, 0.36, 0.38, 1), 0.65, 0.7)
    iron = metal_mat("SunkIron", (0.12, 0.13, 0.12), 0.7, 0.8)
    # seabed
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=260.0)
    sb = mesh_obj("Seabed", bm, [C_UNDER], loc=(0, 60, SEABED), smooth=False)
    sb.data.materials.append(sand)
    # roads
    bm = bmesh.new()
    box(bm, 0, 60, SEABED, 10.0, 150, 0.06)
    for cy in (38.0, 74.0):
        box(bm, 0, cy, SEABED, 150, 10.0, 0.06)
    for cx in (-38, 38):
        box(bm, cx, 60, SEABED, 10.0, 150, 0.06)
    rd = mesh_obj("Roads", bm, [C_UNDER], smooth=False)
    rd.data.materials.append(road)

    # buildings
    bm = bmesh.new()
    rbm = bmesh.new()   # roof props
    lots = []
    xs_blocks = [(-33.0, -5.0), (5.0, 33.0), (-71.0, -43.0), (43.0, 71.0)]
    ys_blocks = [(9.0, 33.0), (43.0, 69.0), (79.0, 105.0)]
    for (xa, xb) in xs_blocks:
        for (ya, yb) in ys_blocks:
            nx_, ny_ = 2, 2
            for i in range(nx_):
                for j in range(ny_):
                    x0 = xa + (xb - xa) * i / nx_ + 0.6
                    x1 = xa + (xb - xa) * (i + 1) / nx_ - 0.6
                    y0 = ya + (yb - ya) * j / ny_ + 0.6
                    y1 = ya + (yb - ya) * (j + 1) / ny_ - 0.6
                    lots.append((x0, x1, y0, y1))
    towers = []
    for (x0, x1, y0, y1) in lots:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w, d = x1 - x0, y1 - y0
        h = rnd.uniform(6.5, 15.5)
        if abs(cx) < 20 and 12 < cy < 30:
            h = rnd.uniform(14.0, 20.0)
        # near canyon start: tall
        h1 = h
        LOTINFO.append((x0, x1, y0, y1, h1))
        box(bm, cx, cy, SEABED - 0.5, w, d, h1 + 0.5)
        # setback upper section
        if rnd.random() < 0.7:
            s = rnd.uniform(0.55, 0.8)
            h2 = rnd.uniform(2.5, 6.0)
            box(bm, cx + rnd.uniform(-1, 1), cy + rnd.uniform(-1, 1), SEABED + h1 - 0.1, w * s, d * s, h2 + 0.1)
            top = SEABED + h1 + h2
            rw, rd_ = w * s, d * s
        else:
            top = SEABED + h1
            rw, rd_ = w, d
        # roof props
        for k in range(rnd.randint(1, 3)):
            ww = rnd.uniform(0.9, 2.2)
            box(rbm, cx + rnd.uniform(-rw / 3, rw / 3), cy + rnd.uniform(-rd_ / 3, rd_ / 3), top - 0.05, ww, ww * rnd.uniform(0.8, 1.6), rnd.uniform(0.6, 1.6))
        towers.append((cx, cy, top))
    b = mesh_obj("Buildings", bm, [C_UNDER], smooth=False)
    b.data.materials.append(facade)
    bv = b.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.09
    bv.segments = 1
    bv.limit_method = "ANGLE"
    r = mesh_obj("RoofProps", rbm, [C_UNDER], smooth=False)
    r.data.materials.append(facade)

    # lamp posts + cars + hydrant style clutter on the main canyon
    bm = bmesh.new()
    heads = []
    for y in np.arange(12.0, 96.0, 15.0):
        for sx in (-1, 1):
            x = 4.3 * sx
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.09, radius2=0.06, depth=6.0,
                                  matrix=Matrix.Translation((x, y, SEABED + 3.0)))
            box(bm, x - 0.9 * sx, y, SEABED + 5.95, 1.8, 0.09, 0.09)
            heads.append((x - 1.7 * sx, y, SEABED + 5.85))
    lp = mesh_obj("LampPosts", bm, [C_UNDER])
    lp.data.materials.append(iron)
    # cars
    bm = bmesh.new()
    carcols = []
    for (x, y, rot) in ():
        M0 = Matrix.Translation((x, y, SEABED)) @ Matrix.Rotation(rot, 4, "Z")
        bmesh.ops.create_cube(bm, size=1.0, matrix=M0 @ Matrix.Translation((0, 0, 0.7)) @ Matrix.Diagonal((1.8, 4.4, 0.85, 1)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=M0 @ Matrix.Translation((0, -0.2, 1.3)) @ Matrix.Diagonal((1.6, 2.3, 0.7, 1)))
    cars = mesh_obj("Cars", bm, [C_UNDER], smooth=False)
    cars.modifiers.new("Bevel", "BEVEL").width = 0.12
    cars.modifiers["Bevel"].segments = 2
    cm, nt = new_mat("CarRust")
    bs = principled(nt)
    tc = N(nt, "ShaderNodeTexCoord")
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.0
    nz.inputs["Detail"].default_value = 10
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    mm = N(nt, "ShaderNodeMix")
    mm.data_type = "RGBA"
    mm.inputs[6].default_value = (0.25, 0.32, 0.36, 1)
    mm.inputs[7].default_value = (0.26, 0.11, 0.05, 1)
    L(nt, nz.outputs["Fac"], mm.inputs[0])
    L(nt, mm.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.55
    bs.inputs["Metallic"].default_value = 0.6
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    cars.data.materials.append(cm)
    # street lamp heads (emissive) + a few real lights
    bm = bmesh.new()
    for (x, y, z) in heads:
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.22, matrix=Matrix.Translation((x, y, z)) @ Matrix.Diagonal((1, 1, 0.55, 1)))
    hd = mesh_obj("LampHeads", bm, [C_UNDER])
    hm, nt = new_mat("LampGlow")
    em = N(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.62, 0.25, 1)
    em.inputs["Strength"].default_value = 140.0
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, em.outputs[0], out.inputs["Surface"])
    hd.data.materials.append(hm)
    lit_heads = [h for i, h in enumerate(heads) if (i % 3 != 2)]
    for (x, y, z) in lit_heads:
        if y > 92:
            continue
        ld = bpy.data.lights.new("Lamp", "POINT")
        ld.energy = 2400
        ld.color = (1.0, 0.6, 0.25)
        ld.shadow_soft_size = 0.25
        ld.use_shadow = False
        ld.volume_factor = 1.0
        lo = bpy.data.objects.new("Lamp", ld)
        lo.location = (x, y, z - 0.2)
        link(lo, C_UNDER)
    # facade practicals: warm lights at "lit windows" along the canyon walls
    for k in range(22):
        sx = rnd.choice([-1, 1])
        ld = bpy.data.lights.new("Win", "POINT")
        ld.energy = rnd.uniform(1400, 2600)
        ld.color = (1.0, rnd.uniform(0.5, 0.75), rnd.uniform(0.2, 0.4))
        ld.shadow_soft_size = 0.6
        ld.use_shadow = False
        lo = bpy.data.objects.new("Win", ld)
        lo.location = (sx * rnd.uniform(5.6, 7.0), rnd.uniform(9.0, 82.0), rnd.uniform(SEABED + 4, -4.5))
        link(lo, C_UNDER)
    return towers


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


def add_statue(bm, x, y, z0, yaw, sc=1.0, arm_up=True, plinth=True):
    if plinth:
        vbox(bm, x, y, z0 + 0.15, 1.9, 1.9, 0.3)
        vbox(bm, x, y, z0 + 1.2, 1.4, 1.4, 1.9)
        vbox(bm, x, y, z0 + 2.25, 1.75, 1.75, 0.22)
    zb = z0 + (2.36 if plinth else 0.0)
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
        add_column(bs_, sx * 3.6, 17.0, SB + 0.1, 10.0, 0.75)
    vbox(bs_, 0, 17.0, SB + 10.1 + 0.45, 8.4, 1.7, 0.9)
    add_lantern(bg_, bb_, -2.6, 17.0, SB + 6.0)
    add_lantern(bg_, bb_, 2.6, 17.0, SB + 6.0)
    # v4: inner slalom columns (alternate sides) the FPV weaves through
    for k_, y_ in enumerate((22.6, 27.0, 31.4, 35.8, 40.2, 44.6)):
        add_column(bs_, (2.6 if k_ % 2 == 0 else -2.6), y_, SB + 0.1, 9.0, 0.7)
    # hero fallen drum (near miss)
    bmesh.ops.create_cone(bd_, cap_ends=True, segments=18, radius1=0.75, radius2=0.72, depth=2.0,
                          matrix=Matrix.Translation((0.6, 51.4, SB + 0.75)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    # toppled statue = orbit centre
    tmp_ = bmesh.new()
    add_statue(tmp_, 0, 0, 0, 0.0, 1.0, True, plinth=False)
    bmesh.ops.transform(tmp_, matrix=Matrix.Translation((0.5, 63.5, SB + 0.55)) @ Matrix.Rotation(0.35, 4, 'Z') @ Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Translation((0, 0, -1.4)), verts=tmp_.verts)
    me_ = bpy.data.meshes.new('toppled')
    tmp_.to_mesh(me_)
    tmp_.free()
    bs_.from_mesh(me_)
    vbox(bd_, 0.5 + 1.0, 63.5 + 2.4, SB + 0.5, 1.5, 1.5, 1.0, 0.4)   # broken plinth stub

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
    add_statue(bs_, -11.5, 36.0, SB + 0.1, 0.6, 1.0, True)
    add_statue(bs_, -12.5, 50.0, SB + 0.1, 0.3, 0.9, True)
    add_statue(bs_, 12.5, 22.0, SB + 0.1, -0.4, 1.0, False)
    for (sx, sy) in ((-11.5, 36.0), (-12.5, 50.0), (12.5, 22.0)):
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

TOWERS = build_forum()

# ----------------------------------------------------------------------------- drowned-street dressing
DRESS = []   # objects hidden until the dive


def weather_mat(name, col, metallic=0.1, rough=0.6, emit=None):
    """painted / metal surface with algae low down, silt on top faces, speckle wear"""
    m, nt = new_mat(name)
    geo = N(nt, "ShaderNodeNewGeometry")
    pz = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo.outputs["Position"], pz.inputs[0])
    nw = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo.outputs["Normal"], nw.inputs[0])
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 10
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nz.inputs["Vector"])
    # base colour varies with noise (faded, blotchy paint)
    base = N(nt, "ShaderNodeMix")
    base.data_type = "RGBA"
    base.inputs[6].default_value = tuple(col) + (1.0,)
    base.inputs[7].default_value = (col[0] * 0.45, col[1] * 0.5, col[2] * 0.5, 1)
    L(nt, nz.outputs["Fac"], base.inputs[0])
    # algae low down
    lm = N(nt, "ShaderNodeMapRange")
    lm.inputs["From Min"].default_value = SEABED + 2.2
    lm.inputs["From Max"].default_value = SEABED + 0.1
    L(nt, pz.outputs["Z"], lm.inputs["Value"])
    alg = N(nt, "ShaderNodeMix")
    alg.data_type = "RGBA"
    alg.inputs[7].default_value = (0.035, 0.085, 0.04, 1)
    L(nt, MATH(nt, "MULTIPLY", lm.outputs[0], MATH(nt, "ADD", 0.35, MATH(nt, "MULTIPLY", nz.outputs["Fac"], 0.8))), alg.inputs[0])
    L(nt, base.outputs[2], alg.inputs[6])
    sm = N(nt, "ShaderNodeMapRange")
    sm.inputs["From Min"].default_value = 0.5
    sm.inputs["From Max"].default_value = 0.9
    L(nt, nw.outputs["Z"], sm.inputs["Value"])
    silt = N(nt, "ShaderNodeMix")
    silt.data_type = "RGBA"
    silt.inputs[7].default_value = (0.08, 0.08, 0.065, 1)
    L(nt, MATH(nt, "MULTIPLY", sm.outputs[0], 0.6), silt.inputs[0])
    L(nt, alg.outputs[2], silt.inputs[6])
    bs = principled(nt)
    L(nt, silt.outputs[2], bs.inputs["Base Color"])
    set_in(bs, "Metallic", metallic)
    L(nt, MATH(nt, "MAXIMUM", MATH(nt, "MULTIPLY", nz.outputs["Fac"], 0.5), rough * 0.8), bs.inputs["Roughness"])
    bp = N(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.25
    bp.inputs["Distance"].default_value = 0.01
    nz2 = N(nt, "ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 90.0
    nz2.inputs["Detail"].default_value = 4
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nz2.inputs["Vector"])
    L(nt, nz2.outputs["Fac"], bp.inputs["Height"])
    L(nt, bp.outputs[0], bs.inputs["Normal"])
    if emit:
        set_in(bs, "Emission Color", emit[0] + (1.0,))
        set_in(bs, "Emission Strength", emit[1])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def glass_mat(name="DrownedGlass"):
    m, nt = new_mat(name)
    bs = principled(nt)
    set_in(bs, "Base Color", (0.008, 0.014, 0.014))
    set_in(bs, "Roughness", 0.10)
    set_in(bs, "Specular IOR Level", 0.7)
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def rubber_mat():
    m, nt = new_mat("Rubber")
    bs = principled(nt)
    set_in(bs, "Base Color", (0.02, 0.022, 0.02))
    set_in(bs, "Roughness", 0.9)
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    return m


def rot_pt(x, y, yaw):
    c, s_ = math.cos(yaw), math.sin(yaw)
    return (x * c - y * s_, x * s_ + y * c)


def xf_box(bm, cx, cy, cz, w, d, h, yaw=0.0, mat=0):
    M = Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((w, d, h, 1))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r


def add_car(bm, x, y, yaw, roll, pnt, wheel_sink=0.0):
    """low-poly but real car silhouette; local +Y = front. mats: pnt (paint index), 5 glass, 6 rubber"""
    T = Matrix.Translation((x, y, SEABED + 0.0)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(roll, 4, "Y")

    def place(v):
        return T @ Vector(v)

    def prism(bottom, top, mat):
        vs = [bm.verts.new(place(p)) for p in bottom + top]
        res = bmesh.ops.convex_hull(bm, input=vs)
        for f in res["geom"]:
            if isinstance(f, bmesh.types.BMFace):
                f.material_index = mat
    # lower body (hood + trunk) with sloped nose
    W = 0.9
    prism([(-W, -2.1, 0.30 - wheel_sink), (W, -2.1, 0.30 - wheel_sink), (W, 2.15, 0.30 - wheel_sink), (-W, 2.15, 0.30 - wheel_sink)],
          [(-W + 0.05, -2.05, 0.92 - wheel_sink), (W - 0.05, -2.05, 0.92 - wheel_sink), (W - 0.06, 2.05, 0.80 - wheel_sink), (-W + 0.06, 2.05, 0.80 - wheel_sink)], pnt)
    # glass cabin
    prism([(-0.82, -1.25, 0.92 - wheel_sink), (0.82, -1.25, 0.92 - wheel_sink), (0.82, 1.05, 0.90 - wheel_sink), (-0.82, 1.05, 0.90 - wheel_sink)],
          [(-0.72, -0.95, 1.46 - wheel_sink), (0.72, -0.95, 1.46 - wheel_sink), (0.72, 0.30, 1.44 - wheel_sink), (-0.72, 0.30, 1.44 - wheel_sink)], 5)
    # painted roof + pillars
    prism([(-0.74, -1.0, 1.44 - wheel_sink), (0.74, -1.0, 1.44 - wheel_sink), (0.74, 0.34, 1.42 - wheel_sink), (-0.74, 0.34, 1.42 - wheel_sink)],
          [(-0.74, -1.0, 1.51 - wheel_sink), (0.74, -1.0, 1.51 - wheel_sink), (0.74, 0.34, 1.49 - wheel_sink), (-0.74, 0.34, 1.49 - wheel_sink)], pnt)
    # bumpers
    for yy in (-2.16, 2.2):
        prism([(-W - 0.03, yy - 0.06, 0.22 - wheel_sink), (W + 0.03, yy - 0.06, 0.22 - wheel_sink), (W + 0.03, yy + 0.06, 0.22 - wheel_sink), (-W - 0.03, yy + 0.06, 0.22 - wheel_sink)],
              [(-W - 0.03, yy - 0.06, 0.48 - wheel_sink), (W + 0.03, yy - 0.06, 0.48 - wheel_sink), (W + 0.03, yy + 0.06, 0.48 - wheel_sink), (-W - 0.03, yy + 0.06, 0.48 - wheel_sink)], 6)
    # wheels (two flat)
    for i, (wx, wy) in enumerate(((-0.86, 1.35), (0.86, 1.35), (-0.86, -1.3), (0.86, -1.3))):
        r_ = 0.31 if (i + int(x * 3)) % 3 else 0.25
        M = T @ Matrix.Translation((wx, wy, r_ - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=r_, radius2=r_, depth=0.24, matrix=M)
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = 6


def add_bus(bm, x, y, yaw, roll, pnt):
    T = Matrix.Translation((x, y, SEABED)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(roll, 4, "Y")

    def prism(bottom, top, mat):
        vs = [bm.verts.new(T @ Vector(p)) for p in bottom + top]
        res = bmesh.ops.convex_hull(bm, input=vs)
        for f in res["geom"]:
            if isinstance(f, bmesh.types.BMFace):
                f.material_index = mat
    L_, W, H0, H1 = 5.6, 1.28, 0.45, 3.2
    prism([(-W, -L_, H0), (W, -L_, H0), (W, L_, H0), (-W, L_, H0)], [(-W, -L_, H1), (W, -L_, H1), (W, L_, H1 - 0.05), (-W, L_, H1 - 0.05)], pnt)
    # window band (glass) protruding slightly on both sides + windscreen
    for sx in (-1, 1):
        prism([(sx * (W + 0.01), -L_ + 0.7, 1.55), (sx * (W + 0.01), L_ - 0.5, 1.55), (sx * (W + 0.01), L_ - 0.5, 1.56), (sx * (W + 0.01), -L_ + 0.7, 1.56)],
              [(sx * (W + 0.03), -L_ + 0.7, 2.75), (sx * (W + 0.03), L_ - 0.5, 2.75), (sx * (W + 0.03), L_ - 0.5, 2.76), (sx * (W + 0.03), -L_ + 0.7, 2.76)], 5)
    prism([(-W + 0.15, L_ + 0.01, 1.4), (W - 0.15, L_ + 0.01, 1.4), (W - 0.15, L_ + 0.03, 1.4), (-W + 0.15, L_ + 0.03, 1.4)],
          [(-W + 0.15, L_ + 0.02, 2.8), (W - 0.15, L_ + 0.02, 2.8), (W - 0.15, L_ + 0.04, 2.8), (-W + 0.15, L_ + 0.04, 2.8)], 5)
    for wy in (-3.6, 3.7):
        for sx in (-1, 1):
            M = T @ Matrix.Translation((sx * (W - 0.05), wy, 0.5)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.5, radius2=0.5, depth=0.28, matrix=M)
            for f in {f for v in res["verts"] for f in v.link_faces}:
                f.material_index = 6


def make_text(txt, loc, yaw, size, mat, pitch=0.0):
    cu = bpy.data.curves.new("T_" + txt, "FONT")
    cu.body = txt
    cu.size = size
    cu.extrude = 0.012
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    tob = bpy.data.objects.new("T_" + txt, cu)
    C_UNDER.objects.link(tob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tob.evaluated_get(dg))
    C_UNDER.objects.unlink(tob)
    bpy.data.objects.remove(tob)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Sign_" + txt, me)
    ob.location = loc
    ob.rotation_euler = (math.pi / 2 + pitch, 0, yaw)
    link(ob, C_UNDER)
    DRESS.append(ob)
    return ob


def build_dress():
    concrete = weather_mat("DressConcrete", (0.42, 0.43, 0.40), 0.0, 0.85)
    ironm = weather_mat("DressIron", (0.10, 0.10, 0.09), 0.7, 0.6)
    paints = [weather_mat(f"Paint{i}", c, 0.25, 0.5) for i, c in enumerate(
        [(0.26, 0.045, 0.035), (0.045, 0.09, 0.20), (0.33, 0.25, 0.06), (0.26, 0.27, 0.26), (0.05, 0.16, 0.12)])]
    awn = [weather_mat("Awning0", (0.55, 0.10, 0.08), 0.0, 0.9), weather_mat("Awning1", (0.10, 0.32, 0.34), 0.0, 0.9),
           weather_mat("Awning2", (0.62, 0.50, 0.14), 0.0, 0.9)]
    plate = weather_mat("SignPlate", (0.06, 0.20, 0.24), 0.2, 0.55)
    letters = weather_mat("SignLetters", (0.78, 0.72, 0.55), 0.1, 0.5)
    glass, rub = glass_mat(), rubber_mat()
    names = ["CAFE ORION", "HOTEL LUNA", "BAR PORTO", "FARMACIA", "LIBRERIA", "PANE E VINO", "NETTUNO", "MARE TAXI", "OTTICA SOL", "TRATTORIA"]
    # ---- facade dressing on street-facing lots
    bm_c = bmesh.new()   # concrete: ledges, balconies, cornices
    bm_i = bmesh.new()   # iron: rails, downpipes
    bm_a = [bmesh.new(), bmesh.new(), bmesh.new()]  # awnings
    bm_p = bmesh.new()   # sign plates
    ni = 0
    cw, ch = 3.4, 3.7
    for (x0, x1, y0, y1, h1) in LOTINFO:
        cx = (x0 + x1) / 2
        if cx > 0 and x0 < 6.5:
            fx, o = x0, -1.0
        elif cx < 0 and x1 > -6.5:
            fx, o = x1, 1.0
        else:
            continue
        top = SEABED + h1
        nfl = int(h1 / ch)
        d = y1 - y0
        cy = (y0 + y1) / 2
        for j in range(1, nfl):
            zs = SEABED + (j + 0.26) * ch
            xf_box(bm_c, fx + o * 0.09, cy, zs, 0.18, d, 0.10)          # sill band
            xf_box(bm_c, fx + o * 0.10, cy, SEABED + (j + 0.93) * ch, 0.20, d, 0.16)  # floor band
        xf_box(bm_c, fx + o * 0.25, cy, top - 0.22, 0.5, d + 0.2, 0.44)     # cornice
        xf_box(bm_c, fx + o * 0.35, cy, top + 0.05, 0.7, d + 0.3, 0.12)
        # balconies
        for j in range(1, nfl):
            for k in range(int(y0 / cw) - 1, int(y1 / cw) + 2):
                yc = (k + 0.49) * cw
                if yc < y0 + 1.4 or yc > y1 - 1.4 or rnd.random() > 0.28:
                    continue
                zb = SEABED + (j + 0.28) * ch
                xf_box(bm_c, fx + o * 0.55, yc, zb - 0.05, 1.1, 2.3, 0.12)
                for yy in (-1.12, 1.12):
                    xf_box(bm_i, fx + o * 0.55, yc + yy, zb + 0.45, 1.05, 0.04, 0.9)
                xf_box(bm_i, fx + o * 1.07, yc, zb + 0.45, 0.04, 2.3, 0.05)
                xf_box(bm_i, fx + o * 1.07, yc, zb + 0.95, 0.05, 2.3, 0.06)
                for yy in np.linspace(-1.1, 1.1, 9):
                    xf_box(bm_i, fx + o * 1.07, yc + yy, zb + 0.5, 0.03, 0.03, 0.9)
        # downpipes
        for yy in (y0 + 0.5, y1 - 0.5):
            res = bmesh.ops.create_cone(bm_i, cap_ends=True, segments=8, radius1=0.05, radius2=0.05, depth=h1 - 0.6,
                                        matrix=Matrix.Translation((fx + o * 0.08, yy, SEABED + h1 / 2 - 0.1)))
        # shop awnings + signs on the ground floor
        for k in range(int(y0 / cw) - 1, int(y1 / cw) + 2):
            yc = (k + 0.49) * cw
            if yc < y0 + 1.3 or yc > y1 - 1.3 or rnd.random() > 0.55:
                continue
            ai = rnd.randrange(3)
            b = bm_a[ai]
            pts_b = [(fx, yc - 1.4, SEABED + 3.0), (fx, yc + 1.4, SEABED + 3.0), (fx + o * 1.5, yc + 1.4, SEABED + 2.45), (fx + o * 1.5, yc - 1.4, SEABED + 2.45)]
            pts_t = [(fx, yc - 1.4, SEABED + 3.08), (fx, yc + 1.4, SEABED + 3.08), (fx + o * 1.5, yc + 1.4, SEABED + 2.53), (fx + o * 1.5, yc - 1.4, SEABED + 2.53)]
            vs = [b.verts.new(p) for p in pts_b + pts_t]
            bmesh.ops.convex_hull(b, input=vs)
            xf_box(bm_p, fx + o * 0.12, yc, SEABED + 3.55, 0.12, 2.6, 0.6)
            nm = names[ni % len(names)]
            ni += 1
            # letters face the street (normal = o * x). text plane is XZ; yaw so that its front faces +/-x
            make_text(nm, (fx + o * 0.19, yc, SEABED + 3.55), (math.pi / 2 if o < 0 else -math.pi / 2), 0.42, letters)
    for nm_, bm_, mt in [("DressConcrete", bm_c, concrete), ("DressIron", bm_i, ironm), ("SignPlates", bm_p, plate)] + \
            [(f"Awning{i}", bm_a[i], awn[i]) for i in range(3)]:
        ob = mesh_obj(nm_, bm_, [C_UNDER], smooth=False)
        ob.data.materials.append(mt)
        if nm_ in ("DressConcrete", "DressIron"):
            bv = ob.modifiers.new("Bevel", "BEVEL")
            bv.width = 0.015
            bv.segments = 1
        DRESS.append(ob)

    # ---- vehicles: cars parked on flat tyres in silt, a bus alongside the last stretch of the dive
    bm = bmesh.new()
    for (x, y, yaw, roll, pi_) in ((3.3, 14.0, 0.06, 0.05, 0), (-3.4, 19.5, -0.10, -0.06, 1), (3.1, 25.0, 0.12, 0.04, 2), (-3.5, 27.0, 0.0, 0.07, 3),
                                   (3.4, 31.5, -0.04, -0.05, 4), (-1.6, 12.0, 0.9, 0.09, 1), (3.2, 47.0, 0.08, 0.05, 3), (-3.3, 52.0, 3.2, -0.04, 0),
                                   (0.5, 60.0, 1.4, 0.06, 2)):
        add_car(bm, x, y, yaw, roll, pi_, wheel_sink=0.04)
    add_bus(bm, -3.4, 36.0, 0.07, 0.035, 4)
    cars = mesh_obj("CarsNew", bm, [C_UNDER], smooth=False)
    for m_ in paints + [glass, rub]:
        cars.data.materials.append(m_)
    bv = cars.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.05
    bv.segments = 2
    bv.limit_method = "ANGLE"
    DRESS.append(cars)
    # ---- street furniture: tilted traffic lights, street signs
    bm = bmesh.new()
    bmh = bmesh.new()
    for (x, y, tilt, yaw) in ((5.0, 21.0, 0.22, math.pi), (-5.0, 58.0, -0.28, 0.0), (5.1, 44.0, 0.15, math.pi)):
        T = Matrix.Translation((x, y, SEABED)) @ Matrix.Rotation(tilt, 4, "Y") @ Matrix.Rotation(yaw, 4, "Z")
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.09, radius2=0.06, depth=4.6, matrix=T @ Matrix.Translation((0, 0, 2.3)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=T @ Matrix.Translation((-1.2, 0, 4.5)) @ Matrix.Diagonal((2.4, 0.08, 0.08, 1)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=T @ Matrix.Translation((-2.1, 0, 4.15)) @ Matrix.Diagonal((0.32, 0.30, 0.95, 1)))
        for k_, zz in enumerate((4.45, 4.15, 3.85)):
            bmesh.ops.create_cone(bmh, cap_ends=True, segments=10, radius1=0.10, radius2=0.10, depth=0.03,
                                  matrix=T @ Matrix.Translation((-2.1, 0.16, zz)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    tl = mesh_obj("TrafficLights", bm, [C_UNDER], smooth=False)
    tl.data.materials.append(ironm)
    DRESS.append(tl)
    lamp = mesh_obj("TrafficLamps", bmh, [C_UNDER], smooth=False)
    lamp.data.materials.append(weather_mat("TLamp", (0.5, 0.12, 0.05), 0.0, 0.4, emit=((1.0, 0.25, 0.08), 6.0)))
    DRESS.append(lamp)
    bm = bmesh.new()
    for (x, y, nm_, yaw) in ((5.0, 16.0, "VIA MARE", -math.pi / 2), (-5.0, 34.0, "VIA ORION", math.pi / 2), (5.0, 40.0, "PIAZZA SOL", -math.pi / 2)):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.045, radius2=0.045, depth=3.0, matrix=Matrix.Translation((x, y, SEABED + 1.5)))
        xf_box(bm, x - math.copysign(0.06, x), y, SEABED + 2.85, 0.05, 1.3, 0.3)
        make_text(nm_, (x - math.copysign(0.10, x), y, SEABED + 2.85), -math.pi / 2 if x > 0 else math.pi / 2, 0.16, letters)
    sg = mesh_obj("StreetSigns", bm, [C_UNDER], smooth=False)
    sg.data.materials.append(plate)
    DRESS.append(sg)
    # ---- silt drifts + debris
    bm = bmesh.new()
    for i in range(110):
        side = rnd.choice([-1, 1])
        x = side * rnd.uniform(3.2, 5.6) if rnd.random() < 0.75 else rnd.uniform(-4, 4)
        y = rnd.uniform(7, 66)
        sx_, sy_, sz_ = rnd.uniform(0.5, 1.5), rnd.uniform(0.8, 2.6), rnd.uniform(0.06, 0.16)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=Matrix.Translation((x, y, SEABED)) @ Matrix.Diagonal((sx_, sy_, sz_, 1)))
    for v in bm.verts:
        v.co.z = max(v.co.z, SEABED - 0.05)
    sm = bpy.data.materials.new("SiltDrift")
    sm.use_nodes = True
    nt = sm.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bs = principled(nt)
    set_in(bs, "Base Color", (0.10, 0.098, 0.08))
    set_in(bs, "Roughness", 0.95)
    nzb = N(nt, "ShaderNodeTexNoise")
    nzb.inputs["Scale"].default_value = 40.0
    nzb.inputs["Detail"].default_value = 6
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nzb.inputs["Vector"])
    bpn = N(nt, "ShaderNodeBump")
    bpn.inputs["Strength"].default_value = 0.6
    bpn.inputs["Distance"].default_value = 0.05
    L(nt, nzb.outputs["Fac"], bpn.inputs["Height"])
    L(nt, bpn.outputs[0], bs.inputs["Normal"])
    o_ = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], o_.inputs["Surface"])
    dr = mesh_obj("SiltDrifts", bm, [C_UNDER])
    dr.data.materials.append(sm)
    DRESS.append(dr)
    bm = bmesh.new()
    for i in range(70):
        x = rnd.uniform(-5.0, 5.0)
        y = rnd.uniform(8, 60)
        kind = rnd.random()
        if kind < 0.5:   # planks / boards
            xf_box(bm, x, y, SEABED + 0.05, rnd.uniform(0.15, 0.3), rnd.uniform(1.0, 2.6), 0.04, rnd.uniform(0, 3.1))
        elif kind < 0.8:   # crates
            s_ = rnd.uniform(0.3, 0.6)
            xf_box(bm, x, y, SEABED + s_ / 2, s_, s_, s_, rnd.uniform(0, 3.1))
        else:   # barrels / tyres
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.28, radius2=0.28, depth=0.7, matrix=Matrix.Translation((x, y, SEABED + 0.35)))
    de = mesh_obj("DebrisBits", bm, [C_UNDER], smooth=False)
    de.data.materials.append(concrete)
    DRESS.append(de)
    for ob in DRESS:
        hidden_until(ob, HOOK - 2)




def build_shafts():
    """god-ray cards from the surface: slanted, soft-edged, alpha-modulated, slowly drifting"""
    m, nt = new_mat("Shaft")
    m.surface_render_method = "BLENDED"
    tc = N(nt, "ShaderNodeTexCoord")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["UV"], sp.inputs[0])
    # across-width profile: bright core, soft edges
    edge = MATH(nt, "SUBTRACT", 1.0, MATH(nt, "ABSOLUTE", MATH(nt, "SUBTRACT", MATH(nt, "MULTIPLY", sp.outputs["X"], 2.0), 1.0)))
    prof = MATH(nt, "POWER", edge, 1.6)
    # along-length falloff: strongest near the surface, fading with depth
    along = MATH(nt, "POWER", sp.outputs["Y"], 1.3)
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.noise_dimensions = "3D"
    L(nt, tc.outputs["Object"], nz.inputs["Vector"])
    a = MATH(nt, "MULTIPLY", MATH(nt, "MULTIPLY", prof, along), MATH(nt, "ADD", 0.45, nz.outputs["Fac"]))
    em = N(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.45, 0.85, 0.85, 1)
    em.inputs["Strength"].default_value = 1.6
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    L(nt, MATH(nt, "MULTIPLY", a, 0.22), mx.inputs[0])
    L(nt, tr.outputs[0], mx.inputs[1])
    L(nt, em.outputs[0], mx.inputs[2])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, mx.outputs[0], out.inputs["Surface"])
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    dirh = Vector((-math.cos(math.radians(70)), -math.sin(math.radians(70)), 0)) * 0.325
    for i in range(52):
        x = rnd.uniform(-17, 17)
        y = rnd.uniform(4, 88)
        wtop = rnd.uniform(0.5, 1.1)
        wbot = wtop * rnd.uniform(1.8, 3.0)
        for rot in (0.0, math.pi / 2):
            cr, sr = math.cos(rot), math.sin(rot)
            def V(dx, dz, wd):
                off = dirh * (-dz)
                return bm.verts.new((x + off.x + cr * dx * wd, y + off.y + sr * dx * wd, dz))
            zt, zb = -0.2, SEABED + 0.5
            vs = [V(-1, zt, wtop), V(1, zt, wtop), V(1, zb, wbot), V(-1, zb, wbot)]
            f = bm.faces.new(vs)
            uvs = [(0, 1), (1, 1), (1, 0), (0, 0)]
            for l_, u_ in zip(f.loops, uvs):
                l_[uv].uv = u_
    sh = mesh_obj("Shafts", bm, [C_UNDER], smooth=False)
    sh.data.materials.append(m)
    sh.visible_shadow = False
    hidden_until(sh, HOOK + 2)
    return sh


build_shafts()


# ----------------------------------------------------------------------------- ENDING: lit window at the end of the canyon
def build_ending():
    """v2 ending B: the camera reaches a lit window; a silhouette inside turns and waves (last 2 s)."""
    facade = bpy.data.materials["SunkenFacade"]
    YF = 84.0            # facade plane (faces -Y, toward the camera)
    WZ = -15.6           # window centre height
    bm = bmesh.new()
    box(bm, 0.0, YF + 6.0, SEABED - 0.5, 16.8, 12.0, 12.3)
    eb = mesh_obj("EndBuilding", bm, [C_UNDER], smooth=False)
    eb.data.materials.append(facade)
    bv = eb.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.09
    bv.segments = 1
    bv.limit_method = "ANGLE"
    DRESS.append(eb)
    concrete = bpy.data.materials["DressConcrete"]
    # window frame: sill, lintel, jambs, mullion cross
    bmf = bmesh.new()
    W, H = 2.5, 1.95
    yy = YF - 0.06
    xf_box(bmf, 0, yy, WZ - H / 2 - 0.08, W + 0.5, 0.35, 0.16)          # sill
    xf_box(bmf, 0, yy, WZ + H / 2 + 0.07, W + 0.4, 0.22, 0.14)          # lintel
    for sx in (-1, 1):
        xf_box(bmf, sx * (W / 2 + 0.06), yy, WZ, 0.12, 0.22, H + 0.1)
    xf_box(bmf, 0, yy - 0.02, WZ, 0.06, 0.08, H)
    xf_box(bmf, 0, yy - 0.02, WZ + 0.25, W, 0.08, 0.06)
    fr_ = mesh_obj("WindowFrame", bmf, [C_UNDER], smooth=False)
    fr_.data.materials.append(bpy.data.materials["DressIron"] if "DressIron" in bpy.data.materials else concrete)
    DRESS.append(fr_)
    # glowing room behind the glass: warm radial gradient (lamp upper-right), emissive
    bmq = bmesh.new()
    uv = bmq.loops.layers.uv.new("UV")
    vs = [bmq.verts.new((-W / 2, YF - 0.02, WZ - H / 2)), bmq.verts.new((W / 2, YF - 0.02, WZ - H / 2)),
          bmq.verts.new((W / 2, YF - 0.02, WZ + H / 2)), bmq.verts.new((-W / 2, YF - 0.02, WZ + H / 2))]
    f_ = bmq.faces.new(vs)
    for l_, u_ in zip(f_.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        l_[uv].uv = u_
    q = mesh_obj("WindowGlow", bmq, [C_UNDER], smooth=False)
    m, nt = new_mat("RoomGlow")
    tc = N(nt, "ShaderNodeTexCoord")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["UV"], sp.inputs[0])
    dx = MATH(nt, "SUBTRACT", sp.outputs["X"], 0.72)
    dy = MATH(nt, "SUBTRACT", sp.outputs["Y"], 0.62)
    dist = MATH(nt, "SQRT", MATH(nt, "ADD", MATH(nt, "MULTIPLY", dx, dx), MATH(nt, "MULTIPLY", dy, dy)))
    g = MATH(nt, "SUBTRACT", 1.15, MATH(nt, "MULTIPLY", dist, 1.5))
    g = MATH(nt, "MAXIMUM", g, 0.35)
    col = N(nt, "ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (1.0, 0.36, 0.06, 1)
    col.inputs[7].default_value = (1.0, 0.72, 0.36, 1)
    L(nt, MATH(nt, "MINIMUM", MATH(nt, "MULTIPLY", g, 0.9), 1.0), col.inputs[0])
    em = N(nt, "ShaderNodeEmission")
    L(nt, col.outputs[2], em.inputs["Color"])
    L(nt, MATH(nt, "MULTIPLY", g, 5.0), em.inputs["Strength"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, em.outputs[0], out.inputs["Surface"])
    q.data.materials.append(m)
    DRESS.append(q)
    # curtains (dark warm rags at the sides)
    bmc = bmesh.new()
    for sx in (-1, 1):
        xf_box(bmc, sx * (W / 2 - 0.16), YF - 0.05, WZ + 0.1, 0.32, 0.05, H - 0.2)
    cur = mesh_obj("Curtains", bmc, [C_UNDER], smooth=False)
    cur.data.materials.append(simple_mat("CurtainCloth", (0.16, 0.05, 0.03), 0.95))
    DRESS.append(cur)
    # warm spill light so the frame and water glow
    ld = bpy.data.lights.new("WinSpill", "POINT")
    ld.energy = 1500
    ld.color = (1.0, 0.55, 0.2)
    ld.shadow_soft_size = 0.5
    ld.use_shadow = False
    lo = bpy.data.objects.new("WinSpill", ld)
    lo.location = (0.4, YF - 0.9, WZ)
    link(lo, C_UNDER)
    keyed_bool(lo, "hide_render", [(1, True), (HOOK + 3, False)])
    # the silhouette (person) - pivots so it can turn and wave
    dark = simple_mat("FigureDark", (0.004, 0.003, 0.003), 0.9)
    root = bpy.data.objects.new("FigRoot", None)
    root.location = (0.15, YF - 0.30, WZ - 0.5)
    link(root, C_MISC)
    piv = bpy.data.objects.new("FigTurn", None)
    piv.parent = root
    link(piv, C_MISC)

    def sph(name, r, loc, scl, par):
        bmm = bmesh.new()
        bmesh.ops.create_uvsphere(bmm, u_segments=16, v_segments=10, radius=1.0, matrix=Matrix.Diagonal((r * scl[0], r * scl[1], r * scl[2], 1)))
        ob = mesh_obj(name, bmm, [C_UNDER])
        ob.data.materials.append(dark)
        ob.parent = par
        ob.location = loc
        DRESS.append(ob)
        return ob
    sph("FigTorso", 1.0, (0, 0, -0.05), (0.19, 0.12, 0.62), piv)
    sph("FigShoulders", 1.0, (0, 0, 0.5), (0.31, 0.11, 0.10), piv)
    sph("FigHead", 1.0, (0, 0, 0.78), (0.125, 0.14, 0.15), piv)
    sph("FigHair", 1.0, (0, 0.06, 0.82), (0.14, 0.13, 0.15), piv)
    sph("FigBun", 1.0, (0.0, 0.14, 0.95), (0.06, 0.06, 0.06), piv)
    sph("FigNeck", 1.0, (0, 0, 0.62), (0.05, 0.05, 0.07), piv)
    armL = bpy.data.objects.new("ArmL", None)
    armL.parent = piv
    armL.location = (-0.30, 0, 0.50)
    link(armL, C_MISC)
    armR = bpy.data.objects.new("ArmR", None)
    armR.parent = piv
    armR.location = (0.30, 0, 0.50)
    link(armR, C_MISC)
    for nm, par in (("ArmLm", armL), ("ArmRm", armR)):
        bmm = bmesh.new()
        bmesh.ops.create_uvsphere(bmm, u_segments=10, v_segments=8, radius=1.0, matrix=Matrix.Translation((0, 0, -0.3)) @ Matrix.Diagonal((0.055, 0.055, 0.32, 1)))
        ob = mesh_obj(nm, bmm, [C_UNDER])
        ob.data.materials.append(dark)
        ob.parent = par
        DRESS.append(ob)
        bmm = bmesh.new()
        bmesh.ops.create_uvsphere(bmm, u_segments=10, v_segments=8, radius=1.0, matrix=Matrix.Translation((0, 0, -0.66)) @ Matrix.Diagonal((0.05, 0.035, 0.07, 1)))
        ob = mesh_obj(nm + "hand", bmm, [C_UNDER])
        ob.data.materials.append(dark)
        ob.parent = par
        DRESS.append(ob)
    # animation: profile (facing +x) -> turn to camera (f492..528) -> raise right arm and wave (f528..576)
    for f in range(1, NF + 1):
        turn = smoothstep(492, 528, f)
        piv.rotation_euler = (0, 0, (1 - turn) * 1.45 + 0.03 * math.sin(f / 24 * 1.3))
        piv.keyframe_insert("rotation_euler", frame=f)
        up = smoothstep(524, 546, f)
        wave = math.sin((f - 540) / 24.0 * 2 * math.pi * 1.7) * 0.32 * up
        armR.rotation_euler = (0, -(0.06 + up * 2.45) + wave * 0.0, 0)
        armR.rotation_euler = (0, -(0.06 + up * 2.5 + wave), 0)
        armR.keyframe_insert("rotation_euler", frame=f)
        armL.rotation_euler = (0, 0.08 + 0.02 * math.sin(f / 24.0), 0)
        armL.keyframe_insert("rotation_euler", frame=f)
    for ob in list(DRESS):
        pass
    for ob in DRESS[-1:]:
        pass
    for ob in list(bpy.data.objects):
        if ob.name in ("FigRoot",) or ob.parent is not None and ob.name.startswith(("Fig", "Arm")):
            pass
    for ob in (eb, fr_, q, cur):
        hidden_until(ob, HOOK - 2)
    for ob in bpy.data.objects:
        if ob.name.startswith(("Fig", "Arm")) and ob.type == "MESH":
            hidden_until(ob, HOOK - 2)


build_ending()


# ----------------------------------------------------------------------------- kelp, silt-fauna, rubble
def kelp_material():
    m, nt = new_mat("Kelp")
    bs = principled(nt)
    set_in(bs, "Base Color", (0.10, 0.17, 0.035))
    set_in(bs, "Roughness", 0.45)
    set_in(bs, "Subsurface Weight", 0.5)
    set_in(bs, "Subsurface Radius", (0.3, 0.6, 0.1))
    set_in(bs, "Subsurface Scale", 0.05)
    nz = N(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 6
    L(nt, N(nt, "ShaderNodeTexCoord").outputs["Object"], nz.inputs["Vector"])
    mm = N(nt, "ShaderNodeMix")
    mm.data_type = "RGBA"
    mm.inputs[6].default_value = (0.10, 0.17, 0.035, 1)
    mm.inputs[7].default_value = (0.30, 0.24, 0.05, 1)
    L(nt, nz.outputs["Fac"], mm.inputs[0])
    L(nt, mm.outputs[2], bs.inputs["Base Color"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def build_kelp():
    km = kelp_material()
    bm = bmesh.new()
    spots = []
    # along the canyon: at road edges, on building bases, on cars
    for i in range(170):
        x = rnd.choice([-1, 1]) * rnd.uniform(6.6, 19.0)
        y = rnd.uniform(6.0, 62.0)
        spots.append((x, y, SEABED))
    for i in range(60):
        spots.append((rnd.choice([-1, 1]) * rnd.uniform(6.6, 12), rnd.uniform(6, 30), SEABED))
    # some grow from rooftops
    for (cx, cy, top) in TOWERS[:14]:
        for k in range(5):
            spots.append((cx + rnd.uniform(-3, 3), cy + rnd.uniform(-3, 3), top))
    for (x, y, z) in spots:
        hgt = rnd.uniform(1.5, 6.5) if z == SEABED else rnd.uniform(1.2, 3.0)
        segs = 10
        wid = rnd.uniform(0.10, 0.22)
        ang = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.0, 0.5)
        dx, dy = math.cos(ang), math.sin(ang)
        rows = []
        for s in range(segs + 1):
            t = s / segs
            off = lean * hgt * t * t + 0.12 * math.sin(t * 5 + x)
            cxx, cyy, czz = x + dx * off, y + dy * off, z + hgt * t
            ww = wid * (1 - 0.6 * t) * (1 + 0.3 * math.sin(t * 12 + y))
            px, py = -dy, dx
            rows.append((bm.verts.new((cxx - px * ww, cyy - py * ww, czz)), bm.verts.new((cxx + px * ww, cyy + py * ww, czz))))
        for s in range(segs):
            bm.faces.new((rows[s][0], rows[s][1], rows[s + 1][1], rows[s + 1][0]))
    k = mesh_obj("Kelp", bm, [C_UNDER])
    k.data.materials.append(km)
    wv = k.modifiers.new("Sway", "WAVE")
    wv.use_normal = True
    wv.use_normal_x = True
    wv.use_normal_y = True
    wv.use_normal_z = False
    wv.height = 0.10
    wv.width = 2.2
    wv.narrowness = 3.0
    wv.speed = 0.035
    wv.time_offset = 0
    wv.use_x = True
    wv.use_y = True
    wv.start_position_x = 0
    wv.start_position_y = 0
    wv.falloff_radius = 0
    return k


build_kelp()


def build_debris():
    """rubble, drifting silt clouds, barnacle bumps are in shaders; add rubble + tilted signs"""
    bm = bmesh.new()
    for i in range(160):
        x = rnd.uniform(-17, 17)
        y = rnd.uniform(6, 94)
        s = rnd.uniform(0.08, 0.5)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s, matrix=Matrix.Translation((x, y, SEABED + s * 0.3)) @ Matrix.Diagonal((1, rnd.uniform(0.6, 1.4), rnd.uniform(0.4, 0.9), 1)))
    for v in bm.verts:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.03
    rub = mesh_obj("Rubble", bm, [C_UNDER], smooth=False)
    m, nt = new_mat("Rubble")
    col, rough, nor = pbr_maps(nt, "rock_boulder_cracked", scale=0.6, strength=1.0)
    bs = principled(nt)
    tt = N(nt, "ShaderNodeMix")
    tt.data_type = "RGBA"
    tt.blend_type = "MULTIPLY"
    tt.inputs[0].default_value = 1
    tt.inputs[7].default_value = (0.45, 0.5, 0.45, 1)
    L(nt, col, tt.inputs[6])
    L(nt, tt.outputs[2], bs.inputs["Base Color"])
    L(nt, rough, bs.inputs["Roughness"])
    L(nt, nor, bs.inputs["Normal"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    rub.data.materials.append(m)


build_debris()


# ----------------------------------------------------------------------------- water volume, fog shell, caustics, marine snow
def build_volume():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 60, -30)) @ Matrix.Diagonal((400, 300, 60, 1)))
    vol = mesh_obj("WaterVolume", bm, [C_UNDER], smooth=False)
    m, nt = new_mat("WaterVolume")
    ab = N(nt, "ShaderNodeVolumeAbsorption")
    ab.inputs["Color"].default_value = (0.10, 0.42, 0.85, 1)
    ab.inputs["Density"].default_value = 0.05
    sc = N(nt, "ShaderNodeVolumeScatter")
    sc.inputs["Color"].default_value = (0.12, 0.45, 0.75, 1)
    sc.inputs["Density"].default_value = 0.012
    sc.inputs["Anisotropy"].default_value = 0.55
    ad = N(nt, "ShaderNodeAddShader")
    L(nt, ab.outputs[0], ad.inputs[0])
    L(nt, sc.outputs[0], ad.inputs[1])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, ad.outputs[0], out.inputs["Volume"])
    vol.data.materials.append(m)
    hidden_until(vol, HOOK + 3)
    return vol


VOL = build_volume()


def build_fog_shell():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=60.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.5], context="VERTS")
    for f in [f for f in bm.faces if False]:
        pass
    # flip normals inward
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    sh = mesh_obj("FogShell", bm, [C_UNDER])
    m, nt = new_mat("FogShell")
    geo = N(nt, "ShaderNodeNewGeometry")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    tcx = N(nt, "ShaderNodeTexCoord")
    L(nt, tcx.outputs["Object"], sp.inputs[0])
    mr = N(nt, "ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -60.0
    mr.inputs["From Max"].default_value = 0.0
    L(nt, sp.outputs["Z"], mr.inputs["Value"])
    ramp = N(nt, "ShaderNodeMix")
    ramp.data_type = "RGBA"
    ramp.inputs[6].default_value = (0.004, 0.05, 0.14, 1)
    ramp.inputs[7].default_value = (0.03, 0.26, 0.46, 1)
    L(nt, mr.outputs[0], ramp.inputs[0])
    em = N(nt, "ShaderNodeEmission")
    L(nt, ramp.outputs[2], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, em.outputs[0], out.inputs["Surface"])
    sh.data.materials.append(m)
    sh.visible_shadow = False
    for f in range(1, NF + 1):
        sh.location = (CAMPOS[f - 1][0], CAMPOS[f - 1][1], 0.0)
        sh.keyframe_insert("location", frame=f)
    hidden_until(sh, HOOK + 3)
    return sh


build_fog_shell()


def build_caustic_caster():
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=140.0)
    pl = mesh_obj("CausticCaster", bm, [C_UNDER], loc=(0, 40, -0.35), smooth=False)
    m, nt = new_mat("CausticCaster")
    m.surface_render_method = "DITHERED"
    m.use_transparent_shadow = True if hasattr(m, "use_transparent_shadow") else None
    tc = N(nt, "ShaderNodeTexCoord")
    vor = N(nt, "ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.voronoi_dimensions = "4D"
    vor.inputs["Scale"].default_value = 0.55
    w = N(nt, "ShaderNodeValue")
    dd = w.outputs[0].driver_add("default_value").driver
    dd.type = "SCRIPTED"
    dd.expression = "frame*0.028"
    L(nt, w.outputs[0], vor.inputs["W"])
    L(nt, tc.outputs["Object"], vor.inputs["Vector"])
    vor2 = N(nt, "ShaderNodeTexVoronoi")
    vor2.feature = "DISTANCE_TO_EDGE"
    vor2.voronoi_dimensions = "4D"
    vor2.inputs["Scale"].default_value = 0.23
    L(nt, MATH(nt, "MULTIPLY", w.outputs[0], 0.6), vor2.inputs["W"])
    L(nt, tc.outputs["Object"], vor2.inputs["Vector"])
    # alpha: mostly opaque (blocks light) with bright web lines letting light through
    mr = N(nt, "ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.16
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 1.0
    L(nt, vor.outputs["Distance"], mr.inputs["Value"])
    mr2 = N(nt, "ShaderNodeMapRange")
    mr2.inputs["From Min"].default_value = 0.0
    mr2.inputs["From Max"].default_value = 0.25
    L(nt, vor2.outputs["Distance"], mr2.inputs["Value"])
    a = MATH(nt, "MULTIPLY", MATH(nt, "MINIMUM", mr.outputs[0], 1.0), MATH(nt, "ADD", 0.35, MATH(nt, "MULTIPLY", MATH(nt, "MINIMUM", mr2.outputs[0], 1.0), 0.65)))
    bs = principled(nt)
    L(nt, MATH(nt, "MULTIPLY", MATH(nt, "SUBTRACT", 1.0, a), 0.92), bs.inputs["Alpha"])
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    pl.data.materials.append(m)
    for at in ("visible_camera", "visible_glossy", "visible_diffuse", "visible_transmission", "visible_volume_scatter"):
        setattr(pl, at, False)
    hidden_until(pl, HOOK + 3)
    return pl


build_caustic_caster()


def build_marine_snow():
    n = 150000
    bm = bmesh.new()
    lo = np.array([-11, 2.5, -19.0])
    hi = np.array([11, 92.0, -1.5])
    pts = nrng.uniform(lo, hi, (n, 3))
    sz = nrng.uniform(0.004, 0.014, n)
    for p, s in zip(pts, sz):
        a = bm.verts.new((p[0], p[1], p[2] + s))
        b = bm.verts.new((p[0] + s, p[1] - s * 0.5, p[2] - s * 0.5))
        c = bm.verts.new((p[0] - s, p[1] - s * 0.5, p[2] - s * 0.5))
        d = bm.verts.new((p[0], p[1] + s, p[2] - s * 0.5))
        bm.faces.new((a, b, c))
        bm.faces.new((a, c, d))
        bm.faces.new((a, d, b))
        bm.faces.new((b, d, c))
    ob = mesh_obj("MarineSnow", bm, [C_UNDER], smooth=False)
    m, nt = new_mat("Snow")
    bs = principled(nt)
    set_in(bs, "Base Color", (0.75, 0.8, 0.72))
    set_in(bs, "Roughness", 0.8)
    set_in(bs, "Emission Color", (0.55, 0.85, 0.85, 1))
    set_in(bs, "Emission Strength", 0.12)
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    # slow global drift so the particulate never sits still
    ob.location = (0, 0, 0)
    ob.keyframe_insert("location", frame=1)
    ob.location = (0.3, 0.9, 0.45)
    ob.keyframe_insert("location", frame=NF)
    ob.visible_shadow = False
    hidden_until(ob, HOOK + 3)
    return ob


build_marine_snow()


# ----------------------------------------------------------------------------- fish
def build_fish():
    def fish_mesh(name, L_, H, W):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=1.0, matrix=Matrix.Diagonal((L_ * 0.5, H * 0.5, W * 0.5, 1)))
        # tail
        t0 = bm.verts.new((-L_ * 0.42, 0, 0))
        t1 = bm.verts.new((-L_ * 0.78, H * 0.55, 0))
        t2 = bm.verts.new((-L_ * 0.78, -H * 0.55, 0))
        t3 = bm.verts.new((-L_ * 0.5, 0, W * 0.05))
        bm.faces.new((t0, t1, t2))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        return me

    mfish = bpy.data.materials.new("Fish")
    mfish.use_nodes = True
    nt = mfish.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bs = principled(nt)
    tc = N(nt, "ShaderNodeTexCoord")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc.outputs["Object"], sep.inputs[0])
    mr = N(nt, "ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.12
    mr.inputs["From Max"].default_value = 0.12
    L(nt, sep.outputs["Y"], mr.inputs["Value"])
    cm = N(nt, "ShaderNodeMix")
    cm.data_type = "RGBA"
    cm.inputs[6].default_value = (0.25, 0.32, 0.36, 1)
    cm.inputs[7].default_value = (0.85, 0.88, 0.86, 1)
    L(nt, mr.outputs[0], cm.inputs[0])
    L(nt, cm.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Metallic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = 0.28
    out = N(nt, "ShaderNodeOutputMaterial")
    L(nt, bs.outputs[0], out.inputs["Surface"])
    small = fish_mesh("FishSmall", 0.26, 0.09, 0.03)
    big = fish_mesh("FishBig", 0.8, 0.28, 0.09)
    for me in (small, big):
        me.materials.append(mfish)
    fr = np.arange(1, NF + 1)
    schools = [
        (small, 46, Vector((-9.0, 36.0, -18.3)), Vector((4.2, 0.0, 0.1)), 180, 255, (2.0, 1.6, 1.0)),
        (small, 40, Vector((9.0, 60.0, -18.5)), Vector((-4.0, 0.3, 0.0)), 285, 360, (2.0, 1.4, 1.0)),
        (big, 4, Vector((-6.0, 70.0, -18.5)), Vector((3.0, 0.0, 0.2)), 330, 420, (1.4, 1.5, 0.8)),
        (small, 44, Vector((8.0, 68.0, -19.0)), Vector((-3.6, -0.5, 0.1)), 395, 470, (2.0, 1.4, 1.0)),
    ]
    for si, (me, cnt, c0, vel, fs, fe, spr) in enumerate(schools):
        for i in range(cnt):
            off = Vector((rnd.gauss(0, spr[0]), rnd.gauss(0, spr[1]), rnd.gauss(0, spr[2])))
            ob = bpy.data.objects.new(f"Fish{si}_{i}", me)
            link(ob, C_UNDER)
            sc = rnd.uniform(0.8, 1.25)
            ob.scale = (sc, sc, sc)
            ph = rnd.uniform(0, 6.28)
            spd = rnd.uniform(0.9, 1.1)
            heading = math.atan2(vel.y, vel.x)
            ob.rotation_mode = "XYZ"
            for f in range(fs, fe + 1, 2):
                t = (f - fs) / 24.0
                p = c0 + off + vel * spd * t
                p += Vector((0.15 * math.sin(t * 2.1 + ph), 0.1 * math.cos(t * 1.7 + ph), 0.1 * math.sin(t * 2.7 + ph)))
                ob.location = p
                ob.rotation_euler = (0.0, 0.0, heading + 0.28 * math.sin(f / 24 * 2 * math.pi * 3.0 + ph) + 0.05 * math.sin(t + ph))
                ob.keyframe_insert("location", frame=f)
                ob.keyframe_insert("rotation_euler", frame=f)
            keyed_bool(ob, "hide_render", [(1, True), (max(1, fs - 1), False), (fe + 1, True)]) if fe < NF else keyed_bool(ob, "hide_render", [(1, True), (max(1, fs - 1), False)])


build_fish()


# ----------------------------------------------------------------------------- lighting swap + world exposure over time
def key_swap():
    # sun swap: golden air sun off, blue-white underwater sun on, world ambient down
    sun_air.data.energy = 3.0
    sun_air.data.keyframe_insert("energy", frame=HOOK + 3)
    sun_air.data.energy = 0.0
    sun_air.data.keyframe_insert("energy", frame=HOOK + 8)
    sun_under.data.energy = 0.0
    sun_under.data.keyframe_insert("energy", frame=HOOK + 3)
    sun_under.data.energy = 1.9
    sun_under.data.keyframe_insert("energy", frame=HOOK + 9)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Strength"].default_value = 2.0
    bg.inputs["Strength"].keyframe_insert("default_value", frame=HOOK + 3)
    bg.inputs["Strength"].default_value = 0.10
    bg.inputs["Strength"].keyframe_insert("default_value", frame=HOOK + 9)
    for a in (sun_air, sun_under):
        for lay in a.data.animation_data.action.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"


key_swap()

# everything under the surface that is not needed before the dive stays hidden (speed)
visible_until(BEACH, HOOK + 3)
for nm in ("Buildings", "Seabed", "Roads", "LampPosts", "LampHeads", "Kelp", "Rubble", "DoorCards"):
    hidden_until(bpy.data.objects[nm], HOOK - 2)
for ob in list(bpy.data.objects):
    if ob.type == "LIGHT" and ob.name.startswith(("Lamp", "Win")):
        keyed_bool(ob, "hide_render", [(1, True), (HOOK + 3, False)])

if "--check" in sys.argv:
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    trees = {}
    for nm in ("Buildings", "Rubble", "LampPosts", "LampHeads", "Piles", "PierSub", "Kelp", "DoorCards"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            trees[nm] = BVHTree.FromObject(ob, dg)
    cam_ = scene.camera
    bad = []
    seg = {}
    for f in range(100, 481):
        scene.frame_set(f)
        p = cam_.matrix_world.translation
        best = (9e9, "")
        for nm, t in trees.items():
            r = t.find_nearest(p)
            if r[0] is not None and r[3] < best[0]:
                best = (r[3], nm)
        seg[f] = best
        if best[0] < 0.55:
            bad.append((f, round(best[0], 2), best[1], tuple(round(v, 1) for v in p)))
    print("CLEARANCE violations (<0.55 m):", len(bad))
    for b in bad[:60]:
        print("  CLR", b)
    for a in range(100, 481, 12):
        print("  MIN12", a, round(min(seg[f][0] for f in range(a, min(a + 12, 481))), 2))
    # vault: lowest vertex of the kid inside the rail slab (x within 0.08 of 2.5), frames 60..82
    kid_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.parent is not None and o.name.endswith(("mL", "mR", "pelvis_m", "torso_m"))]
    for f in range(60, 84):
        scene.frame_set(f)
        zmin = 9e9
        for o in kid_objs:
            me = o.evaluated_get(dg).to_mesh()
            mw = o.matrix_world
            for v in me.vertices:
                w = mw @ v.co
                if abs(w.x - 2.5) < 0.08 and w.z < zmin:
                    zmin = w.z
            o.evaluated_get(dg).to_mesh_clear()
        print("  VAULT", f, "lowest kid vertex in rail slab z=%.2f clearance over finial top (2.63)=%.2f" % (zmin, zmin - 2.63) if zmin < 9e8 else "none in slab")

scene.frame_set(1)
save = None
if "--save" in sys.argv:
    save = sys.argv[sys.argv.index("--save") + 1]
if save:
    bpy.ops.wm.save_as_mainfile(filepath=save)
    print("saved", save)
