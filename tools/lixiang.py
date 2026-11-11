"""Li Auto (lixiang.com) -> конфигуратор на общем движке. Цен нет намеренно.
  python3 lixiang.py snyat  <seriesId> <папка проекта>            – версии, опции, адреса кадров -> raw/li-raw.json
  python3 lixiang.py sobrat <папка проекта> "<Li Auto L9>" "<L9>" <slug> – кадры в WebP и js/zeekr-data.js
API отвечает только из контекста их страницы (заголовки x-chj-*), поэтому запросы идут через Playwright.
Картинка кузова у Li Auto зависит от цвета, дисков, декора кузова и салона (его видно через стёкла);
пороги, стёкла и прочие допы картинку не меняют. Кадры салона зависят от цвета кузова и салона."""
import json, os, re, sys, itertools, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

EXE = '/Users/artemgalimov/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'
API = 'https://api-web.lixiang.com/vehicle-api/v1-0/'
EXT_GROUPS = ['外观', '轮毂', '外观套件', '内饰']          # от них зависит картинка кузова
ROLE = {'外观': 'paint', '轮毂': 'wheel', '内饰': 'int'}

RU = {
 # кузов
 '珍珠白金属漆': 'Белый перламутр', '极地灰冷光漆': 'Серый «Полярный»', '钻石黑金属漆': 'Чёрный «Бриллиант»', '钛金色金属漆': 'Титановый',
 '祖母绿特别版珍珠漆': 'Изумрудный, особая серия', '暗夜紫特别版珍珠漆': 'Фиолетовый «Тёмная ночь», особая серия', '松露金特别版珍珠漆': 'Золотой «Трюфель», особая серия',
 '绿金定制版双色车身': 'Двухцветный: зелёный с золотом', '紫金定制版双色车身': 'Двухцветный: фиолетовый с золотом', '棕金定制版双色车身': 'Двухцветный: коричневый с золотом',
 '黑金定制版双色车身': 'Двухцветный: чёрный с золотом', '风信紫冷光漆': 'Сиреневый «Гиацинт»', '外星银金属漆': 'Серебристый «Космос»', '黑武士金属漆': 'Чёрный «Воин»',
 '云朵黄冷光漆': 'Жёлтый «Облако»', '磁力蓝珍珠漆': 'Синий «Магнит»', '白色珍珠漆': 'Белый перламутр', '银色金属漆': 'Серебристый металлик', '黑色金属漆': 'Чёрный металлик',
 '小象灰特别版冷光漆': 'Серый «Слонёнок», особая серия', '紫晶灰金属漆': 'Серый «Аметист»', '新大象灰冷光漆': 'Серый «Слон»', '流光银金属漆': 'Серебристый «Сияние»',
 '量子钛金金属漆': 'Титановый «Квант»', '乌木金金属漆': 'Золотой «Эбен»', '雾海蓝冷光漆': 'Синий «Туманное море»', '灰色金属漆': 'Серый металлик', '熊猫白珍珠漆': 'Белый «Панда»',
 'GT银金属漆': 'Серебристый GT', '陨石灰金属漆': 'Серый «Метеорит»', '曜石黑金属漆': 'Чёрный «Обсидиан»', '小象灰冷光漆': 'Серый «Слонёнок»', '沙丘黄冷光漆': 'Жёлтый «Дюна»',
 '冰川灰冷光漆': 'Серый «Ледник»',
 # диски
 '20英寸低风阻轮毂': '20″ аэродинамические', '21英寸七辐运动轮毂': '21″ спортивные, 7 спиц', '21英寸低风阻轮毂': '21″ аэродинамические', '22英寸七芒星轮毂': '22″ «Семиконечная звезда»',
 '18英寸深空灰飞碟轮毂': '18″ «Диск», тёмно-серые', '18英寸熊猫白飞碟轮毂': '18″ «Диск», белые', '18英寸黑灰双色低风阻轮毂': '18″ аэродинамические, чёрно-серые',
 '20英寸黑色五辐轮毂': '20″ чёрные, 5 спиц', '20英寸银色五辐轮毂': '20″ серебристые, 5 спиц', '21英寸黑色七辐轮毂': '21″ чёрные, 7 спиц', '21英寸银色七辐轮毂': '21″ серебристые, 7 спиц',
 '21英寸黑色五辐轮毂': '21″ чёрные, 5 спиц', '21英寸银色五辐轮毂': '21″ серебристые, 5 спиц', '22英寸黑色七辐轮毂': '22″ чёрные, 7 спиц', '22英寸银色七辐轮毂': '22″ серебристые, 7 спиц',
 'Livis专属22英寸晶灰轮毂': '22″ Livis, серые', '21英寸银色轮毂': '21″ серебристые', '21英寸黑色轮毂': '21″ чёрные', '22英寸银色轮毂': '22″ серебристые',
 # салон
 '棕白双色内饰': 'Коричневый с белым', '绿白双色内饰': 'Зелёный с белым', '棕咖双色内饰': 'Коричневый с кофейным', '灰紫双色内饰': 'Серый с фиолетовым', '白色内饰': 'Белый',
 '灰棕色内饰': 'Серо-коричневый', '橙黄色内饰': 'Оранжево-жёлтый', '白灰双色内饰': 'Белый с серым', '雪原白双色内饰': 'Белый «Снежная равнина»', '旷野棕双色内饰': 'Коричневый «Простор»',
 '琥珀橙双色内饰': 'Оранжевый «Янтарь»',
 # декор, звук, привод
 '银色套件': 'Серебристый декор', '曜黑专属运动设计套件': 'Чёрный спортивный пакет', '高级音响': 'Premium', '铂金音响': 'Platinum', '理想Home剧院音响': '«Театр»',
 '理想Home音乐厅': '«Концертный зал»', '无瑕星环剧院音响': 'Аудиосистема «Звёздное кольцо»', '双电机四驱': '2 мотора, полный привод', '后驱': 'Задний привод',
 # дополнительно
 '双马赫M100套装': 'Пакет с двумя чипами M100', '后舱娱乐屏套装': 'Экран для задних пассажиров', '后舱21英寸4K移动屏': 'Экран 21″ 4K для задних пассажиров',
 '电动拖车钩': 'Электрический фаркоп', '隐藏式电动踏板': 'Выдвижные пороги', '二三排电动调光玻璃': 'Затемняемые стёкла второго и третьего ряда',
 '270°电动调光玻璃': 'Затемняемое остекление 270°', '第二排电动调光玻璃': 'Затемняемые стёкла второго ряда', '悬浮组合桌板': 'Складной столик',
 '主副驾零重力座椅': 'Передние кресла «невесомость»', '全车静音电吸门': 'Доводчики всех дверей', '8.8L智能电动冷暖冰箱': 'Холодильник 8,8 л с подогревом',
}
GT = {'外观': 'Цвет кузова', '轮毂': 'Диски', '内饰': 'Цвет салона', '外观套件': 'Декор кузова', '音响': 'Аудиосистема', '驱动': 'Привод'}
VN = [('Livis', 'Livis', ''), ('Ultra', 'Ultra', ''), ('四驱高性能', 'Performance', 'Полный привод'), ('后驱长续航', 'Long Range', 'Задний привод'), ('Home', 'Home', '')]
SHOTS = [{'id': 'hero', 'label': 'Студия'}, {'id': 'side', 'label': 'Сбоку'}, {'id': 'front34', 'label': 'Спереди'}, {'id': 'rear34', 'label': 'Сзади ¾'},
         {'id': 'wheel', 'label': 'Диск'}, {'id': 'int', 'label': 'Салон', 'kind': 'int'}, {'id': 'int2', 'label': 'Кресла', 'kind': 'int'}]
is_none = lambda n: n.startswith('无')


def snyat(sid, proj):
    from playwright.sync_api import sync_playwright
    os.makedirs(f'{proj}/raw', exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=EXE)
        try:
            pg = b.new_page(); H = {}
            pg.on('request', lambda r: H.update({k: v for k, v in r.headers.items() if k.startswith('x-chj') or k == 'accept'}) if ('vehicle-api' in r.url and not H) else None)
            pg.goto(f'https://www.lixiang.com/mall/buy-new/config.html?seriesId={sid}&buyRuntime=new', wait_until='networkidle', timeout=90000)
            JS = '''async ([urls,h])=>Promise.all(urls.map(async u=>{for(let a=0;a<3;a++){try{const r=await fetch(u,{headers:h,credentials:"include"});const j=await r.json();if(j&&j.data!==undefined&&j.data!==null)return j.data}catch(e){}await new Promise(r=>setTimeout(r,700))}return null}))'''
            def many(urls):
                out = []
                for i in range(0, len(urls), 6): out += pg.evaluate(JS, [urls[i:i + 6], H])
                return out
            prods = many([f'{API}products/product/all-on-sale/by-series?productId=&seriesId={sid}'])[0] or []
            res = {'series': sid, 'products': []}
            for pr in prods:
                pid = str(pr['productId'])
                lite = many([f'{API}products/lite?productId={pid}'])[0]
                if not lite: continue
                opts = lite['options']
                defaults = dict(x.split('-') for x in lite['defaultVariant']['attributesSet'].split(','))
                extg = [o for o in opts if o['name'] in EXT_GROUPS]
                combos = list(itertools.product(*[[str(i['id']) for i in o['items'] if i.get('available', True)] for o in extg]))
                def aset(combo):
                    cur = dict(defaults); cur.update({str(o['id']): c for o, c in zip(extg, combo)})
                    return ','.join(f'{o["id"]}-{cur[str(o["id"])]}' for o in opts if str(o['id']) in cur)
                rv = many([f'{API}products/{pid}/resolve-variant?attributeSet={aset(c)}' for c in combos])
                ok = [(c, r['variantId']) for c, r in zip(combos, rv) if r and r.get('available') and r.get('variantId')]
                vs = many([f'{API}products/variant/{vid}' for _, vid in ok])
                variants = {}
                for (c, _), v in zip(ok, vs):
                    if not v: continue
                    info = {a['attributeSet']: a['imgs'] for a in v['attributeInfos']}
                    g = {o['name']: f'{o["id"]}-{ci}' for o, ci in zip(extg, c)}
                    variants['_'.join(c)] = {'hero': v.get('imgUrl'), 'views': info.get(g.get('外观'), []), 'wheel': (info.get(g.get('轮毂')) or [None])[0], 'int': info.get(g.get('内饰'), [])}
                res['products'].append({'productId': pid, 'name': pr['productName'], 'options': opts, 'defaults': defaults,
                                        'extSkus': [str(o['id']) for o in extg], 'variants': variants})
                print(pid, pr['productName'], 'сочетаний', len(combos), 'с кадрами', len(variants), flush=True)
            json.dump(res, open(f'{proj}/raw/li-raw.json', 'w'), ensure_ascii=False)
        finally:
            b.close()


def fetch_img(url, dst, kind):
    """Скачать и сразу перевести в WebP. kind: hero | view | int | icon."""
    from PIL import Image
    if os.path.exists(dst): return 'skip'
    if not url: return 'нет'
    tmp = tempfile.mktemp(suffix=os.path.splitext(url)[1] or '.img')
    try:
        for a in range(3):
            r = subprocess.run(['curl', '-s', '--max-time', '90', '-o', tmp, '-w', '%{http_code}', url], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout == '200' and os.path.getsize(tmp) > 1500:
                try:
                    im = Image.open(tmp); im.load()
                except Exception:
                    continue
                if kind == 'hero':
                    im = im.convert('RGBA'); im.thumbnail((1600, 1600)); im.save(dst, 'WEBP', quality=82, method=6)
                elif kind == 'icon':
                    im = im.convert('RGBA'); im.thumbnail((112, 112)); im.save(dst, 'WEBP', quality=85, method=6)
                else:
                    im = im.convert('RGB'); w, h = im.size
                    ch = int(w * 10 / 16)                                   # сцена 4:3 -> 16:10
                    if ch < h:
                        top = int((h - ch) * (0.72 if kind == 'view' else 0.5)); im = im.crop((0, top, w, top + ch))
                    im = im.resize((1280, 800), Image.LANCZOS); im.save(dst, 'WEBP', quality=78, method=6)
                return 'ok'
        return 'нет'
    finally:
        if os.path.exists(tmp): os.remove(tmp)


def sobrat(proj, car, short, slug):
    raw = json.load(open(f'{proj}/raw/li-raw.json'))
    IMG = f'img/{slug}'
    for d in ('ext', 'int', 'options'): os.makedirs(f'{proj}/{IMG}/{d}', exist_ok=True)
    def ru(cn):
        if cn not in RU: raise SystemExit('нет перевода: ' + cn)
        return RU[cn]
    jobs, options, vers, have, ang, ints = [], {}, [], {}, {}, set()
    for pr in raw['products']:
        vname = next(((n, t) for k, n, t in VN if k in pr['name']), (short, ''))
        dfl = pr['defaults']; secs = []; extras = []
        paint_sku = next((str(o['id']) for o in pr['options'] if o['name'] == '外观'), None)
        int_sku = next((str(o['id']) for o in pr['options'] if o['name'] == '内饰'), None)
        for o in pr['options']:
            sku = str(o['id']); items = [i for i in o['items'] if i.get('available', True) and i.get('displayed', True) is not False]
            real = [i for i in items if not is_none(i['name'])]
            for i in real:
                pc = str(i['id'])
                icon = f'{IMG}/options/{pc}.webp' if (i.get('imgUrl') and o['name'] in ROLE) else None
                if icon: jobs.append((i['imgUrl'], f'{proj}/{icon}', 'icon'))
                options[pc] = {'name': ru(i['name']), 'note': '', 'icon': icon, 'mutex': [], 'cascade': [], 'sku': sku}
            role = ROLE.get(o['name'])
            mk = lambda i, **kw: dict({'id': str(i['id']), 'def': dfl.get(sku) == str(i['id']), 'promo': False, 'promoTo': ''}, **kw)
            if role:
                secs.append({'sku': sku, 'role': role, 'title': GT[o['name']], 'kind': 'option' if role == 'wheel' else 'swatch', 'img': 'int' if role == 'int' else 'ext', 'opts': [mk(i) for i in real]})
            elif len(real) > 1:
                if o['name'] not in GT: raise SystemExit('нет перевода группы: ' + o['name'])
                secs.append({'sku': sku, 'role': 'choice', 'title': GT[o['name']], 'kind': 'seg', 'img': 'ext' if o['name'] in EXT_GROUPS else '', 'opts': [mk(i) for i in real]})
            elif real:
                i = real[0]; has_none = len(items) > 1
                extras.append({'sku': sku, 'role': 'extra', 'title': options[str(i['id'])]['name'], 'kind': 'check', 'img': '',
                               'opts': [{'id': str(i['id']), 'def': not has_none, 'pre': has_none and dfl.get(sku) == str(i['id']), 'promo': False, 'promoTo': ''}]})
        rank = {'paint': 0, 'choice': 2, 'wheel': 3, 'int': 4}
        secs.sort(key=lambda s: (1 if (s['role'] == 'choice' and s['img'] == 'ext') else (5 if s['role'] == 'choice' else rank[s['role']])))
        pre = pr['productId'][-6:] + '-'                           # у версий одной модели коды опций совпадают, а машины разные
        for code0, v in pr['variants'].items():
            code = pre + code0
            have[code] = ['hero']; jobs.append((v['hero'], f'{proj}/{IMG}/ext/{code}--hero.webp', 'hero'))
            sh = []
            for name, url in list(zip(['side', 'front34', 'rear34'], v['views'])) + [('wheel', v['wheel'])]:
                if url: sh.append(name); jobs.append((url, f'{proj}/{IMG}/ext/{code}--{name}.webp', 'view'))
            ang[code] = sh
            parts = dict(zip(pr['extSkus'], code0.split('_')))
            icode = f'{pre}{parts[paint_sku]}_{parts[int_sku]}'
            if icode not in ints and len(v['int']) >= 2:
                ints.add(icode)
                jobs.append((v['int'][0], f'{proj}/{IMG}/int/{icode}--int.webp', 'int')); jobs.append((v['int'][1], f'{proj}/{IMG}/int/{icode}--int2.webp', 'int'))
        vers.append({'id': pr['productId'], 'name': vname[0], 'tag': vname[1], 'group': '', 'drive': '', 'level': [], 'secs': secs + extras,
                     'codePrefix': pre, 'vehicleSkus': pr['extSkus'], 'angleSkus': pr['extSkus'], 'interiorSkus': [paint_sku, int_sku], 'ranges': {}})
    with ThreadPoolExecutor(10) as ex: res = list(ex.map(lambda j: fetch_img(*j), jobs))
    import collections; print('картинки', collections.Counter(res), flush=True)
    ex_ = lambda f: os.path.exists(f'{proj}/{f}')
    have = {c: s for c, s in have.items() if ex_(f'{IMG}/ext/{c}--hero.webp')}
    ang = {c: [x for x in s if ex_(f'{IMG}/ext/{c}--{x}.webp')] for c, s in ang.items() if c in have}
    ints = sorted(c for c in ints if ex_(f'{IMG}/int/{c}--int.webp') and ex_(f'{IMG}/int/{c}--int2.webp'))
    for o in options.values():
        if o['icon'] and not ex_(o['icon']): o['icon'] = None
    for v in vers:                                                   # без иконки цвет или салон показываем кнопкой с названием
        for s in v['secs']:
            if s['kind'] == 'swatch' and not all(options[o['id']]['icon'] for o in s['opts']): s['kind'] = 'seg'
    data = {'car': car, 'short': short, 'groups': [], 'versions': vers, 'options': options, 'have': have, 'ang': ang, 'int': ints,
            'paths': {'ext': IMG + '/ext/{code}--{shot}.webp', 'int': IMG + '/int/{code}--{shot}.webp'}, 'shots': SHOTS}
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    cjk = sorted(set(re.findall(r'[㐀-鿿＀-￯][^"]{0,20}', js)))
    if cjk: raise SystemExit('в данных остался китайский текст: ' + ', '.join(cjk[:20]))
    os.makedirs(f'{proj}/js', exist_ok=True)
    open(f'{proj}/js/zeekr-data.js', 'w').write('/* Данные конфигуратора ' + car + ': официальный конфигуратор lixiang.com, сняты скриптом tools/lixiang.py. Цен нет намеренно. */\nwindow.ZEEKR_CFG = ' + js + ';\n')
    print(car, 'версий', len(vers), 'сборок кузова', len(have), 'салонов', len(ints))


if __name__ == '__main__':
    if sys.argv[1] == 'snyat': snyat(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'sobrat': sobrat(*sys.argv[2:6])
