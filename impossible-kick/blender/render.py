# FINAL renderer. usage (through the queue):
#   render_slot.sh 08-impossible-kick blender -b blender/scene.blend -P blender/render.py -- [--start 0 --end 191 --samples 48 --res 720 1280 --out renders/frames]
# Cycles on Metal GPU + OpenImageDenoise, PNG sequence, overwrite OFF so an interrupted render resumes.
import bpy, sys, os
a = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def opt(k, d, n=1):
    if k in a:
        v = a[a.index(k)+1:a.index(k)+1+n]; return v if n > 1 else v[0]
    return d
start = int(opt('--start', 0)); end = int(opt('--end', 191)); samples = int(opt('--samples', 48))
rx, ry = (int(x) for x in opt('--res', ('720', '1280'), 2))
out = os.path.abspath(opt('--out', 'renders/frames')); os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; c = sc.cycles
c.device = 'GPU'; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02; c.adaptive_min_samples = 8
c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.max_bounces = 6; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transmission_bounces = 4; c.volume_bounces = 1; c.transparent_max_bounces = 6
c.volume_step_rate = 2.0; c.volume_max_steps = 64
c.sample_clamp_indirect = 8.0; c.sample_clamp_direct = 0
c.film_exposure = 1.0
p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'METAL'; p.get_devices()
for d in p.devices: d.use = (d.type != 'CPU')
sc.render.resolution_x = rx; sc.render.resolution_y = ry; sc.render.resolution_percentage = 100
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'; sc.render.image_settings.compression = 15
sc.render.use_overwrite = False; sc.render.use_placeholder = True
import time
for f in range(start, end+1):
    path = f'{out}/f_{f:04d}.png'
    if os.path.exists(path): continue
    t = time.time(); sc.frame_set(f); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time()-t:.1f}s', flush=True)
