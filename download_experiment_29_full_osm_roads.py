# -*- coding: utf-8 -*-
"""Download full HOT OSM road archives for selected expansion countries."""
from __future__ import annotations
import argparse,concurrent.futures,zipfile
from pathlib import Path
import requests,pandas as pd
ROOT=Path(__file__).resolve().parent;BASE=ROOT/'data/external/hdx/countries';OUT=ROOT/'output/experiments/experiment_29_global_expansion'
DEFAULT=['NPL','KGZ','PNG','JOR','KHM','HND','RWA','GEO','LKA','GTM','GHA','SEN','MLI','ZMB']
a=pd.read_csv(OUT/'full_osm_road_availability.csv').set_index('iso3');CHUNK=8*1024*1024;WORKERS=8
def head(url):
 r=requests.head(url,timeout=(20,120),allow_redirects=True);r.raise_for_status();total=int(r.headers.get('content-length',0));return total
def fetch(url,path,start,end):
 expected=end-start+1;pos=path.stat().st_size if path.exists() else 0
 if pos==expected:return
 if pos>expected:path.unlink();pos=0
 headers={'Range':f'bytes={start+pos}-{end}','User-Agent':'road-access-research/0.1'}
 for attempt in range(6):
  try:
   with requests.get(url,headers=headers,stream=True,timeout=(30,600)) as r:
    if r.status_code!=206:raise RuntimeError('range status '+str(r.status_code))
    with path.open('ab' if pos else 'wb') as f:
     for c in r.iter_content(1024*1024):
      if c:f.write(c)
   if path.stat().st_size!=expected:raise RuntimeError('short chunk')
   return
  except Exception:
   if attempt==5:raise
   pos=path.stat().st_size if path.exists() else 0;headers={'Range':f'bytes={start+pos}-{end}','User-Agent':'road-access-research/0.1'}
def extract(iso,archive):
 target=archive.with_suffix('');marker=target/'.extracted'
 if marker.exists() and marker.stat().st_mtime>=archive.stat().st_mtime:return 'already_extracted'
 target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for m in z.infolist():
   dest=(target/m.filename).resolve()
   if not str(dest).startswith(str(target.resolve())):raise RuntimeError('unsafe archive member')
   z.extract(m,target)
 marker.write_text('ok\n',encoding='utf-8');return 'extracted'
def process(iso):
 r=a.loc[iso];url='https://production-raw-data-api.s3.amazonaws.com/'+str(r.chosen_key);final=BASE/iso/'local_roads'/'hotosm_roads_gpkg.zip';final.parent.mkdir(parents=True,exist_ok=True)
 if not(final.exists() and final.stat().st_size==int(r.chosen_size_bytes)):
  total=head(url);jobs=[]
  for i,start in enumerate(range(0,total,CHUNK)):
   end=min(start+CHUNK,total)-1;jobs.append((i,final.parent/f'.{final.name}.part-{i:05d}',start,end))
  with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
   list(ex.map(lambda x:fetch(url,x[1],x[2],x[3]),jobs))
  assembling=final.with_suffix('.zip.assembling')
  with assembling.open('wb') as out:
   for _,p,_,_ in sorted(jobs):
    with p.open('rb') as inp:out.write(inp.read())
  if assembling.stat().st_size!=total:raise RuntimeError('assembly mismatch')
  assembling.replace(final)
  for _,p,_,_ in jobs:p.unlink()
 status=extract(iso,final);return {'iso3':iso,'url':url,'archive':str(final),'bytes':final.stat().st_size,'status':status}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--countries',nargs='+',default=DEFAULT);countries=ap.parse_args().countries;rows=[]
 for iso in countries:
  r=process(iso);rows.append(r);print(iso,r['status'],round(r['bytes']/1e6,1),'MB',flush=True)
 pd.DataFrame(rows).to_csv(OUT/'full_osm_road_download_log.csv',index=False,encoding='utf-8-sig');print('DONE',len(rows))
if __name__=='__main__':main()

