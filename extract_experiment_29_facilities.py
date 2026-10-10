# -*- coding: utf-8 -*-
"""Extract expansion facility GPKG archives without overwriting existing exports."""
from pathlib import Path
import zipfile
ROOT=Path('.');BASE=ROOT/'data/external/hdx/countries';sample=list(BASE.glob('???/hotosm_*_facilities_*_gpkg.zip'));rows=[]
for z in sorted(sample):
 # Skip the seven original countries already extracted by the earlier pipeline if a matching directory exists.
 stem=z.stem;out=z.with_name(stem)
 if out.exists() and list(out.rglob('*.gpkg')):
  rows.append((str(z),'already_extracted',len(list(out.rglob('*.gpkg')))));continue
 out.mkdir(parents=True,exist_ok=True);n=0
 with zipfile.ZipFile(z) as archive:
  for info in archive.infolist():
   target=out/info.filename
   resolved=target.resolve()
   if not str(reserved_target := resolved).startswith(str(out.resolve())):raise RuntimeError('unsafe archive path: '+info.filename)
   if info.is_dir():
    target.mkdir(parents=True,exist_ok=True);continue
   target.parent.mkdir(parents=True,exist_ok=True);archive.extract(info,out);n+=1
 gpkg_count=len(list(out.rglob('*.gpkg')));rows.append((str(z),'extracted',gpkg_count));print(z.name,'files',n,'gpkg',gpkg_count)
import pandas as pd
pd.DataFrame(rows,columns=['archive','status','gpkg_files']).to_csv('output/experiments/experiment_29_global_expansion/facility_extraction_log.csv',index=False,encoding='utf-8-sig')
