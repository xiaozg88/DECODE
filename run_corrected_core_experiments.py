# -*- coding: utf-8 -*-
"""Corrected-model reruns of Experiments 6, 8, 15, and 17.

The corrected main model uses:
1. topology-noded Planet + HOT OSM road networks; and
2. official facility registries where spatially available:
   - Ethiopia health registry;
   - Bangladesh LGED education registry;
   - Mozambique OCHA health registry.

This script writes one directory per country so long jobs can be resumed country by country.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as warp_transform
from scipy.spatial import cKDTree
import prototype_multicountry_access as base

ROOT=Path(__file__).resolve().parent
OUTBASE=ROOT/'output/experiments/corrected_core'
GHS=ROOT/'data/external/ghs/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif'
MODELS=['m1_class_only','m2_class_surface','m3_class_surface_width']
SCENARIOS=['baseline','no_unpaved','surface_aware','all_remove','all_slow','surface_only']

def noded_path(iso):
    d=ROOT/'data/external/hdx/countries'/iso/'local_roads'
    return next(d.glob('*noded_segments.gpkg'))

def facility_sets(iso,service):
    current=base.load_facilities(iso,service)
    if service=='health':
        current=current[current.amenity.isin(['hospital','clinic'])].copy()
    else:
        current=current[current.amenity.eq('school')].copy()
    if iso=='ETH' and service=='health':
        registry=gpd.read_file(ROOT/'data/external/facility_validation/ETH_health_facilities_2025/Ethiopian_health_Facilities/Ethiopian Health Facilities.shp').to_crs(4326)
        t=registry.Type.astype(str)
        registry=registry[t.str.contains('Hospital|Clinic|Health Center',case=False,regex=True)].copy()
        union=gpd.GeoDataFrame(pd.concat([current[['geometry']].assign(origin='osm'),registry[['geometry']].assign(origin='registry')],ignore_index=True),geometry='geometry',crs=4326)
        return {'osm':current,'registry_union':union}
    if iso=='BGD' and service=='education':
        registry=gpd.read_file(ROOT/'data/external/facility_validation/BGD_LGED_education_2017/bgd_poi_educationfacilities_lged.shp').to_crs(4326)
        union=gpd.GeoDataFrame(pd.concat([current[['geometry']].assign(origin='osm'),registry[['geometry']].assign(origin='lged')],ignore_index=True),geometry='geometry',crs=4326)
        return {'osm':current,'registry_union':union}
    if iso=='MOZ' and service=='health':
        registry=gpd.read_file(ROOT/'data/external/facility_validation/MOZ_MFL_health_2017/Mozambique-health-facilities/mozambique-healthfacilities.shp').to_crs(4326)
        union=gpd.GeoDataFrame(pd.concat([current[['geometry']].assign(origin='osm'),registry[['geometry']].assign(origin='ocha')],ignore_index=True),geometry='geometry',crs=4326)
        return {'osm':current,'registry_union':union}
    return {'osm':current}

def model_speed(row,model):
    speed=float(base.BASE_SPEED.get(str(row.highway),35.0))
    if model in {'m2_class_surface','m3_class_surface_width'}:
        speed*=float(base.SURFACE_MULT.get(str(row.surface_class),.75))
    if model=='m3_class_surface_width':
        speed*=float(row.width_multiplier)
    return speed

def build_graph(roads,model):
    g=nx.MultiGraph(); ids={}
    def endpoint(xy):
        key=(round(float(xy[0]),7),round(float(xy[1]),7))
        if key not in ids:
            n=len(ids);ids[key]=n;g.add_node(n,x=key[0],y=key[1])
        return ids[key]
    speeds=[]
    for idx,row in roads.iterrows():
        geom=row.geometry
        if geom is None or geom.is_empty or geom.geom_type not in {'LineString','MultiLineString'}:continue
        coords=list(geom.coords)
        if len(coords)<2:continue
        left,right=endpoint(coords[0]),endpoint(coords[-1])
        if left==right:continue
        speed=model_speed(row,model);travel=float(row.length_m)/1000/speed*60
        speeds.append(travel)
        g.add_edge(left,right,key=int(idx),road_index=int(idx),source=row.source,highway=row.highway,surface=row.surface_class,length_m=float(row.length_m),travel_time_min=travel,hazard=bool(row.hazard_intersect))
    return g

def graph_index(g):
    nodes=np.array(list(g),dtype=int);ll=np.array([(g.nodes[n]['x'],g.nodes[n]['y']) for n in nodes]);xy=np.column_stack(base.TRANSFORMER.transform(ll[:,0],ll[:,1]));return nodes,cKDTree(xy)

def source_nodes(f,nodes,tree):
    p=f.geometry.representative_point().to_crs(3857);xy=np.column_stack([p.geometry.x,p.geometry.y]);d,i=tree.query(xy);k=d<=1000
    return list(map(int,set(nodes[i[k]])))

def scenario_graph(basegraph,roads,scenario):
 if scenario=='baseline':return basegraph
 g=basegraph.copy();remove=[];updates=[]
 for u,v,k,d in g.edges(keys=True,data=True):
  hit=bool(d.get('hazard',False));surface=str(d.get('surface'))
  if scenario=='no_unpaved' and surface=='unpaved':remove.append((u,v,k))
  elif scenario=='surface_aware':
   if hit and surface=='unpaved':remove.append((u,v,k))
   elif hit:updates.append((u,v,k,{**d,'travel_time_min':float(d['travel_time_min'])*2}))
  elif scenario=='all_remove' and hit:remove.append((u,v,k))
  elif scenario=='all_slow' and hit:updates.append((u,v,k,{**d,'travel_time_min':float(d['travel_time_min'])*2}))
  elif scenario=='surface_only' and hit and surface=='unpaved':remove.append((u,v,k))
 for u,v,k in remove:g.remove_edge(u,v,key=k)
 # Re-add updated edges with fresh attribute dictionaries; a shallow MultiGraph copy
 # would otherwise mutate the same nested dictionaries in basegraph.
 for u,v,k,d in updates:
  if g.has_edge(u,v,k):g.remove_edge(u,v,key=k)
  g.add_edge(u,v,key=k,**d)
 return g

def travel_values(g,src,cellnodes):
    if not src:return np.full(len(cellnodes),np.nan)
    dist=nx.multi_source_dijkstra_path_length(g,src,weight='travel_time_min')
    return np.array([dist.get(int(n),np.nan) for n in cellnodes],dtype=float)

def access(vals,pop):
    valid=np.isfinite(vals);total=float(pop.sum());row={'population_total':total,'population_finite':float(pop[valid].sum()),'population_unreachable':float(pop[~valid].sum()),'mean_travel_reachable_min':float(np.average(vals[valid],weights=pop[valid])) if valid.any() else np.nan,'median_travel_reachable_min':float(np.median(vals[valid])) if valid.any() else np.nan}
    for t in [30,60,120,240]:row['share_'+str(t)+'min_pct']=100*pop[valid&(vals<=t)].sum()/total
    return row

def weighted_gini(vals,pop):
    v=np.asarray(vals,float);w=np.asarray(pop,float);k=np.isfinite(v)&np.isfinite(w)&(w>0)
    if k.sum()<2:return np.nan
    v,w=v[k],w[k];order=np.argsort(v);v,w=v[order],w[order]
    cw=np.cumsum(w)/w.sum();cy=np.cumsum(v*w)/np.sum(v*w)
    dw=np.diff(np.r_[0,cw]);dy=np.diff(np.r_[0,cy])
    return float(1.0-np.sum(dw*(2*cy-dy)))

def concentration(outcome,pop):
    y=np.asarray(outcome,float);w=np.asarray(pop,float);k=np.isfinite(y)&np.isfinite(w)&(w>0)
    if k.sum()<3:return np.nan
    y,w=y[k],w[k];order=np.argsort(w);y,w=y[order],w[order];rw=np.cumsum(w)/w.sum();ry=np.cumsum(y*w)/np.sum(y*w);return float(2*np.sum((rw-np.r_[0,rw[:-1]])*((ry+np.r_[0,ry[:-1]])/2))-1)

def smod_classes(xy):
    # xy is EPSG:4326 lon/lat; convert to GHS Mollweide and sample nearest pixel.
    with rasterio.open(GHS) as src:
        transformed=np.column_stack(warp_transform(4326,src.crs,xy[:,0],xy[:,1]))
        rows,cols=rasterio.transform.rowcol(src.transform,transformed[:,0],transformed[:,1]);out=np.full(len(xy),np.nan)
        for i,(r,c) in enumerate(zip(rows,cols)):
            if 0<=r<src.height and 0<=c<src.width:out[i]=src.read(1,window=rasterio.windows.Window(c,r,1,1))[0,0]
        return out

def process(iso):
    out=OUTBASE/iso.lower();marker=out/'.complete'
    if marker.exists():print(iso+' already complete',flush=True);return
    out.mkdir(parents=True,exist_ok=True)
    roads=gpd.read_file(noded_path(iso))
    facilities={'health':facility_sets(iso,'health'),'education':facility_sets(iso,'education')}
    print(iso+' loaded '+str(len(roads))+' segments',flush=True)
    # Build M3 first for shared node index and population assignment.
    graphs={}
    graphs['m3_class_surface_width']=build_graph(roads,'m3_class_surface_width')
    nodes,tree=graph_index(graphs['m3_class_surface_width'])
    sources={s:{v:source_nodes(facilities[s][v],nodes,tree) for v in facilities[s]} for s in facilities}
    xy,xy3857,pop=base.load_population(iso);_,idx=tree.query(xy3857);cells=nodes[idx]
    smod=smod_classes(xy);urban=np.isin(smod,[21,22,23,30]);rural=np.isin(smod,[11,12,13])
    print(iso+' graph '+str(graphs['m3_class_surface_width'].number_of_nodes())+' nodes / '+str(graphs['m3_class_surface_width'].number_of_edges())+' edges',flush=True)
    # Experiment 6 corrected: model ablation with official-union facilities.
    ab=[]
    if (out/'experiment_06_corrected.csv').exists():
        print(iso+' experiment 06 corrected already saved; skipping',flush=True)
    else:
      for model in MODELS:
        if model not in graphs:
            print(iso+' building '+model,flush=True);graphs[model]=build_graph(roads,model)
        for service,variants in sources.items():
            for facility_variant,src in variants.items():
                for scenario in ['baseline','surface_aware']:
                    g=scenario_graph(graphs[model],roads,scenario);vals=travel_values(g,src,cells);ab.append({'experiment':6,'model':model,'facility_variant':facility_variant,'service':service,'scenario':scenario,**access(vals,pop)})
        print(iso+' completed '+model,flush=True)
    if ab:
        pd.DataFrame(ab).to_csv(out/'experiment_06_corrected.csv',index=False,encoding='utf-8-sig')
    # Experiment 8 corrected: hazard rules, M3 and union facilities.
    rules=[]
    if (out/'experiment_08_corrected.csv').exists():
        print(iso+' experiment 08 corrected already saved; skipping',flush=True)
    else:
      for service,variants in sources.items():
        for facility_variant,src in variants.items():
            for scenario in SCENARIOS:
                g=scenario_graph(graphs['m3_class_surface_width'],roads,scenario);vals=travel_values(g,src,cells);rules.append({'experiment':8,'facility_variant':facility_variant,'service':service,'scenario':scenario,**access(vals,pop)})
    if rules:
        pd.DataFrame(rules).to_csv(out/'experiment_08_corrected.csv',index=False,encoding='utf-8-sig')
    # Corrected cell-level M3 values for experiments 15/17, using registry union.
    cellrows=[];urban_rows=[];ineq=[];quintiles=[]
    for service,variants in sources.items():
        src=variants.get('registry_union',variants['osm'])
        vals_by_scenario={}
        for scenario in ['baseline','no_unpaved','surface_aware']:
            g=scenario_graph(graphs['m3_class_surface_width'],roads,scenario);vals=travel_values(g,src,cells);vals_by_scenario[scenario]=vals
            row={'service':service,'scenario':scenario,**access(vals,pop),'gini_reachable':weighted_gini(vals,pop),'gini_censored_999':weighted_gini(np.where(np.isfinite(vals),vals,999),pop)}
            ineq.append(row)
            for label,mask in [('urban',urban),('rural',rural),('unknown',~(urban|rural))]:
                if mask.any():urban_rows.append({'service':service,'scenario':scenario,'group':label,'population_cells':int(mask.sum()),**access(vals[mask],pop[mask])})
            # Population-density quintiles (population is also density because cells are ~1 km).
            try:q=pd.qcut(pd.Series(pop),5,labels=False,duplicates='drop').to_numpy()
            except Exception:q=np.ones(len(pop),dtype=int)
            for qi in np.unique(q):
                m=q==qi
                if m.any():quintiles.append({'service':service,'scenario':scenario,'density_quintile':int(qi)+1,'population_cells':int(m.sum()),**access(vals[m],pop[m])})
            # Save a compact cell table with identifiers rather than full geometries.
            cellrows.append(pd.DataFrame({'lon':xy[:,0],'lat':xy[:,1],'population':pop,'smod':smod,'service':service,'scenario':scenario,'travel_time_min':vals}))
        baseline=vals_by_scenario['baseline'];hazard=vals_by_scenario['surface_aware'];extra=np.where(np.isfinite(hazard),hazard,999)-np.where(np.isfinite(baseline),baseline,999)
        ineq.extend([{'service':service,'scenario':'concentration_baseline','concentration_index_population_density':concentration(baseline,pop)},{'service':service,'scenario':'concentration_hazard_extra','concentration_index_population_density':concentration(extra,pop)}])
    pd.concat(cellrows,ignore_index=True).to_csv(out/'corrected_cell_travel_times.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(urban_rows).to_csv(out/'experiment_15_corrected.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(ineq).to_csv(out/'experiment_17_corrected_summary.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(quintiles).to_csv(out/'experiment_17_corrected_density_quintiles.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([{'country':base.COUNTRIES[iso],'iso3':iso,'segments':len(roads),'nodes':graphs['m3_class_surface_width'].number_of_nodes(),'edges':graphs['m3_class_surface_width'].number_of_edges(),'facility_variants':{s:list(v) for s,v in facilities.items()},'urban_cells':int(urban.sum()),'rural_cells':int(rural.sum())}]).to_json(out/'inventory.json',orient='records',indent=2)
    marker.write_text('complete\n',encoding='utf-8');print(iso+' COMPLETE',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--countries',nargs='+',default=['PAK','MOZ','BGD','ETH','KEN','PHL','COL']);a=ap.parse_args()
    for iso in a.countries:process(iso)
if __name__=='__main__':main()
