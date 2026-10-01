# PREVIS renderer (EEVEE, 540x960, 24 fps, PNG sequence, overwrite OFF so it resumes).
#   render_slot.sh 08-impossible-kick blender -b blender/scene.blend -P blender/render_previs.py -- [--start 0 --end 191 --out renders/frames]
import bpy, sys, os, time
a = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def opt(k, d):
    return a[a.index(k)+1] if k in a else d
start = int(opt('--start', 0)); end = int(opt('--end', 191)); out = os.path.abspath(opt('--out', 'renders/frames')); os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 12
sc.render.resolution_x = 540; sc.render.resolution_y = 960; sc.render.resolution_percentage = 100
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.30
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
sc.render.use_overwrite = False
for f in range(start, end+1):
    path = f'{out}/f_{f:04d}.png'
    if os.path.exists(path): continue
    t = time.time(); sc.frame_set(f); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time()-t:.1f}s', flush=True)
