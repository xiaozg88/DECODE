# -*- coding: utf-8 -*-
"""Download chosen HOT OSM facility GPKG exports for the expansion sample."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import requests,pandas as pd
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/experiments/experiment_29_global_expansion';a=pd.read_csv(OUT/'facility_gpkg_availability.csv');items=[]
for _,r in a.iterrows():
 if not str(r.chosen_key):continue
 url='https://production-raw-data-api.s3.amazonaws.com/'+str(r.chosen_key);dest=ROOT/'data/external/hdx/countries'/str(r.iso3)/Path(str(r.chosen_key)).name;items.append((str(r.iso3),str(r.facility_type),url,dest,int(r.chosen_size_bytes)))
def download(x):
 iso,kind,url,dest,expected=x
 if dest.exists() and dest.stat().st_size==expected:return {'iso3':iso,'facility_type':kind,'status':'already_complete','bytes':dest.stat().st_size,'path':str(dest)}
 dest.parent.mkdir(parents=True,exist_ok=True);tmp=dest.with_suffix(dest.suffix+'.part')
 try:
  with requests.get(url,stream=True,timeout=(20,120),headers={'User-Agent':'road-access-research/0.1'}) as r:
   r.raise_for_status();n=0
   with tmp.open('wb') as f:
    for c in r.iter_content(chunk_size=1024*1024):
     if c:f.write(c);n+=len(c)
  if n!=expected:raise RuntimeError(f'size mismatch {n}!={expected}')
  tmp.replace(dest);return {'iso3':iso,'facility_type':kind,'status':'downloaded','bytes':n,'path':str(dest)}
 except Exception as e:return {'iso3':iso,'facility_type':kind,'status':'error','bytes':tmp.stat().st_size if tmp.exists() else 0,'path':str(tmp),'error':str(e)}
rows=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 for f in as_completed([ex.submit(download,x) for x in items]):
  r=f.result();rows.append(r);print(r['iso3'],r['facility_type'],r['status'],round(r['bytes']/1e6,2),'MB',r.get('error',''),flush=True)
pd.DataFrame(rows).to_csv(OUT/'facility_download_log.csv',index=False,encoding='utf-8-sig');print('DONE',len(rows),'errors',sum(x['status']=='error' for x in rows))
