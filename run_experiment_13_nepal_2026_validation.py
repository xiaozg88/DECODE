# -*- coding: utf-8 -*-
"""Second-event validation: Nepal 2026 flash flood road damage status."""
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent;BASE=ROOT/'data/external/hdx/hazards/validation/nepal_flash_flood_2026';OUT=ROOT/'output/experiments/experiment_13_hazard_validation/nepal_2026'
def metrics(y,p):
 tp=int((p&y).sum());fp=int((p&~y).sum());fn=int((~p&y).sum());tn=int((~p&~y).sum());prec=tp/(tp+fp) if tp+fp else np.nan;rec=tp/(tp+fn) if tp+fn else np.nan;f1=2*prec*rec/(prec+rec) if prec and rec and np.isfinite(prec+rec) else np.nan
 return {'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,'precision':prec,'recall':rec,'f1':f1,'specificity':tn/(tn+fp) if tn+fp else np.nan,'accuracy':(tp+tn)/len(p) if len(p) else np.nan}
def main():
 OUT.mkdir(parents=True,exist_ok=True);roads=[];events=[];blocks=[]
 for p in BASE.rglob('*transportationL*.shp'):
  if '__MACOSX' in str(p):continue
  g=gpd.read_file(p).to_crs(4326);g['source_file']=str(p.relative_to(BASE));roads.append(g)
 for p in BASE.rglob('*observedEvent*.shp'):
  if '__MACOSX' in str(p):continue
  g=gpd.read_file(p).to_crs(4326);events.append(g)
 roads=pd.concat(roads,ignore_index=True);events=pd.concat(events,ignore_index=True)
 # Exclude Not Analysed from explicit status validation.
 roads=roads[~roads.damage_gra.eq('Not Analysed')].reset_index(drop=True);roads['actual_restricted']=~roads.damage_gra.eq('No visible damage')
 event_union=gpd.GeoDataFrame(geometry=[events.geometry.union_all()],crs=4326).to_crs(3857);r=roads.to_crs(3857)
 joined=gpd.sjoin_nearest(r[['geometry']],event_union,how='left',distance_col='event_distance_m')
 roads['event_distance_m']=joined.event_distance_m.to_numpy()
 # Rough unpaved proxy before Planet match: local roads/cart tracks.
 roads['rough_unpaved_proxy']=roads['info'].astype(str).str.contains('Local Road|Cart Track',case=False,regex=True)
 rules={'event_direct':roads.event_distance_m.le(0),'event_100m':roads.event_distance_m.le(100),'event_500m':roads.event_distance_m.le(500),'event_1km':roads.event_distance_m.le(1000),'event_5km':roads.event_distance_m.le(5000),'rough_unpaved_proxy':roads.rough_unpaved_proxy,'event1km_or_rough':roads.event_distance_m.le(1000)|roads.rough_unpaved_proxy,'event5km_or_rough':roads.event_distance_m.le(5000)|roads.rough_unpaved_proxy}
 rows=[]
 for name,p in rules.items():rows.append({'rule':name,'n':len(roads),**metrics(roads.actual_restricted.to_numpy(),p.to_numpy())})
 out=pd.DataFrame(rows).sort_values('f1',ascending=False);roads.to_csv(OUT/'nepal_2026_road_status_inventory.csv',index=False,encoding='utf-8-sig');out.to_csv(OUT/'nepal_2026_hazard_rule_metrics.csv',index=False,encoding='utf-8-sig')
 # PRN blockage points: distance to observed event union.
 bpaths=[p for p in BASE.rglob('*.shp') if 'road_blockages' in p.name and '__MACOSX' not in str(p)]
 if bpaths:
  b=pd.concat([gpd.read_file(p).to_crs(4326) for p in bpaths],ignore_index=True);bj=gpd.sjoin_nearest(b.to_crs(3857)[['geometry']],event_union,how='left',distance_col='event_distance_m');b['event_distance_m']=bj.event_distance_m.to_numpy();b.to_csv(OUT/'nepal_2026_blockage_point_event_distances.csv',index=False,encoding='utf-8-sig');print('blockages',len(b),'direct',int(b.event_distance_m.le(0).sum()),'1km',int(b.event_distance_m.le(1000).sum()),'5km',int(b.event_distance_m.le(5000).sum()))
 print('roads',len(roads),'restricted',int(roads.actual_restricted.sum()));print(out.to_string(index=False))
if __name__=='__main__':main()
