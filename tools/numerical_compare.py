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

def metrics(a,b,teacher=None):
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid arrays')
    la = a - np.max(a); la -= np.log(np.exp(la).sum())
    lb = b - np.max(b); lb -= np.log(np.exp(lb).sum())
    pa,pb = np.exp(la),np.exp(lb)
    ia,ib = int(a.argmax()),int(b.argmax())
    delta = (a-a.mean())-(b-b.mean())
    result = {'kl':max(0.0,float(np.sum(pa*(la-lb)))),
            'tv':float(np.abs(pa-pb).sum()/2),
            'centered_rms':float(np.sqrt(np.mean(delta*delta))),
            'top1_equal':ia==ib,'top1_a':ia,'top1_b':ib,
            'base_margin':float(a[ia]-np.partition(a,-2)[-2]),
            'base_probability_of_candidate_top1':float(pa[ib]),
            'base_top1_probability':float(pa[ia])}
    if teacher is not None:
        result.update(teacher_token=teacher,teacher_nll_a=float(-la[teacher]),teacher_nll_b=float(-lb[teacher]))
    return result

def compare(left,right,force=None):
    a,b = read(left),read(right)
    if a.keys()!=b.keys():
        raise ValueError('missing or mismatched request/position records')
    teacher={}
    if force:
        for line in Path(force).read_text().splitlines():
            fields=list(map(int,line.split())); rid,count=fields[:2]
            if len(fields)!=count+2: raise ValueError('invalid teacher fixture')
            teacher[rid]=fields[2:]
    rows = [dict(request=k[0],step=k[1],position=k[2],**metrics(a[k],b[k],teacher[k[0]][k[1]] if teacher else None)) for k in sorted(a)]
    result = {'positions':len(rows),'mean_kl':float(np.mean([r['kl'] for r in rows])),
              'max_kl':max(r['kl'] for r in rows),'mean_tv':float(np.mean([r['tv'] for r in rows])),
              'top1_agreement':sum(r['top1_equal'] for r in rows)/len(rows),'rows':rows}
    result['absolute_screen_pass'] = result['mean_kl']<=0.001 and result['max_kl']<=0.02 and result['mean_tv']<=0.01
    if teacher:
        result['mean_teacher_nll_a']=float(np.mean([r['teacher_nll_a'] for r in rows]))
        result['mean_teacher_nll_b']=float(np.mean([r['teacher_nll_b'] for r in rows]))
        result['teacher_nll_delta']=result['mean_teacher_nll_b']-result['mean_teacher_nll_a']
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('left'); ap.add_argument('right'); ap.add_argument('--output',required=True); ap.add_argument('--force')
    args=ap.parse_args(); result=compare(args.left,args.right,args.force)
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
