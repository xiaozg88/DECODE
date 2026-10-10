# -*- coding: utf-8 -*-
from __future__ import annotations
import concurrent.futures, zipfile
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
CHUNK=16*1024*1024; WORKERS=24
def head_total(url):
 with requests.head(url,timeout=(30,120)) as r:
  r.raise_for_status(); total=int(r.headers['content-length']); accept=r.headers.get('accept-ranges','').lower()
  if 'bytes' not in accept: raise RuntimeError('server does not accept ranges')
 return total
def fetch_chunk(url,path,start,end):
 expected=end-start+1; pos=path.stat().st_size if path.exists() else 0
 if pos==expected: return path.stat().st_size
 if pos>expected: path.unlink(); pos=0
 headers={'Range':f'bytes={start+pos}-{end}'}
 for attempt in range(6):
  try:
   with requests.get(url,headers=headers,stream=True,timeout=(30,600)) as r:
    if r.status_code!=206: raise RuntimeError('range status '+str(r.status_code))
    with path.open('ab' if pos else 'wb') as f:
     for c in r.iter_content(1024*1024):
      if c: f.write(c)
   if path.stat().st_size!=expected: raise RuntimeError('short chunk')
   return path.stat().st_size
  except Exception as e:
   if attempt==5: raise
   pos=path.stat().st_size if path.exists() else 0; headers={'Range':f'bytes={start+pos}-{end}'}
def download_parallel(iso,url):
 final=BASE/iso/'local_roads'/'hotosm_roads_gpkg.zip'; final.parent.mkdir(parents=True,exist_ok=True)
 if final.exists() and final.stat().st_size>0: print(iso+' exists '+str(round(final.stat().st_size/1e6,1))+' MB',flush=True); return final
 legacy=final.with_suffix('.zip.part')
 if legacy.exists(): legacy.unlink()
 total=head_total(url); jobs=[]
 for i,start in enumerate(range(0,total,CHUNK)):
  end=min(start+CHUNK,total)-1; jobs.append((i,url,final.parent/f'.{final.name}.part-{i:05d}',start,end))
 print(iso+' parallel downloading '+str(round(total/1e6,1))+' MB in '+str(len(jobs))+' chunks',flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
  futures={ex.submit(fetch_chunk,u,p,s,e):(i,p) for i,u,p,s,e in jobs}
  for future in concurrent.futures.as_completed(futures):
   i,p=futures[future]; n=future.result(); print(iso+' chunk '+str(i)+' complete '+str(round(n/1e6,1))+' MB',flush=True)
 assembling=final.with_suffix('.zip.assembling')
 with assembling.open('wb') as out:
  for _,_,p,_,_ in sorted(jobs):
   with p.open('rb') as inp:
    while True:
     c=inp.read(1024*1024)
     if not c: break
     out.write(c)
 if assembling.stat().st_size!=total: raise RuntimeError(iso+' assembled size mismatch')
 assembling.replace(final)
 for _,_,p,_,_ in jobs: p.unlink()
 print(iso+' saved '+str(round(final.stat().st_size/1e6,1))+' MB',flush=True); return final
def extract(iso,archive):
 target=archive.with_suffix(''); marker=target/'.extracted'
 if marker.exists(): print(iso+' already extracted',flush=True); return
 target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as zf:
  for member in zf.infolist():
   dest=(target/member.filename).resolve()
   if not str(dest).startswith(str(target.resolve())): raise RuntimeError('unsafe member')
   zf.extract(member,target)
 marker.write_text('ok\n',encoding='utf-8'); print(iso+' extracted',flush=True)
for iso,url in URLS.items(): extract(iso,download_parallel(iso,url))
print('Done',flush=True)
