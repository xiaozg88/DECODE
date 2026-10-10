
import os, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(B,'figures','v29')
plt.rcParams.update({'font.size':8,'axes.titlesize':8.5,'axes.labelsize':8,
 'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
 'figure.dpi':150,'savefig.bbox':'tight'})
C=dict(blue='#3B6FB0',orange='#E08A3C',green='#4C9A6A',red='#C0453C',grey='#8A8A85')
e3=json.load(open(os.path.join(B,'output','experiments','v28','e3_results.json')))
e1=json.load(open(os.path.join(B,'output','experiments','v28','e1_results.json')))
n2=json.load(open(os.path.join(B,'output','experiments','v28','e2b_null_models.json')))
P=e3['E_pub   (legacy baseline)']; T=e3['E_total (same baseline)']
fig,axes=plt.subplots(1,3,figsize=(7.6,3.1))
fig.set_constrained_layout(True)
fig.subplots_adjust(wspace=0.42)
ax=axes[0]
labels=['OLS\n$R^2$','cluster\nSE','Huber\n|slope|','LOCO\n$R^2$','LOCO\ndir.acc.']
pub=[P['ols']['r2'],P['cluster']['se'],abs(P['huber']),P['loco_country']['oof_r2'],P['loco_country']['dir_acc']/100]
tot=[T['ols']['r2'],T['cluster']['se'],abs(T['huber']),T['loco_country']['oof_r2'],T['loco_country']['dir_acc']/100]
x=np.arange(len(labels))
ax.bar(x-0.19,pub,0.38,color=C['grey'],label='legacy baseline')
ax.bar(x+0.19,tot,0.38,color=C['blue'],label='same baseline')
ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=5.8)
ax.set_ylim(0,1.18)
ax.set_title('a  Every inference changes\non a common baseline',loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=5.8, ncol=2)
ax.text(0.30,0.60,'LOCO $R^2$: 0.714 $\\rightarrow$ -0.022\ndirection: 83.3% $\\rightarrow$ 55.0%',
 transform=ax.transAxes,fontsize=5.8,bbox=dict(fc='white',ec=C['grey'],lw=0.4,alpha=0.95))
ax=axes[1]
nm=['complete','stratified','block_bootstrap']
pv=[n2['delta_pub'][k]['null_mean'] for k in nm]
tv=[n2['delta_total'][k]['null_mean'] for k in nm]
x=np.arange(3)
ax.bar(x-0.19,pv,0.38,color=C['grey'],label='null mean, $\\Delta_{pub}$')
ax.bar(x+0.19,tv,0.38,color=C['blue'],label='null mean, $\\Delta_{total}$')
ax.axhline(0,color='black',lw=0.6)
ax.set_xticks(x); ax.set_xticklabels(['complete','stratified','block\nbootstrap'],fontsize=6.2)
ax.set_ylabel('null mean $R^2$',fontsize=7.5)
ax.set_ylim(0,0.95)
ax.set_title('b  A valid permutation null\ncentres on 0',loc='left')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=5.8, ncol=2)
ax.text(0.33,0.42,'block bootstrap keeps country\nstructure: $\\Delta_{pub}$\nnull mean 0.765',
 transform=ax.transAxes,fontsize=5.8,bbox=dict(fc='white',ec=C['grey'],lw=0.4,alpha=0.95))
ax=axes[2]
ths=['30','60','120']
mn=[e1['edge_by_threshold'][t]['min'] for t in ths]
md=[e1['edge_by_threshold'][t]['median'] for t in ths]
mx=[e1['edge_by_threshold'][t]['max'] for t in ths]
ng=[e1['edge_by_threshold'][t]['neg'] for t in ths]
x=np.arange(3)
ax.errorbar(x,md,yerr=[np.array(md)-np.array(mn),np.array(mx)-np.array(md)],
 fmt='o',color=C['blue'],capsize=4,lw=1.2,ms=5)
for i,t in enumerate(ths):
    ax.text(i,md[i]-6.0,'neg %d/60'%ng[i],ha='center',fontsize=6.0)
ax.axhline(0,color='black',lw=0.6)
ax.set_xticks(x); ax.set_xticklabels(['30 min','60 min','120 min'])
ax.set_ylabel('$\\Delta_{edge}$ (pp)',fontsize=7.5)
ax.set_title('c  Edge increment non-negative\nat every threshold',loc='left')
ax.set_ylim(-9,50)
for e in ('png','pdf'):
    fig.savefig(os.path.join(OUT,'fig4_inference_and_nulls.'+e),dpi=300)
print('ok')

