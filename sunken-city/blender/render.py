"""Render frames of blender/scene.blend. Steps every frame (particle sims need it) but only writes wanted ones.
blender -b blender/scene.blend -P blender/render.py -- --out DIR [--pct 100] [--step 1] [--frames 10,50] [--samples 48] [--overwrite]
Existing files are skipped unless --overwrite (so an interrupted render resumes)."""
import bpy, sys, os
a = sys.argv[sys.argv.index("--") + 1:]
def opt(k, d=None):
    return a[a.index(k) + 1] if k in a else d
out = opt("--out")
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_percentage = int(opt("--pct", 75))  # PREVIS: 540x960
sc.eevee.taa_render_samples = int(opt("--samples", 8))
sc.eevee.use_raytracing = False
sc.eevee.use_fast_gi = False
sc.eevee.volumetric_tile_size = "16"
sc.eevee.volumetric_samples = 32
sc.eevee.motion_blur_steps = 2
step = int(opt("--step", 1))
frames = [int(x) for x in opt("--frames").split(",")] if opt("--frames") else list(range(1, sc.frame_end + 1, step))
if opt("--vol"):
    sc.eevee.volumetric_tile_size = opt("--vol")
sc.render.use_overwrite = "--overwrite" in a
import time
for f in range(sc.frame_start, max(frames) + 1):
    sc.frame_set(f)
    sc.eevee.use_shadows = f <= 100   # underwater shadow pass costs 100+ s/frame; beams are shaft cards
    if f in frames:
        p = os.path.join(out, f"f{f:04d}.png")
        if os.path.exists(p) and "--overwrite" not in a:
            continue
        sc.render.filepath = p
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"FRAME {f} {time.time()-t:.1f}s", flush=True)
