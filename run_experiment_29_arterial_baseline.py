# -*- coding: utf-8 -*-
"""Experiment 29, phase 2: 30-country arterial baseline scalability audit.

This is an expansion diagnostic on Planet arterial roads. It is not yet the corrected
local-road main model, because full HOT OSM road exports for additions remain pending.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from pyproj import Transformer
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/experiments/experiment_29_global_expansion/arterial_baseline';OUT.mkdir(parents=True,exist_ok=True)
sample=pd.read_csv(ROOT/'output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv');additions=sample[sample.sample_status.eq('addition')].copy();additions['road_size']=additions.road_content_length_bytes;additions=additions.sort_values('road_size')
TRANSFORMER=Transformer.from_crs(4326,3857,always_xy=True)
BASE_SPEED={'motorway':100,'trunk':80,'primary':70,'primary_link':45,'secondary':55,'secondary_link':35,'tertiary':40,'tertiary_link':25,'residential':30,'unclassified':30}
SURFACE={'paved':1.,'unpaved':.55,'unknown':.75};WIDTH={1:.65,2:.8,3:1.}
def facility_files(iso,kind):
 d=ROOT/'data/external/hdx/countries'/iso
 root=list((d/f'hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg').rglob('*.gpkg'))
 if root:return root
 out=[]
 for geom in ['points','polygons']:out.extend((d/f'hotosm_{iso.lower()}_{kind}_facilities_{geom}_gpkg').rglob('*.gpkg'))
 return out
def load_facilities(iso,kind):
 parts=[]
 for p in facility_files(iso,kind):
  layer=pyogrio.list_layers(p)[0,0];g=gpd.read_file(p,layer=layer)
  if g.crs is None:g=g.set_crs(4326)
  parts.append(g.to_crs(4326))
 if not parts:raise FileNotFoundError(f'{iso} {kind}')
 return gpd.GeoDataFrame(pd.concat(parts,ignore_index=True),crs=4326)
def speed(row):
 s=BASE_SPEED.get(str(row.get('osm_tags_highway','')),35)*SURFACE.get(str(row.get('DL_road_class_2024','unknown')),.75)
 try:s*=WIDTH.get(float(row.get('rw_class',np.nan)),.8)
 except:s*=.8
 return s
def build_graph(roads):
 g=nx.MultiGraph();ids={}
 def node(xy):
  key=(round(float(xy[0]),7),round(float(xy[1]),7))
  if key not in ids:ids[key]=len(ids);g.add_node(ids[key],x=key[0],y=key[1])
  return ids[key]
 lengths=roads.to_crs(3857).geometry.length
 for i,r in roads.iterrows():
  geom=r.geometry
  if geom is None or geom.is_empty or geom.geom_type not in {'LineString','MultiLineString'}:continue
  cs=list(geom.coords)
  if len(cs)<2:continue
  l,rn=node(cs[0]),node(cs[-1])
  if l==rn:continue
  t=float(lengths.iloc[i])/1000/float(speed(r))*60
  g.add_edge(l,rn,key=int(i),travel_time_min=t)
 return g
def graph_index(g):
 nodes=np.array(list(g));ll=np.array([(g.nodes[n]['x'],g.nodes[n]['y']) for n in nodes]);xy=np.column_stack(TRANSFORMER.transform(ll[:,0],ll[:,1]));return nodes,cKDTree(xy)
def sources(f,nodes,tree):
 p=f.geometry.representative_point().to_crs(3857);xy=np.column_stack([p.geometry.x,p.geometry.y]);d,i=tree.query(xy);return list(map(int,set(nodes[i[d<=10000]]))),float(np.median(d[d<=10000])) if np.any(d<=10000) else np.nan
def population(iso):
 p=ROOT/'data/external/hdx/countries'/iso/f'{iso.lower()}_pd_2020_1km.tif'
 with rasterio.open(p) as src:
  a=src.read(1).astype('float32');transform=src.transform;nodata=src.nodata
 valid=np.isfinite(a)&(a!=nodata)&(a>0);rows,cols=np.where(valid);vals=a[valid];lon=transform.c+(cols+.5)*transform.a;lat=transform.f+(rows+.5)*transform.e;xy=np.column_stack([lon,lat]);return xy,np.column_stack(TRANSFORMER.transform(xy[:,0],xy[:,1])),vals
def access(g,src,cells,pop):
 d=nx.multi_source_dijkstra_path_length(g,src,weight='travel_time_min') if src else {};v=np.array([d.get(int(n),np.nan) for n in cells]);valid=np.isfinite(v);r={'population_finite':float(pop[valid].sum()),'population_unreachable':float(pop[~valid].sum()),'mean_travel_reachable_min':float(np.average(v[valid],weights=pop[valid])) if valid.any() else np.nan}
 for t in [30,60,120,240]:r[f'share_{t}min_pct']=100*pop[valid&(v<=t)].sum()/pop.sum()
 return r
def process(r):
 iso=str(r.iso3);out=OUT/iso.lower();marker=out/'.complete';output=out/f'{iso.lower()}_arterial_baseline.csv';out.mkdir(parents=True,exist_ok=True)
 if marker.exists() and output.exists():print(iso+' complete',flush=True);return
 road=ROOT/'data/external/hdx/roads'/f"heigit_{r.iso2}_planet_roadsurface_lines.gpkg";roads=gpd.read_file(road)
 if roads.crs is None:roads=roads.set_crs(4326)
 roads=roads.to_crs(4326).reset_index(drop=True);g=build_graph(roads);nodes,tree=graph_index(g);xy,xy3857,pop=population(iso);_,idx=tree.query(xy3857);cells=nodes[idx]
 print(iso+' roads='+str(len(roads))+' graph='+str(g.number_of_nodes())+'/'+str(g.number_of_edges())+' popcells='+str(len(pop)),flush=True)
 rows=[]
 for service,kind,values in [('health','health',['hospital','clinic']),('education','education',['school'])]:
  fac=load_facilities(iso,kind);fac=fac[fac.amenity.astype(str).isin(values)].copy();src,median_snap=sources(fac,nodes,tree);a=access(g,src,cells,pop);rows.append({'country':r.country,'iso3':iso,'service':service,'facility_records':len(fac),'facility_source_nodes':len(src),'median_facility_snap_m':median_snap,'road_records':len(roads),'graph_nodes':g.number_of_nodes(),'graph_edges':g.number_of_edges(),'population_cells':len(pop),**a});print(iso+' '+service+' facilities='+str(len(fac))+' sources='+str(len(src)),flush=True)
 d=pd.DataFrame(rows);d.to_csv(output,index=False,encoding='utf-8-sig');marker.write_text('ok\n',encoding='utf-8');print(iso+' COMPLETE',flush=True)
def main():
 frames=[]
 for _,r in additions.iterrows():
  process(r)
  p=OUT/str(r.iso3).lower()/f"{str(r.iso3).lower()}_arterial_baseline.csv"
  if p.exists():frames.append(pd.read_csv(p))
 d=pd.concat(frames,ignore_index=True);d.to_csv(OUT/'expansion_arterial_baseline_summary.csv',index=False,encoding='utf-8-sig');print('SUMMARY',d.shape,flush=True)
if __name__=='__main__':main()
