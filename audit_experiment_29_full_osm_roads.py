# -*- coding: utf-8 -*-
"""Audit full HOT OSM road export availability and size for expansion countries."""
from pathlib import Path
import xml.etree.ElementTree as ET
import requests,pandas as pd
ROOT=Path('.');sample=pd.read_csv('output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv');ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'};rows=[]
for iso3 in sample.loc[sample.sample_status.eq('addition'),'iso3']:
 url=f'https://production-raw-data-api.s3.amazonaws.com/?list-type=2&prefix=ISO3/{iso3}/roads/';r=requests.get(url,timeout=30);r.raise_for_status();root=ET.fromstring(r.content);contents=[]
 for c in root.findall('s:Contents',ns):
  key=c.findtext('s:Key',namespaces=ns);size=int(c.findtext('s:Size',namespaces=ns));mod=c.findtext('s:LastModified',namespaces=ns);contents.append((key,size,mod))
 candidates=[x for x in contents if x[0].endswith('_gpkg.zip')]
 preferred=[x for x in candidates if x[0].startswith(f'ISO3/{iso3}/roads/hotosm_') and (x[0].endswith('_osm_gpkg.zip') or x[0].endswith('_lines_gpkg.zip'))]
 chosen=preferred[0] if preferred else (max(candidates,key=lambda x:x[1]) if candidates else None)
 rows.append({'iso3':iso3,'http_status':r.status_code,'available_gpkg_zips':len(candidates),'chosen_key':chosen[0] if chosen else '','chosen_size_bytes':chosen[1] if chosen else 0,'chosen_size_gb':(chosen[1] if chosen else 0)/1e9,'chosen_last_modified':chosen[2] if chosen else '','all_keys':'|'.join(x[0] for x in candidates)});print(iso3,len(candidates),round((chosen[1] if chosen else 0)/1e9,3),'GB')
d=pd.DataFrame(rows);d.to_csv('output/experiments/experiment_29_global_expansion/full_osm_road_availability.csv',index=False,encoding='utf-8-sig');print('available',d.chosen_key.ne('').sum(),'of',len(d),'total GB',d.chosen_size_bytes.sum()/1e9)

