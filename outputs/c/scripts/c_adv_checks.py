import itertools,json
import numpy as np
import pandas as pd
from PIL import Image
from c_adv_common import ROOT,GROUPS,load,sha

def run_checks(out):
 checks=[]
 def check(name,result): checks.append((name,bool(result)))
 manifest=json.loads((out/'manifest.json').read_text(encoding='utf8')); check('input fingerprints unchanged',all(sha(ROOT/path)==value for path,value in manifest['input_sha256'].items())); check('recorded code fingerprints unchanged',bool(manifest.get('code_sha256')) and all(sha(ROOT/path)==value for path,value in manifest['code_sha256'].items())); x=load(out); rel=pd.read_csv(out/'relations.csv'); spatial=pd.read_csv(out/'spatial_features.csv'); co=pd.read_csv(out/'cooccurrence.csv',dtype={'group':str}); data=x.merge(rel,on='id',validate='one_to_one').merge(spatial,on='id',validate='one_to_one',suffixes=('','_spatial')); con=pd.read_csv(out/'advanced_contrasts.csv',dtype={'group_a':str,'group_b':str}); weights=pd.read_csv(out/'country_reference_weights.csv'); weights_pca=pd.read_csv(out/'pca_reference_weights.csv'); scores=pd.read_csv(out/'pca_scores.csv'); variables=pd.read_csv(out/'pca_variance.csv'); sup=pd.read_csv(out/'period_support.csv'); distances=pd.read_csv(out/'pairwise_period_distance.csv'); summaries=pd.read_csv(out/'convergence_summary.csv'); boots=pd.read_csv(out/'convergence_bootstrap.csv'); matrices=np.load(out/'pairwise_period_matrices.npz'); scaler=json.loads((out/'scaler.json').read_text(encoding='utf8')); residual=np.load(out/'spatial_map_residuals.npz');
 check('one-to-one feature joins and independent time/country sample sizes',len(data)==19694 and data.id.is_unique and len(data[data.year.between(2001,2025)&data.country_main.isin(GROUPS)])==10115)
 check('spatial failures retained with IDs',int((~spatial.spatial_valid).sum())==len(pd.read_csv(out/'image_audit.csv')))
 check('country metric reference weights are seven equal groups',all(len(f)==7 and np.allclose(f.group_weight,1/7) and np.isclose((f.per_movie_weight*f.n_valid).sum(),1) for _,f in weights.groupby('feature_set_or_metric')))
 check('country PCA reference weights each group 1/7',all(np.allclose(f.groupby('group').weight.sum().reindex(GROUPS),1/7) for _,f in weights_pca[weights_pca.model_scope=='country_group_equal'].groupby('feature_set')))
 check('PCA country group mean scores centered',all(np.allclose(f.groupby('group')[['PC1','PC2']].mean().mean(axis=0),0,atol=1e-10) for _,f in scores[scores.model_scope=='country_group_equal'].groupby('feature_set')))
 check('PCA explained variance sums to one',all(np.isclose(f.explained_variance_ratio.sum(),1) for _,f in variables.groupby(['feature_set','model_scope'])))
 loadings=pd.read_csv(out/'pca_loadings.csv'); projection_ok=[]
 for key,model in scaler.items():
  fs,dim=key.split('_'); scope=model['model_scope']; kept=model['kept_features']; indices=[model['features'].index(f) for f in kept]; sc=scores[(scores.feature_set==fs)&(scores.model_scope==scope)]; raw=data.set_index('id').loc[sc.id,kept].to_numpy(); standardized=(raw-np.asarray(model['mean'])[indices])/np.asarray(model['sd'])[indices]; ls=loadings[(loadings.feature_set==fs)&(loadings.model_scope==scope)].pivot(index='metric',columns='component',values='loading').loc[kept].to_numpy(); cols=[f'PC{i+1}' for i in range(ls.shape[1])]; projection_ok.append(np.allclose(standardized@ls,sc[cols].to_numpy(),atol=1e-9))
 check('all saved PCA scores equal the standardized projection',all(projection_ok))
 pair=con[(con.dimension=='country')&(con.contrast_kind=='pairwise')]; check('all 21 country pairs per metric',all(len(f)==21 and set(zip(f.group_a,f.group_b))==set(itertools.combinations(GROUPS,2)) for _,f in pair.groupby('metric')))
 main=co[(co.matrix_kind=='class14')&(~co.ordered)]; check('all 105 unordered 14-class cells per group',all(len(f)==105 and f.n_pair.sum()==f.n_valid_movies.iloc[0] for _,f in main.groupby(['dimension','group'])))
 ref=pd.read_csv(out/'cooccurrence_reference.csv'); valid_ref=[]
 for (kind,ordered,ca,cb),f in co[co.dimension=='country'].groupby(['matrix_kind','ordered','class_a','class_b']):
  r=ref[(ref.dimension=='country')&(ref.matrix_kind==kind)&(ref.ordered==ordered)&(ref.class_a==ca)&(ref.class_b==cb)].iloc[0]; valid_ref.append(len(f)==7 and np.isclose(r.joint_probability,f.joint_probability.mean(),equal_nan=True))
 check('cooccurrence country reference equals mean of seven group probabilities',all(valid_ref))
 cb=pd.read_csv(out/'country_deviation_bootstrap.csv'); pivot=cb.pivot(index=['metric','replicate'],columns='group',values='deviation'); center=cb.pivot(index=['metric','replicate'],columns='group',values='group_mean').mean(axis=1); saved_center=cb.groupby(['metric','replicate']).equal_group_mean.first(); check('joint country bootstrap uses the seven means from each same replicate',np.allclose(pivot.sum(axis=1),0,atol=1e-11) and np.allclose(center,saved_center,atol=1e-11)); cidev=[]
 for (metric,group), f in cb.groupby(['metric','group']):
  a=con[(con.dimension=='country')&(con.metric==metric)&(con.group_a==group)&(con.contrast_kind=='deviation_from_equal_group_mean')].iloc[0]; cidev.append(np.allclose([a.ci_low,a.ci_high],np.percentile(f.deviation,[2.5,97.5])))
 check('country deviation intervals use joint bootstrap',all(cidev))
 hue=data[[f'h{i}' for i in range(12)]].to_numpy(float); good=np.isfinite(hue).all(axis=1)&(hue>=0).all(axis=1)&(hue.sum(axis=1)>0)&(data.sat_frac.to_numpy()>=.1); check('warmth validity matches raw hue and saturation rules',np.array_equal(good,data.warmth_valid.to_numpy()))
 check('hue-pair validity implies delta-E validity',(~data.pair_hue_valid|data.pair_delta_e_valid).all())
 thresholds=pd.read_csv(out/'tail_thresholds.csv'); tails=pd.read_csv(out/'tail_shares.csv',dtype={'group':str}); valid_thresholds=[]; valid_tails=[]
 for row in thresholds.itertuples():
  groups=[data[data.year.between(2001,2025)&(data.country_main==g)][row.metric].dropna().to_numpy() for g in GROUPS] if row.dimension=='country' else [data[row.metric].dropna().to_numpy()]
  if all(len(g) for g in groups):
   z=np.concatenate(groups)
   if row.dimension=='time': expected=np.quantile(z,[.1,.9])
   else:
    w=np.concatenate([np.full(len(g),1/(7*len(g))) for g in groups]); order=np.argsort(z,kind='stable'); zs=z[order]; cw=np.cumsum(w[order]); expected=[zs[np.searchsorted(cw,q)] for q in [.1,.9]]
   valid_thresholds.append(np.allclose([row.threshold_p10,row.threshold_p90],expected))
   for t in tails[(tails.dimension==row.dimension)&(tails.metric==row.metric)].itertuples():
    f=data[data.decade.astype(str)==t.group] if row.dimension=='time' else data[data.year.between(2001,2025)&(data.country_main==t.group)]; v=f[row.metric].dropna().to_numpy(); valid_tails.append(t.n_valid==len(v) and t.low_n==(v<expected[0]).sum() and t.high_n==(v>expected[1]).sum() and t.middle_n==len(v)-t.low_n-t.high_n)
 check('fixed time and equal-group thresholds reproducible',all(valid_thresholds)); check('tails use fixed thresholds and valid denominators',all(valid_tails))
 for metric in ['v','s']:
  check('equal-group spatial residual mean zero '+metric,np.allclose(np.stack([residual[f'{metric}_country_group_equal_{g}'] for g in GROUPS]).mean(axis=0),0,atol=1e-6))
 top=pd.read_csv(out/'cooccurrence_top_pairs.csv',dtype={'group':str}); check('fixed top eight plus other sum to one by decade',all(len(f)==9 and f.n_pair.sum()==f.n_valid_movies.iloc[0] and np.isclose(f.share.sum(),1) for _,f in top.groupby('group')))
 classes=['dark','neutral']+[f'h{i}' for i in range(12)]; time_pairs=main[main.dimension=='time'].groupby(['class_a','class_b'],as_index=False).n_pair.sum(); time_pairs['a']=time_pairs.class_a.map({v:i for i,v in enumerate(classes)}); time_pairs['b']=time_pairs.class_b.map({v:i for i,v in enumerate(classes)}); selected=list(map(tuple,time_pairs.sort_values(['n_pair','a','b'],ascending=[False,True,True]).head(8)[['class_a','class_b']].to_numpy())); check('top eight pairs fixed globally with deterministic category tie-break',all(list(zip(f[f.category=='top8'].class_a,f[f.category=='top8'].class_b))==selected for _,f in top.groupby('group')))
 selection=pd.read_csv(out/'spot_check_selection.csv'); audit=pd.read_csv(out/'spot_check_audit.csv'); check('spot selection has eight deterministic extremes and twelve audited random movies',len(selection)==20 and len(audit)==20 and selection.id.is_unique and (audit.review_status=='visually_plausible').all())
 used=set(); chosen=[]
 for category,metric,ascending in [('center_bright','center_edge_v',False),('edge_bright','center_edge_v',True),('left_right_difference','left_right_delta_e76',False),('dominant_pair_difference','pair_delta_e76',False)]:
  ranked=data[data.spatial_valid & data[metric].notna()].sort_values([metric,'id'],ascending=[ascending,True],kind='stable'); found=[]
  for movie in ranked.id:
   if movie not in used: found.append(movie); used.add(movie)
   if len(found)==2: break
  chosen+=found
 check('extreme card selection and tie-breaking reproducible',chosen==selection.id.head(8).tolist())
 random_pool=data[data.spatial_valid&~data.id.isin(used)].sort_values('id'); rng=np.random.default_rng(42); chosen_random=random_pool.iloc[rng.choice(len(random_pool),12,replace=False)].id.tolist(); check('random card audit selection reproducible',chosen_random==selection.id.tail(12).tolist())
 ell=pd.read_csv(out/'lab_ellipse_status.csv'); lb=pd.read_csv(out/'lab_mean_bootstrap.csv'); check('Lab bootstrap uses shared joint sample count',all(r.n_joint==len(data[data.year.between(2001,2025)&(data.country_main==r.group)][['lab_a_mean','lab_b_mean']].dropna()) and (lb[lb.group==r.group].n_joint==r.n_joint).all() for r in ell.itertuples()))
 forest=pd.read_csv(out/'forest_plot_values.csv'); originals=con.merge(pd.read_csv(out/'standardization_reference.csv')[['dimension','metric','sd']],on=['dimension','metric'],validate='many_to_one'); merged=forest.merge(originals,on=['dimension','group_a','group_b','metric'],validate='one_to_one'); check('forest estimates and intervals share the fixed reference SD',len(merged)==54 and np.allclose(merged.standardized_estimate,merged.estimate/merged.sd) and np.allclose(merged.standardized_ci_low,merged.ci_low/merged.sd) and np.allclose(merged.standardized_ci_high,merged.ci_high/merged.sd))
 # Recompute PCA weighted spectrum and distance estimates; permuting country labels must only permute matrix rows/columns.
 pca_ok=[]; permutation_ok=[]; distance_ok=[]; summary_ok=[]; boot_ok=[]; support_ok=[]
 period_map={'2001-2010':(2001,2010),'2011-2020':(2011,2020),'2021-2025':(2021,2025)}
 for fs in ['base','extended']:
  model=scaler[fs+'_country']; feats=model['kept_features']; frame=data[data.year.between(2001,2025)&data.country_main.isin(GROUPS)].dropna(subset=model['features']).copy(); ids=[model['features'].index(f) for f in feats]; z=(frame[feats].to_numpy()-np.array(model['mean'])[ids])/np.array(model['sd'])[ids]; labels=frame.country_main.to_numpy(); counts=frame.country_main.value_counts(); w=np.array([1/(7*counts[g]) for g in labels]); cov=(z*w[:,None]).T@z; eig=np.linalg.eigvalsh(cov)[::-1]; ev=variables[(variables.feature_set==fs)&(variables.model_scope=='country_group_equal')].sort_values('component').explained_variance_ratio.to_numpy(); pca_ok.append(np.allclose(eig/eig.sum(),ev,atol=1e-10)); perm=dict(zip(GROUPS,GROUPS[::-1])); renamed=np.array([perm[g] for g in labels]); wc=np.array([1/(7*np.sum(renamed==g)) for g in renamed]); cov2=(z*wc[:,None]).T@z; permutation_ok.append(np.allclose(np.linalg.eigvalsh(cov),np.linalg.eigvalsh(cov2),atol=1e-10))
  for period,(lo,hi) in period_map.items():
   vals={g:z[(labels==g)&frame.year.between(lo,hi).to_numpy()] for g in GROUPS}; ok={g:len(vals[g])>=30 for g in GROUPS}; sp=sup[(sup.feature_set==fs)&(sup.period==period)].set_index('group'); support_ok.extend(int(sp.loc[g,'n'])==len(vals[g]) and bool(sp.loc[g,'supported'])==ok[g] for g in GROUPS); mat=matrices[fs+'_'+period]; long=distances[(distances.feature_set==fs)&(distances.period==period)]; estimates=[]
   for row in long.itertuples():
    a,b=vals[row.group_a],vals[row.group_b]; expected=np.sum((a.mean(axis=0)-b.mean(axis=0))**2)-np.var(a,axis=0,ddof=1).sum()/len(a)-np.var(b,axis=0,ddof=1).sum()/len(b) if ok[row.group_a] and ok[row.group_b] else np.nan
    i,j=GROUPS.index(row.group_a),GROUPS.index(row.group_b); distance_ok.append(np.isclose(row.bias_corrected_squared_distance,expected,equal_nan=True) and np.isclose(mat[i,j],expected,equal_nan=True) and np.isclose(mat[j,i],expected,equal_nan=True)); estimates.append(expected)
   sr=summaries[(summaries.feature_set==fs)&(summaries.period==period)].iloc[0]; expected=np.mean(estimates) if np.isfinite(estimates).all() else np.nan; summary_ok.append(np.isclose(sr.global_heterogeneity_index,expected,equal_nan=True) and sr.n_pairs==np.isfinite(estimates).sum()); permuted_vals={perm[g]:vals[g] for g in GROUPS}; permutation_ok.append(np.isclose(np.nanmean(mat),np.nanmean(mat[::-1,::-1]),equal_nan=True))
   for row in long.itertuples():
    a=permuted_vals[perm[row.group_a]]; b=permuted_vals[perm[row.group_b]]
    if ok[row.group_a] and ok[row.group_b]: permutation_ok.append(np.isclose(np.sum((a.mean(axis=0)-b.mean(axis=0))**2)-np.var(a,axis=0,ddof=1).sum()/len(a)-np.var(b,axis=0,ddof=1).sum()/len(b),row.bias_corrected_squared_distance))
   b=boots[(boots.feature_set==fs)&(boots.period==period)]; wide=b.pivot(index='replicate',columns='pair_or_summary',values='estimate'); pairs=[q for q in wide.columns if q!='global_heterogeneity_index']; actual=wide[pairs].mean(axis=1,skipna=False); boot_ok.append(len(wide)==1000 and np.allclose(wide.global_heterogeneity_index,actual,equal_nan=True));
   if np.isfinite(actual).all(): boot_ok.append(np.allclose([sr.ci_low,sr.ci_high],np.percentile(actual,[2.5,97.5])))
 check('period support and threshold match complete cases',all(support_ok)); check('weighted SVD variance matches weighted covariance',all(pca_ok)); check('group label permutation preserves spectrum and pairwise aggregate',all(permutation_ok)); check('bias-corrected pair estimates and symmetric matrices',all(distance_ok)); check('heterogeneity uses 21 complete pairs only',all(summary_ok)); check('summary CI comes from joint bootstrap replicates',all(boot_ok))
 figs=ROOT/'figures/c/advanced'/out.name; ppt=ROOT/'outputs/c/ppt/advanced'/out.name
 check('PPT exports are 16:9',all(Image.open(p).width*9==Image.open(p).height*16 for p in ppt.glob('*.png')) and len(list(ppt.glob('*.png')))>0)
 legacy=(out/'legacy_validation_log.txt').read_text(encoding='utf8') if (out/'legacy_validation_log.txt').exists() else ''; check('legacy scripts and both validation stages pass in isolated copy',all(s in legacy for s in ['c01_country_group.py: exit 0','c02_time.py: exit 0','c03_country.py: exit 0','c04_palettes.py: exit 0','c05_comparisons.py: exit 0','validation time: exit 0','validation all: exit 0']))
 check('synthetic tests passed', (out/'synthetic_test_log.txt').exists() and 'Synthetic checks passed' in (out/'synthetic_test_log.txt').read_text(encoding='utf8'))
 check('bootstrap reproducibility verified', (out/'reproducibility_log.txt').exists() and 'REPRODUCIBLE: YES' in (out/'reproducibility_log.txt').read_text(encoding='utf8'))
 check('visual review completed', (out/'visual_review.md').exists())
 return checks
