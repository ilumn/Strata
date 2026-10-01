"""Serial coding repeats, lifecycle and actual HTTP streaming after timing qualification."""
import os
import json
from pathlib import Path
import subprocess
import sys
from campaign_v2 import ROOT,OUT,run,decode_metrics

tools=Path(__file__).parent
env={k:v for k,v in os.environ.items() if not k.startswith(('STRATA_','CUDA_','CUBLAS_'))}
env['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
subprocess.run([sys.executable,'-u',str(tools/'campaign_v2.py'),'decode','--arms','F','combined_measured',
                '--dataset','code','--prefix','local-candidate-code'],cwd=ROOT,env=env,check=True)
sampled=OUT/'local-candidate-sampled-code-fixture.json'
if sampled.exists(): raise FileExistsError(sampled)
cases=json.loads((OUT/'code-decode-fixture.json').read_text())
for i,case in enumerate(cases):
    case['sampling']=f' temperature=0.35 top_p=0.95 top_k=20 seed={1234+i}'
sampled.write_text(json.dumps(cases,indent=2))
for arm in ('combined_measured','F'):
    label='local-candidate-sampled-code-'+arm
    result=run(label,arm,'decode',sampled)
    metrics=decode_metrics(result)
    (OUT/(label+'-metrics.json')).write_text(json.dumps(metrics,indent=2))
    print('SAMPLED CODE',arm,metrics,flush=True)
report=OUT/'local-candidate-repeat-0-overlap-combined_measured.json'
subprocess.run([sys.executable,'-u',str(ROOT/'exports/strata-responsiveness/yield_lifecycle.py'),
                '--config-report',str(report),'--output',str(OUT/'local-candidate-lifecycle.json')],cwd=ROOT,env=env,check=True)
subprocess.run([sys.executable,'-u',str(tools/'campaign_sse.py'),'--report',str(report),
                '--output',str(OUT/'local-candidate-sse.json'),'--rounds','3'],cwd=ROOT,env=env,check=True)
