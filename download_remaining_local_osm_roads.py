# -*- coding: utf-8 -*-
from __future__ import annotations
import zipfile
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent; BASE=ROOT/'data/external/hdx/countries'
URLS={
 'PAK':'https://s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/PAK/roads/lines/hotosm_pak_roads_lines_gpkg.zip',
 'BGD':'https://production-raw-data-api.s3.amazonaws.com/ISO3/BGD/roads/hotosm_bgd_roads_osm_gpkg.zip',
 'ETH':'https://production-raw-data-api.s3.amazonaws.com/ISO3/ETH/roads/hotosm_eth_roads_osm_gpkg.zip',
 'KEN':'https://production-raw-data-api.s3.amazonaws.com/ISO3/KEN/roads/hotosm_ken_roads_osm_gpkg.zip',
 'PHL':'https://s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/PHL/roads/lines/hotosm_phl_roads_lines_gpkg.zip',
 'COL':'https://production-raw-data-api.s3.amazonaws.com/ISO3/COL/roads/hotosm_col_roads_osm_gpkg.zip'}
def download(iso,url):
 out=BASE/iso/'local_roads'/'hotosm_roads_gpkg.zip'; out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists() and out.stat().st_size>0: print(iso+' exists '+str(round(out.stat().st_size/1e6,1))+' MB',flush=True); return out
 tmp=out.with_suffix('.zip.part'); pos=tmp.stat().st_size if tmp.exists() else 0
 headers={'Range':'bytes='+str(pos)+'-'} if pos else {}
 print(iso+' downloading from byte '+str(pos),flush=True)
 with requests.get(url,headers=headers,stream=True,timeout=(30,900)) as r:
  if pos and r.status_code!=206:
   print(iso+' range resume unsupported; restarting',flush=True); pos=0; headers={}
   r.close(); r=requests.get(url,stream=True,timeout=(30,900))
  r.raise_for_status(); cr=r.headers.get('Content-Range'); total=int(cr.split('/')[-1]) if cr else pos+int(r.headers.get('content-length') or 0); mode='ab' if pos and r.status_code==206 else 'wb'
  done=pos
  with tmp.open(mode) as f:
   for chunk in r.iter_content(chunk_size=1024*1024):
    if not chunk: continue
    f.write(chunk); done+=len(chunk)
    if done//(50*1024*1024)!=(done-len(chunk))//(50*1024*1024): print(iso+' '+str(round(done/1e6))+'/'+str(round(total/1e6))+' MB',flush=True)
 if done!=total: raise RuntimeError(iso+' incomplete download '+str(done)+' of '+str(total))
 tmp.replace(out); print(iso+' saved '+str(round(out.stat().st_size/1e6,1))+' MB',flush=True); return out
def extract(iso,archive):
 target=archive.with_suffix(''); marker=target/'.extracted'
 if marker.exists(): print(iso+' already extracted',flush=True); return
 target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as zf:
  for member in zf.infolist():
   dest=(target/member.filename).resolve()
   if not str(dest).startswith(str(target.resolve())): raise RuntimeError('unsafe member '+member.filename)
   zf.extract(member,target)
 marker.write_text('ok\n',encoding='utf-8'); print(iso+' extracted',flush=True)
for iso,url in URLS.items(): extract(iso,download(iso,url))
print('Done',flush=True)
