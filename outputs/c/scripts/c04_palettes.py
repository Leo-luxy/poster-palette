"""Aggregate per-film dominant colours and draw abstract proportional mosaics."""
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv
from c_common import ROOT, OUT, TABLES, GROUPS, load_safe
from c_plot import NAMES

HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

def summarize(g, dimension, label):
    colors=g[['dom1','dom2','dom3']].fillna('').astype(str)
    weights=g[['ds1','ds2','ds3']].to_numpy(dtype=float)
    valid=colors.apply(lambda col: col.map(lambda s: bool(HEX.fullmatch(s)))).all(axis=1).to_numpy().copy()
    valid &= np.isfinite(weights).all(axis=1) & (weights>=0).all(axis=1) & (weights.sum(axis=1)>0)
    weights=weights[valid]
    if len(weights)<30:
        raise ValueError(f'{dimension}/{label}: fewer than 30 usable palettes')
    weights/=weights.sum(axis=1,keepdims=True)
    rgb=np.array([[int(s[i:i+2],16) for i in (1,3,5)] for s in colors.loc[valid].to_numpy().ravel()],dtype=float)
    hsv=rgb_to_hsv(rgb/255)
    bins=np.minimum((hsv[:,0]*12).astype(int),11)+2
    bins[hsv[:,1]<.20]=1
    bins[hsv[:,2]<.20]=0
    w=weights.ravel(); rows=[]
    for bin_id in range(14):
        mask=bins==bin_id
        if not mask.any(): continue
        points=rgb[mask]; pweight=w[mask]
        center=np.average(points,axis=0,weights=pweight)
        # Use an actual upstream colour closest to the weighted centre, rather
        # than inventing a potentially muddy colour by averaging RGB values.
        observed=points[np.argmin(np.sum((points-center)**2,axis=1))].astype(int)
        rows.append({'dimension':dimension,'group':str(label),'n_total':len(g),
                     'n_palette':len(weights),'n_excluded_palette':len(g)-len(weights),
                     'bin_id':bin_id,'bin_label':'dark' if bin_id==0 else 'neutral' if bin_id==1 else f'h{bin_id-2}',
                     'color':'#%02x%02x%02x' % tuple(observed),'share':pweight.sum()/len(weights)})
    return rows

def mosaic(ax, colors, shares, x, y, w, h, depth=0):
    """Recursively divide a rectangle; each colour retains its exact area."""
    if len(colors)==1:
        ax.add_patch(plt.Rectangle((x,y),w,h,facecolor=colors[0],edgecolor='none'))
        return
    weights=np.asarray(shares,dtype=float)
    split=int(np.argmin(abs(np.cumsum(weights)[:-1]-weights.sum()/2)))+1
    fraction=weights[:split].sum()/weights.sum()
    if depth%2==0:
        mosaic(ax,colors[:split],shares[:split],x,y,w*fraction,h,depth+1)
        mosaic(ax,colors[split:],shares[split:],x+w*fraction,y,w*(1-fraction),h,depth+1)
    else:
        mosaic(ax,colors[:split],shares[:split],x,y,w,h*fraction,depth+1)
        mosaic(ax,colors[split:],shares[split:],x,y+h*fraction,w,h*(1-fraction),depth+1)

def draw(rows,dimension):
    fig=plt.figure(figsize=(14,8.8),layout='constrained')
    grid=fig.add_gridspec(2,4)
    title='全球各上映年代的抽象配色组合' if dimension=='time' else '各国家／地区组的抽象配色组合'
    period='1950—2025' if dimension=='time' else '2001—2025'
    fig.suptitle(title+'\n'+period+' · 组内主色按色相和明暗汇总，拼接为抽象色块',fontsize=16,fontweight='bold')
    for i,group in enumerate(rows):
        r=group[0]
        ax=fig.add_subplot(grid[i//4,i%4]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_aspect('equal'); ax.axis('off')
        label=('2020—2025' if r['group']=='2020' else r['group']+'年代') if dimension=='time' else NAMES[r['group']]
        ax.set_title(f"{label}  ·  n={r['n_palette']:,}",fontsize=11,loc='left',pad=7)
        ordered=sorted(group,key=lambda item:(-item['share'],item['bin_id']))
        colors=[item['color'] for item in ordered]
        shares=[item['share'] for item in ordered]
        mosaic(ax,colors,shares,0,0,1,1)
    if len(rows)<8: fig.add_subplot(grid[1,3]).axis('off')
    fig.supxlabel('色块面积表示主色的汇总权重；颜色取自现有主色记录，拼接布局用于展示。',fontsize=10)
    fig.savefig(ROOT/'figures'/('fig_q2_palettes.png' if dimension=='time' else 'fig_q4_palettes.png'),dpi=300)
    plt.close(fig)

def main():
    x=load_safe().merge(pd.read_csv(TABLES/'country_group.csv',keep_default_na=False)[['id','country_main']],on='id',validate='one_to_one')
    recent=x[x.year.between(2001,2025)]
    time=[summarize(x[x.decade==d],'time',d) for d in range(1950,2030,10)]
    country=[summarize(recent[recent.country_main==g],'country',g) for g in GROUPS]
    pd.DataFrame([row for group in time+country for row in group]).to_csv(TABLES/'palette_summary.csv',index=False,encoding='utf-8')
    manifest={'method':'dark_value_lt_0.20, neutral_saturation_lt_0.20, otherwise 12 HSV hue sectors; observed color nearest weighted RGB center', 'upstream_feature_manifest':'run_manifest.json'}
    (OUT/'palette_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    draw(time,'time'); draw(country,'country')
    print('Completed 8 decade mosaics and 7 country mosaics.')

if __name__=='__main__': main()
