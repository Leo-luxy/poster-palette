import argparse, itertools, re
import numpy as np
import pandas as pd
from matplotlib.colors import rgb_to_hsv
from c_adv_common import ROOT, GROUPS, setup, load, rgb_to_lab, write_manifest

CLASSES=['dark','neutral']+[f'h{i}' for i in range(12)]
def calculate(x,c):
    n=len(x); result=pd.DataFrame({'id':x.id})
    rgb=np.full((n,3,3),np.nan)
    for j in range(3):
        for i,v in enumerate(x[f'dom{j+1}']):
            if isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',v): rgb[i,j]=[int(v[k:k+2],16)/255 for k in (1,3,5)]
    hsv=rgb_to_hsv(rgb); hsv[:,:,0]*=360; lab=rgb_to_lab(rgb)
    shares=x[['ds1','ds2','ds3']].apply(pd.to_numeric,errors='coerce').to_numpy(float)
    share_valid=np.isfinite(shares).all(axis=1)&(shares>=0).all(axis=1)&(shares.sum(axis=1)>0)
    norm=np.full_like(shares,np.nan); norm[share_valid]=shares[share_valid]/shares[share_valid].sum(axis=1)[:,None]
    for j in range(3):
        for k,name in enumerate(['h','s','v']): result[f'dom{j+1}_{name}']=hsv[:,j,k]
        for k,name in enumerate(['l','a','b']): result[f'dom{j+1}_{name}']=lab[:,j,k]
    result['secondary_share']=norm[:,1]
    valid_rgb=np.isfinite(rgb[:,:2,:]).all(axis=(1,2))
    de_valid=valid_rgb & share_valid & (norm[:,1]>=c['pair_min_secondary_share'])
    hue_valid=de_valid & (hsv[:,:2,1]>=c['pair_min_s']).all(axis=1)&(hsv[:,:2,2]>=c['pair_min_v']).all(axis=1)
    gap=np.abs(hsv[:,0,0]-hsv[:,1,0]); result['pair_hue_gap_deg']=np.where(hue_valid,np.minimum(gap,360-gap),np.nan)
    result['pair_delta_e76']=np.where(de_valid,np.linalg.norm(lab[:,0,:]-lab[:,1,:],axis=1),np.nan)
    for j,label in enumerate(['primary','secondary']):
        hh=hsv[:,j,0]; ok=np.isfinite(hh); bins=np.full(n,-1,dtype=int); bins[ok]=(np.floor(hh[ok]/30).astype(int)%12)
        result[f'{label}_hue_bin']=pd.array(np.where(hue_valid,bins,np.nan),dtype='Int64')
        cls=np.full(n,None,dtype=object)
        for i in np.flatnonzero(ok): cls[i]='dark' if hsv[i,j,2]<.2 else 'neutral' if hsv[i,j,1]<.2 else f'h{bins[i]}'
        result[f'{label}_class14']=cls
    h=x[[f'h{i}' for i in range(12)]].to_numpy(float); valid=np.isfinite(h).all(axis=1)&(h>=0).all(axis=1)&(h.sum(axis=1)>0)&(x.sat_frac.to_numpy()>=c['hue_min_fraction']); normh=np.zeros_like(h); normh[valid]=h[valid]/h[valid].sum(axis=1)[:,None]
    for alpha in [c['warmth_anchor_deg'],*c['warmth_alternatives_deg']]: result[f'warmth_{alpha}']=np.where(valid,normh@np.cos(np.deg2rad((np.arange(12)+.5)*30-alpha)),np.nan)
    result['pair_hue_valid']=hue_valid; result['pair_delta_e_valid']=de_valid; result['warmth_valid']=valid
    result['status']=np.where(~valid_rgb,'invalid_color',np.where(~share_valid,'invalid_shares',np.where(~de_valid,'secondary_below_threshold','ok')))
    return result

def cooccurrence(x,r):
    df=x[['id','decade','year','country_main']].merge(r,on='id',validate='one_to_one'); rows=[]
    sets=[('time',str(g),f) for g,f in df.groupby('decade',sort=True)]+[('country',g,df[df.year.between(2001,2025)&(df.country_main==g)]) for g in GROUPS]
    for dim,group,f in sets:
        for kind,classes,ordered in [('class14',CLASSES,False),('hue12',[f'h{i}' for i in range(12)],False)]+([('class14',CLASSES,True)] if dim=='time' else []):
            # 14-class uses valid colors and shares, without imposing secondary-share threshold.
            if kind=='class14':
                valid=f.primary_class14.notna()&f.secondary_class14.notna()&f.secondary_share.notna(); a=f.loc[valid,'primary_class14']; b=f.loc[valid,'secondary_class14']
            else:
                valid=f.pair_hue_valid; a='h'+f.loc[valid,'primary_hue_bin'].astype(str); b='h'+f.loc[valid,'secondary_hue_bin'].astype(str)
            order={v:i for i,v in enumerate(classes)}; counts={}
            for aa,bb in zip(a,b):
                if not ordered and order[aa]>order[bb]: aa,bb=bb,aa
                counts[(aa,bb)]=counts.get((aa,bb),0)+1
            pairs=itertools.product(classes,repeat=2) if ordered else itertools.combinations_with_replacement(classes,2)
            for aa,bb in pairs:
                count=counts.get((aa,bb),0); rows.append(dict(dimension=dim,group=group,matrix_kind=kind,ordered=ordered,class_a=aa,class_b=bb,n_pair=count,n_valid_movies=int(valid.sum()),joint_probability=count/valid.sum() if valid.sum() else np.nan,n_total=len(f)))
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--config',default=str(ROOT/'outputs/c/scripts/c_adv_config.json')); args=p.parse_args()
    out,c,manifest=setup(args.run_id,args.config); x=load(out); r=calculate(x,c); r.to_csv(out/'relations.csv',index=False); co=cooccurrence(x,r); co.to_csv(out/'cooccurrence.csv',index=False)
    refs=[]
    for (dim,kind,ordered,aa,bb), f in co.groupby(['dimension','matrix_kind','ordered','class_a','class_b'],sort=True):
        if dim=='country':
            reference=f.joint_probability.mean() if len(f)==7 and f.joint_probability.notna().all() else np.nan; policy='country_group_equal'
        else:
            n=f.n_valid_movies.sum(); reference=f.n_pair.sum()/n if n else np.nan; policy='time_movie_equal'
        refs.append(dict(dimension=dim,matrix_kind=kind,ordered=ordered,class_a=aa,class_b=bb,joint_probability=reference,reference_scope=policy,n_valid_movies=int(f.n_valid_movies.sum()),n_groups=int(f.joint_probability.notna().sum())))
    pd.DataFrame(refs).to_csv(out/'cooccurrence_reference.csv',index=False)
    ref_weights=[]
    unique=co.drop_duplicates(['dimension','group','matrix_kind','ordered'])
    for (dim,kind,ordered), frame in unique.groupby(['dimension','matrix_kind','ordered']):
        complete=(frame.n_valid_movies>0).all() and (dim!='country' or len(frame)==7); total=frame.n_valid_movies.sum()
        for row in frame.itertuples():
            weight=(1/7 if dim=='country' else row.n_valid_movies/total) if complete and total else np.nan
            ref_weights.append(dict(dimension=dim,group=row.group,matrix_kind=kind,ordered=ordered,n_valid=row.n_valid_movies,group_weight=weight,reference_scope='country_group_equal' if dim=='country' else 'time_movie_equal'))
    pd.DataFrame(ref_weights).to_csv(out/'cooccurrence_reference_weights.csv',index=False)
    manifest['stages']['c06']={'rows':len(r),'invalid_color':int((r.status=='invalid_color').sum()),'invalid_shares':int((r.status=='invalid_shares').sum()),'pair_hue_valid':int(r.pair_hue_valid.sum()),'pair_delta_e_valid':int(r.pair_delta_e_valid.sum()),'warmth_valid':int(r.warmth_valid.sum())}; write_manifest(out,manifest)
    print(manifest['stages']['c06'])
if __name__=='__main__': main()
