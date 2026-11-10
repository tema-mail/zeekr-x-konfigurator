"""Свод опций любой модели Zeekr из z9x-raw.json (sniat-opcii.py) -> model.json.
Роли опций определяются по китайскому названию группы. Картинка кузова и салона у Zeekr – это
коды выбранных опций в порядке vehiclePicUrlSkuCodes / interiorPicUrlSkuCodes (невыбранные пропускаются).
Запуск: python3 svod.py z9x-raw.json model.json"""
import json, itertools, sys, re
raw = json.load(open(sys.argv[1]))
ROLE = {'外饰': 'paint', '车漆': 'paint', '轮毂': 'wheel', '颜色': 'int', '中控屏': 'screen'}
EXTRA = ['旋转座椅', '六座悦享包', '座椅', '拖车钩', '电动拖车钩', 'Naim音响', '音响', '吸顶屏', '踏板', '电动踏板']
SKIP_GROUPS = {'软件'}

opts, vers = {}, []
for v in raw['versions']:
    key0 = [k for k, x in v['items'].items() if x][0]
    secs = []   # [{sku, role, name, opts:[{id,def,promo}]}]
    for g in v['items'][key0]:
        if g['itemName'] in SKIP_GROUPS: continue
        for s in g['skuResultList']:
            role = ROLE.get(s['itemName'])
            if s['itemName'] in ('配件', '家充桩'): continue
            nvalid = sum(1 for x in s['subSkuResultList'] if x['isValidOption'])
            if not role:
                role = 'choice' if (s.get('mustSelected') or nvalid > 1) else 'extra'
            lst = []
            for x in s['subSkuResultList']:
                pc = x['productCode']
                o = opts.setdefault(pc, {'cn': x['subSkuName'], 'sku': s['skuCode'], 'cover': x['coverImg'], 'mutex': set(), 'cascade': set(), 'comment': {}})
                o['mutex'].update(x['mutexProduct']); o['cascade'].update(x['cascadeProduct'])
                promo = (not x['isValidOption']) and any(a.get('actionCode') == 'NO_VALID_SELECTED' for a in (x.get('subSkuActionResults') or []))
                if not x['isValidOption'] and not (role == 'wheel' and promo): continue
                to = re.search(r'(\d+)英寸', x.get('noValidSelectedNotice') or '') if promo else None
                lst.append({'id': pc, 'def': bool(x['isDefaultSelected']), 'promo': promo, 'promoTo': (to.group(1) + '″') if to else ''})
            if lst: secs.append({'sku': s['skuCode'], 'role': role, 'cn': s['itemName'], 'gcn': g['itemName'], 'must': bool(s.get('mustSelected')) or role != 'extra', 'opts': lst})
    # комментарии (запас хода) по комбинациям уровня версии
    for key, items in v['items'].items():
        for g in items or []:
            for s in g['skuResultList']:
                for x in s['subSkuResultList']:
                    if x.get('configComment') and x['productCode'] in opts:
                        opts[x['productCode']]['comment'][key] = x['configComment']
    lvl = {}
    for sku, x in v['level'].items():
        lvl[sku] = {'cn': x['name'], 'opts': [{'id': pc, 'cn': n, 'def': bool(d)} for pc, n, d in x['opts']]}
        for pc, n, d in x['opts']:
            opts.setdefault(pc, {'cn': n, 'sku': sku, 'cover': '', 'mutex': set(), 'cascade': set(), 'comment': {}})
    ang = next((b['skuCodeList'] for b in (v.get('bigPic') or []) if b.get('skuCodeList')), None) or v['vehicleSkus']
    vers.append({'id': v['id'], 'cn': v['name'], 'group': v['group'], 'level': lvl, 'secs': secs,
                 'vehicleSkus': v['vehicleSkus'], 'interiorSkus': v['interiorSkus'], 'angleSkus': ang, 'levelKeys': list(v['items'])})

def conflict(a, b):
    return b in opts[a]['mutex'] or a in opts[b]['mutex']
def ok(sel):
    for a in sel:
        for b in sel:
            if a != b and conflict(a, b): return False
    for a in sel:
        for c in opts[a]['cascade']:
            for x in sel:
                if x != c and opts[x]['sku'] == opts[c]['sku']: return False
    return True

ext, intr, angs, where = set(), set(), set(), {}
for V in vers:
    bysku = {s['sku']: s for s in V['secs']}
    for sku in V['level']: bysku[sku] = {'sku': sku, 'opts': V['level'][sku]['opts'], 'must': True}
    def choices(skus):
        cols = []
        for sku in skus:
            s = bysku.get(sku)
            if not s: continue
            c = [o['id'] for o in s['opts']]
            if not s.get('must', True) or (s.get('role') == 'extra'): c = c + [None]
            cols.append(c)
        return itertools.product(*cols)
    for combo in choices(V['vehicleSkus']):
        sel = [c for c in combo if c]
        if ok(sel):
            code = '_'.join(sel); ext.add(code); where.setdefault(code, V['id'])
            bys = {opts[c]['sku']: c for c in sel}
            acode = '_'.join(bys[k] for k in V['angleSkus'] if k in bys)
            angs.add(acode); where.setdefault('A' + acode, V['id'])
    for combo in choices(V['interiorSkus']):
        sel = [c for c in combo if c]
        if ok(sel):
            code = '_'.join(sel); intr.add(code); where.setdefault('I' + code, V['id'])

json.dump({'opts': {k: {**v, 'mutex': sorted(v['mutex']), 'cascade': sorted(v['cascade'])} for k, v in opts.items()},
           'vers': vers, 'ext': sorted(ext), 'ang': sorted(angs), 'int': sorted(intr), 'where': where}, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)
print('версий', len(vers), 'сборок кузова', len(ext), 'ракурсов', len(angs), 'салонов', len(intr))
for V in vers: print(V['id'], V['cn'], [(s['role'], s['cn'], len(s['opts'])) for s in V['secs']])
