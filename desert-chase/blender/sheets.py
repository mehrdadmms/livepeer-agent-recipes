import bpy, math, os
from mathutils import Vector, Matrix
sc = bpy.context.scene
OUT = bpy.path.abspath("//sheets"); os.makedirs(OUT, exist_ok=True)
sc.frame_set(1)
sc.render.use_motion_blur = False
sc.timeline_markers.clear()
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 768, 512, 100

def look_cam(name, loc, target, lens):
    cam = bpy.data.cameras.new(name); cam.lens = lens; cam.clip_end = 5000
    o = bpy.data.objects.new(name, cam); sc.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o

def set_hidden(root, h):
    stack = [root]
    while stack:
        o = stack.pop(); o.hide_render = h; stack.extend(o.children)

lead, chase = bpy.data.objects["LeadCar"], bpy.data.objects["ChaseCar"]
def render(name, cam):
    sc.camera = cam; sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)

# car turnarounds: front 3/4, side, rear 3/4, front
views = [("a_front34", (4.5, 6.5, 1.2)), ("b_side", (8.5, 0, 1.0)), ("c_rear34", (-4.5, -6.5, 1.4)), ("d_front", (0, 9, 1.1))]
for car, other, tag in ((lead, chase, "car1"), (chase, lead, "car2")):
    set_hidden(other, True); set_hidden(car, False)
    M = car.matrix_world
    tgt = M @ Vector((0, 0, 0.7))
    for vn, off in views:
        render(f"{tag}_{vn}", look_cam(vn, M @ Vector(off), tgt, 40))
set_hidden(lead, True); set_hidden(chase, True)

# environment views along the road (frame 1 positions, cars hidden)
p = bpy.data.objects["LeadRig"].matrix_world
E = [("a_wide", p @ Vector((-14, -30, 6)), p @ Vector((5, 80, 0)), 24),
     ("b_road", p @ Vector((0, -5, 1.2)), p @ Vector((0, 60, 1.0)), 28),
     ("c_aerial", p @ Vector((0, 60, 120)), p @ Vector((20, 180, 0)), 24),
     ("d_side", p @ Vector((-25, 140, 2)), p @ Vector((150, 260, 5)), 35)]
for vn, loc, tg, lens in E:
    render(f"env_{vn}", look_cam(vn, loc, tg, lens))
