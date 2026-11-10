"""Скачать официальные кадры Zeekr по model.json. Запуск: python3 skachat.py model.json <modelInfoId> <папка raw>
Главный кадр без фона, три ракурса (ищутся по всем версиям модели), салон, иконки опций. 6 потоков, повторы."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
m = json.load(open(sys.argv[1])); MID = sys.argv[2]; RAW = sys.argv[3]
B = 'https://zeekrlife-oss.zeekrlife.com/showcar/'
VIDS = [v['id'] for v in m['vers']]
for d in ('ext', 'int', 'ico'): os.makedirs(f'{RAW}/{d}', exist_ok=True)
def fetch(urls, f):
    if os.path.exists(f) and os.path.getsize(f) > 2000: return 'skip'
    for u in urls:
        for a in range(2):
            r = subprocess.run(['curl', '-s', '--max-time', '60', '-o', f + '.part', '-w', '%{http_code}', u], capture_output=True, text=True)
            # код 200 curl печатает и при обрыве по таймауту – принимаем файл, только если curl завершился без ошибки
            if r.returncode == 0 and r.stdout == '200' and os.path.getsize(f + '.part') > 2000:
                os.replace(f + '.part', f); return 'ok'
            if r.stdout == '404': break
    if os.path.exists(f + '.part'): os.remove(f + '.part')
    return 'нет'
def order(first): return [first] + [v for v in VIDS if v != first]
# версии папок ракурсов у каждой модели свои (bigPicRuleList): берём из сырых данных
RAWF = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'z9x-raw.json')
ANGV = {}
if os.path.exists(RAWF):
    for v in json.load(open(RAWF))['versions']:
        for b in v.get('bigPic') or []:
            ang = b['domainUrl'].rstrip('/').split('/')[-1]
            ANGV.setdefault(v['id'], {}).setdefault(ang, [])
            if b['imageVersion'] not in ANGV[v['id']][ang]: ANGV[v['id']][ang].append(b['imageVersion'])
def vers_for(v, ang, fallback):
    a = ANGV.get(v, {})
    if ang in a: return a[ang]
    if ang == 'right_rear': return (a.get('left_front', []) + a.get('left', [])) or fallback
    return fallback
jobs = []
for code in m['ext']:
    w = m['where'][code]
    jobs.append(([f'{B}vehicle/{MID}/{v}/{code}.png' for v in order(w)], f'{RAW}/ext/{code}--hero.png'))
for code in m.get('ang', m['ext']):
    w = m['where'].get('A' + code, m['where'].get(code))
    for shot, ang, ver in (('front34', 'left_front', 'v5'), ('side', 'left', 'v4'), ('rear34', 'right_rear', 'v5')):
        urls = [f'{B}carPic/{ang}/{MID}/{v}/{vv}/{code}.png' for v in order(w)[:3] for vv in vers_for(v, ang, [ver])]
        jobs.append((urls, f'{RAW}/ext/{code}--{shot}.png'))
for code in m['int']:
    w = m['where']['I' + code]
    jobs.append(([f'{B}Interior/{MID}/{v}/{code}.png' for v in order(w)], f'{RAW}/int/{code}.png'))
for pc, o in m['opts'].items():
    if o.get('cover'): jobs.append(([o['cover']], f'{RAW}/ico/{pc}--cover.png'))
with ThreadPoolExecutor(10) as ex: res = list(ex.map(lambda j: fetch(*j), jobs))
import collections; print(len(jobs), collections.Counter(res))
