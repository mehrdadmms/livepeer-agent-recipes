# usage: python sheet.py out.png cols img1 img2 ...
import sys
from PIL import Image
out=sys.argv[1]; cols=int(sys.argv[2]); ims=[Image.open(p).convert('RGB') for p in sys.argv[3:]]
w,h=ims[0].size; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(w*cols,h*rows))
for i,im in enumerate(ims): S.paste(im,((i%cols)*w,(i//cols)*h))
S.save(out)
