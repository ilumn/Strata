"""Isolate depth and overlap/yield using the saved reduced-cache references."""
import json
from campaign_v2 import OUT, run
from numerical_compare import compare

summary={}
for dataset in ('code','essay'):
    fixture=OUT/('code-numeric-fixture.json' if dataset=='code' else 'numeric-fixture.json')
    force=OUT/('force-code.txt' if dataset=='code' else 'force.txt')
    refs=[OUT/f'finalist-numeric-{dataset}-{i}-R.logits' for i in (0,1)]
    baseline=compare(*refs,force)
    expected={}
    for line in force.read_text().splitlines():
        fields=list(map(int,line.split())); expected[str(fields[0])]=fields[2:]
    for arm in ('depth2','combined_measured'):
        label=f'ablation-{dataset}-{arm}'
        report=run(label,arm,'numeric',fixture,force)
        for rid,item in report['runs'][0]['requests'].items():
            assert item['tokens']==expected[rid], 'forced continuation differs'
        results=[]
        for index,ref in enumerate(refs):
            result=compare(ref,OUT/(label+'.logits'),force)
            result['relative_limit']=max(2*baseline['mean_kl'],.0001)
            result['relative_pass']=result['mean_kl']<=result['relative_limit']
            (OUT/f'{label}-ref{index}.json').write_text(json.dumps(result,indent=2))
            results.append({k:v for k,v in result.items() if k!='rows'})
        summary[label]=results
        (OUT/'ablation-summary.json').write_text(json.dumps(summary,indent=2))
        print(label,json.dumps(results),flush=True)
