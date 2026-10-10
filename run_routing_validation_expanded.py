# -*- coding: utf-8 -*-
"""Validate corrected-model road travel times against public OSRM routes."""
from __future__ import annotations
import argparse,time,random
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import networkx as nx
from scipy.spatial import cKDTree
import prototype_multicountry_access as base
import run_corrected_core_experiments as core

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/experiments/routing_validation_expanded'
OSRM='https://router.project-osrm.org/route/v1/driving/'
SESSION=requests.Session();SESSION.headers.update({'User-Agent':'road-access-research/0.1'})

def sample_cells(pop,n=15,seed=42):
    rng=np.random.default_rng(seed);idx=np.arange(len(pop));
    # Stratify by population rank: low, lower-middle, middle, upper-middle, high, plus random fill.
    order=np.argsort(pop);slots=np.array_split(order,5);picked=[]
    per=max(1,n//5)
    for slot in slots:
        take=min(per,len(slot));picked.extend(rng.choice(slot,size=take,replace=False).tolist())
    remaining=np.setdiff1d(idx,np.array(picked),assume_unique=False)
    if len(picked)<n and len(remaining):picked.extend(rng.choice(remaining,size=min(n-len(picked),len(remaining)),replace=False).tolist())
    return np.array(picked[:n])

def osrm_route(lon1,lat1,lon2,lat2):
    url=OSRM+f'{lon1:.6f},{lat1:.6f};{lon2:.6f},{lat2:.6f}?overview=false&alternatives=false&steps=false'
    last=''
    for attempt in range(3):
        try:
            r=SESSION.get(url,timeout=(10,30))
            if r.status_code in {429,500,502,503,504}:
                last=f'HTTP {r.status_code}';time.sleep(1+attempt*2);continue
            r.raise_for_status();j=r.json()
            if j.get('code')!='Ok':return None,j.get('code',None)
            route=j['routes'][0]
            waypoints=j.get('waypoints',[]);snap=[]
            for w in waypoints:snap.append(float(w.get('distance',np.nan)))
            return {'osrm_duration_min':float(route['duration'])/60,'osrm_distance_km':float(route['distance'])/1000,'origin_snap_m':snap[0] if snap else np.nan,'destination_snap_m':snap[1] if len(snap)>1 else np.nan},None
        except Exception as e:last=str(e);time.sleep(1+attempt*2)
    return None,last

def process(iso,per_service):
    out=OUT/iso.lower();out.mkdir(parents=True,exist_ok=True);marker=out/'.complete'
    if marker.exists():print(iso+' already complete',flush=True);return
    path=next((ROOT/'data/external/hdx/countries'/iso/'local_roads').glob('*noded_segments.gpkg'))
    roads=gpd.read_file(path);g=core.build_graph(roads,'m3_class_surface_width');nodes,tree=core.graph_index(g);xy,xy3857,pop=base.load_population(iso);_,cell_idx=tree.query(xy3857);cell_nodes=nodes[cell_idx]
    print(iso+' graph='+str(g.number_of_nodes())+'/'+str(g.number_of_edges()),flush=True)
    rows=[]
    for service in ['health','education']:
        facilities=core.facility_sets(iso,service);fv='registry_union' if 'registry_union' in facilities else 'osm';fac=facilities[fv];sources=core.source_nodes(fac,nodes,tree)
        if not sources:continue
        src_arr=np.array(sources,dtype=int);src_pos={n:i for i,n in enumerate(src_arr)};src_ll=np.array([(g.nodes[n]['x'],g.nodes[n]['y']) for n in src_arr]);src_xy=np.column_stack(base.TRANSFORMER.transform(src_ll[:,0],src_ll[:,1]));src_tree=cKDTree(src_xy)
        cell_sample=sample_cells(pop,per_service,seed=42+len(service))
        for j,ci in enumerate(cell_sample):
            cn=int(cell_nodes[ci]);_,si=src_tree.query(xy3857[ci]);sn=int(src_arr[si])
            if cn==sn:continue
            try:model_min=nx.dijkstra_path_length(g,sn,cn,weight='travel_time_min')
            except Exception:continue
            if not np.isfinite(model_min) or model_min<=0 or model_min>600:continue
            olat,olon=src_ll[si,1],src_ll[si,0];dlat,dlon=xy[ci,1],xy[ci,0]
            osrm,err=osrm_route(olon,olat,dlon,dlat)
            rows.append({'country':base.COUNTRIES[iso],'iso3':iso,'service':service,'facility_variant':fv,'sample_rank':j+1,'population':float(pop[ci]),'model_travel_min':float(model_min),'osrm_status':'ok' if osrm else 'error','osrm_error':err,**(osrm or {})})
            print(iso+' '+service+' '+str(j+1)+' model='+str(round(model_min,1))+' osrm='+str(round((osrm or {}).get('osrm_duration_min',np.nan),1)),flush=True)
            time.sleep(0.15)
    d=pd.DataFrame(rows);d.to_csv(out/(iso.lower()+'_osrm_validation.csv'),index=False,encoding='utf-8-sig');marker.write_text('ok\n',encoding='utf-8');print(iso+' COMPLETE '+str(len(d)),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--countries',nargs='+',default=['PAK','MOZ','BGD','ETH','KEN','PHL','COL']);ap.add_argument('--per-service',type=int,default=50);a=ap.parse_args()
    for iso in a.countries:process(iso,a.per_service)
if __name__=='__main__':main()
