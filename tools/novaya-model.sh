#!/bin/bash
# Собрать и выложить конфигуратор модели Zeekr из готовых кадров в ~/Sites/zeekr-<slug>-konfigurator/raw
# (raw/ заполняют sniat-opcii.py -> svod.py -> skachat.py, см. README).
# Запуск: novaya-model.sh <slug> <modelInfoId> "<Zeekr 7X>" "<7X>"
set -e
SLUG=$1; MID=$2; CAR=$3; SHORT=$4
SRC=~/Sites/zeekr-9x-konfigurator
D=~/Sites/zeekr-$SLUG-konfigurator
IMG=img/zeekr-$SLUG
cd "$D"
[ -d .git ] || git init -q -b main
mkdir -p css js tools .github/workflows "$IMG"/{ext,int,options}
cp $SRC/css/konfigurator.css css/; cp $SRC/js/konfigurator.js js/; cp $SRC/tools/*.py $SRC/tools/novaya-model.sh tools/
cp $SRC/.github/workflows/pages.yml .github/workflows/; cp $SRC/robots.txt $SRC/.gitignore $SRC/.nojekyll .
sed "s/Конфигуратор Zeekr 9X/Конфигуратор $CAR/g" $SRC/index.html > index.html
python3 tools/kadry.py raw "$IMG"
python3 tools/dannye.py raw/model.json js/zeekr-data.js "$CAR" "$SHORT" "$IMG" "$MID"
python3 - "$CAR" "$SLUG" "$MID" <<'EOF'
import json, sys, os, re
car, slug, mid = sys.argv[1:4]
src = open('js/zeekr-data.js').read()
d = json.loads(src.split('window.ZEEKR_CFG = ', 1)[1].rstrip().rstrip(';'))
vers = ', '.join(v['name'] for v in d['versions'])
groups = []
for v in d['versions']:
    for g in v['secs']:
        if g['role'] != 'extra' and g['title'] not in groups: groups.append(g['title'])
ex = sorted({d['options'][g['opts'][0]['id']]['name'] for v in d['versions'] for g in v['secs'] if g['role'] == 'extra'})
myc = json.load(open('raw/z9x-raw.json'))['versions'][0].get('myc', '')
t = open(os.path.expanduser('~/Sites/zeekr-9x-konfigurator/README.md')).read()
head = f'''# Конфигуратор {car}

Только конфигуратор: без шапки, логотипа, подвала и цен. Его собирают в сборку и встраивают в страницу модели на сайте.

Посмотреть: https://tema-mail.github.io/zeekr-{slug}-konfigurator/ (закрыт от индексации).
Локально: `python3 -m http.server 8940`, затем http://127.0.0.1:8940/

## Что выбирает человек
Версия ({vers}); {', '.join(g.lower() for g in groups)}{('; дополнительно – ' + ', '.join(x.lower() for x in ex)) if ex else ''}.
Варианты и правила совместимости – из официального конфигуратора Zeekr (zeekrlife.com), выбор подстраивается сам.
Диски, которые Zeekr сейчас по акции меняет на другие, есть с пометкой.

## Картинки
Официальные рендеры Zeekr конкретной сборки: главный кадр без фона, ракурсы спереди ¾, сбоку, сзади ¾ (где Zeekr их сделал)
и салон (если Zeekr даёт картинку салона для этой модели). {len(d['have'])} сборок кузова, {len(d['int'])} вариантов салона, всё в WebP.
'''
rest = t[t.index('## Встраивание в сайт'):]
rest = rest.replace('img/zeekr-9x', f'img/zeekr-{slug}').replace('"Zeekr 9X" 9X', f'"{car}" ' + car.replace('Zeekr ', '').replace(' ', '')).replace('img/zeekr-' + slug + ' 10', f'img/zeekr-{slug} {mid}')
rest = re.sub(r'sniat-opcii\.py 10 GMY_9X_01', f'sniat-opcii.py {mid} <код года из списка моделей>', rest)
rest = re.sub(r'skachat\.py model\.json <modelInfoId> raw|skachat\.py model\.json 10 raw', f'skachat.py model.json {mid} raw', rest)
rest = re.sub(r'Данные сняты .*', f'Данные сняты 12.11.2026, модель {car} (modelInfoId {mid}). Сборка и выкладка новой модели целиком – `tools/novaya-model.sh`.', rest)
open('README.md', 'w').write(head + '\n' + rest)
EOF
grep -rn "—" index.html README.md js css && { echo "длинное тире"; exit 1; } || true
python3 - <<'PYCJK'
import glob, re, sys
bad = [f'{f}: {m}' for f in glob.glob('*.html') + glob.glob('js/*.js') + glob.glob('css/*.css') + glob.glob('*.md')
       for m in re.findall(r'[\u3400-\u9fff\uff00-\uffef]+', open(f, encoding='utf8').read())]
if bad: sys.exit('китайский текст на странице: ' + '; '.join(bad[:10]))
PYCJK
[ -n "$NOPUSH" ] && { echo "собрано без выкладки: $D"; exit 0; }
git add -A
git commit -q -m "Конфигуратор $CAR: сборка без цен, рендеры Zeekr под каждую сборку, отправка менеджеру

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
if ! ~/.local/bin/gh repo view tema-mail/zeekr-$SLUG-konfigurator >/dev/null 2>&1; then
  ~/.local/bin/gh repo create tema-mail/zeekr-$SLUG-konfigurator --public --source . --push -d "Конфигуратор $CAR для встраивания на сайт" >/dev/null
  ~/.local/bin/gh api -X POST repos/tema-mail/zeekr-$SLUG-konfigurator/pages -f build_type=workflow >/dev/null
  ~/.local/bin/gh workflow run Pages -R tema-mail/zeekr-$SLUG-konfigurator
else
  git push -q
fi
echo "готово: https://tema-mail.github.io/zeekr-$SLUG-konfigurator/"
