# Generates invented murals + fan flags (no real people, teams or brands). Run from the scene folder:
#   ../_shared/venv/bin/python blender/make_murals.py
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
out = "assets/textures/"; rng = np.random.default_rng(88)
W, H = 1024, 1365
def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Impact.ttf", "/System/Library/Fonts/Supplemental/Arial Black.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
def player(d, cx, cy, s, col, kick=True):
    """crude kicking silhouette (torso, head, two legs, arms) - painted-mural flat style"""
    d.ellipse([cx-0.09*s, cy-0.62*s, cx+0.09*s, cy-0.44*s], fill=col)                  # head
    d.polygon([(cx-0.12*s, cy-0.42*s), (cx+0.12*s, cy-0.42*s), (cx+0.09*s, cy), (cx-0.09*s, cy)], fill=col)   # torso
    if kick:
        d.polygon([(cx-0.09*s, cy), (cx+0.02*s, cy), (cx-0.16*s, cy+0.45*s), (cx-0.26*s, cy+0.42*s)], fill=col)   # plant leg
        d.polygon([(cx+0.02*s, cy), (cx+0.10*s, cy-0.02*s), (cx+0.62*s, cy-0.16*s), (cx+0.60*s, cy-0.06*s)], fill=col)   # kicking leg
        d.polygon([(cx-0.12*s, cy-0.38*s), (cx-0.4*s, cy-0.22*s), (cx-0.38*s, cy-0.16*s), (cx-0.08*s, cy-0.30*s)], fill=col)
        d.polygon([(cx+0.12*s, cy-0.38*s), (cx+0.36*s, cy-0.52*s), (cx+0.40*s, cy-0.46*s), (cx+0.10*s, cy-0.30*s)], fill=col)
def ball(d, x, y, r, col=(245, 245, 240), line=(20, 20, 20)):
    d.ellipse([x-r, y-r, x+r, y+r], fill=col, outline=line, width=max(3, r//14))
    d.regular_polygon((x, y, r*0.42), 5, fill=line)
def star(d, x, y, r, col):
    pts = []
    for i in range(10):
        a = -math.pi/2 + i*math.pi/5; rr = r if i % 2 == 0 else r*0.42
        pts.append((x+rr*math.cos(a), y+rr*math.sin(a)))
    d.polygon(pts, fill=col)
def finish(im, name):
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(im.convert("RGB")).astype(np.float32)/255
    # paint wear: mottled fade, cracks of lighter plaster
    noise = rng.random((H, W)); k = np.asarray(Image.fromarray((noise*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))).astype(np.float32)/255
    a = a*(0.72+0.5*k[..., None]) + 0.07*(k[..., None] > 0.62)
    Image.fromarray(np.clip(a*255, 0, 255).astype(np.uint8)).save(out+name+".png")
    ImageOps.mirror(Image.open(out+name+".png")).save(out+name+"_r.png")
# --- mural 1: red kicker on cream, invented club "LOS ROJOS"
im = Image.new("RGB", (W, H), (236, 214, 170)); d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 230], fill=(190, 40, 36)); d.text((60, 40), "LOS ROJOS", font=font(170), fill=(250, 240, 220))
player(d, 420, 780, 1150, (190, 40, 36)); ball(d, 930, 760, 70)
for i in range(5): star(d, 120+i*90, 1250, 34, (190, 40, 36))
finish(im, "mural1")
# --- mural 2: blue keeper dive on yellow, "AZUL 09"
im = Image.new("RGB", (W, H), (240, 196, 50)); d = ImageDraw.Draw(im)
d.rectangle([0, H-260, W, H], fill=(30, 64, 140)); d.text((70, H-240), "AZUL 09", font=font(190), fill=(250, 240, 200))
d.polygon([(150, 700), (330, 640), (760, 560), (900, 520), (930, 560), (780, 640), (340, 790), (180, 800)], fill=(30, 64, 140))   # diving body
d.ellipse([880, 470, 970, 560], fill=(30, 64, 140)); ball(d, 640, 380, 80)
finish(im, "mural2")
# --- mural 3: trophy + ball + stars on teal
im = Image.new("RGB", (W, H), (28, 130, 120)); d = ImageDraw.Draw(im)
d.polygon([(330, 300), (700, 300), (660, 640), (560, 720), (470, 720), (370, 640)], fill=(250, 210, 70))
d.rectangle([470, 720, 560, 980], fill=(250, 210, 70)); d.rectangle([390, 980, 640, 1080], fill=(210, 160, 40))
d.arc([230, 330, 400, 560], 90, 270, fill=(250, 210, 70), width=34); d.arc([630, 330, 800, 560], 270, 90, fill=(250, 210, 70), width=34)
ball(d, 520, 200, 90)
for i in range(7): star(d, 90+i*140, 1230, 40, (250, 210, 70))
d.text((250, 40), "COPA", font=font(160), fill=(250, 240, 220))
finish(im, "mural3")
# --- mural 4: scarves stripes "ULTRAS"
im = Image.new("RGB", (W, H), (20, 20, 28)); d = ImageDraw.Draw(im)
cols = [(190, 40, 36), (245, 245, 240), (30, 64, 140), (240, 196, 50)]
for i in range(-6, 20):
    x = i*90; d.polygon([(x, 0), (x+50, 0), (x+50+380, H), (x+380, H)], fill=cols[i % 4])
d.rectangle([0, 520, W, 860], fill=(20, 20, 28)); d.text((90, 560), "ULTRAS", font=font(250), fill=(250, 240, 220))
finish(im, "mural4")
# --- fan flags 512x320: A red/white stripes + star, B blue/yellow diagonal
fa = Image.new("RGB", (512, 320), (190, 40, 36)); d = ImageDraw.Draw(fa)
for i in range(0, 320, 64): d.rectangle([0, i, 512, i+32], fill=(245, 240, 232))
star(d, 256, 160, 90, (250, 210, 70)); fa.save(out+"flag_a.png")
fb = Image.new("RGB", (512, 320), (30, 64, 140)); d = ImageDraw.Draw(fb)
d.polygon([(0, 320), (0, 160), (512, 0), (512, 160)], fill=(240, 196, 50)); ball(d, 256, 160, 70); fb.save(out+"flag_b.png")
print("murals ok")
