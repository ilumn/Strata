"""Pair each completed diagnostic against both reference runs, without hiding triggers."""
import argparse
import json
from pathlib import Path
from numerical_compare import compare

root=Path(__file__).resolve().parents[2]
out=root/'exports/strata-campaign-v2'
summary={}
ap=argparse.ArgumentParser(); ap.add_argument('--groups',nargs='+',default=['numeric:force.txt','code-numeric:force-code.txt'])
ap.add_argument('--output',default='numerical-summary.json'); args=ap.parse_args()
for prefix,force_name in [group.split(':',1) for group in args.groups]:
    refs=[out/f'{prefix}-{i}-R.logits' for i in (0,1)]
    if not all(p.exists() and p.with_suffix('.json').exists() and json.loads(p.with_suffix('.json').read_text()).get('complete') for p in refs): continue
    baseline=compare(*refs,out/force_name)
    rows={}
    for path in sorted(out.glob(prefix+'-*.logits')):
        report=path.with_suffix('.json')
        if not report.exists() or not json.loads(report.read_text()).get('complete'): continue
        results=[compare(ref,path,out/force_name) for ref in refs]
        for index,result in enumerate(results):
            result['relative_mean_kl_limit']=max(2*baseline['mean_kl'],.0001)
            result['relative_mean_kl_pass']=result['mean_kl']<=result['relative_mean_kl_limit']
            (out/f'{path.stem}-vs-ref{index}-full.json').write_text(json.dumps(result,indent=2))
        rows[path.stem]=[{k:v for k,v in result.items() if k!='rows'} for result in results]
    summary[prefix]={'baseline':{k:v for k,v in baseline.items() if k!='rows'},'arms':rows}
(out/args.output).write_text(json.dumps(summary,indent=2))
for dataset,group in summary.items():
    print(dataset,'BASE meanKL',group['baseline']['mean_kl'])
    for arm,values in group['arms'].items():
        print(arm,[(round(r['mean_kl'],6),round(r['max_kl'],6),round(r['mean_tv'],6),round(r['teacher_nll_delta'],6),r['absolute_screen_pass'],r['relative_mean_kl_pass']) for r in values])
