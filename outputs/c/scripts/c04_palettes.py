"""Select a reproducible example per group and abstract its poster colours."""
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import gaussian_filter, label, binary_dilation
from c_common import ROOT, OUT, TABLES, GROUPS, METRICS, load_safe
from c_plot import NAMES

HUES=[f'h{i}' for i in range(12)]

def select_example(group, dimension, key):
    """Choose the poster closest to group medians and mean hue composition."""
    features=group[METRICS].to_numpy(dtype=float)
    hues=group[HUES].to_numpy(dtype=float)
    valid=np.isfinite(features).all(axis=1) & np.isfinite(hues).all(axis=1)
    valid &= (hues>=0).all(axis=1) & (hues.sum(axis=1)>0) & (group.sat_frac.to_numpy()>=.10)
    sample=group.loc[valid].copy()
    features=features[valid]; hues=hues[valid]
    if len(sample)<30: raise ValueError(f'{dimension}/{key}: 可用样本不足 30')
    hues=hues/hues.sum(axis=1,keepdims=True)
    median=np.median(features,axis=0)
    iqr=np.percentile(features,75,axis=0)-np.percentile(features,25,axis=0)
    iqr[iqr==0]=1
    metric_distance=np.mean(((features-median)/iqr)**2,axis=1)
    hue_distance=np.abs(hues-hues.mean(axis=0)).sum(axis=1)/2
    sample['selection_score']=metric_distance+hue_distance**2
    sample['metric_distance']=metric_distance
    sample['hue_distance']=hue_distance
    ranked=sample.sort_values(['selection_score','id'])
    selected=next((r for _,r in ranked.iterrows() if (ROOT/'data'/'posters'/f'{r.id}.jpg').is_file()),None)
    if selected is None: raise ValueError(f'{dimension}/{key}: 未找到海报图片')
    poster=ROOT/'data'/'posters'/f'{selected.id}.jpg'
    return {'dimension':dimension,'group':str(key),'n_total':len(group),'n_candidates':len(sample),
            'id':int(selected.id),'title':selected.title,'year':int(selected.year),
            'selection_score':selected.selection_score,'metric_distance':selected.metric_distance,
            'hue_distance':selected.hue_distance,'poster_sha256':hashlib.sha256(poster.read_bytes()).hexdigest()}

def abstract_poster(id):
    """Simplify a poster into smooth, contiguous fields in their original positions."""
    with Image.open(ROOT/'data'/'posters'/f'{id}.jpg') as source:
        source=source.convert('RGB')
        source=source.crop((0,0,source.width,int(source.height*.88)))
        source=source.resize((120,160),Image.Resampling.BOX)
        softened=gaussian_filter(np.asarray(source,dtype=float),sigma=(6,6,0))
        image=Image.fromarray(np.clip(softened,0,255).astype(np.uint8)).quantize(colors=7,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
        labels=np.asarray(image,dtype=np.uint8)
        # Smooth each colour's local support independently; the winning mask
        # merges tiny details into contiguous regions without rearranging them.
        support=np.stack([gaussian_filter((labels==i).astype(float),sigma=3) for i in range(7)],axis=-1)
        # Consolidate into a coarse square grid, then absorb isolated one- or
        # two-cell components into their most common neighbouring colour.
        grid=support.reshape(10,16,8,15,7).mean(axis=(1,3)).argmax(axis=-1)
        for _ in range(3):
            changed=False
            for color in range(7):
                components,count=label(grid==color)
                for component in range(1,count+1):
                    region=components==component
                    if region.sum()>=3: continue
                    neighbours=grid[binary_dilation(region)&~region]
                    if len(neighbours):
                        grid[region]=np.bincount(neighbours,minlength=7).argmax(); changed=True
            if not changed: break
        simplified=grid
        palette=image.getpalette()
        colors=['#%02x%02x%02x' % tuple(palette[i*3:i*3+3]) for i in range(7)]
        shares=np.bincount(simplified.ravel(),minlength=7)/simplified.size
        output=np.asarray(palette[:21],dtype=np.uint8).reshape(7,3)[simplified]
        return Image.fromarray(output),colors,shares

def draw(rows,dimension,ppt=False):
    fig=plt.figure(figsize=(16,9) if ppt else (13,11),layout=None if ppt else 'constrained')
    grid=fig.add_gridspec(2,4,left=.04,right=.96,bottom=.10,top=.84,wspace=.16,hspace=.20) if ppt else fig.add_gridspec(2,4)
    title='全球各上映年代海报的典型配色组合' if dimension=='time' else '各国家/地区组电影海报的典型配色组合'
    fig.suptitle(title if dimension=='time' else title+'\n2001-2025',fontsize=21 if ppt else 16,fontweight='bold')
    for i,r in enumerate(rows):
        ax=fig.add_subplot(grid[i//4,i%4]); ax.axis('off')
        group=r['group']
        label=('2020—2025' if group=='2020' else group+'年代') if dimension=='time' else NAMES[group]
        ax.set_title(label,fontsize=16 if ppt else 12,loc='left',pad=7)
        image,_,_=abstract_poster(r['id'])
        ax.imshow(image,interpolation='nearest',aspect='equal')
    if len(rows)<8: fig.add_subplot(grid[1,3]).axis('off')
    note_options={'y':.025} if ppt else {}
    fig.supxlabel('每幅图简化自该组一张海报，不代表组内全部海报。',fontsize=13 if ppt else 10,color='#5c6268',**note_options)
    target=OUT/'ppt' if ppt else ROOT/'figures'/'c'; target.mkdir(parents=True,exist_ok=True)
    fig.savefig(target/('fig_q2_palettes.png' if dimension=='time' else 'fig_q4_palettes.png'),dpi=150 if ppt else 300)
    plt.close(fig)

def main():
    x=load_safe().merge(pd.read_csv(TABLES/'country_group.csv',keep_default_na=False)[['id','country_main']],on='id',validate='one_to_one')
    recent=x[x.year.between(2001,2025)]
    time=[select_example(x[x.decade==d],'time',d) for d in range(1950,2030,10)]
    country=[select_example(recent[recent.country_main==g],'country',g) for g in GROUPS]
    for row in time+country:
        _,colors,shares=abstract_poster(row['id'])
        for i,(color,share) in enumerate(zip(colors,shares),1):
            row[f'color{i}']=color; row[f'share{i}']=share
    pd.DataFrame(time+country).to_csv(TABLES/'palette_examples.csv',index=False,encoding='utf-8')
    manifest={'selection':'mean squared IQR-scaled distance to group metric medians + squared hue total variation distance to group mean; ties by id',
              'selection_hue_min_sat_frac':.10,'crop_bottom_fraction':.12,'quantized_colors':7,'source_blur_sigma':6,'region_smoothing_sigma':3,'grid_columns':8,'grid_rows':10,'minimum_component_cells':3,'layout':'square-edged simplified poster colour fields',
              'posters_sha256':{str(r['id']):r['poster_sha256'] for r in time+country},'input_manifest':'run_manifest.json'}
    (OUT/'palette_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    draw(time,'time'); draw(country,'country'); draw(time,'time',ppt=True); draw(country,'country',ppt=True)
    print('Completed 8 decade and 7 country abstract poster palettes.')
if __name__=='__main__': main()
