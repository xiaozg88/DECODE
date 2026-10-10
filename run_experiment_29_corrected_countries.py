# -*- coding: utf-8 -*-
"""Build corrected topology-noded baseline graphs for selected expansion additions."""
from __future__ import annotations
import argparse
from pathlib import Path
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pyogrio
import rasterio
import shapely
from pyproj import Transformer
from scipy.spatial import cKDTree
import prototype_multicountry_access as base
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output/experiments/experiment_29_global_expansion/corrected_countries';OUT.mkdir(parents=True,exist_ok=True)
TRANSFORMER=Transformer.from_crs(4326,3857,always_xy=True)
MOTORABLE={'motorway','trunk','primary','secondary','tertiary','motorway_link','trunk_link','primary_link','secondary_link','tertiary_link','residential','unclassified','service','track','living_street','road'}
PAVED={'paved','asphalt','concrete','concrete_blocks','paving_stones','bricks','metal','wood'};UNPAVED={'unpaved','ground','dirt','sand','compacted','gravel','earth','grass','mud','fine_gravel','dirt/sand','dirt/rock','sand,_stoney'}
def osm_surface(v):
 if pd.isna(v):return 'unknown'
 v=str(v).strip().lower();return 'paved' if v in PAVED else ('unpaved' if v in UNPAVED else 'unknown')
def flatten(g):
 if g.geom_type=='GeometryCollection':
  for x in g.geoms:yield from flatten(x)
 elif g.geom_type in {'MultiLineString','LinearRing'}:
  for x in g.geoms:yield from flatten(x)
 elif g.geom_type=='LineString' and not g.is_empty:yield g
def facility_files(iso,kind):
 d=ROOT/'data/external/hdx/countries'/iso;root=list((d/f'hotosm_{iso.lower()}_{kind}_facilities_osm_gpkg').rglob('*.gpkg'))
 if root:return root
 out=[]
 for geom in ['points','polygons']:out.extend((d/f'hotosm_{iso.lower()}_{kind}_facilities_{geom}_gpkg').rglob('*.gpkg'))
 return out
def load_facilities(iso,kind):
 parts=[]
 for p in facility_files(iso,kind):
  g=gpd.read_file(p,layer=pyogrio.list_layers(p)[0,0])
  if g.crs is None:g=g.set_crs(4326)
  parts.append(g.to_crs(4326))
 return gpd.GeoDataFrame(pd.concat(parts,ignore_index=True),crs=4326)
def population(iso):
 with rasterio.open(ROOT/'data/external/hdx/countries'/iso/f'{iso.lower()}_pd_2020_1km.tif') as src:
  a=src.read(1).astype('float32');transform=src.transform;nodata=src.nodata
 valid=np.isfinite(a)&(a!=nodata)&(a>0);rows,cols=np.where(valid);pop=a[valid];lon=transform.c+(cols+.5)*transform.a;lat=transform.f+(rows+.5)*transform.e;xy=np.column_stack([lon,lat]);return xy,np.column_stack(TRANSFORMER.transform(xy[:,0],xy[:,1])),pop
def prepare_noded(iso,iso2):
 cache=ROOT/'data/external/hdx/countries'/iso/'local_roads'/f'{iso.lower()}_noded_segments.gpkg'
 if cache.exists():return gpd.read_file(cache),cache
 planet=gpd.read_file(ROOT/'data/external/hdx/roads'/f'heigit_{iso2}_planet_roadsurface_lines.gpkg')
 if planet.crs is None:planet=planet.set_crs(4326)
 planet=planet.to_crs(4326).copy();planet['source']='planet_arterial';planet['highway']=planet.osm_tags_highway;planet['surface_class']=planet.DL_road_class_2024;planet['width_multiplier']=planet.rw_class.map(lambda x:base.WIDTH_MULT.get(float(x),.8) if pd.notna(x) else .8);planet['source_priority']=0
 osmpaths=list((ROOT/'data/external/hdx/countries'/iso/'local_roads'/'hotosm_roads_gpkg').rglob('*.gpkg'));assert osmpaths,iso
 osm=gpd.read_file(osmpaths[0])
 if osm.crs is None:osm=osm.set_crs(4326)
 osm=osm[osm.highway.isin(MOTORABLE)&osm.geometry.notna()&~osm.geometry.is_empty].copy();osm['surface_class']=osm.surface.map(osm_surface);osm['width_multiplier']=.8;osm['source']='osm_motorable';osm['highway']=osm.highway.astype(str);osm['source_priority']=1;osm=osm.to_crs(4326)
 print(iso+' originals planet='+str(len(planet))+' osm='+str(len(osm)),flush=True)
 originals=pd.concat([planet[['source','highway','surface_class','width_multiplier','source_priority','geometry']],osm[['source','highway','surface_class','width_multiplier','source_priority','geometry']]],ignore_index=True).reset_index(names='original_index')
 union=shapely.union_all(originals.geometry.to_numpy());lines=list(flatten(union));print(iso+' union segments='+str(len(lines)),flush=True)
 noded=gpd.GeoDataFrame(geometry=lines,crs=4326);left=noded.to_crs(3857);right=originals.to_crs(3857)
 joined=gpd.sjoin_nearest(left,right[['original_index','source','highway','surface_class','width_multiplier','source_priority','geometry']],how='left',distance_col='attribute_match_distance_m');joined=joined.reset_index(names='segment_id').sort_values(['segment_id','attribute_match_distance_m','source_priority','original_index']).drop_duplicates('segment_id');joined=gpd.GeoDataFrame(joined,geometry='geometry',crs=3857).to_crs(4326)
 joined['length_m']=joined.geometry.to_crs(3857).length;speed=joined.highway.map(lambda x:base.BASE_SPEED.get(str(x),35)).astype(float)*joined.surface_class.map(lambda x:base.SURFACE_MULT.get(str(x),.75)).astype(float)*joined.width_multiplier.astype(float);joined['speed_kmh']=speed;joined['travel_time_min']=joined.length_m/1000/speed*60;joined['hazard_intersect']=False
 joined.to_file(cache,driver='GPKG',layer='noded_segments');return joined,cache
def graph_index(g):
 nodes=np.array(list(g));ll=np.array([(g.nodes[n]['x'],g.nodes[n]['y']) for n in nodes]);xy=np.column_stack(TRANSFORMER.transform(ll[:,0],ll[:,1]));return nodes,cKDTree(xy)
def source_nodes(f,nodes,tree):
 p=f.geometry.representative_point().to_crs(3857);xy=np.column_stack([p.geometry.x,p.geometry.y]);d,i=tree.query(xy);return list(map(int,set(nodes[i[d<=1000]]))),d
def access(g,src,cells,pop):
 d=nx.multi_source_dijkstra_path_length(g,src,weight='travel_time_min') if src else {};v=np.array([d.get(int(n),np.nan) for n in cells]);valid=np.isfinite(v);r={'population_total':float(pop.sum()),'population_finite':float(pop[valid].sum()),'population_unreachable':float(pop[~valid].sum()),'mean_travel_reachable_min':float(np.average(v[valid],weights=pop[valid])) if valid.any() else np.nan}
 for t in [30,60,120,240]:r[f'share_{t}min_pct']=100*pop[valid&(v<=t)].sum()/pop.sum()
 return r
def process(iso,iso2,name):
 out=OUT/iso.lower();marker=out/'.complete';summary=out/f'{iso.lower()}_corrected_baseline.csv';out.mkdir(parents=True,exist_ok=True)
 if marker.exists() and summary.exists():print(iso+' complete',flush=True);return
 roads,cache=prepare_noded(iso,iso2);g=nx.MultiGraph();ids={}
 def node(xy):
  key=(round(float(xy[0]),7),round(float(xy[1]),7))
  if key not in ids:ids[key]=len(ids);g.add_node(ids[key],x=key[0],y=key[1])
  return ids[key]
 for i,r in roads.iterrows():
  geom=r.geometry
  if geom is None or geom.is_empty or geom.geom_type not in {'LineString','MultiLineString'}:continue
  cs=list(geom.coords)
  if len(cs)<2:continue
  l,rn=node(cs[0]),node(cs[-1])
  if l==rn:continue
  g.add_edge(l,rn,key=int(i),road_index=int(i),surface=r.surface_class,travel_time_min=float(r.travel_time_min))
 nodes,tree=graph_index(g);xy,xy3857,pop=population(iso);_,idx=tree.query(xy3857);cells=nodes[idx];rows=[]
 print(iso+' graph='+str(g.number_of_nodes())+'/'+str(g.number_of_edges()),flush=True)
 for service,kind,vals in [('health','health',['hospital','clinic']),('education','education',['school'])]:
  fac=load_facilities(iso,kind);fac=fac[fac.amenity.astype(str).isin(vals)].copy();src,snap=source_nodes(fac,nodes,tree);rows.append({'country':name,'iso3':iso,'service':service,'facility_records':len(fac),'facility_source_nodes':len(src),'median_facility_snap_m':float(np.median(snap[snap<=1000])) if np.any(snap<=1000) else np.nan,'noded_segments':len(roads),'graph_nodes':g.number_of_nodes(),'graph_edges':g.number_of_edges(),'noded_cache':str(cache),**access(g,src,cells,pop)});print(iso+' '+service+' facilities='+str(len(fac))+' sources='+str(len(src)),flush=True)
 pd.DataFrame(rows).to_csv(summary,index=False,encoding='utf-8-sig');marker.write_text('ok\n',encoding='utf-8');print(iso+' COMPLETE',flush=True)
def main():
 default=['KGZ','KHM','PNG','JOR','HND']

 q=pd.read_csv(ROOT/'output/experiments/experiment_29_global_expansion/country_sample_and_input_availability.csv')[['iso3','iso2','country']]
 names={r.iso3:(r.iso2,r.country) for _,r in q.iterrows()}
 ap=argparse.ArgumentParser();ap.add_argument('--countries',nargs='+',default=default);a=ap.parse_args()
 frames=[]
 for iso in a.countries:
  process(iso,*names[iso])
  p=OUT/iso.lower()/f'{iso.lower()}_corrected_baseline.csv'
  if p.exists():frames.append(pd.read_csv(p))
 if frames:pd.concat(frames,ignore_index=True).to_csv(OUT/'corrected_expansion_baseline_summary.csv',index=False,encoding='utf-8-sig');print('SUMMARY',len(frames)*2,flush=True)
if __name__=='__main__':main()

