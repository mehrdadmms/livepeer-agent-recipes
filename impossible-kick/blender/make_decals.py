# Generates invented decals (graffiti tag, torn posters, grime streak sheet). No real brands.
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
out="assets/textures/"; rng=np.random.default_rng(81)
def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Impact.ttf","/System/Library/Fonts/Supplemental/Arial Black.ttf"]:
        try: return ImageFont.truetype(p,sz)
        except: pass
    return ImageFont.load_default()
# --- graffiti tag (RGBA)
W,H=1024,512
im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
f=font(300); t="KIKO"
for off,col in ((14,(10,10,12,255)),(0,(240,60,120,255))):
    d.text((60+off,70+off),t,font=f,fill=col)
d.text((60,70),t,font=f,fill=(240,60,120,255),stroke_width=0)
d.text((70,90),t,font=f,fill=(255,200,220,90))
# crown + underline swoosh
d.polygon([(700,40),(740,90),(780,50),(820,95),(860,40),(860,120),(700,120)],fill=(250,220,60,255))
d.line([(60,420),(300,440),(560,410),(900,450)],fill=(20,20,24,255),width=16)
im=im.filter(ImageFilter.GaussianBlur(1.6))
a=np.asarray(im).astype(np.float32)
# spray speckle + drips
al=a[...,3]/255
al*= (0.75+0.25*rng.random(al.shape))
for _ in range(14):
    x=int(rng.integers(80,820)); y0=int(rng.integers(250,420)); L=int(rng.integers(30,90))
    al[y0:y0+L,x:x+3]=np.maximum(al[y0:y0+L,x:x+3],0.7)
a[...,3]=np.clip(al,0,1)*255
Image.fromarray(a.astype(np.uint8)).save(out+"graffiti_tag.png")
# --- torn posters (RGBA), 512x768
def poster(seed,bg,accent,txt,sub):
    r=np.random.default_rng(seed); W,H=512,768
    im=Image.new("RGBA",(W,H),bg); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,190],fill=accent)
    d.text((30,40),txt,font=font(110),fill=(250,245,230,255))
    d.ellipse([110,260,410,560],fill=accent); d.ellipse([150,300,370,520],fill=bg)
    d.text((40,620),sub,font=font(62),fill=(30,25,25,255))
    im=im.filter(ImageFilter.GaussianBlur(1.0)); a=np.asarray(im).astype(np.float32)
    # tear mask + creases + fade
    m=np.ones((H,W),np.float32)
    for y in range(H):
        e=int(30*np.sin(y*0.02+seed)+r.integers(0,14)); m[y,:max(0,e-10)]=0
    tear=int(H*r.uniform(0.6,0.85)); 
    for x in range(W): m[int(tear+25*np.sin(x*0.03+seed)+r.integers(0,10)):,x]=0
    a[...,3]=m*255
    a[...,:3]*= (0.55+0.35*r.random((H,W,1))**2)
    Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(out+f"poster{seed}.png")
poster(1,(235,205,120,255),(190,40,40,255),"DERBY","SAT 8PM")
poster(2,(150,190,205,255),(30,60,110,255),"FIESTA","LIVE")
poster(3,(230,230,225,255),(20,120,90,255),"FUTSAL","CUP")
print("ok")
# --- advertising boards strip (invented sponsors), 4096x128
W,H=4096,128
im=Image.new("RGB",(W,H),(14,14,18)); d=ImageDraw.Draw(im)
names=[("SOLARA",(0,150,200)),("NOVA","(230,70,40)"),("KITE MOBILE",(250,200,30)),("AQUALINE",(20,110,190)),("TERRA FOODS",(40,150,80)),("VELO",(220,220,225)),("ORBITA",(150,60,190)),("ZAPPO",(200,40,30))]
x=0; i=0
while x<W:
    n,c=names[i%len(names)]
    if isinstance(c,str): c=(230,70,40)
    w=512
    d.rectangle([x+4,6,x+w-4,H-6],fill=tuple(int(v*0.55) for v in c))
    f=font(78); tw=d.textlength(n,font=f); d.text((x+w/2-tw/2,22),n,font=f,fill=(255,255,255))
    x+=w; i+=1
im.save(out+"adboards.png")
