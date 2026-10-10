# -*- coding: utf-8 -*-
"""Download Planet road and WorldPop inputs for the pre-specified expansion sample."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import requests
import pandas as pd
ROOT=Path(__file__).resolve().parent
sample=pd.read_csv(ROOT/'output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv')
files=[]
for _,r in sample[sample.sample_status.eq('addition')].iterrows():
 road=ROOT/'data/external/hdx/roads'/f"heigit_{r.iso2}_planet_roadsurface_lines.gpkg";pop=ROOT/'data/external/hdx/countries'/r.iso3/f"{str(r.iso3).lower()}_pd_2020_1km.tif"
 files.append((r.iso3,'planet_road',r.road_url,road,int(r.road_content_length_bytes)));files.append((r.iso3,'worldpop',r.population_url,pop,int(r.population_content_length_bytes)))

def download(item):
 iso,kind,url,path,expected=item
 if path.exists() and path.stat().st_size==expected:return {'iso3':iso,'file_type':kind,'status':'already_complete','bytes':path.stat().st_size,'path':str(path)}
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.part')
 try:
  with requests.get(url,stream=True,timeout=(20,120),headers={'User-Agent':'road-access-research/0.1'}) as r:
   r.raise_for_status();total=0
   with tmp.open('wb') as f:
    for chunk in r.iter_content(chunk_size=1024*1024):
     if chunk:f.write(chunk);total+=len(chunk)
  if total!=expected:raise RuntimeError(f'size mismatch {total} != {expected}')
  tmp.replace(path);return {'iso3':iso,'file_type':kind,'status':'downloaded','bytes':total,'path':str(path)}
 except Exception as e:
  return {'iso3':iso,'file_type':kind,'status':'error','bytes':tmp.stat().st_size if tmp.exists() else 0,'path':str(tmp),'error':str(e)}
rows=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 futs=[ex.submit(download,x) for x in files]
 for f in as_completed(futs):
  r=f.result();rows.append(r);print(r['iso3'],r['file_type'],r['status'],round(r['bytes']/1e6,1),'MB',r.get('error',''),flush=True)
out=ROOT/'output/experiments/experiment_29_global_expansion/input_download_log.csv';pd.DataFrame(rows).to_csv(out,index=False,encoding='utf-8-sig');print('DONE',len(rows),'files;',sum(r['status'].eq('error') for r in rows),'errors')
