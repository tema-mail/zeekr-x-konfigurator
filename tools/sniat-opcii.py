import json, subprocess, itertools, os, sys
MID, MYC = sys.argv[1], sys.argv[2]   # пример: 10 GMY_9X_01 (9X), 11 GMY_Z012_01 (8X)
API='https://api-gw-toc.zeekrlife.com/zeekrlife-config-order/v1/model/pub/toc/'
from playwright.sync_api import sync_playwright
EXE='/Users/artemgalimov/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'
HDR={}
PG=None
def post(path, body):
    for a in range(3):
        d=PG.evaluate('''async ([u,b,h])=>{const r=await fetch(u,{method:'POST',headers:h,body:JSON.stringify(b)});return await r.text()}''',[API+path,body,HDR])
        try:
            d=json.loads(d)
            if d.get('code')=='000000': return d['data']
        except Exception: pass
    raise SystemExit('fail '+path+json.dumps(body)+str(d)[:300])
out={'versions':[]}
_p=sync_playwright().start(); _b=_p.chromium.launch(executable_path=EXE)
try:
  PG=_b.new_page()
  def onreq(r):
    if 'modelVersion/list' in r.url and not HDR: HDR.update({k:v for k,v in r.headers.items() if not k.startswith(':') and k.lower() not in ('content-length','host','cookie','referer','user-agent','accept-encoding','origin')})
  PG.on('request',onreq)
  PG.goto(f'https://www.zeekrlife.com/toReserve?modelInfoId={MID}&modelYearCode={MYC}',wait_until='networkidle',timeout=90000)
  print('headers:',sorted(HDR.keys()))
  grp=post('modelYearVersionGroup',{'modelYearCode':MYC}) or {}
  gids=[g['versionGroupId'] for g in (grp.get('modelYearVersionGroupItemParamList') or [])] or [None]
  print('группы',gids)
  for gid in gids:
      vs=post('modelVersion/list',{'modelInfoId':MID,'couponChoose':None,'modelYearCode':MYC,'versionGroupId':gid})
      for v in vs:
          import re as _re
          gc=sorted(set(_re.findall(r'"groupCode": "([^"]+)"',json.dumps(v.get('saleItemAndSkuResults'),ensure_ascii=False))))[0]
          lvl={}
          def walk(o):
              if isinstance(o,dict):
                  if 'subSkuResultList' in o and o.get('skuCode'):
                      lvl[o['skuCode']]={'name':o.get('itemName'),'opts':[(x['productCode'],x['subSkuName'],x.get('isDefaultSelected')) for x in o['subSkuResultList']]}
                  for k,x in o.items():
                      if k!='subSkuResultList': walk(x)
              elif isinstance(o,list):
                  for x in o: walk(x)
          walk(v.get('saleItemAndSkuResults'))
          combos=list(itertools.product(*[[c for c,_,_ in lvl[k]['opts']] for k in lvl]))
          items={}
          for combo in combos:
              data=post('modelItem/list',{'modelInfoId':MID,'modelVersionId':v['modelVersionId'],'groupCode':gc,'productCodes':list(combo),'couponChoose':None})
              items['_'.join(combo)]=data
          out['versions'].append({'group':gid,'id':v['modelVersionId'],'name':v['versionName'],'groupCode':gc,'level':lvl,'vehicleSkus':v['vehiclePicUrlSkuCodes'],'interiorSkus':v['interiorPicUrlSkuCodes'],'bigPic':v.get('bigPicRuleList'),'items':items,'detailImgs':v.get('versionDetailImgList')})
          print(v['modelVersionId'],v['versionName'],len(combos),'комбинаций уровня версии')
  json.dump(out,open('z9x-raw.json','w'),ensure_ascii=False)

finally:
  _b.close(); _p.stop()
