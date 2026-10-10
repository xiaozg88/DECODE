# -*- coding: utf-8 -*-
"""Experiment 29, phase 1: pre-specified 30-country expansion sample and input audit."""
from __future__ import annotations
from pathlib import Path
import requests
import pandas as pd
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/experiments/experiment_29_global_expansion';OUT.mkdir(parents=True,exist_ok=True)
# Selection was defined before downloading additional inputs. Current seven corrected countries are
# retained; 23 additions span regions, income groups, island/topography settings and hazard profiles.
COUNTRIES=[
 ('PAK','Pakistan','PK','South Asia','lower-middle','flood/monsoon','current'),
 ('MOZ','Mozambique','MZ','Sub-Saharan Africa','low','cyclone/flood','current'),
 ('BGD','Bangladesh','BD','South Asia','lower-middle','flood/cyclone','current'),
 ('ETH','Ethiopia','ET','Sub-Saharan Africa','low','flood/drought','current'),
 ('KEN','Kenya','KE','Sub-Saharan Africa','lower-middle','flood/drought','current'),
 ('PHL','Philippines','PH','East Asia & Pacific','lower-middle','typhoon/flood/landslide','current'),
 ('COL','Colombia','CO','Latin America & Caribbean','upper-middle','flood/landslide','current'),
 ('NPL','Nepal','NP','South Asia','lower-middle','flash flood/landslide','addition'),
 ('LKA','Sri Lanka','LK','South Asia','lower-middle','flood/cyclone','addition'),
 ('IND','India','IN','South Asia','lower-middle','flood/cyclone','addition'),
 ('IDN','Indonesia','ID','East Asia & Pacific','upper-middle','flood/earthquake/volcano','addition'),
 ('VNM','Viet Nam','VN','East Asia & Pacific','lower-middle','flood/typhoon','addition'),
 ('PNG','Papua New Guinea','PG','East Asia & Pacific','lower-middle','flood/landslide','addition'),
 ('KHM','Cambodia','KH','East Asia & Pacific','lower-middle','flood','addition'),
 ('NGA','Nigeria','NG','Sub-Saharan Africa','lower-middle','flood','addition'),
 ('GHA','Ghana','GH','Sub-Saharan Africa','lower-middle','flood','addition'),
 ('SEN','Senegal','SN','Sub-Saharan Africa','lower-middle','flood','addition'),
 ('RWA','Rwanda','RW','Sub-Saharan Africa','low','flood/landslide','addition'),
 ('TZA','Tanzania','TZ','Sub-Saharan Africa','lower-middle','flood','addition'),
 ('ZMB','Zambia','ZM','Sub-Saharan Africa','lower-middle','flood','addition'),
 ('MLI','Mali','ML','Sub-Saharan Africa','low','flood','addition'),
 ('PER','Peru','PE','Latin America & Caribbean','upper-middle','flood/landslide','addition'),
 ('HND','Honduras','HN','Latin America & Caribbean','lower-middle','hurricane/flood','addition'),
 ('GTM','Guatemala','GT','Latin America & Caribbean','upper-middle','flood/landslide','addition'),
 ('MEX','Mexico','MX','Latin America & Caribbean','upper-middle','hurricane/flood/earthquake','addition'),
 ('EGY','Egypt','EG','Middle East & North Africa','lower-middle','flood','addition'),
 ('JOR','Jordan','JO','Middle East & North Africa','upper-middle','flash flood','addition'),
 ('GEO','Georgia','GE','Europe & Central Asia','upper-middle','flood/landslide','addition'),
 ('KGZ','Kyrgyzstan','KG','Europe & Central Asia','low-middle','flood/landslide','addition'),
 ('TUR','Turkey','TR','Europe & Central Asia','upper-middle','flood/earthquake','addition'),
]
ROAD='https://hot.storage.heigit.org/heigit-hdx-public/planet_road_data/heigit_{ISO2}_planet_roadsurface_lines.gpkg'
POP='https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km/2020/{iso3}/{iso3_lower}_pd_2020_1km.tif'
def audit(url):
 try:
  r=requests.head(url,timeout=20,allow_redirects=True)
  return r.status_code,int(r.headers.get('content-length',0)),r.headers.get('last-modified','')
 except Exception as e:return 'ERROR',0,str(e)
rows=[]
for iso3,name,iso2,region,income,hazard,status in COUNTRIES:
 road_url=ROAD.format(ISO2=iso2);pop_url=POP.format(iso3=iso3,iso3_lower=iso3.lower())
 road_code,road_size,road_note=audit(road_url);pop_code,pop_size,pop_note=audit(pop_url)
 local_road=(ROOT/'data/external/hdx/roads'/f'heigit_{iso2}_planet_roadsurface_lines.gpkg').exists();local_pop=(ROOT/'data/external/hdx/countries'/iso3/f'{iso3.lower()}_pd_2020_1km.tif').exists()
 rows.append({'country':name,'iso3':iso3,'iso2':iso2,'region':region,'income_group':income,'hazard_profile':hazard,'sample_status':status,'road_url':road_url,'road_http_status':road_code,'road_content_length_bytes':road_size,'road_last_modified':road_note,'local_road_exists':local_road,'population_url':pop_url,'population_http_status':pop_code,'population_content_length_bytes':pop_size,'population_last_modified':pop_note,'local_population_exists':local_pop})
d=pd.DataFrame(rows);d.to_csv(OUT/'country_sample_and_input_availability.csv',index=False,encoding='utf-8-sig')
summary={
 'selection_rule':'Pre-specified stratified 30-country design retaining the seven corrected countries and adding 23 countries across regions, income groups, island/topography settings and hazard profiles.',
 'total_countries':len(d),'additions':int(d.sample_status.eq('addition').sum()),'current':int(d.sample_status.eq('current').sum()),
 'road_url_available':int(d.road_http_status.eq(200).sum()),'population_url_available':int(d.population_http_status.eq(200).sum()),
 'regions':d.region.value_counts().to_dict(),'income_groups':d.income_group.value_counts().to_dict(),
 'limitations':['Availability audit uses HTTP HEAD and does not download datasets.','A representative multi-hazard archive still must be defined before annual-risk claims.','Facility and hazard inputs are not audited in this phase.']}
import json;(OUT/'sample_design_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(d.groupby(['region','income_group']).size().to_string());print('\nURL availability');print(d.groupby('sample_status')[['road_http_status','population_http_status']].apply(lambda x:x.eq(200).sum()).to_string());print('\nUnavailable roads');print(d[~d.road_http_status.eq(200)][['iso3','road_http_status','road_content_length_bytes']].to_string(index=False));print('\nUnavailable population');print(d[~d.population_http_status.eq(200)][['iso3','population_http_status','population_content_length_bytes']].to_string(index=False))


