"""Лист всех иконок, которые видны на странице модели, – глазами проверить, нет ли текста (китайского). python3 ikonki-list.py <out.png>"""
import json, sys
from PIL import Image
t = open('js/zeekr-data.js').read(); d = json.loads(t.split('window.ZEEKR_CFG = ', 1)[1].rstrip().rstrip(';'))
used = sorted({d['options'][o['id']]['icon'] for v in d['versions'] for g in v['secs'] if g['kind'] in ('swatch', 'option') for o in g['opts'] if d['options'][o['id']]['icon']})
tiles = [Image.open(ic).convert('RGB').resize((96, 96)) for ic in used]
cols = 16; o = Image.new('RGB', (cols * 100, max(1, (len(tiles) + cols - 1) // cols) * 100), 'white')
for i, tl in enumerate(tiles): o.paste(tl, ((i % cols) * 100, (i // cols) * 100))
o.save(sys.argv[1]); print(len(tiles), 'иконок')
