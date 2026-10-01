# Generates invented can label + city window texture + pitch stripes + crowd (no real brands)
import numpy as np, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
out="assets/textures/"
rng=np.random.default_rng(8)
# ---- can label (wraps 360deg: 2048 x 640) ----
W,H=2048,640
img=Image.new("RGB",(W,H),(20,120,110))
d=ImageDraw.Draw(img)
# diagonal citrus bands
for i in range(-10,30):
    x=i*140
    d.polygon([(x,0),(x+70,0),(x-60+ (0),H),(x-130,H)],fill=(232,190,40) if i%2 else (24,132,118))
def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Impact.ttf","/System/Library/Fonts/Supplemental/Arial Black.ttf","/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(p,sz)
        except: pass
    return ImageFont.load_default()
# repeat brand on front (x~512) and back (x~1536)
for cx in (512,1536):
    d.ellipse([cx-300,60,cx+300,580],fill=(200,40,30))
    d.ellipse([cx-280,80,cx+280,560],outline=(255,240,200),width=8)
    f=font(150); t="ZAPPO"
    tw=d.textlength(t,font=f); d.text((cx-tw/2+6,190+6),t,font=f,fill=(70,10,10)); d.text((cx-tw/2,190),t,font=f,fill=(255,244,214))
    f2=font(52); t2="LEMON SODA"; tw=d.textlength(t2,font=f2); d.text((cx-tw/2,360),t2,font=f2,fill=(255,225,90))
    f3=font(32); t3="330 ml  -  ICE COLD"; tw=d.textlength(t3,font=f3); d.text((cx-tw/2,440),t3,font=f3,fill=(255,244,214))
    d.polygon([(cx-30,110),(cx+40,110),(cx+5,175),(cx+45,175),(cx-45,265),(cx-15,190),(cx-50,190)],fill=(255,225,90))
img=img.filter(ImageFilter.GaussianBlur(0.8))
a=np.asarray(img).astype(np.float32)/255
a*= (0.9+0.1*rng.random((H,W,1)))  # print noise
Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)).save(out+"can_label.png")
# ---- window facade texture 1024x1024 : 4 cols x 4 floors ----
S=1024; im=Image.new("RGB",(S,S),(0,0,0)); em=Image.new("RGB",(S,S),(0,0,0)); dm=ImageDraw.Draw(im); de=ImageDraw.Draw(em)
base=(150,140,128)
im.paste(base,[0,0,S,S])
for r in range(4):
    for c in range(4):
        x0=c*256+70; y0=r*256+60; x1=x0+116; y1=y0+140
        lit=random.random()<0.30
        dm.rectangle([x0-8,y0-8,x1+8,y1+8],fill=(70,64,60))
        dm.rectangle([x0,y0,x1,y1],fill=(24,30,44))
        if lit:
            col=random.choice([(255,190,110),(255,170,80),(255,215,150),(190,220,255)])
            de.rectangle([x0,y0,x1,y1],fill=tuple(int(v*0.8) for v in col))
            # curtain
            if random.random()<0.5: de.rectangle([x0,y0,x0+40,y1],fill=tuple(int(v*0.5) for v in col))
im=im.filter(ImageFilter.GaussianBlur(0.6)); em=em.filter(ImageFilter.GaussianBlur(0.8))
im.save(out+"facade_diff.png"); em.save(out+"facade_emit.png")
# ---- crowd 1024x512 : dense colourful specks in rows ----
cw,ch=2048,512
c=np.zeros((ch,cw,3),np.float32)
cols=np.array([[0.9,0.1,0.1],[0.95,0.95,0.95],[0.1,0.2,0.85],[0.95,0.75,0.1],[0.15,0.15,0.18],[0.9,0.5,0.15],[0.6,0.6,0.65]])
for y in range(0,ch,6):
    for x in range(0,cw,5):
        col=cols[rng.integers(len(cols))]*(0.35+0.65*rng.random())
        xx=x+int(rng.integers(-1,2)); 
        c[y:y+4,xx:xx+4]=col
        if rng.random()<0.06: c[y:y+3,xx:xx+3]=(1,0.95,0.8)  # phone lights
c=np.asarray(Image.fromarray((c*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))).astype(np.float32)/255
Image.fromarray((np.clip(c,0,1)*255).astype(np.uint8)).save(out+"crowd.png")
print("ok")
