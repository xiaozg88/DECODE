# -*- coding: utf-8 -*-
"""Audit HOT OSM facility export availability for the expansion sample."""
from pathlib import Path
import xml.etree.ElementTree as ET
import requests,pandas as pd
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/experiments/experiment_29_global_expansion';sample=pd.read_csv(OUT/'country_sample_and_input_availability.csv');ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
rows=[]
for iso3 in sample.loc[sample.sample_status.eq('addition'),'iso3']:
 for kind in ['health_facilities','education_facilities']:
  url=f'https://production-raw-data-api.s3.amazonaws.com/?list-type=2&prefix=ISO3/{iso3}/{kind}/'
  r=requests.get(url,timeout=30);r.raise_for_status();root=ET.fromstring(r.content);contents=[]
  for c in root.findall('s:Contents',ns):
   key=c.findtext('s:Key',namespaces=ns);size=int(c.findtext('s:Size',namespaces=ns));modified=c.findtext('s:LastModified',namespaces=ns);contents.append((key,size,modified))
  candidates=[x for x in contents if x[0].endswith('_gpkg.zip')]
  preferred=[x for x in candidates if f'hotosm_{iso3.lower()}_{kind}_osm_gpkg.zip' in x[0]]
  split=[x for x in candidates if '_points_gpkg.zip' in x[0] or '_polygons_gpkg.zip' in x[0]]
  chosen=preferred[0] if preferred else (max(candidates,key=lambda x:x[1]) if candidates else None)
  rows.append({'iso3':iso3,'facility_type':kind,'http_status':r.status_code,'available_gpkg_zips':len(candidates),'chosen_key':chosen[0] if chosen else '','chosen_size_bytes':chosen[1] if chosen else 0,'chosen_last_modified':chosen[2] if chosen else '','all_keys':'|'.join(x[0] for x in candidates)});print(iso3,kind,len(candidates),round((chosen[1] if chosen else 0)/1e6,1),'MB')
d=pd.DataFrame(rows);d.to_csv(OUT/'facility_gpkg_availability.csv',index=False,encoding='utf-8-sig');print('available',d.chosen_key.ne('').sum(),'of',len(d),'total GB',d.chosen_size_bytes.sum()/1e9);print(d[d.chosen_key.eq('')].to_string(index=False))


