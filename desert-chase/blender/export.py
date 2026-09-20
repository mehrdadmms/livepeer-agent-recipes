import bpy, json, math
sc = bpy.context.scene
path = [list(v) for v in []]
marks = sorted([(m.frame, m.camera) for m in sc.timeline_markers], key=lambda t: t[0])
data = {"frames": []}
# road samples
cd = bpy.data.objects["RoadPath"]
dg = bpy.context.evaluated_depsgraph_get()
me = cd.evaluated_get(dg).to_mesh()
data["road"] = [[v.co.x, v.co.y] for v in me.vertices]
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
    cam = ([c for fr, c in marks if fr <= f] or [marks[0][1]])[-1]
    mw = cam.matrix_world
    fwd = mw.to_3x3() @ __import__("mathutils").Vector((0, 0, -1))
    data["frames"].append({
        "lead": list(bpy.data.objects["LeadCar"].matrix_world.translation)[:2],
        "chase": list(bpy.data.objects["ChaseCar"].matrix_world.translation)[:2],
        "cam": list(mw.translation), "fwd": list(fwd)[:2], "lens": cam.data.lens, "name": cam.name})
json.dump(data, open(bpy.path.abspath("//motion.json"), "w"))
