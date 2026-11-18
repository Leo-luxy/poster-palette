from pathlib import Path
import hashlib, subprocess, sys, argparse
from c_adv_common import OUT

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); a=p.parse_args()
 if not all(c.isalnum() or c in '-_' for c in a.run_id): raise ValueError('Invalid run ID')
 out=OUT/'tables/advanced'/a.run_id; names=['group_summary.csv','tail_thresholds.csv','tail_shares.csv','advanced_contrasts.csv','country_deviation_bootstrap.csv','lab_mean_bootstrap.csv','pca_scores.csv','pca_loadings.csv','pca_variance.csv','pairwise_period_distance.csv','convergence_summary.csv','convergence_bootstrap.csv','cluster_stability.csv','genre_adjusted_summary.csv']
 def digest(n): return hashlib.sha256((out/n).read_bytes()).hexdigest()
 before={n:digest(n) for n in names}; log=[]
 for script in ['c08_distributions.py','c09_synthesis.py']:
  r=subprocess.run([sys.executable,'outputs/c/scripts/'+script,'--run-id',a.run_id],capture_output=True,text=True,encoding='utf8',errors='replace'); log.append(f'{script}: exit {r.returncode}\n{r.stdout}\n{r.stderr}')
  if r.returncode: break
 after={n:digest(n) for n in names}; okay=before==after and all('exit 0' in i for i in log) and len(log)==2
 log.extend(f'{n}: {"match" if before[n]==after[n] else "DIFFERENT"}' for n in names); log.append('REPRODUCIBLE: '+('YES' if okay else 'NO')); (out/'reproducibility_log.txt').write_text('\n'.join(log)+'\n',encoding='utf8'); print(log[-1])
 if not okay: raise SystemExit(1)
if __name__=='__main__': main()
