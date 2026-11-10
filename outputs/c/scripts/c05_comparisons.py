"""Report figures showing the pre-specified differences and their intervals."""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from c_common import ROOT, TABLES, METRICS
from c_plot import LABELS, NAMES

def plot(dimension):
    data=pd.read_csv(TABLES/'contrasts.csv',dtype={'group_a':str,'group_b':str})
    data=data[data.dimension==dimension]
    if dimension=='time':
        groups=['2010','2020']
        labels=['2010—2019 减 1950—1959','2020—2025 减 2010—2019']
        title='全球年代配色差异：预定对比'
    else:
        groups=['GB','FR','IT','JP','ZH','KR']
        labels=[NAMES[g]+' 减 美国' for g in groups]
        title='各国家/地区组与美国的配色差异'
    fig,axes=plt.subplots(1,3,figsize=(13,4.8 if dimension=='time' else 6),layout='constrained')
    fig.suptitle(title,fontsize=16,fontweight='bold')
    for ax,metric in zip(axes,METRICS):
        rows=data[data.metric==metric].set_index('group_a').loc[groups]
        means=rows.mean_difference.to_numpy(); lo=rows.ci_low.to_numpy(); hi=rows.ci_high.to_numpy()
        y=list(range(len(groups)))
        ax.axvline(0,color='#999999',lw=1)
        ax.errorbar(means,y,xerr=[means-lo,hi-means],fmt='o',color='#345a73',capsize=3,lw=1.5,markersize=6)
        ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_title(LABELS[metric],loc='left',fontweight='bold')
        ax.grid(axis='x',color='#d9dfe3',alpha=.55); ax.tick_params(axis='y',length=0)
        ax.set_xlabel('均值差（原单位）' if metric=='colorful' else '均值差（0—1 尺度）')
    caption='点为均值差，横线为逐项 95% 置信区间；2020—2025 并非完整十年。' if dimension=='time' else '2001—2025 · 点为均值差，横线为逐项 95% 置信区间；各组保留实际样本构成。'
    fig.supxlabel(caption,fontsize=10,color='#5c6268')
    target=ROOT/'figures'/'c'; target.mkdir(parents=True,exist_ok=True)
    fig.savefig(target/('fig_q2_comparisons.png' if dimension=='time' else 'fig_q4_comparisons.png'),dpi=300)
    plt.close(fig)

if __name__=='__main__':
    plot('time'); plot('country')
