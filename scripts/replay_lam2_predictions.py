"""用 best.pt 重放 λ=2 主结果的逐键预测（不重训）。"""
import sys
import numpy as np, torch
from pathlib import Path
sys.path.insert(0, 'src')
from evcs_station_graph.eventtime.data import FrozenData
from evcs_station_graph.eventtime.night_models import build_night_model

DATA='data/eventtime/dataset.npz'
if not Path(DATA).exists():
    DATA='outputs/evidence/checkpoint-replay-20261012/components/sg019/data/eventtime/dataset.npz'
fd=FrozenData(DATA)
zero=np.array([-0.267]*10, dtype=np.float32)
graphs=np.stack([np.eye(10)]*3)
root=Path('outputs/experiments/SENSFIX-20261108/lam2')
w=fd.windows('test')
N=len(w)
Xs=np.empty((N,96,10,7), dtype='float32'); Ys=np.empty((N,4,10), dtype='float32'); Ks=np.empty(N, dtype='int64')
for i in range(N):
    x,y,k=w[i]; Xs[i]=x; Ys[i]=y; Ks[i]=k
for seed in [2024,2025,2026,2027,2028]:
    ck_p=root/f'seed-{seed}'/'best.pt'
    if not ck_p.exists(): print(f"seed-{seed}: 缺失"); continue
    ck=torch.load(ck_p, map_location='cpu', weights_only=False)
    m=build_night_model('qnh_v3fix', graphs, zero_level=zero)
    m.load_state_dict(ck['model']); m.eval()
    preds=[]
    with torch.no_grad():
        for i in range(0, N, 512):
            xb=torch.from_numpy(Xs[i:i+512])
            out=m(xb); p=out.prediction if hasattr(out,'prediction') else out
            preds.append(p.numpy())
    pr=np.concatenate(preds)
    pr_o=pr*fd.arrays["target_std"][None,None,:]+fd.arrays["target_mean"][None,None,:]
    tr_o=Ys*fd.arrays["target_std"][None,None,:]+fd.arrays["target_mean"][None,None,:]
    mae=float(np.abs(pr_o-tr_o).mean())
    np.savez_compressed(root/f'seed-{seed}'/'predictions_test.npz',
                        y_true=tr_o.astype('float32'), y_pred=pr_o.astype('float32'), origins=Ks)
    print(f"seed-{seed}: 重放 MAE {mae:.6f}")
