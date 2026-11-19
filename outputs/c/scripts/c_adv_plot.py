import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from scipy.stats import chi2
from c_adv_common import ROOT,GROUPS,setup,load

plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','PingFang SC','Arial Unicode MS','DejaVu Sans'],'axes.unicode_minus':False,'savefig.facecolor':'white'})
NAMES={'US':'美国','GB':'英国','FR':'法国','IT':'意大利','JP':'日本','ZH':'华语组','KR':'韩国'}

def main():
 p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--config',default=str(ROOT/'outputs/c/scripts/c_adv_config.json')); p.add_argument('--figures',default='all'); a=p.parse_args(); out,c,_=setup(a.run_id,a.config); dest=ROOT/'figures/c/advanced'/a.run_id; dest.mkdir(parents=True,exist_ok=True)
 x=load(out).merge(pd.read_csv(out/'relations.csv'),on='id',validate='one_to_one').merge(pd.read_csv(out/'spatial_features.csv'),on='id',validate='one_to_one',suffixes=('','_spatial'))
 windows=[]
 for y in range(1952,2024):
  f=x[x.year.between(y-2,y+2)]; row={'year':y}
  for alpha in [15,30,45]: row[f'warmth_{alpha}']=f[f'warmth_{alpha}'].mean(); row[f'n_{alpha}']=f[f'warmth_{alpha}'].notna().sum()
  windows.append(row)
 ww=pd.DataFrame(windows); ww.to_csv(out/'warmth_window_summary.csv',index=False)
 fig,(ax,bx)=plt.subplots(2,1,figsize=(10,9),constrained_layout=True); ax.plot(ww.year,ww.warmth_30,color='black',label='30°'); ax.plot(ww.year,ww.warmth_15,'--',label='15°'); ax.plot(ww.year,ww.warmth_45,'--',label='45°'); ax.fill_between(ww.year,0,ww.warmth_30,where=ww.warmth_30>=0,color='orange',alpha=.3); ax.fill_between(ww.year,0,ww.warmth_30,where=ww.warmth_30<0,color='cyan',alpha=.3); ax.axhline(0,color='gray',lw=.5); ax.set(xlabel='上映年份',ylabel='色相余弦投影',title='冷暖投影五年窗口均值'); ax.legend()
 lab=pd.read_csv(out/'lab_mean_bootstrap.csv'); statuses=[]
 for g in GROUPS:
  f=x[x.year.between(2001,2025)&(x.country_main==g)][['lab_b_mean','lab_a_mean']].dropna(); b=lab[lab.group==g][['lab_b_mean','lab_a_mean']].dropna(); center=f.mean().to_numpy(); marker=bx.scatter(*center,label=f'{NAMES[g]} (n={len(f)})'); cov=np.cov(b.to_numpy().T); eig,vec=np.linalg.eigh(cov); status='ok' if np.isfinite(eig).all() and (eig>0).all() else 'singular'
  if status=='ok':
   angle=np.degrees(np.arctan2(vec[1,1],vec[0,1])); width,height=2*np.sqrt(chi2.ppf(.95,2)*eig[::-1]); bx.add_patch(Ellipse(center,width,height,angle=angle,fill=False,linewidth=.8,edgecolor=marker.get_facecolor()[0]))
  statuses.append({'group':g,'n_joint':len(f),'ellipse_status':status})
 pd.DataFrame(statuses).to_csv(out/'lab_ellipse_status.csv',index=False); bx.legend(fontsize=9,ncol=2); bx.set(xlabel='b* 均值（蓝—黄）',ylabel='a* 均值（绿—红）',title='国家／地区组 Lab 色度均值与 95% 置信椭圆'); fig.savefig(dest/'fig_q2_q4_warmth.png',dpi=300); plt.close(fig)
 summary=pd.read_csv(out/'convergence_summary.csv'); data=np.load(out/'pairwise_period_matrices.npz'); periods=['2001-2010','2011-2020','2021-2025']
 z=summary[summary.feature_set=='base'].set_index('period').loc[periods]; fig,axs=plt.subplots(1,4,figsize=(15,4),constrained_layout=True); ax=axs[0]; positions=np.arange(3); ax.errorbar(positions,z.global_heterogeneity_index,yerr=np.array([z.global_heterogeneity_index-z.ci_low,z.ci_high-z.global_heterogeneity_index]),fmt='o-',capsize=3); ax.set_xticks(positions,periods,rotation=25); ax.set_xlim(-.4,2.4); ax.set_ylabel('偏差校正平方距离'); ax.set_title('21 对国家组平均距离');
 mats=[data['base_'+period] for period in periods]; finite=np.concatenate([m[np.isfinite(m)] for m in mats]); vmin,vmax=finite.min(),finite.max()
 glabels=[NAMES[g] for g in GROUPS]
 for ax,m,period in zip(axs[1:],mats,periods):
  image=ax.imshow(m,vmin=vmin,vmax=vmax,cmap='viridis'); ax.set_xticks(range(7),glabels,rotation=45); ax.set_yticks(range(7),glabels); ax.set_title(period)
 fig.colorbar(image,ax=axs[1:],label='偏差校正平方距离'); fig.savefig(dest/'fig_q4_convergence.png',dpi=300); plt.close(fig)
 from c_adv_plot_extra import render_extra
 render_extra(out,dest,x,c)
 from c_adv_publish import publish
 publish(out,dest,x,c)
if __name__=='__main__': main()
