"""scene_v3.py -> scene_v4.py : rail vault, FPV forum dive, forum tweaks for the slalom/orbit. Plain python text patching."""
import os
here = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(here, "scene_v3.py")).read()
kid = open(os.path.join(here, "_v4_kid.py")).read()
cam = open(os.path.join(here, "_v4_cam.py")).read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- 1. kid constants / vault
rep("TAKEOFF_V1 = 55", "TAKEOFF_V1 = 49")
rep("KX0, KX_T, FLY_VX = 0.3, 1.3, 2.3", "KX0, KX_T, FLY_VX = 0.3, 1.9, 2.3")
rep("KID_EX = KX_T + FLY_VX * (HOOK_V1 - TAKEOFF_V1) / 24.0", "KID_EX = 3.4\nKID_ENTRY_Y = 1.85")
i0 = s.index("KID_ENTRY_Y = KY0 + RUNV")
i1 = s.index("\n", i0)
s = s[:i0] + "KID_ENTRY_Y = 1.85" + s[i1:]
rep("def kid_state(f):\n    return kid_state_v1(f - SHIFT)\n", kid)
rep("TAKEOFF = TAKEOFF_V1 + SHIFT", "TAKEOFF = 62")
rep('KID[f"shoulder{nm}"].rotation_euler = (d[f"sh{nm}"], 0, d["armAbd"] * s)',
    'KID[f"shoulder{nm}"].rotation_euler = (d[f"sh{nm}"], d.get(f"sh{nm}y", 0.0), d["armAbd"] * s)')
rep('        r.keyframe_insert("location", frame=f)\n',
    '        r.keyframe_insert("location", frame=f)\n        r.rotation_euler = (0, d.get("roll", 0.0), 0)\n        r.keyframe_insert("rotation_euler", frame=f)\n')

# ---- 2. camera: pre-hook keys, aim keys, lurch, FPV dive
i0 = s.index("    pos_keys = [")
i1 = s.index("    pos = gauss_smooth(interp_keys(pos_keys), 3.5)")
s = s[:i0] + '''    pos_keys = [
        (1, (-0.1, -15.7, 1.95)), (14, (-0.1, -13.4, 1.95)), (40, (0.2, -8.6, 1.93)), (62, (0.6, -4.3, 1.98)),
        (68, (1.0, -3.0, 2.25)), (73, (1.5, -1.5, 2.90)), (78, (2.4, -0.2, 3.40)), (84, (3.0, 0.1, 3.20)),
        (90, (3.25, 0.1, 2.60)), (94, (3.3, 0.4, 1.90)), (97, (3.35, 0.8, 1.40)), (100, (3.4, 1.4, 0.5)),
        (104, (3.45, 2.0, -0.5)), (109, (3.5, 2.7, -1.3)), (120, (3.4, 3.4, -3.2)),
        (192, (3.4, 7.5, -9.0)), (288, (0.0, 10.5, -15.5)), (384, (0.0, 34.0, -16.4)),
        (480, (0.0, 66.0, -16.2)), (528, (0.0, 76.0, -16.0)), (576, (0.0, 79.6, -15.8)),
    ]
''' + s[i1:]
rep("(84 + S_, (4.0, 4.4, 0.4)), (88 + S_, (4.1, 5.0, 0.0)), (92 + S_, (4.1, 6.0, -1.4)), (98 + S_, (3.9, 6.5, -3.6)),",
    "(84 + S_, (3.4, 1.85, 0.4)), (88 + S_, (3.5, 2.6, -0.3)), (92 + S_, (3.5, 3.5, -1.5)), (98 + S_, (3.4, 4.5, -3.6)),")
rep("    # ---- handheld\n", cam + "    # ---- handheld\n")
rep("rol_n = np.deg2rad(noise([0.4, 1.1], [1.0, 0.5]) * env) + np.deg2rad(1.6)",
    "rol_n = np.deg2rad(noise([0.4, 1.1], [1.0, 0.5]) * env) + np.deg2rad(1.6) + BANK")
rep("        # takeoff bounce\n",
    "        t3 = f - 73\n        if 0 <= t3 < 16:\n            pit_n[i] += math.radians(5.0) * math.exp(-t3 / 5.0) * math.cos(t3 * 0.7)\n            rol_n[i] += math.radians(-6.0) * math.exp(-t3 / 6.0) * math.sin(t3 * 0.6)\n        # takeoff bounce\n")

# ---- 3. forum: slalom columns, gate pair moved, hero drum, toppled statue, statues moved
rep("def add_statue(bm, x, y, z0, yaw, sc=1.0, arm_up=True):\n    vbox(bm, x, y, z0 + 0.15, 1.9, 1.9, 0.3)\n    vbox(bm, x, y, z0 + 1.2, 1.4, 1.4, 1.9)\n    vbox(bm, x, y, z0 + 2.25, 1.75, 1.75, 0.22)\n    zb = z0 + 2.36\n",
    "def add_statue(bm, x, y, z0, yaw, sc=1.0, arm_up=True, plinth=True):\n    if plinth:\n        vbox(bm, x, y, z0 + 0.15, 1.9, 1.9, 0.3)\n        vbox(bm, x, y, z0 + 1.2, 1.4, 1.4, 1.9)\n        vbox(bm, x, y, z0 + 2.25, 1.75, 1.75, 0.22)\n    zb = z0 + (2.36 if plinth else 0.0)\n")
rep("        add_column(bs_, sx * 2.8, 44.0, SB + 0.1, 10.0, 0.75)", "        add_column(bs_, sx * 3.6, 17.0, SB + 0.1, 10.0, 0.75)")
rep("    vbox(bs_, 0, 44.0, SB + 10.1 + 0.45, 6.6, 1.7, 0.9)", "    vbox(bs_, 0, 17.0, SB + 10.1 + 0.45, 8.4, 1.7, 0.9)")
rep("    add_lantern(bg_, bb_, -2.0, 44.0, SB + 6.0)\n    add_lantern(bg_, bb_, 2.0, 44.0, SB + 6.0)",
    "    add_lantern(bg_, bb_, -2.6, 17.0, SB + 6.0)\n    add_lantern(bg_, bb_, 2.6, 17.0, SB + 6.0)\n"
    "    # v4: inner slalom columns (alternate sides) the FPV weaves through\n"
    "    for k_, y_ in enumerate((22.6, 27.0, 31.4, 35.8, 40.2, 44.6)):\n"
    "        add_column(bs_, (2.6 if k_ % 2 == 0 else -2.6), y_, SB + 0.1, 9.0, 0.7)\n"
    "    # hero fallen drum (near miss)\n"
    "    bmesh.ops.create_cone(bd_, cap_ends=True, segments=18, radius1=0.75, radius2=0.72, depth=2.0,\n"
    "                          matrix=Matrix.Translation((0.6, 51.4, SB + 0.75)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))\n"
    "    # toppled statue = orbit centre\n"
    "    tmp_ = bmesh.new()\n"
    "    add_statue(tmp_, 0, 0, 0, 0.0, 1.0, True, plinth=False)\n"
    "    bmesh.ops.transform(tmp_, matrix=Matrix.Translation((0.5, 63.5, SB + 0.55)) @ Matrix.Rotation(0.35, 4, 'Z') @ Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Translation((0, 0, -1.4)), verts=tmp_.verts)\n"
    "    me_ = bpy.data.meshes.new('toppled')\n    tmp_.to_mesh(me_)\n    tmp_.free()\n    bs_.from_mesh(me_)\n"
    "    vbox(bd_, 0.5 + 1.0, 63.5 + 2.4, SB + 0.5, 1.5, 1.5, 1.0, 0.4)   # broken plinth stub\n")
rep("    add_statue(bs_, -3.6, 34.0, SB + 0.1, 0.6, 1.0, True)\n    add_statue(bs_, 4.0, 63.0, SB + 0.1, math.pi - 0.5, 1.1, False)\n",
    "    add_statue(bs_, -11.5, 36.0, SB + 0.1, 0.6, 1.0, True)\n")
rep("    for (sx, sy) in ((-3.6, 34.0), (4.0, 63.0), (-12.5, 50.0), (12.5, 22.0)):", "    for (sx, sy) in ((-11.5, 36.0), (-12.5, 50.0), (12.5, 22.0)):")
# kelp away from the flight corridor
rep("x = rnd.choice([-1, 1]) * rnd.uniform(2.8, 18.0)\n        y = rnd.uniform(6.0, 94.0)",
    "x = rnd.choice([-1, 1]) * rnd.uniform(6.6, 19.0)\n        y = rnd.uniform(6.0, 62.0)")
rep("        spots.append((rnd.uniform(-8, 8), rnd.uniform(6, 30), SEABED))", "        spots.append((rnd.choice([-1, 1]) * rnd.uniform(6.6, 12), rnd.uniform(6, 30), SEABED))")
# fish schools aligned to the new route
i0 = s.index("    schools = [")
i1 = s.index("    ]\n", i0) + 6
s = s[:i0] + '''    schools = [
        (small, 46, Vector((-9.0, 36.0, -18.3)), Vector((4.2, 0.0, 0.1)), 180, 255, (2.0, 1.6, 1.0)),
        (small, 40, Vector((9.0, 60.0, -18.5)), Vector((-4.0, 0.3, 0.0)), 285, 360, (2.0, 1.4, 1.0)),
        (big, 4, Vector((-6.0, 70.0, -18.5)), Vector((3.0, 0.0, 0.2)), 330, 420, (1.4, 1.5, 0.8)),
        (small, 44, Vector((8.0, 68.0, -19.0)), Vector((-3.6, -0.5, 0.1)), 395, 470, (2.0, 1.4, 1.0)),
    ]
''' + s[i1:]

rep("r.motion_blur_shutter = 0.5", "r.motion_blur_shutter = 0.35")
# ---- 4. optional checks (--check): camera clearance + vault foot clearance
chk = open(os.path.join(here, "_v4_check.py")).read()
rep("scene.frame_set(1)\nsave = None", chk + "\nscene.frame_set(1)\nsave = None")
open(os.path.join(here, "scene_v4.py"), "w").write(s)
print("ok", len(s))
