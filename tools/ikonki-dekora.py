"""Иконки декора кузова: вырезка решётки из официального рендера «спереди ¾» (у Zeekr в части иконок китайский текст).
Запуск: python3 ikonki-dekora.py model.json img/zeekr-XX [x0 y0 x1 y1]"""
import json, os, sys
from PIL import Image
m = json.load(open(sys.argv[1])); IMG = sys.argv[2]
box = tuple(int(x) for x in sys.argv[3:7]) if len(sys.argv) > 6 else (25, 280, 255, 510)
kits = {o['id'] for V in m['vers'] for s in V['secs'] if s['role'] == 'kit' or s.get('cn') == '套件' for o in s['opts']}
for pc in sorted(kits):
    codes = [c for c in m['ext'] if pc in c.split('_') and os.path.exists(f'{IMG}/ext/{c}--front34.webp')]
    if not codes: print('нет кадра для', pc); continue
    # декор лучше виден на светлом кузове: серебристый, светло-серый, белый; если декор только для чёрного – берём что есть
    light = ['冰川银', '玄武灰', '极昼白', '月海灰']
    def rank(c):
        cns = [m['opts'][p]['cn'] for p in c.split('_') if p in m['opts']]
        return min([light.index(x) for x in cns if x in light] or [9])
    codes.sort(key=rank)
    im = Image.open(f'{IMG}/ext/{codes[0]}--front34.webp').convert('RGB')
    im.crop(box).resize((112, 112), Image.LANCZOS).save(f'{IMG}/options/{pc}.webp', 'WEBP', quality=85)
    print(pc, codes[0])
