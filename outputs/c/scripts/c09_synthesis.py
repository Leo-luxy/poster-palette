import argparse,itertools,json
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage,fcluster
from c_adv_common import ROOT,GROUPS,setup,load,write_manifest

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--config',default=str(ROOT/'outputs/c/scripts/c_adv_config.json')); a=p.parse_args(); out,c,manifest=setup(a.run_id,a.config); x=load(out)
 for name in ['relations','spatial_features']: x=x.merge(pd.read_csv(out/(name+'.csv')),on='id',validate='one_to_one',suffixes=('','_'+name))
 scores=[]; loads=[]; variances=[]; weights=[]; scalers={}; profiles=[]; corrs=[]; support=[]; distances=[]; summary=[]; boots=[]; stability=[]; matrices={}; genre_support=[]; genre_results=[]; genre_summary=[]; rng=np.random.default_rng(c['seed']); reps=c['bootstrap_repeats']
 for feature_set in ['base','extended']:
  features=c[feature_set+'_features']
  for dim in ['time','country']:
   z=x if dim=='time' else x[x.year.between(2001,2025)&x.country_main.isin(GROUPS)]
   z=z.dropna(subset=features).copy(); arr=z[features].to_numpy(float); counts=z.country_main.value_counts(); w=np.full(len(z),1/len(z)) if dim=='time' else np.array([1/(7*counts[g]) for g in z.country_main]); scope='time_movie_equal' if dim=='time' else 'country_group_equal'
   if dim=='country' and any(g not in counts for g in GROUPS): raise ValueError('A country group has no complete cases')
   mu=np.sum(arr*w[:,None],axis=0); sd=np.sqrt(np.sum(w[:,None]*(arr-mu)**2,axis=0)); keep=sd>1e-12; kept=np.array(features)[keep]; zz=(arr[:,keep]-mu[keep])/sd[keep]; _,sing,vt=np.linalg.svd(np.sqrt(w[:,None])*zz,full_matrices=False); pc=zz@vt.T; ratio=sing**2/np.sum(sing**2)
   scalers[feature_set+'_'+dim]={'model_scope':scope,'features':features,'kept_features':kept.tolist(),'zero_sd_features':np.array(features)[~keep].tolist(),'mean':mu.tolist(),'sd':sd.tolist(),'n':len(z)}
   for i,row in enumerate(z.itertuples()):
    scores.append(dict(id=row.id,feature_set=feature_set,model_scope=scope,group=str(row.decade) if dim=='time' else row.country_main,**{f'PC{j+1}':pc[i,j] for j in range(pc.shape[1])})); weights.append(dict(id=row.id,feature_set=feature_set,model_scope=scope,group=str(row.decade) if dim=='time' else row.country_main,weight=w[i]))
   for k,f in enumerate(kept):
    for j in range(len(sing)): loads.append(dict(feature_set=feature_set,model_scope=scope,component=j+1,metric=f,loading=vt[j,k]))
   for j,v in enumerate(ratio): variances.append(dict(feature_set=feature_set,model_scope=scope,component=j+1,explained_variance_ratio=v))
   cov=(zz*w[:,None]).T@zz; corr=cov/np.sqrt(np.outer(np.diag(cov),np.diag(cov)))
   for i,fa in enumerate(kept):
    for j,fb in enumerate(kept): corrs.append(dict(feature_set=feature_set,model_scope=scope,metric_a=fa,metric_b=fb,r=corr[i,j],high_correlation=i!=j and abs(corr[i,j])>.8))
   labels=z.decade.astype(str).to_numpy() if dim=='time' else z.country_main.to_numpy()
   for group in sorted(set(labels)):
    selected=zz[labels==group]
    for metric,value in zip(kept,selected.mean(axis=0)): profiles.append(dict(feature_set=feature_set,model_scope=scope,group=group,metric=metric,mean_standardized=value,n=len(selected)))
   if dim!='country': continue
   membership=pd.read_csv(out/'genre_membership.csv',dtype={'genre_id':str}); genre_lists=membership.groupby('id').genre_id.agg(set).to_dict(); genre_ids=sorted(membership.genre_id.unique()); all_periods=[('2001-2010',2001,2010),('2011-2020',2011,2020),('2021-2025',2021,2025)]; idarr=z.id.to_numpy(); years=z.year.to_numpy(); common=[]
   for genre in genre_ids:
    observed=[]
    for pr,start,end in all_periods:
     for g in GROUPS:
      mask=(labels==g)&(years>=start)&(years<=end); n=sum(genre in genre_lists.get(i,set()) for i in idarr[mask]); observed.append(n); genre_support.append(dict(feature_set=feature_set,genre_id=genre,period=pr,group=g,n=n,min_support=5))
    if min(observed)>=5: common.append(genre)
   overall_boot_sums=np.zeros((reps,len(GROUPS),len(kept))); overall_boot_counts=np.zeros(len(GROUPS),dtype=int)
   for period,start,end in [('2001-2010',2001,2010),('2011-2020',2011,2020),('2021-2025',2021,2025)]:
    masks={g:(labels==g)&z.year.between(start,end).to_numpy() for g in GROUPS}; data={g:zz[masks[g]] for g in GROUPS}; membership_arrays={g:np.array([[int(genre in genre_lists.get(i,set())) for genre in common] for i in idarr[masks[g]]],dtype=float).reshape(len(data[g]),len(common)) for g in GROUPS}; ok={g:len(v)>=c['group_period_min_n'] for g,v in data.items()}
    for g in GROUPS: support.append(dict(feature_set=feature_set,period=period,group=g,n=len(data[g]),supported=ok[g]))
    pairs=list(itertools.combinations(GROUPS,2)); samples=[]; values={}; matrix=np.full((7,7),np.nan)
    for gi,g in enumerate(GROUPS): overall_boot_counts[gi]+=len(data[g])
    def distance(aa,bb): return np.sum((aa.mean(axis=0)-bb.mean(axis=0))**2)-np.var(aa,axis=0,ddof=1).sum()/len(aa)-np.var(bb,axis=0,ddof=1).sum()/len(bb)
    for ga,gb in pairs:
     val=distance(data[ga],data[gb]) if ok[ga] and ok[gb] else np.nan; values[(ga,gb)]=val; matrix[GROUPS.index(ga),GROUPS.index(gb)]=matrix[GROUPS.index(gb),GROUPS.index(ga)]=val
    matrices[feature_set+'_'+period]=matrix
    allboots={pair:[] for pair in pairs}; agg=[]; genre_boot={pair:[] for pair in pairs}; genre_agg=[]; clusters={(k,ga,gb):0 for k in [2,3] for ga,gb in pairs}
    def adjusted(v,member):
     if not len(common) or not len(v) or (member.sum(axis=0)==0).any(): return None
     weight=(member/member.sum(axis=0)).mean(axis=1); mean=weight@v; denom=1-np.sum(weight**2)
     if denom<=0: return None
     varmean=np.sum((weight[:,None]**2)*(v-mean)**2)/denom
     return mean,varmean
    def adjusted_d(a,b): return np.sum((a[0]-b[0])**2)-a[1]-b[1]
    original_adj={g:adjusted(data[g],membership_arrays[g]) for g in GROUPS}; adjusted_values={pair:adjusted_d(original_adj[pair[0]],original_adj[pair[1]]) if ok[pair[0]] and ok[pair[1]] and original_adj[pair[0]] is not None and original_adj[pair[1]] is not None else np.nan for pair in pairs}
    for rep in range(reps):
     sampled={g:rng.integers(0,len(v),len(v)) for g,v in data.items() if len(v)}; res={g:data[g][i] for g,i in sampled.items()};
     for gi,g in enumerate(GROUPS):
      if g in res: overall_boot_sums[rep,gi]+=res[g].sum(axis=0)
     adj={g:adjusted(res[g],membership_arrays[g][i]) for g,i in sampled.items()}; current=[]; current_adj=[]
     for pair in pairs:
      ga,gb=pair; av=adjusted_d(adj[ga],adj[gb]) if ok[ga] and ok[gb] and ga in adj and gb in adj and adj[ga] is not None and adj[gb] is not None else np.nan; genre_boot[pair].append(av); current_adj.append(av)
     genre_agg.append(np.mean(current_adj) if np.isfinite(current_adj).all() else np.nan)
     for ga,gb in pairs:
      val=distance(res[ga],res[gb]) if ok[ga] and ok[gb] and ga in res and gb in res else np.nan; allboots[(ga,gb)].append(val); boots.append(dict(feature_set=feature_set,period=period,replicate=rep,pair_or_summary=ga+'|'+gb,estimate=val)); current.append(val)
     av=np.mean(current) if np.isfinite(current).all() else np.nan; agg.append(av); boots.append(dict(feature_set=feature_set,period=period,replicate=rep,pair_or_summary='global_heterogeneity_index',estimate=av))
     if len(res)==7 and all(ok.values()):
      tree=linkage(np.stack([res[g].mean(axis=0) for g in GROUPS]),method='average',metric='euclidean')
      for k in [2,3]:
       lab=fcluster(tree,k,criterion='maxclust')
       for ga,gb in pairs: clusters[(k,ga,gb)]+=int(lab[GROUPS.index(ga)]==lab[GROUPS.index(gb)])
    for ga,gb in pairs:
     bv_adj=np.array(genre_boot[(ga,gb)]); valid_adj=bv_adj[np.isfinite(bv_adj)]; ci_adj=np.percentile(valid_adj,[2.5,97.5]) if len(valid_adj)==reps else [np.nan,np.nan]; genre_results.append(dict(feature_set=feature_set,period=period,group_a=ga,group_b=gb,common_genres='|'.join(common),bias_corrected_squared_distance=adjusted_values[(ga,gb)],ci_low=ci_adj[0],ci_high=ci_adj[1],valid_replicates=len(valid_adj),method='equal_common_genre_mixture_multilabel'))
     bv=np.array(allboots[(ga,gb)]); ci=np.percentile(bv,[2.5,97.5]) if np.isfinite(bv).all() else [np.nan,np.nan]; distances.append(dict(feature_set=feature_set,period=period,group_a=ga,group_b=gb,n_a=len(data[ga]),n_b=len(data[gb]),bias_corrected_squared_distance=values[(ga,gb)],ci_low=ci[0],ci_high=ci[1]))
     for k in [2,3]: stability.append(dict(feature_set=feature_set,period=period,k=k,group_a=ga,group_b=gb,same_cluster_frequency=clusters[(k,ga,gb)]/reps if all(ok.values()) else np.nan))
    genre_valid=np.asarray(genre_agg)[np.isfinite(genre_agg)]; genre_ci=np.percentile(genre_valid,[2.5,97.5]) if len(genre_valid)==reps else [np.nan,np.nan]; genre_summary.append(dict(feature_set=feature_set,period=period,common_genres='|'.join(common),global_heterogeneity_index=np.mean(list(adjusted_values.values())) if all(np.isfinite(list(adjusted_values.values()))) else np.nan,ci_low=genre_ci[0],ci_high=genre_ci[1],valid_replicates=len(genre_valid),method='equal_common_genre_mixture_multilabel')); ci=np.percentile(agg,[2.5,97.5]) if np.isfinite(agg).all() else [np.nan,np.nan]; summary.append(dict(feature_set=feature_set,period=period,global_heterogeneity_index=np.mean(list(values.values())) if all(ok.values()) else np.nan,ci_low=ci[0],ci_high=ci[1],n_pairs=sum(np.isfinite(list(values.values())))))
   if all(overall_boot_counts):
    overall_cluster={(k,ga,gb):0 for k in [2,3] for ga,gb in itertools.combinations(GROUPS,2)}
    for rep in range(reps):
     tree=linkage(overall_boot_sums[rep]/overall_boot_counts[:,None],method='average',metric='euclidean')
     for k in [2,3]:
      lab=fcluster(tree,k,criterion='maxclust')
      for ga,gb in itertools.combinations(GROUPS,2): overall_cluster[(k,ga,gb)]+=int(lab[GROUPS.index(ga)]==lab[GROUPS.index(gb)])
    for (k,ga,gb),count in overall_cluster.items(): stability.append(dict(feature_set=feature_set,period='2001-2025',k=k,group_a=ga,group_b=gb,same_cluster_frequency=count/reps))
 for name,rows in [('pca_scores',scores),('pca_loadings',loads),('pca_variance',variances),('pca_reference_weights',weights),('profiles',profiles),('correlations',corrs),('period_support',support),('pairwise_period_distance',distances),('convergence_summary',summary),('convergence_bootstrap',boots),('cluster_stability',stability),('genre_common_support',genre_support),('genre_adjusted_distances',genre_results),('genre_adjusted_summary',genre_summary)]: pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
 np.savez_compressed(out/'pairwise_period_matrices.npz',**matrices); (out/'scaler.json').write_text(json.dumps(scalers,indent=2),encoding='utf8'); manifest['stages']['c09']={'complete_cases':{k:v['n'] for k,v in scalers.items()}}; write_manifest(out,manifest)
if __name__=='__main__': main()
