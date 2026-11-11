#!/bin/bash
# Собрать и выложить конфигуратор модели Li Auto. Перед этим: python3 tools/lixiang.py snyat <seriesId> <папка проекта>
# Запуск: lixiang-model.sh <slug> "<Li Auto L9>" "<L9>"     (NOPUSH=1 – без выкладки)
set -e
SLUG=$1; CAR=$2; SHORT=$3
SRC=~/Sites/zeekr-9x-konfigurator
D=~/Sites/lixiang-$SLUG-konfigurator
cd "$D"
[ -d .git ] || git init -q -b main
mkdir -p css js tools .github/workflows
cp $SRC/css/konfigurator.css css/; cp $SRC/js/konfigurator.js js/
cp $SRC/tools/lixiang.py $SRC/tools/lixiang-model.sh $SRC/tools/proverka.py $SRC/tools/ikonki-list.py tools/
cp $SRC/.github/workflows/pages.yml .github/workflows/; cp $SRC/robots.txt $SRC/.gitignore $SRC/.nojekyll .
sed "s/Zeekr 9X/$CAR/g" $SRC/index.html > index.html
python3 tools/lixiang.py sobrat . "$CAR" "$SHORT" "lixiang-$SLUG"
python3 - "$CAR" "$SLUG" <<'EOF'
import json, sys, os
car, slug = sys.argv[1:3]
d = json.loads(open('js/zeekr-data.js').read().split('window.ZEEKR_CFG = ', 1)[1].rstrip().rstrip(';'))
vers = ', '.join(v['name'] for v in d['versions'])
groups = []
for v in d['versions']:
    for g in v['secs']:
        if g['role'] != 'extra' and g['title'] not in groups: groups.append(g['title'])
ex = sorted({d['options'][g['opts'][0]['id']]['name'] for v in d['versions'] for g in v['secs'] if g['role'] == 'extra'})
t = open(os.path.expanduser('~/Sites/zeekr-9x-konfigurator/README.md')).read()
embed = t[t.index('## Встраивание в сайт'):t.index('## Как обновить данные')]
open('README.md', 'w').write(f'''# Конфигуратор {car}

Только конфигуратор: без шапки, логотипа, подвала и цен. Его собирают в сборку и встраивают в страницу модели на сайте.

Посмотреть: https://tema-mail.github.io/lixiang-{slug}-konfigurator/ (закрыт от индексации).
Локально: `python3 -m http.server 8940`, затем http://127.0.0.1:8940/

## Что выбирает человек
Версия ({vers}); {', '.join(g.lower() for g in groups)}{('; дополнительно – ' + ', '.join(x.lower() for x in ex)) if ex else ''}.
Варианты взяты из официального конфигуратора Li Auto (lixiang.com).

## Картинки
Официальные рендеры Li Auto конкретной сборки: студийный кадр без фона, виды сбоку, спереди и сзади, диск крупно,
салон (панель и кресла). Кузов снят для каждого сочетания цвета, дисков, декора и салона (салон видно через стёкла);
пороги, стёкла и фаркоп на картинке не отражаются. {len(d['have'])} сборок кузова, {len(d['int'])} вариантов салона, всё в WebP.

{embed}## Как обновить данные
Нужны Python 3, Playwright, Pillow; запросы к lixiang.com идут из браузера (их API отвечает только своей странице).
1. `python3 tools/lixiang.py snyat <seriesId> .` – версии, опции и адреса кадров в `raw/li-raw.json`
   (seriesId – из адреса страницы заказа модели на lixiang.com);
2. `tools/lixiang-model.sh {slug} "{car}" "{car.replace('Li Auto ', '')}"` – кадры, данные, проверки и выкладка (NOPUSH=1 – без выкладки).
Движок и стили общие с конфигураторами Zeekr, мастер-копия – репозиторий tema-mail/zeekr-9x-konfigurator.

Данные сняты 12.11.2026.
''')
EOF
grep -rn "—" index.html README.md js css && { echo "длинное тире"; exit 1; } || true
python3 - <<'PYCJK'
import glob, re, sys
bad = [f'{f}: {m}' for f in glob.glob('*.html') + glob.glob('js/*.js') + glob.glob('css/*.css') + glob.glob('*.md')
       for m in re.findall(r'[㐀-鿿＀-￯]+', open(f, encoding='utf8').read())]
if bad: sys.exit('китайский текст на странице: ' + '; '.join(bad[:10]))
PYCJK
[ -n "$NOPUSH" ] && { echo "собрано без выкладки: $D"; exit 0; }
git add -A
git commit -q -m "Конфигуратор $CAR: сборка без цен, рендеры Li Auto под каждую сборку, отправка менеджеру

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>"
if ! ~/.local/bin/gh repo view tema-mail/lixiang-$SLUG-konfigurator >/dev/null 2>&1; then
  ~/.local/bin/gh repo create tema-mail/lixiang-$SLUG-konfigurator --public --source . --push -d "Конфигуратор $CAR для встраивания на сайт" >/dev/null
  ~/.local/bin/gh api -X POST repos/tema-mail/lixiang-$SLUG-konfigurator/pages -f build_type=workflow >/dev/null
  ~/.local/bin/gh workflow run Pages -R tema-mail/lixiang-$SLUG-konfigurator
else
  git push -q
fi
echo "готово: https://tema-mail.github.io/lixiang-$SLUG-konfigurator/"
