import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from PIL import Image, ImageDraw
from scipy.cluster.hierarchy import linkage, dendrogram
from c_adv_common import ROOT,GROUPS

plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','PingFang SC','Arial Unicode MS','DejaVu Sans'],'axes.unicode_minus':False,'savefig.facecolor':'white'})
CLASSES=['dark','neutral']+[f'h{i}' for i in range(12)]
CLASS_LABELS=['暗色','低饱和']+[f'h{i}' for i in range(12)]
CLASS_MAP=dict(zip(CLASSES,CLASS_LABELS))
NAMES={'US':'美国','GB':'英国','FR':'法国','IT':'意大利','JP':'日本','ZH':'华语组','KR':'韩国'}
METRIC_LABELS={'mean_v':'明度','mean_s':'饱和度','colorful':'色彩丰富度','v_std':'明度标准差','pair_delta_e76':'主辅色色差 ΔE76','center_edge_v':'中心减外围明度','top_bottom_v':'上减下明度','left_right_delta_e76':'左右色差 ΔE76','vivid_frac':'高饱和像素占比','pair_hue_gap_deg':'主辅色色相夹角','warmth_30':'冷暖投影 (30°)'}
TIME=[str(n) for n in range(1950,2030,10)]
def display_group(g):
 s=str(g)
 if s in NAMES: return NAMES[s]
 return '2020—2025' if s=='2020' else (s+'年代' if s in TIME else s)
def pair_label(a,b):
 return f'{CLASS_MAP.get(a,a)} + {CLASS_MAP.get(b,b)}' if b else '其余 97 对'
def save(fig,path):
 fig.savefig(path,dpi=300,bbox_inches='tight'); plt.close(fig)
def matrix(f):
 z=np.full((14,14),np.nan)
 for r in f.itertuples():
  i=CLASSES.index(r.class_a); j=CLASSES.index(r.class_b); z[i,j]=r.joint_probability
 return z

def render_extra(out,dest,x,c):
 co=pd.read_csv(out/'cooccurrence.csv',dtype={'group':str}); refs=pd.read_csv(out/'cooccurrence_reference.csv'); summ=pd.read_csv(out/'group_summary.csv',dtype={'group':str}); tail=pd.read_csv(out/'tail_shares.csv',dtype={'group':str}); profiles=pd.read_csv(out/'profiles.csv',dtype={'group':str}); pc=pd.read_csv(out/'pca_scores.csv',dtype={'group':str}); var=pd.read_csv(out/'pca_variance.csv'); maps=np.load(out/'spatial_maps.npz'); idx=pd.read_csv(out/'spatial_maps_index.csv',dtype={'group':str}); dists=pd.read_csv(out/'advanced_contrasts.csv',dtype={'group_a':str,'group_b':str}); std=pd.read_csv(out/'standardization_reference.csv')
 # Fixed time top pairs, with all remaining 97 pairs retained as other.
 base=co[(co.dimension=='time')&(co.matrix_kind=='class14')&(~co.ordered)]; totals=base.groupby(['class_a','class_b'],as_index=False).n_pair.sum(); totals['order_a']=totals.class_a.map({v:i for i,v in enumerate(CLASSES)}); totals['order_b']=totals.class_b.map({v:i for i,v in enumerate(CLASSES)}); totals=totals.sort_values(['n_pair','order_a','order_b'],ascending=[False,True,True],kind='stable'); top=list(map(tuple,totals[['class_a','class_b']].head(8).to_numpy())); top_rows=[]
 for g in TIME:
  f=base[base.group==g]; n=int(f.n_valid_movies.iloc[0]); cnt=[]
  for a,b in top:
   value=int(f[(f.class_a==a)&(f.class_b==b)].n_pair.iloc[0]); cnt.append(value); top_rows.append(dict(group=g,class_a=a,class_b=b,n_pair=value,n_valid_movies=n,share=value/n if n else np.nan,category='top8'))
  top_rows.append(dict(group=g,class_a='OTHER',class_b='',n_pair=n-sum(cnt),n_valid_movies=n,share=(n-sum(cnt))/n if n else np.nan,category='other'))
 pd.DataFrame(top_rows).to_csv(out/'cooccurrence_top_pairs.csv',index=False)
 ticks=[0,1,2,5,8,11,13]; tick_labels=[CLASS_LABELS[i] for i in ticks]
 # Co-occurrence matrices use a single group-equal reference; show all groups on a common scale.
 for dim,groups in [('time',TIME),('country',GROUPS)]:
  source=co[(co.dimension==dim)&(co.matrix_kind=='class14')&(~co.ordered)]; ref=matrix(refs[(refs.dimension==dim)&(refs.matrix_kind=='class14')&(~refs.ordered)])
  diffs=[matrix(source[source.group==g])-ref for g in groups]; vmax=max(np.nanmax(np.abs(m)) for m in diffs)
  fig=plt.figure(figsize=(16,10),constrained_layout=True); grid=fig.add_gridspec(3,4,height_ratios=[1,1,1]); axs=[fig.add_subplot(grid[i//4,i%4]) for i in range(len(groups))]
  for ax,g,m in zip(axs,groups,diffs):
   im=ax.imshow(m,cmap='RdBu_r',vmin=-vmax,vmax=vmax); f=source[source.group==g]; low=matrix(f.assign(joint_probability=np.where(f.n_pair<5,1,np.nan))); yy,xx=np.where(np.isfinite(low)); ax.scatter(xx,yy,s=1.2,c='black',alpha=.45); ax.set_xticks(ticks,tick_labels,rotation=90,fontsize=8); ax.set_yticks(ticks,tick_labels,fontsize=8); ax.set_title(f'{display_group(g)}  (n={int(f.n_valid_movies.iloc[0])})',fontsize=9)
  fig.colorbar(im,ax=axs,shrink=.7,label='联合概率与参照之差'); bottom_grid=grid[2,:].subgridspec(1,2,width_ratios=[2,1]); bottom=fig.add_subplot(bottom_grid[0,0]); side=fig.add_subplot(bottom_grid[0,1]);
  if dim=='time':
   bt=pd.DataFrame(top_rows); bottom_values=[]; bottom_labels=[]
   for pair in top+[('OTHER','')]:
    d=bt[(bt.class_a==pair[0])&(bt.class_b==pair[1])].set_index('group').loc[groups]; bottom_values.append(d.share.to_numpy()); bottom_labels.append(pair_label(*pair))
   stack=np.zeros(len(groups))
   for value,label in zip(bottom_values,bottom_labels): bottom.bar(groups,value,bottom=stack,label=label); stack+=value
   bottom.set_ylim(0,1.0); bottom.set_xticks(range(len(groups)),[display_group(g) for g in groups],rotation=20)
   bottom.set_ylabel('占比'); bottom.legend(ncol=3,fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.28)); bottom.set_title('前八大主辅色对构成')
   vals=[x.loc[x.decade.astype(str)==g,'pair_delta_e76'].dropna().to_numpy() for g in groups]; side.boxplot(vals,tick_labels=[display_group(g) for g in groups],showfliers=False); side.tick_params(axis='x',rotation=30); side.set_ylabel('主辅色色差 ΔE76'); side.set_title('主辅色色差分布')
  else:
   data=[x.loc[x.year.between(2001,2025)&(x.country_main==g),'pair_delta_e76'].dropna().to_numpy() for g in groups]; bottom.boxplot(data,tick_labels=[display_group(g) for g in groups],showfliers=False); bottom.set_ylabel('主辅色色差 ΔE76'); bottom.set_title('主辅色色差分布')
   imref=side.imshow(ref,vmin=0,vmax=np.nanmax(ref),cmap='viridis'); side.set_title('七组等权参照'); side.set_xticks(ticks,tick_labels,rotation=90,fontsize=7); side.set_yticks(ticks,tick_labels,fontsize=7); fig.colorbar(imref,ax=side,shrink=.7)
  fig.suptitle('主辅色共现与色差（年代对比）' if dim=='time' else '主辅色共现与色差（国家／地区对比）',fontsize=13,fontweight='bold'); save(fig,dest/f'fig_q{"2" if dim=="time" else "4"}_relations.png')
 # Spatial maps: same reference IDs and equal-group residuals; retain movie-weighted alternative.
 residual_arrays={}; residual_index=[]
 for metric in ['v','s']:
  means=np.stack([maps[f'country_{g}_{metric}_mean'] for g in GROUPS]); ns=np.array([int(idx[(idx.dimension=='country')&(idx.group==g)&(idx.metric==metric)].n_valid.iloc[0]) for g in GROUPS]); equal=means.mean(axis=0); weighted=np.average(means,axis=0,weights=ns)
  for policy,ref in [('country_group_equal',equal),('country_movie_equal',weighted)]:
   residual_arrays[f'{metric}_{policy}_reference']=ref
   for i,g in enumerate(GROUPS):
    key=f'{metric}_{policy}_{g}'; residual_arrays[key]=means[i]-ref; residual_index.append(dict(metric=metric,group=g,reference=policy,array_key=key,n_valid=ns[i],group_weight=1/7 if policy=='country_group_equal' else ns[i]/ns.sum()))
 np.savez_compressed(out/'spatial_map_residuals.npz',**residual_arrays); pd.DataFrame(residual_index).to_csv(out/'spatial_map_residuals_index.csv',index=False)
 centroids=[]
 for dim,groups in [('time',TIME),('country',GROUPS)]:
  for g in groups:
   f=x[x.decade.astype(str)==g] if dim=='time' else x[x.year.between(2001,2025)&(x.country_main==g)]; f=f[['left_right_delta_e76','top_bottom_v']].dropna(); centroids.append(dict(dimension=dim,group=g,n_joint=len(f),left_right_delta_e76=f.left_right_delta_e76.mean(),top_bottom_v=f.top_bottom_v.mean()))
 pd.DataFrame(centroids).to_csv(out/'spatial_centroids.csv',index=False)
 mname={'v':'明度','s':'饱和度'}
 for dim,groups in [('time',TIME),('country',GROUPS)]:
  rows=4 if dim=='country' else 2; fig,axes=plt.subplots(rows+1,len(groups),figsize=(18,8 if rows==2 else 13),constrained_layout=True)
  for j,g in enumerate(groups):
   for i,metric in enumerate(['v','s']):
    a=axes[i,j]; image=a.imshow(maps[f'{dim}_{g}_{metric}_mean'],vmin=0,vmax=1,cmap='viridis'); a.set_title(f'{display_group(g)} · {mname[metric]}' if i==0 else mname[metric],fontsize=8); a.axis('off')
   if dim=='country':
    for rownum,metric in [(2,'v'),(3,'s')]:
     a=axes[rownum,j]; lim=max(np.abs(residual_arrays[f'{metric}_country_group_equal_{k}']).max() for k in GROUPS); imres=a.imshow(residual_arrays[f'{metric}_country_group_equal_{g}'],vmin=-lim,vmax=lim,cmap='RdBu_r'); a.set_title(f'{mname[metric]}残差',fontsize=8); a.axis('off')
     if j==len(groups)-1: fig.colorbar(imres,ax=list(axes[rownum,:]),shrink=.65,label=f'{mname[metric]}差值')
  # One shared centroid chart occupies the bottom row.
  for a in axes[-1,1:]: a.remove()
  a=axes[-1,0]; spec=a.get_subplotspec(); a.remove(); a=fig.add_subplot(spec.get_gridspec()[-1,:]); cc=pd.DataFrame(centroids); cc=cc[cc.dimension==dim]
  for row in cc.itertuples(): a.scatter(row.left_right_delta_e76,row.top_bottom_v); a.annotate(f' {display_group(row.group)} (n={row.n_joint})',(row.left_right_delta_e76,row.top_bottom_v),fontsize=8,va='center')
  fig.colorbar(image,ax=list(axes[0,:])+list(axes[1,:]),shrink=.6,label='均值 (0—1)')
  a.set(xlabel='左右色差 ΔE76',ylabel='上减下明度',title='各组空间构图中心'); save(fig,dest/f'fig_q{"2" if dim=="time" else "4"}_spatial.png')
 # Distribution: consistent scales and fixed reference tails.
 for dim,groups in [('time',TIME),('country',GROUPS)]:
  fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
  for j,metric in enumerate(['mean_v','mean_s','pair_delta_e76']):
   vals=[]
   for g in groups:
    f=x[x.decade.astype(str)==g] if dim=='time' else x[x.year.between(2001,2025)&(x.country_main==g)]; vals.append(f[metric].dropna().to_numpy())
   axes[0,j].violinplot(vals,showmedians=True,bw_method=.25); axes[0,j].set_xticks(np.arange(1,len(groups)+1),[display_group(g) for g in groups],rotation=30); axes[0,j].set_title(METRIC_LABELS[metric]); axes[0,j].set_ylim((0,1) if metric in ['mean_v','mean_s'] else (0,None))
   t=tail[(tail.dimension==dim)&(tail.metric==metric)].set_index('group').loc[groups]; axes[1,j].bar(groups,t.low_share,label='低于 P10'); axes[1,j].bar(groups,t.high_share,bottom=t.low_share,label='高于 P90'); axes[1,j].set_ylim(0,1); axes[1,j].set_xticks(range(len(groups)),[display_group(g) for g in groups]); axes[1,j].tick_params(axis='x',rotation=30); axes[1,j].set_ylabel('电影占比'); axes[1,j].legend(fontsize=8)
  fig.suptitle('指标分布与两端高／低值占比',fontsize=13,fontweight='bold'); save(fig,dest/f'fig_q{"2" if dim=="time" else "4"}_distributions.png')
 # Profiles and weighted PCA: equal-sized means, uniformly sampled background points.
 for dim,groups,scope in [('time',TIME,'time_movie_equal'),('country',GROUPS,'country_group_equal')]:
  pp=profiles[(profiles.feature_set=='base')&(profiles.model_scope==scope)].pivot(index='group',columns='metric',values='mean_standardized').reindex(groups)[c['base_features']]; p=pc[(pc.feature_set=='base')&(pc.model_scope==scope)]; v=var[(var.feature_set=='base')&(var.model_scope==scope)].sort_values('component'); fig,ax=plt.subplots(1,3,figsize=(16,6),constrained_layout=True)
  im=ax[0].imshow(pp.to_numpy(),aspect='auto',cmap='RdBu_r',vmin=-max(abs(pp.to_numpy().flatten())),vmax=max(abs(pp.to_numpy().flatten()))); ax[0].set_xticks(range(len(pp.columns)),[METRIC_LABELS.get(col,col) for col in pp.columns],rotation=45,ha='right',fontsize=8); ax[0].set_yticks(range(len(groups)),[display_group(g) for g in groups]); fig.colorbar(im,ax=ax[0],label='标准化均值 (SD)'); ax[0].set_title('多维特征画像')
  rng=np.random.default_rng(c['seed']); n=min(100,min((p.group==g).sum() for g in groups))
  for g in groups:
   f=p[p.group==g]; sample=f.iloc[rng.choice(len(f),n,replace=False)]; ax[1].scatter(sample.PC1,sample.PC2,s=5,alpha=.08,color='gray'); ax[1].scatter(f.PC1.mean(),f.PC2.mean(),s=35,label=f'{display_group(g)} (n={len(f)})')
  ax[1].legend(fontsize=7,loc='upper left',ncol=2); ax[1].set(xlabel=f'PC1 ({v.iloc[0].explained_variance_ratio:.1%})',ylabel=f'PC2 ({v.iloc[1].explained_variance_ratio:.1%})',title='主成分投射'); dendrogram(linkage(pp.to_numpy(),method='average'),labels=[display_group(g) for g in groups],orientation='right',ax=ax[2]); ax[2].set_title('组均值层次聚类'); save(fig,dest/f'fig_q{"2" if dim=="time" else "4"}_fingerprint.png')
 # Forest plot uses saved estimates and one fixed reference SD per scene and metric.
 metrics=['mean_v','mean_s','pair_delta_e76','center_edge_v','left_right_delta_e76','warmth_30']; panels=[('time','2010','1950'),('time','2020','2010')]+[('country',g,'ALL7_EQUAL') for g in GROUPS]; fig,axes=plt.subplots(3,3,figsize=(13,10),constrained_layout=True); extent=0; forest=[]
 for ax,(dim,ga,gb) in zip(axes.flat,panels):
  subset=dists[(dists.dimension==dim)&(dists.group_a==ga)&(dists.group_b==gb)].set_index('metric'); ref=std[std.dimension==dim].set_index('metric')
  for i,m in enumerate(metrics):
   if m not in subset.index or m not in ref.index or not ref.loc[m,'sd']>0: continue
   row=subset.loc[m]; sd=ref.loc[m,'sd']; vals=np.array([row.estimate,row.ci_low,row.ci_high])/sd; extent=max(extent,abs(vals[1]),abs(vals[2])); ax.errorbar(vals[0],i,xerr=[[vals[0]-vals[1]],[vals[2]-vals[0]]],fmt='o',capsize=2); forest.append(dict(dimension=dim,group_a=ga,group_b=gb,metric=m,reference_sd=sd,standardized_estimate=vals[0],standardized_ci_low=vals[1],standardized_ci_high=vals[2]))
  ax.axvline(0,color='gray',lw=.6); ax.set_yticks(range(len(metrics)),[METRIC_LABELS[m] for m in metrics],fontsize=8); ax.invert_yaxis()
  tlabel=f'{display_group(ga)} 减 {display_group(gb)}' if dim=='time' else f'{display_group(ga)} 减 七组等权均值'
  ax.set_title(tlabel,fontsize=10,fontweight='bold')
 for ax in axes.flat: ax.set_xlim(-extent*1.1,extent*1.1)
 fig.supxlabel('标准化均值差（单位：参照标准差，95% CI）'); pd.DataFrame(forest).to_csv(out/'forest_plot_values.csv',index=False); save(fig,dest/'fig_q2_q4_contrasts_forest.png')

 # Deterministic extreme selection, deduplicated across categories.
 from PIL import ImageFont
 selection=[]; used=set(); rules=[('center_bright','center_edge_v',False),('edge_bright','center_edge_v',True),('left_right_difference','left_right_delta_e76',False),('dominant_pair_difference','pair_delta_e76',False)]
 for category,metric,ascending in rules:
  rank=x[x.spatial_valid & x[metric].notna()].sort_values([metric,'id'],ascending=[ascending,True],kind='stable')
  for pos,row in enumerate(rank.itertuples(),1):
   if row.id in used: continue
   selection.append(dict(id=row.id,category=category,metric=metric,value=getattr(row,metric),rank=pos,source=f'data/posters/{row.id}.jpg')); used.add(row.id)
   if sum(z['category']==category for z in selection)==2: break
 candidates=x[x.spatial_valid & ~x.id.isin(used)].sort_values('id'); rng=np.random.default_rng(c['seed']); extra=candidates.iloc[rng.choice(len(candidates),12,replace=False)]
 for row in extra.itertuples(): selection.append(dict(id=row.id,category='random_audit',metric='',value=np.nan,rank=np.nan,source=f'data/posters/{row.id}.jpg'))
 selected=pd.DataFrame(selection); selected.to_csv(out/'spot_check_selection.csv',index=False)
 try:
  font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14); small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
 except Exception:
  font=ImageFont.load_default(size=15); small=ImageFont.load_default(size=12)
 cat_labels={'center_bright':'中心亮','edge_bright':'边缘亮','left_right_difference':'左右异色','dominant_pair_difference':'高主辅色差','random_audit':'随机抽检'}
 def card(rec):
  row=x.loc[x.id==rec['id']].iloc[0]; src=Image.open(ROOT/rec['source']).convert('RGB'); src=src.crop((0,0,src.width,int(src.height*(1-c['crop_bottom'])))).resize((120,160),Image.Resampling.BICUBIC).resize((240,320),Image.Resampling.NEAREST); draw=ImageDraw.Draw(src)
  if rec['category'] in ['center_bright','edge_bright']:
   cw=int(120*np.sqrt(c['center_area_fraction'])); ch=int(160*np.sqrt(c['center_area_fraction'])); xx=(120-cw)//2; yy=(160-ch)//2; draw.rectangle((xx*2,yy*2,(xx+cw)*2-1,(yy+ch)*2-1),outline='yellow',width=2)
  elif rec['category']=='left_right_difference':
   for k in [1,2]: draw.line((k*120//3*2,0,k*120//3*2,319),fill='yellow',width=2); draw.line((0,k*160//3*2,239,k*160//3*2),fill='yellow',width=2)
  im=Image.new('RGB',(270,400),'white'); im.paste(src,(15,25)); d=ImageDraw.Draw(im); label=cat_labels.get(rec['category'],rec['category']); d.text((15,3),label,font=font,fill='black')
  if rec['metric']: d.text((15,347),f"{METRIC_LABELS.get(rec['metric'],rec['metric'])}: {rec['value']:.3f}",font=small,fill='black')
  else: d.text((15,347),f"中心-外围={row.center_edge_v:.2f}  左右ΔE={row.left_right_delta_e76:.1f}",font=small,fill='black')
  shares=np.array([row.ds1,row.ds2,row.ds3],float); colors=[row.dom1,row.dom2,row.dom3]; shares=shares/shares.sum() if np.isfinite(shares).all() and shares.sum()>0 else np.zeros(3); left=15
  for share,color in zip(shares,colors):
   width=int(round(240*share));
   if isinstance(color,str) and len(color)==7 and width>0:
    try: d.rectangle((left,370,left+width-1,386),fill=color)
    except ValueError: pass
   left+=width
  return im
 def montage(rows,cols):
  result=Image.new('RGB',(cols*270,((len(rows)+cols-1)//cols)*400),'white')
  for i,rec in enumerate(rows): result.paste(card(rec),((i%cols)*270,(i//cols)*400))
  return result
 montage(selection[:8],4).save(dest/'fig_spot_check_cards.png',dpi=(300,300))
 montage(selection,5).save(out/'spot_check_audit_contact.png',dpi=(150,150))
 thumb_files=sorted(dest.glob('*.png'))
 if thumb_files:
  cols=3; rows=(len(thumb_files)+cols-1)//cols; sheet=Image.new('RGB',(cols*800,rows*520),'white')
  for idx_f,fp in enumerate(thumb_files):
   im=Image.open(fp).convert('RGB'); im.thumbnail((760,460),Image.Resampling.LANCZOS)
   cell=Image.new('RGB',(800,520),'white'); d=ImageDraw.Draw(cell); d.text((20,10),fp.name,font=font,fill='black'); cell.paste(im,((800-im.width)//2,40+(460-im.height)//2))
   sheet.paste(cell,((idx_f%cols)*800,(idx_f//cols)*520))
  sheet.save(out/'figure_review_contact.png',dpi=(150,150))
