"""Проверка конфигуратора: python3 proverka.py <url> <папка снимков>. Прокликивает все версии и все кнопки групп,
ловит ошибки консоли и 4xx, проверяет загрузку всех картинок, ссылку на сборку, ширину на 390 px, форму заявки."""
import sys
from playwright.sync_api import sync_playwright
EXE = '/Users/artemgalimov/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'
U, OUT = sys.argv[1], sys.argv[2]; errs, bad = [], []; fails = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE)
    try:
        pg = b.new_page(viewport={'width': 1440, 'height': 900})
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        pg.on('response', lambda r: bad.append(r.url) if r.status >= 400 else None)
        pg.goto(U, wait_until='networkidle')
        clicks = 0
        for v in pg.eval_on_selector_all('[data-version]', 'e=>e.map(x=>x.dataset.version)'):
            pg.click(f'[data-version="{v}"]'); pg.wait_for_timeout(150)
            for pc in pg.eval_on_selector_all('[data-slot=groups] [data-pc]', 'e=>e.map(x=>x.dataset.pc)'):
                if pg.locator(f'[data-pc="{pc}"]').count() == 0: continue
                pg.click(f'[data-pc="{pc}"]'); pg.wait_for_timeout(60); clicks += 1
                # выбранное должно остаться выбранным (кроме подстройки правилами – тогда хотя бы одна кнопка группы активна)
            for cb in pg.eval_on_selector_all('[data-extra]:not([disabled])', 'e=>e.map(x=>x.dataset.extra)'):
                pg.click(f'[data-extra="{cb}"]'); pg.wait_for_timeout(60); clicks += 1
            cur = pg.evaluate('document.querySelector(".z9__shot.is-front img").currentSrc')
            if not cur or cur.endswith('null') or 'undefined' in cur: fails.append(f'версия {v}: нет картинки {cur}')
        t = pg.evaluate('window.ZeekrCfg.get()')
        print('кликов', clicks, '| сборка:', t['text'][:150])
        pg.screenshot(path=f'{OUT}/proverka-d.png')
        pg2 = b.new_page(); pg2.goto(t['url'], wait_until='networkidle')
        print('ссылка восстанавливает:', pg2.evaluate('window.ZeekrCfg.get().text') == t['text']); pg2.close()
        n = pg.evaluate('''async()=>{const D=window.ZEEKR_CFG;let bad=[],list=[];for(const c in D.have)for(const s of D.have[c])list.push(D.paths.ext.replace('{code}',c).replace('{shot}',s));for(const c in (D.ang||{}))for(const s of D.ang[c])list.push(D.paths.ext.replace('{code}',c).replace('{shot}',s));for(const c of D.int)list.push(D.paths.int.replace('{code}',c));for(const k in D.options)if(D.options[k].icon)list.push(D.options[k].icon);list=[...new Set(list)];for(const u of list){const r=await fetch(u,{method:'HEAD'});if(!r.ok)bad.push(u)}return [list.length,bad.slice(0,3)]}''')
        print('картинок', n[0], 'битых', n[1])
        pg.click('[data-send]'); dis = pg.eval_on_selector('form.z9__form button[type=submit]', 'e=>e.disabled')
        print('кнопка заявки неактивна без галочки:', dis)
        m = b.new_page(viewport={'width': 390, 'height': 844}); m.goto(U, wait_until='networkidle')
        print('ширина на 390:', m.evaluate('document.documentElement.scrollWidth')); m.screenshot(path=f'{OUT}/proverka-m.png'); m.close()
    finally:
        b.close()
print('ошибки консоли', errs[:4], '| 4xx', bad[:4], '| сбои', fails[:4])
