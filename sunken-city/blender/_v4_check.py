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
