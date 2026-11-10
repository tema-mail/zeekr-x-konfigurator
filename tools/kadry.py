"""Официальные кадры Zeekr (raw/) -> WebP для сайта (img/zeekr-9x/). Запуск: python3 tools/kadry.py <папка raw> <img/zeekr-XX>"""
import sys, os, glob
from PIL import Image
RAW = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else 'img/zeekr-9x'
os.makedirs(OUT + '/ext', exist_ok=True); os.makedirs(OUT + '/int', exist_ok=True); os.makedirs(OUT + '/options', exist_ok=True)
n = 0
for f in sorted(glob.glob(RAW + '/ext/*.png')):
    name = os.path.basename(f)[:-4]; dst = f'{OUT}/ext/{name}.webp'
    if os.path.exists(dst): continue
    im = Image.open(f)
    if name.endswith('--hero'):
        im = im.convert('RGBA'); im.thumbnail((1600, 1600)); im.save(dst, 'WEBP', quality=82, method=6)
    else:
        im = im.convert('RGB').crop((75, 473, 1275, 1223)); im.save(dst, 'WEBP', quality=80, method=6)
    n += 1
for f in sorted(glob.glob(RAW + '/int/*.png')):
    dst = f'{OUT}/int/{os.path.basename(f)[:-4]}.webp'
    if os.path.exists(dst): continue
    im = Image.open(f).convert('RGB'); im.thumbnail((1280, 1280)); im.save(dst, 'WEBP', quality=80, method=6); n += 1
for f in sorted(glob.glob(RAW + '/ico/*--cover.png')):
    pc = os.path.basename(f).split('--')[0]; dst = f'{OUT}/options/{pc}.webp'
    im = Image.open(f).convert('RGBA'); im.thumbnail((112, 112)); im.save(dst, 'WEBP', quality=85, method=6); n += 1
print('сделано', n)
