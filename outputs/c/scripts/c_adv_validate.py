from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from c_adv_common import ROOT, OUT, GROUPS

def validate(run_id):
 if not run_id or not all(c.isalnum() or c in '-_' for c in run_id): raise ValueError('Invalid run ID')
 out=OUT/'tables/advanced'/run_id; figs=ROOT/'figures/c/advanced'/run_id; results=[]
 def check(name,ok): results.append((name,bool(ok)))
 files=['manifest.json','relations.csv','cooccurrence.csv','spatial_features.csv','image_audit.csv','spatial_maps.npz','spatial_maps_index.csv','group_summary.csv','tail_thresholds.csv','tail_shares.csv','advanced_contrasts.csv','standardization_reference.csv','country_reference_weights.csv','lab_mean_bootstrap.csv','coverage.csv','pca_scores.csv','pca_loadings.csv','pca_variance.csv','scaler.json','pca_reference_weights.csv','period_support.csv','pairwise_period_distance.csv','pairwise_period_matrices.npz','convergence_summary.csv','convergence_bootstrap.csv','cluster_stability.csv','artifact_index.csv','spot_check_selection.csv','spot_check_audit.csv','spatial_map_residuals.npz','cooccurrence_top_pairs.csv']
 for f in files: check('file '+f,(out/f).is_file())
 for f in ['fig_q2_relations.png','fig_q4_relations.png','fig_q2_spatial.png','fig_q4_spatial.png','fig_q2_distributions.png','fig_q4_distributions.png','fig_q2_fingerprint.png','fig_q4_fingerprint.png','fig_q4_convergence.png','fig_q2_q4_warmth.png','fig_spot_check_cards.png','fig_q2_q4_contrasts_forest.png']:
  path=figs/f; check('figure '+f,path.exists())
  if path.exists(): check('300 dpi '+f,abs(Image.open(path).info.get('dpi',(0,0))[0]-300)<1)
 if (out/'relations.csv').exists():
  d=pd.read_csv(out/'relations.csv'); check('relations covers unique baseline IDs',len(d)==19694 and d.id.is_unique)
 if (out/'spatial_features.csv').exists():
  d=pd.read_csv(out/'spatial_features.csv'); check('spatial covers unique baseline IDs',len(d)==19694 and d.id.is_unique)
 if (out/'cooccurrence.csv').exists():
  d=pd.read_csv(out/'cooccurrence.csv'); groups=d.groupby(['dimension','group','matrix_kind','ordered']); check('cooccurrence sums',all(np.isclose(g.joint_probability.sum(),1) if g.n_valid_movies.iloc[0]>0 else g.joint_probability.isna().all() for _,g in groups))
 if (out/'tail_shares.csv').exists():
  d=pd.read_csv(out/'tail_shares.csv'); d=d[d.n_valid>0]; check('tail shares sum to one',np.allclose(d.low_share+d.middle_share+d.high_share,1))
 if (out/'advanced_contrasts.csv').exists():
  d=pd.read_csv(out/'advanced_contrasts.csv'); d=d[(d.dimension=='country')&(d.contrast_kind=='deviation_from_equal_group_mean')]; check('equal-group deviations sum to zero',not d.empty and all(len(g)==7 and np.isclose(g.estimate.sum(),0,atol=1e-10) for _,g in d.groupby('metric')))
 from c_adv_checks import run_checks
 for label,ok in run_checks(out): check(label,ok)
 report='# Advanced validation\n\n'+''.join(f'- [{"x" if ok else " "}] {name}\n' for name,ok in results); out.mkdir(parents=True,exist_ok=True); (out/'validation_report.md').write_text(report,encoding='utf8'); print(report)
 if not all(ok for _,ok in results): raise SystemExit(1)
