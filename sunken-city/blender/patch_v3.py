"""Builds scene_v3.py from scene.py (v2a) + _v3_pier.py + _v3_forum.py. Run with plain python3 (text patching only)."""
import re, os
here = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(here, "scene.py")).read()
pier = open(os.path.join(here, "_v3_pier.py")).read()
forum = open(os.path.join(here, "_v3_forum.py")).read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:70])
    s = s.replace(old, new)


# 1. world: procedural Nishita sunset sky (deep blue -> orange), sun direction shared with the sun lamp
rep('''    mp = N(nt, "ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(WORLD_ROT))
    env = N(nt, "ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(A, "hdri", "kloppenheim_06_puresky_4k.hdr"))
''', '''    el_, az_ = math.radians(SUN_EL_DEG), math.radians(SUN_AZ_DEG)
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
''')
rep('''    L(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    L(nt, mp.outputs[0], env.inputs["Vector"])
    L(nt, env.outputs["Color"], bg.inputs["Color"])
''', '''    L(nt, skycol, bg.inputs["Color"])
''')
rep('WORLD_ROT = float(os.environ.get("WORLD_ROT", "200"))\nbuild_world()',
    'SUN_AZ_DEG, SUN_EL_DEG = 83.0, 4.0\nbuild_world()')
rep('sun_air = make_sun("SunAir", (1.0, 0.62, 0.32), 3.0, 5.0, 104.0, None, angle=1.5)',
    'sun_air = make_sun("SunAir", (1.0, 0.58, 0.28), 3.4, SUN_EL_DEG, SUN_AZ_DEG, None, angle=1.5)')

# 2. pier
rep('\nbuild_pier()\n', '\n' + pier + '\nbuild_pier_v3()\n')

# 3. kid materials (blond, striped tee, rolled jeans, barefoot) + constants + motion
rep('''    skin = simple_mat("Skin", (0.05, 0.032, 0.024), 0.55)
    hair = simple_mat("Hair", (0.006, 0.005, 0.004), 0.6)
    hood = simple_mat("Hoodie", (0.035, 0.018, 0.014), 0.9, bump=1.2)
    shorts = simple_mat("Shorts", (0.012, 0.016, 0.03), 0.85, bump=0.8)
    shoe = simple_mat("Shoe", (0.05, 0.047, 0.042), 0.7, bump=0.3)
''', '''    skin = simple_mat("Skin", (0.50, 0.30, 0.22), 0.55)
    hair = simple_mat("Hair", (0.50, 0.33, 0.10), 0.6)
    hood = stripe_mat("StripeTee")
    shorts = simple_mat("Shorts", (0.04, 0.10, 0.28), 0.85, bump=0.8)
    shoe = skin
''')
rep('def build_kid():', '''def stripe_mat(name):
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


def build_kid():''')
rep('''TAKEOFF_V1 = 59
KY0 = -10.5
RUNV = 4.5
FLY_VY = 3.4
FLY_VH = 4.0
''', '''TAKEOFF_V1 = 55
KY0 = -10.5
RUNV = 4.5
FLY_VY = 4.44
FLY_VH = 4.0
KX0, KX_T, FLY_VX = 0.3, 1.3, 2.3          # veer to the side rail, then vault it
KID_EX = KX_T + FLY_VX * (HOOK_V1 - TAKEOFF_V1) / 24.0
''')
rep('d["pos"] = (0.0 + 0.04 * math.sin(ph), y, z)',
    'd["pos"] = (KX0 + (KX_T - KX0) * smoothstep(TAKEOFF_V1 - 34, TAKEOFF_V1 - 3, f) + 0.04 * math.sin(ph), y, z)')
rep('d["pos"] = (0.02, y, z)', 'd["pos"] = (KX_T + FLY_VX * ta, y, z)')
rep('d["pos"] = (0.02 + 0.12 * rel, y, z)',
    'd["pos"] = (KID_EX + 0.12 * rel + 0.4 * tau * (1 - math.exp(-tt / tau)) / 24.0, y, z)')
rep('print("kid entry y", KID_ENTRY_Y)', 'KID_ENTRY_X = KID_EX\nprint("kid entry", KID_ENTRY_X, KID_ENTRY_Y)\nBEACH = build_beach()\nvisible_until_ = None')
s = s.replace("(0, ey,", "(KID_ENTRY_X, ey,")
assert s.count("(KID_ENTRY_X, ey,") >= 6

# 4. camera path
i0 = s.index("    pos_keys = [")
i1 = s.index("    pos = gauss_smooth(interp_keys(pos_keys), 3.5)")
s = s[:i0] + '''    pos_keys = [
        (1, (-0.1, -15.7, 1.95)), (14, (-0.1, -13.4, 1.95)), (40, (0.2, -8.6, 1.93)), (62, (0.6, -4.3, 1.98)),
        (68, (0.9, -3.3, 2.30)), (76, (1.6, -1.6, 2.90)), (84, (2.4, 0.0, 3.30)), (93, (3.0, 1.9, 2.70)),
        (101, (3.3, 3.1, 1.70)), (105, (3.5, 4.0, 0.40)), (109, (3.6, 4.6, -1.30)), (120, (3.4, 5.4, -3.2)),
        (192, (3.4, 7.5, -9.0)), (288, (0.0, 10.5, -15.5)), (384, (0.0, 34.0, -16.4)),
        (480, (0.0, 66.0, -16.2)), (528, (0.0, 76.0, -16.0)), (576, (0.0, 79.6, -15.8)),
    ]
''' + s[i1:]
rep('''        (84 + S_, (0, 3.2, 0.9)), (88 + S_, (0, 5.0, 0.6)), (92 + S_, (0, 6.0, -1.4)), (98 + S_, (0, 6.5, -3.6)),''',
    '''        (84 + S_, (4.0, 4.4, 0.4)), (88 + S_, (4.1, 5.0, 0.0)), (92 + S_, (4.1, 6.0, -1.4)), (98 + S_, (3.9, 6.5, -3.6)),''')

# 5. forum instead of the street canyon
rep('TOWERS = build_city()', forum + '\nTOWERS = build_forum()')
rep('\nbuild_dress()\n', '\n')
rep('''    box(bm, 0.0, YF + 6.0, SEABED - 0.5, 12.0, 12.0, 15.5)''', '''    box(bm, 0.0, YF + 6.0, SEABED - 0.5, 16.8, 12.0, 12.3)''')
rep('for i in range(34):', 'for i in range(52):')
rep('x = rnd.uniform(-8, 8)\n        y = rnd.uniform(4, 62)', 'x = rnd.uniform(-17, 17)\n        y = rnd.uniform(4, 88)')
rep('MATH(nt, "MULTIPLY", a, 0.13)', 'MATH(nt, "MULTIPLY", a, 0.22)')
rep('x = rnd.choice([-1, 1]) * rnd.uniform(3.4, 5.2)\n        y = rnd.uniform(6.0, 70.0)',
    'x = rnd.choice([-1, 1]) * rnd.uniform(2.8, 18.0)\n        y = rnd.uniform(6.0, 94.0)')
rep('x = rnd.uniform(-5.2, 5.2)\n        y = rnd.uniform(6, 70)', 'x = rnd.uniform(-17, 17)\n        y = rnd.uniform(6, 94)')
rep('ab.inputs["Density"].default_value = 0.08', 'ab.inputs["Density"].default_value = 0.05')
rep('sc.inputs["Density"].default_value = 0.018', 'sc.inputs["Density"].default_value = 0.012')
rep('ramp.inputs[6].default_value = (0.002, 0.03, 0.05, 1)', 'ramp.inputs[6].default_value = (0.004, 0.05, 0.14, 1)')
rep('ramp.inputs[7].default_value = (0.01, 0.16, 0.22, 1)', 'ramp.inputs[7].default_value = (0.03, 0.26, 0.46, 1)')
rep('for nm in ("Buildings", "RoofProps", "Cars", "Seabed", "Roads", "LampPosts", "LampHeads", "Kelp", "Rubble"):',
    'visible_until(BEACH, HOOK + 3)\nfor nm in ("Buildings", "Seabed", "Roads", "LampPosts", "LampHeads", "Kelp", "Rubble", "DoorCards"):')
rep('visible_until_ = None', '')
rep('MATH(nt, "POWER", cm2.outputs[0], 1.5), 0.22)', 'MATH(nt, "POWER", cm2.outputs[0], 1.5), 0.09)')
rep('(kp.x * 0.5, kp.y + 0.2, kp.z + 0.72)', '(kp.x * 1.0, kp.y + 0.2, kp.z + 0.72)')
rep('(kp.x * 0.5, kp.y + 0.2, kp.z + 0.5)', '(kp.x * 1.0, kp.y + 0.2, kp.z + 0.5)')
rep('    bg.inputs["Strength"].default_value = 1.0\n    bg.inputs["Strength"].keyframe_insert("default_value", frame=HOOK + 3)',
    '    bg.inputs["Strength"].default_value = 2.0\n    bg.inputs["Strength"].keyframe_insert("default_value", frame=HOOK + 3)')
rep('    scene.view_settings.exposure = 0.0', '    scene.view_settings.exposure = 0.3')
open(os.path.join(here, "scene_v3.py"), "w").write(s)
print("ok", len(s))
