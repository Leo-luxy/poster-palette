import colorsys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from c_common import ROOT, OUT, TABLES, GROUPS, METRICS

plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','PingFang SC','Arial Unicode MS','DejaVu Sans'],'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'font.size':11,'savefig.facecolor':'white'})
COLORS=[colorsys.hsv_to_rgb((i+.5)/12,.68,.88) for i in range(12)]
NAMES={'US':'美国','GB':'英国','FR':'法国','IT':'意大利','JP':'日本','ZH':'华语组','KR':'韩国'}
LABELS={'mean_v':'明度','mean_s':'饱和度','colorful':'色彩丰富度'}

def hue(ax, rows, labels):
    left=np.zeros(len(rows)); y=np.arange(len(rows))
    for i,c in enumerate(COLORS):
        v=np.where(rows.n_hue.to_numpy() >= 30, rows[f'h{i}'].to_numpy()*100, 0)
        ax.barh(y,v,left=left,color=c,height=.66); left+=v
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlim(0,100); ax.set_xlabel('平均色相占比（%）'); ax.set_xticks([0,25,50,75,100]); ax.spines[['top','right','left']].set_visible(False); ax.tick_params(axis='y',length=0)
    ax.legend([Patch(color=COLORS[i]) for i in [0,1,4,6,7,9]],['红','黄','绿','青','蓝','紫'],loc='lower center',bbox_to_anchor=(.5,1.01),ncol=6,frameon=False,fontsize='small')

def metric_time(ax,m,annual):
    z=annual.dropna(subset=[f'{m}_window_median']); xx=z.year.to_numpy()
    ax.fill_between(xx,z[f'{m}_window_q1'].to_numpy(),z[f'{m}_window_q3'].to_numpy(),color='#66849a',alpha=.22)
    ax.plot(xx,z[f'{m}_window_median'],color='#345a73',lw=2); ax.set_title(LABELS[m],loc='left',fontweight='bold'); ax.grid(axis='y',alpha=.15); ax.set_xlim(1950,2025); ax.set_xlabel('上映年份')

def metric_country(ax,m,s):
    y=np.arange(len(s)); means=s[f'{m}_mean'].to_numpy(); lo=s[f'{m}_mean_ci_low'].to_numpy(); hi=s[f'{m}_mean_ci_high'].to_numpy()
    ax.errorbar(means,y,xerr=[means-lo,hi-means],fmt='o',color='#345a73',capsize=3,markersize=5,lw=1.3); ax.set_yticks(y,[NAMES[g] for g in GROUPS]); ax.invert_yaxis(); ax.set_title(LABELS[m],loc='left',fontweight='bold'); ax.grid(axis='x',alpha=.15); ax.tick_params(axis='y',length=0)

def make(dim):
    rows=pd.read_csv(TABLES/'hue_summary.csv',dtype={'group':str}); rows=rows[rows.dimension==dim].set_index('group')
    if dim=='time':
        keys=[str(y) for y in range(1950,2030,10)]; rows=rows.loc[keys]; labels=[('2020—2025' if k=='2020' else k+'年代')+f'  (n={int(n):,})' for k,n in zip(keys,rows.n_total)]
        stats=pd.read_csv(TABLES/'time_yearly.csv'); draw=metric_time; title='全球电影海报配色的时间变化'; subtitle='1950—2025 · 色相排除近灰海报；趋势线为中位数，带为片间四分位距'
    else:
        rows=rows.loc[GROUPS]; labels=[NAMES[k]+f'  (n={int(n):,})' for k,n in zip(GROUPS,rows.n_total)]
        stats=pd.read_csv(TABLES/'country_summary.csv').set_index('country_main').loc[GROUPS].reset_index(); draw=metric_country; title='电影海报配色的国家／地区差异'; subtitle='2001—2025 · 色相排除近灰海报；点和区间为均值及逐项 95% CI'
    fig=plt.figure(figsize=(12,10),layout='constrained'); gs=fig.add_gridspec(2,3,height_ratios=[1.15,1]); ax=fig.add_subplot(gs[0,:]); hue(ax,rows,labels)
    for i,m in enumerate(METRICS): draw(fig.add_subplot(gs[1,i]),m,stats)
    fig.suptitle(title+'\n'+subtitle,fontsize=14,fontweight='bold'); path=ROOT/'figures'/('fig_q2_trend.png' if dim=='time' else 'fig_q4_country.png'); fig.savefig(path,dpi=300); plt.close(fig)
    (OUT/'ppt').mkdir(exist_ok=True)
    with plt.rc_context({'font.size':17, 'axes.titlesize':19, 'axes.labelsize':17, 'xtick.labelsize':15, 'ytick.labelsize':15}):
        period='1950—2025' if dim=='time' else '2001—2025'
        fig,ax=plt.subplots(figsize=(16,9),layout='constrained'); hue(ax,rows,labels)
        fig.suptitle(title+'：色相分布\n'+period+' · 排除近灰海报，按电影等权平均',fontsize=20)
        fig.savefig(OUT/'ppt'/('fig_q2_hue.png' if dim=='time' else 'fig_q4_hue.png'),dpi=150); plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(16,9),layout='constrained')
        for ax,m in zip(axes,METRICS[:2]): draw(ax,m,stats)
        note='五年窗口中位数及片间四分位距' if dim=='time' else '均值及逐项 95% CI'
        fig.suptitle(title+'：明度与饱和度\n'+period+' · '+note,fontsize=20)
        fig.savefig(OUT/'ppt'/('fig_q2_metrics.png' if dim=='time' else 'fig_q4_metrics.png'),dpi=150); plt.close(fig)
if __name__=='__main__':
    make('time'); make('country')
