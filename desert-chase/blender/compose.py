import json, math, os
from PIL import Image, ImageDraw, ImageFont
D = json.load(open("out/motion.json")); F = D["frames"]; road = D["road"]
os.makedirs("out/comp", exist_ok=True)
def font(sz, bold=False):
    for p in ["/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Courier New.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
f14, f18, f24 = font(14), font(18), font(24)
SHOTS = {"CamA_side": ("A", "CAMERA CAR · SIDE TRACK", "0:00–3:12"), "CamB_drone": ("B", "DRONE · HIGH CHASE", "3:12–6:12"),
         "CamC_rear": ("C", "REAR BUMPER MOUNT · LOOKING BACK", "6:12–10:00")}
MW, MH = 440, 720
xs = [p[0] for p in road]; ys = [p[1] for p in road]
x0, x1, y0, y1 = min(xs) - 60, max(xs) + 60, min(ys) + 30, 560
sc = (MH - 110) / 170.0     # 170 m tall window that follows the cars
C = [0.0, 0.0]
def M(p): return (MW / 2 + (p[0] - C[0]) * sc, 70 + (MH - 80) / 2 - (p[1] - C[1]) * sc)
GREY, BLUE, CAM = (205, 208, 212), (40, 110, 255), (255, 196, 0)
def make_base():
  base = Image.new("RGB", (MW, MH), (24, 22, 20)); bd = ImageDraw.Draw(base)
  bd.line([M(p) for p in road], fill=(80, 76, 70), width=int(11 * sc), joint="curve")
  bd.line([M(p) for p in road], fill=(200, 170, 60), width=1)
  bd.text((20, 16), "OVERHEAD · MOTION MAP", font=f18, fill=(235, 230, 220))
  bd.text((20, 42), "lead car", font=f14, fill=GREY); bd.text((170, 42), "chaser", font=f14, fill=BLUE); bd.text((310, 42), "camera", font=f14, fill=CAM)
  bd.rectangle((10, 70, MW - 10, MH - 10), outline=(60, 56, 52))
  return base
def speed(i, key):
    j = min(i + 1, len(F) - 1); k = max(j - 2, 0)
    a, b = F[k][key], F[j][key]; return math.dist(a, b) / ((j - k) / 24) * 3.6
for i, fr in enumerate(F):
    im = Image.open(f"out/frames/f_{i+1:04d}.png").convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    nm = fr["name"]; tag = nm[:2]; desc = nm[3:].replace("_", " ").upper(); rng = ""
    d.rectangle((0, 0, 1280, 44), fill=(0, 0, 0, 140))
    d.text((16, 10), f"SHOT {tag}  ·  {desc}  ·  {fr['lens']:.0f}mm", font=f18, fill=(255, 255, 255))
    t = i / 24; d.text((1100, 10), f"{int(t):02d}:{int((t%1)*24):02d} / 20:00", font=f18, fill=(255, 220, 120))
    d.rectangle((0, 676, 1280, 720), fill=(0, 0, 0, 140))
    gap = math.dist(fr["lead"], fr["chase"])
    d.text((16, 688), f"LEAD {speed(i,'lead'):5.0f} km/h", font=f18, fill=GREY)
    d.text((300, 688), f"CHASER {speed(i,'chase'):5.0f} km/h", font=f18, fill=BLUE)
    d.text((540, 688), f"GAP {gap:4.1f} m", font=f18, fill=(255, 255, 255))
    BPM = float(os.environ.get("BPM", "140")); B0 = float(os.environ.get("BEAT0", "0")); bl = 60 / BPM; bn = max(0, int((t - B0) // bl)); ph = ((t - B0) % bl) / bl if t >= B0 else 0.99
    r_ = 14 if ph < 0.25 else 8
    d.ellipse((930 - r_, 698 - r_, 930 + r_, 698 + r_), fill=(255, 60, 40, 230 if ph < 0.25 else 120))
    d.text((955, 688), f"BEAT {bn+1:02d}  ·  {BPM:.0f} BPM", font=f18, fill=(255, 255, 255))
    C[0] = (fr['lead'][0] + fr['chase'][0]) / 2; C[1] = (fr['lead'][1] + fr['chase'][1]) / 2
    m = make_base(); md = ImageDraw.Draw(m, "RGBA")
    for key, col in (("lead", GREY), ("chase", BLUE)):
        tr = [M(F[j][key]) for j in range(max(0, i - 48), i + 1)]
        if len(tr) > 1: md.line(tr, fill=col + (150,), width=2)
    cx, cy = M(fr["cam"]); fx, fy = fr["fwd"]; n = math.hypot(fx, fy) or 1
    hf = math.atan(18 / fr["lens"]); ang = math.atan2(fy, fx); L = 110
    pts = [(cx, cy)] + [(cx + L * math.cos(ang + s * hf), cy - L * math.sin(ang + s * hf)) for s in (-1, 1)]
    md.polygon(pts, fill=CAM + (60,), outline=CAM)
    md.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=CAM)
    for key, col in (("lead", GREY), ("chase", BLUE)):
        px, py = M(fr[key]); md.ellipse((px - 6, py - 6, px + 6, py + 6), fill=col, outline=(0, 0, 0))
    md.text((20, MH - 60 + 30 - 30), f"SHOT {tag}", font=f14, fill=CAM)
    out = Image.new("RGB", (1280 + MW, 720)); out.paste(im, (0, 0)); out.paste(m, (1280, 0))
    out.save(f"out/comp/c_{i+1:04d}.jpg", quality=90)
