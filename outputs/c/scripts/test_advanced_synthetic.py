import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from c_adv_common import rgb_to_lab
from c06_relations import calculate,cooccurrence
from c07_spatial import extract

def main():
 c=json.loads((Path(__file__).parent/'c_adv_config.json').read_text(encoding='utf8'))
 assert np.allclose(rgb_to_lab([1,1,1]),[100,0,0],atol=.02)
 assert np.allclose(rgb_to_lab([1,0,0]),[53.2408,80.0925,67.2032],atol=.02)
 x=pd.DataFrame({'id':[1,2,3], 'year':[2001]*3,'decade':[2000]*3,'country_main':['US']*3,'dom1':['#ff0000','#555555','#000000'],'dom2':['#ff0001','#555555','#010101'],'dom3':['#ff0000']*3,'ds1':[.5]*3,'ds2':[.3]*3,'ds3':[.2]*3,'sat_frac':[.5,0,0],**{f'h{i}':[1 if i==0 else 0,0,0] for i in range(12)}})
 r=calculate(x,c); assert r.loc[0,'pair_hue_gap_deg']<1; assert r.loc[1,'pair_delta_e76']==0; assert r.loc[2,'primary_class14']=='dark'; assert not r.loc[1,'pair_hue_valid']; assert not r.loc[1,'warmth_valid']
 co=cooccurrence(x,r); summed=co.groupby(['dimension','group','matrix_kind','ordered']).joint_probability.sum(); assert np.allclose(summed[summed>0],1)
 img=np.zeros((160,120,3),np.uint8); img[35:105,20:100]=255; f,_=extract(Image.fromarray(img),c); assert f['center_edge_v']>0 and abs(f['center_actual_area_fraction']-.5)<.02
 img[:]=0; img[:,:40,0]=255; img[:,80:,2]=255; f,_=extract(Image.fromarray(img),c); assert f['left_right_delta_e76']>0
 f,_=extract(Image.fromarray(np.zeros_like(img)),c); assert f['vivid_frac']==0 and np.isnan(f['v_skew'])
 print('Synthetic checks passed')
if __name__=='__main__': main()
