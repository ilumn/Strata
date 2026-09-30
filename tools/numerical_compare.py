"""Full-vocabulary teacher-forced probability comparison; no generation timing claims."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np

def read(path):
    records = {}
    with Path(path).open('rb') as file:
        while header := file.read(32):
            if len(header) != 32:
                raise ValueError('truncated header')
            rid, step, pos, vocab = struct.unpack('<QQQQ',header)
            if not 1 <= vocab <= 1000000:
                raise ValueError('invalid vocabulary')
            raw = file.read(vocab*4)
            if len(raw) != vocab*4:
                raise ValueError('truncated logits')
            values = np.frombuffer(raw,dtype='<f4').astype(np.float64)
            key = (rid,step,pos)
            if key in records or not np.isfinite(values).all():
                raise ValueError('duplicate or nonfinite logits')
            records[key] = values
    if not records:
        raise ValueError('empty trace')
    return records

def metrics(a,b):
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid arrays')
    la = a - np.max(a); la -= np.log(np.exp(la).sum())
    lb = b - np.max(b); lb -= np.log(np.exp(lb).sum())
    pa,pb = np.exp(la),np.exp(lb)
    ia,ib = int(a.argmax()),int(b.argmax())
    delta = (a-a.mean())-(b-b.mean())
    return {'kl':max(0.0,float(np.sum(pa*(la-lb)))),
            'tv':float(np.abs(pa-pb).sum()/2),
            'centered_rms':float(np.sqrt(np.mean(delta*delta))),
            'top1_equal':ia==ib,'top1_a':ia,'top1_b':ib,
            'base_margin':float(a[ia]-np.partition(a,-2)[-2]),
            'base_probability_of_candidate_top1':float(pa[ib]),
            'base_top1_probability':float(pa[ia])}

def compare(left,right):
    a,b = read(left),read(right)
    if a.keys()!=b.keys():
        raise ValueError('missing or mismatched request/position records')
    rows = [dict(request=k[0],step=k[1],position=k[2],**metrics(a[k],b[k])) for k in sorted(a)]
    result = {'positions':len(rows),'mean_kl':float(np.mean([r['kl'] for r in rows])),
              'max_kl':max(r['kl'] for r in rows),'mean_tv':float(np.mean([r['tv'] for r in rows])),
              'top1_agreement':sum(r['top1_equal'] for r in rows)/len(rows),'rows':rows}
    result['absolute_screen_pass'] = result['mean_kl']<=0.001 and result['max_kl']<=0.02 and result['mean_tv']<=0.01
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('left'); ap.add_argument('right'); ap.add_argument('--output',required=True)
    args=ap.parse_args(); result=compare(args.left,args.right)
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
