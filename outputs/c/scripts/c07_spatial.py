import argparse, hashlib, io, json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import skew
from c_adv_common import ROOT, OUT, GROUPS, setup, load, rgb_to_lab, sha, write_manifest

def extract(im,c):
    im=im.convert('RGB'); im=im.crop((0,0,im.width,int(im.height*(1-c['crop_bottom'])))).resize(tuple(c['image_size_wh']),getattr(Image.Resampling,c['image_resample']))
    rgb=np.asarray(im,dtype=float)/255; hsv=np.asarray(im.convert('HSV'),dtype=float); s=hsv[:,:,1]/255; v=hsv[:,:,2]/255; lab=rgb_to_lab(rgb); h,w=v.shape
    d={}; grids=[]
    for r in range(3):
        line=[]
        for col in range(3):
            ys=slice(r*h//3,(r+1)*h//3); xs=slice(col*w//3,(col+1)*w//3); vv=v[ys,xs]; ss=s[ys,xs]; ll=lab[ys,xs]; prefix=f'grid_r{r}c{col}_'
            d.update({prefix+'v':vv.mean(),prefix+'s':ss.mean(),prefix+'color_fraction':(ss>=c['hue_pixel_min_s']).mean()}); line.append(ll.mean(axis=(0,1)))
        grids.append(line)
    cw=int(w*np.sqrt(c['center_area_fraction'])); ch=int(h*np.sqrt(c['center_area_fraction'])); x=(w-cw)//2; y=(h-ch)//2; mask=np.zeros((h,w),bool); mask[y:y+ch,x:x+cw]=True
    d['center_actual_area_fraction']=mask.mean()
    for name,arr in [('v',v),('s',s)]:
        d[f'center_edge_{name}']=arr[mask].mean()-arr[~mask].mean(); d[f'top_bottom_{name}']=arr[:h//3].mean()-arr[2*h//3:].mean(); d[f'left_right_{name}']=arr[:,:w//3].mean()-arr[:,2*w//3:].mean()
    for r in range(3): d[f'left_right_delta_e76_r{r}']=np.linalg.norm(grids[r][0]-grids[r][2])
    d['left_right_delta_e76']=np.mean([d[f'left_right_delta_e76_r{r}'] for r in range(3)])
    d.update(dict(zip(['v_p10','v_p50','v_p90'],np.percentile(v,[10,50,90])))); d['v_skew']=skew(v.ravel()) if np.ptp(v)>0 else np.nan
    d['lab_a_mean']=lab[:,:,1].mean(); d['lab_b_mean']=lab[:,:,2].mean(); d['vivid_frac']=((s>c['vivid_min_s'])&(v>c['vivid_min_v'])).mean()
    maps={name:np.asarray(Image.fromarray(arr.astype(np.float32),mode='F').resize(tuple(c['heatmap_size_wh']),Image.Resampling.BOX),dtype=np.float32) for name,arr in [('v',v),('s',s)]}
    return d,maps

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--config',default=str(ROOT/'outputs/c/scripts/c_adv_config.json')); p.add_argument('--mode',choices=['smoke','full'],required=True); p.add_argument('--limit',type=int); p.add_argument('--resume',action='store_true'); a=p.parse_args()
    if a.limit and a.mode!='smoke': p.error('--limit is only valid for smoke')
    out,c,manifest=setup(a.run_id,a.config); dest=out/'smoke' if a.mode=='smoke' else out; dest.mkdir(exist_ok=True); x=load(dest); x=x.head(a.limit or 100) if a.mode=='smoke' else x
    cache=OUT/'cache/advanced'; cache.mkdir(parents=True,exist_ok=True); config_key=json.dumps({k:c[k] for k in ['crop_bottom','image_size_wh','image_resample','heatmap_size_wh','hue_pixel_min_s','center_area_fraction','vivid_min_s','vivid_min_v']},sort_keys=True).encode(); rows=[]; maps=[]; audits=[]
    for row in x.itertuples():
        path=ROOT/'data/posters'/f'{row.id}.jpg'; d={}; grids=None; status='ok'
        if not path.is_file(): status='missing_file'
        else:
            key=hashlib.sha256((sha(path)).encode()+config_key).hexdigest(); cp=cache/(key+'.npz')
            try:
                if a.resume and cp.exists():
                    with np.load(cp,allow_pickle=False) as z: d=json.loads(str(z['features'])); grids={'v':z['v'],'s':z['s']}
                else:
                    with Image.open(path) as im: d,grids=extract(im,c)
                    np.savez_compressed(cp,features=json.dumps(d),**grids)
                if not all(np.isfinite(g).all() for g in grids.values()): status='invalid_pixels'; d={}; grids=None
            except (OSError,ValueError) as e: status='decode_error'; audits.append({'id':row.id,'status':status,'detail':str(e)})
        if status!='ok' and status!='decode_error': audits.append({'id':row.id,'status':status,'detail':''})
        rows.append({'id':row.id,'spatial_valid':status=='ok','status':status,**d}); maps.append(grids)
    pd.DataFrame(rows).to_csv(dest/'spatial_features.csv',index=False); pd.DataFrame(audits,columns=['id','status','detail']).to_csv(dest/'image_audit.csv',index=False)
    arrays={}; index=[]
    for dim,group,mask in [('time',str(g),x.decade==g) for g in sorted(x.decade.unique())]+[('country',g,x.year.between(2001,2025)&(x.country_main==g)) for g in GROUPS]:
        indices=np.flatnonzero(mask.to_numpy()); valid=[maps[i] for i in indices if maps[i] is not None]
        if not valid: continue
        for metric in ['v','s']:
            stack=np.stack([z[metric] for z in valid]); prefix=f'{dim}_{group}_{metric}'
            for stat,arr in [('mean',np.mean(stack,axis=0)),('median',np.median(stack,axis=0)),('std',np.std(stack,axis=0)),('n',np.full(stack.shape[1:],len(stack),dtype=np.int32))]: arrays[prefix+'_'+stat]=arr
            index.append({'dimension':dim,'group':group,'metric':metric,'array_prefix':prefix,'n_valid':len(valid),'n_total':len(indices)})
    np.savez_compressed(dest/'spatial_maps.npz',**arrays); pd.DataFrame(index).to_csv(dest/'spatial_maps_index.csv',index=False)
    manifest['stages']['c07_'+a.mode]={'rows':len(rows),'failures':len(audits)}; write_manifest(out,manifest); print(manifest['stages']['c07_'+a.mode])
if __name__=='__main__': main()
