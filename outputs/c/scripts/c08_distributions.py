import argparse,itertools
import numpy as np
import pandas as pd
from c_adv_common import ROOT,GROUPS,setup,load,write_manifest

def boot(a,rng,reps):
    return np.array([rng.choice(a,len(a),replace=True).mean() for _ in range(reps)]) if len(a) else np.full(reps,np.nan)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--config',default=str(ROOT/'outputs/c/scripts/c_adv_config.json')); a=p.parse_args(); out,c,manifest=setup(a.run_id,a.config); x=load(out)
    for name in ['relations','spatial_features']: x=x.merge(pd.read_csv(out/(name+'.csv')),on='id',validate='one_to_one',suffixes=('','_'+name))
    metrics=list(dict.fromkeys(c['extended_features']+['warmth_15','warmth_45','center_edge_s','top_bottom_s','left_right_v','left_right_s','v_p10','v_p50','v_p90','v_skew','lab_a_mean','lab_b_mean','secondary_share']))
    frames={'time':{str(k):v for k,v in x.groupby('decade')},'country':{g:x[x.year.between(2001,2025)&(x.country_main==g)] for g in GROUPS}}
    summaries=[]; thresholds=[]; tails=[]; contrasts=[]; refs=[]; weights=[]; labboot=[]; coverage=[]; country_boot=[]; rng=np.random.default_rng(c['seed']); reps=c['bootstrap_repeats']
    for dim,groups in frames.items():
        for metric in metrics:
            vals={g:pd.to_numeric(f[metric],errors='coerce').to_numpy(float) for g,f in groups.items()}; vals={g:v[np.isfinite(v)] for g,v in vals.items()}; boots={g:boot(v,rng,reps) for g,v in vals.items()}
            for g,v in vals.items():
                n=len(v); q=np.percentile(v,[10,25,50,75,90]) if n else [np.nan]*5; ci=np.percentile(boots[g],[2.5,97.5]) if n else [np.nan]*2
                summaries.append(dict(dimension=dim,group=g,metric=metric,n_total=len(groups[g]),n_valid=n,mean=v.mean() if n else np.nan,median=q[2],q1=q[1],q3=q[3],p10=q[0],p90=q[4],p90_p10=q[4]-q[0],iqr=q[3]-q[1],mean_ci_low=ci[0],mean_ci_high=ci[1]))
                coverage.append(dict(dimension=dim,group=g,metric=metric,n_total=len(groups[g]),n_valid=n,n_excluded=len(groups[g])-n,reason='missing_or_nonfinite'))
            if dim=='time':
                z=np.concatenate(list(vals.values())); w=np.full(len(z),1/len(z)); scope='time_movie_equal'
            elif all(len(v)>0 for v in vals.values()):
                z=np.concatenate(list(vals.values())); w=np.concatenate([np.full(len(v),1/(7*len(v))) for v in vals.values()]); scope='country_group_equal'
                for g,v in vals.items(): weights.append(dict(feature_set_or_metric=metric,group=g,n_valid=len(v),group_weight=1/7,per_movie_weight=1/(7*len(v))))
            else: z=np.array([]); w=np.array([]); scope='country_group_equal'
            if len(z):
                ix=np.argsort(z,kind='stable'); zs=z[ix]; ws=w[ix]; cum=np.cumsum(ws); lo,hi=(np.quantile(z,[.1,.9]) if dim=='time' else [zs[min(np.searchsorted(cum,q),len(zs)-1)] for q in [.1,.9]]); mu=np.sum(z*w); sd=np.sqrt(np.sum(w*(z-mu)**2))
            else: lo=hi=mu=sd=np.nan
            thresholds.append(dict(dimension=dim,metric=metric,reference_n=len(z),threshold_p10=lo,threshold_p90=hi,equal_p10=int((z==lo).sum()),equal_p90=int((z==hi).sum())))
            refs.append(dict(dimension=dim,metric=metric,reference_scope=scope,weight_policy=scope,n_valid=len(z),n_groups=len(vals),mean=mu,sd=sd))
            for g,v in vals.items():
                n=len(v); low=int((v<lo).sum()); high=int((v>hi).sum()); mid=n-low-high
                tails.append(dict(dimension=dim,group=g,metric=metric,n_valid=n,low_n=low,middle_n=mid,high_n=high,low_share=low/n if n else np.nan,middle_share=mid/n if n else np.nan,high_share=high/n if n else np.nan))
            pairs=[('2010','1950'),('2020','2010')] if dim=='time' else list(itertools.combinations(GROUPS,2))
            def add(ga,gb,kind,est,bv,nb):
                ci=np.percentile(bv,[2.5,97.5]) if np.isfinite(bv).all() else [np.nan,np.nan]
                contrasts.append(dict(dimension=dim,group_a=ga,group_b=gb,metric=metric,contrast_kind=kind,estimate_kind='mean_difference',estimate=est,ci_low=ci[0],ci_high=ci[1],n_a=len(vals[ga]),n_b=nb,reference_scope=scope,weight_policy=scope,comparison_family=dim))
            for ga,gb in pairs: add(ga,gb,'pairwise',vals[ga].mean()-vals[gb].mean() if len(vals[ga]) and len(vals[gb]) else np.nan,boots[ga]-boots[gb],len(vals[gb]))
            if dim=='country' and all(len(v) for v in vals.values()):
                center=np.mean([v.mean() for v in vals.values()]); joint=np.mean(np.stack(list(boots.values())),axis=0)
                for g in GROUPS:
                    add(g,'ALL7_EQUAL','deviation_from_equal_group_mean',vals[g].mean()-center,boots[g]-joint,sum(len(v) for v in vals.values()))
                    country_boot.extend(dict(metric=metric,group=g,replicate=i,group_mean=boots[g][i],equal_group_mean=joint[i],deviation=boots[g][i]-joint[i]) for i in range(reps))
    for g,f in frames['country'].items():
        v=f[['lab_a_mean','lab_b_mean']].dropna().to_numpy(); n=len(v)
        for rep in range(reps):
            sample=v[rng.integers(0,n,n)] if n else np.empty((0,2)); mean=sample.mean(axis=0) if n else [np.nan,np.nan]; labboot.append(dict(group=g,replicate=rep,n_joint=n,lab_a_mean=mean[0],lab_b_mean=mean[1]))
    membership=pd.read_csv(out/'genre_membership.csv',dtype={'genre_id':str}); linked=x[['id','year','country_main','spatial_valid','pair_delta_e_valid','pair_hue_valid','warmth_valid']].merge(membership,on='id',how='left',validate='one_to_many')
    for dim,subset in [('time',linked),('country',linked[linked.year.between(2001,2025)&linked.country_main.isin(GROUPS)])]:
        subset=subset.copy(); subset['period']=np.select([subset.year.between(2001,2010),subset.year.between(2011,2020),subset.year.between(2021,2025)],['2001-2010','2011-2020','2021-2025'],default='other'); subset['group']=np.where(dim=='country',subset.country_main,(subset.year//10*10).astype(str))
        for (group,period,genre),f in subset.groupby(['group','period','genre_id'],dropna=False):
            for metric in ['spatial_valid','pair_delta_e_valid','pair_hue_valid','warmth_valid']:
                valid=int(f[metric].fillna(False).astype(bool).sum()); coverage.append(dict(dimension=dim,group=group,period=period,genre_id=genre,metric=metric,n_total=len(f),n_valid=valid,n_excluded=len(f)-valid,reason='module_invalid'))
    for name,rows in [('group_summary',summaries),('tail_thresholds',thresholds),('tail_shares',tails),('advanced_contrasts',contrasts),('standardization_reference',refs),('country_reference_weights',weights),('lab_mean_bootstrap',labboot),('coverage',coverage),('country_deviation_bootstrap',country_boot)]: pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    manifest['stages']['c08']={'rows':len(x),'metrics':len(metrics)}; write_manifest(out,manifest)
if __name__=='__main__': main()
