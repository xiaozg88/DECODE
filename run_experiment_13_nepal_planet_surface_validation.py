# -*- coding: utf-8 -*-
"""Match Nepal 2026 road status to Planet surface and test combined rules."""
from pathlib import Path
import geopandas as gpd,numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent;BASE=ROOT/'data/external/hdx/hazards/validation/nepal_flash_flood_2026';OUT=ROOT/'output/experiments/experiment_13_hazard_validation/nepal_2026/planet_surface';OUT.mkdir(parents=True,exist_ok=True)
def metrics(y,p):
 tp=int((p&y).sum());fp=int((p&~y).sum());fn=int((~p&y).sum());tn=int((~p&~y).sum());pr=tp/(tp+fp) if tp+fp else np.nan;re=tp/(tp+fn) if tp+fn else np.nan;f=2*pr*re/(pr+re) if pr and re and np.isfinite(pr+re) else np.nan;return {'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,'precision':pr,'recall':re,'f1':f,'specificity':tn/(tn+fp) if tn+fp else np.nan}
roads=[]
for p in BASE.rglob('*transportationL*.shp'):
 if '__MACOSX' not in str(p):g=gpd.read_file(p).to_crs(4326);g['source_file']=str(p.relative_to(BASE));roads.append(g)
r=pd.concat(roads,ignore_index=True);r=r[~r.damage_gra.eq('Not Analysed')].reset_index(drop=True);r['actual_restricted']=~r.damage_gra.eq('No visible damage')
prev=pd.read_csv(ROOT/'output/experiments/experiment_13_hazard_validation/nepal_2026/nepal_2026_road_status_inventory.csv');r['event_distance_m']=prev.event_distance_m.to_numpy()
planet=gpd.read_file(BASE/'heigit_NP_planet_roadsurface_lines.gpkg').to_crs(3857)
j=gpd.sjoin_nearest(r.to_crs(3857)[['geometry']],planet[['geometry','DL_road_class_2024','osm_tags_highway','rw_class']],how='left',distance_col='planet_distance_m')
j=j.sort_index()
j=j[~j.index.duplicated(keep='first')]
for c in ['DL_road_class_2024','osm_tags_highway','rw_class','planet_distance_m']:r['planet_'+c]=j[c].to_numpy()
r.to_csv(OUT/'nepal_status_planet_match.csv',index=False,encoding='utf-8-sig')
rows=[]
for threshold in [25,50,100,250,500,1000]:
 q=r[r.planet_planet_distance_m.le(threshold)];y=q.actual_restricted.to_numpy();unp=q.planet_DL_road_class_2024.eq('unpaved').to_numpy();direct=q.event_distance_m.le(0).to_numpy();direct1k=q.event_distance_m.le(1000).to_numpy()
 for name,p in [('planet_unpaved',unp),('event_direct',direct),('event_direct_or_unpaved',direct|unp),('event1km_or_unpaved',direct1k|unp)]:rows.append({'match_threshold_m':threshold,'rule':name,'n':len(q),**metrics(y,p)})
out=pd.DataFrame(rows);out.to_csv(OUT/'nepal_planet_surface_rule_metrics.csv',index=False,encoding='utf-8-sig');print(out.to_string(index=False))
