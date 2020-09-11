import os
import cv2
import numpy
dirin = r'images/cones/raw'
dirout = r'images/cones/train'
for filename in os.listdir(dirin):
    if filename.endswith(".jpg"):
        fin = os.path.join(dirin, filename)
        fout = os.path.join(dirout, filename)
        print(fin)
        img = cv2.imread(fin)
        (h, w) = img.shape[:2]
        print(h)
        print(w)
        max = 720
        if (h > w):
            r = max / float(h)
            dim = (int(w*r), max)
        else:
            r = max / float(w)
            dim = (max, int(h*r))
        res = cv2.resize(img, dim, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(fout,res)
    else:
        continue
