# usage: blender -b blender/scene.blend -P blender/draft.py -- out_dir frame1,frame2,... [engine] [w h]
import bpy, sys
a = sys.argv[sys.argv.index('--')+1:]
out = a[0]; frames = [int(x) for x in a[1].split(',')]
sc = bpy.context.scene
eng = a[2] if len(a) > 2 else 'BLENDER_EEVEE'
sc.render.engine = eng
sc.render.resolution_x = int(a[3]) if len(a) > 3 else 360; sc.render.resolution_y = int(a[4]) if len(a) > 4 else 640
sc.render.resolution_percentage = 100
if eng == 'CYCLES':
    sc.cycles.samples = 24; sc.cycles.use_denoising = True; sc.cycles.device = 'GPU'
    p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'METAL'; p.get_devices()
    for d in p.devices: d.use = True
else:
    sc.eevee.taa_render_samples = 16
for f in frames:
    sc.frame_set(f); sc.render.filepath = f'{out}/d_{f:03d}.png'
    bpy.ops.render.render(write_still=True)
