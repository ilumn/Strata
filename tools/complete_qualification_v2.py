"""Controlled suites after numerical screening; reuse only the completed c4 control."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from campaign_v2 import ROOT,OUT,run,parity

ap=argparse.ArgumentParser(); ap.add_argument('--arm',required=True); ap.add_argument('--prefix',required=True)
args=ap.parse_args(); driver=Path(__file__).with_name('campaign_v2.py')
base=json.loads((OUT/'resumed-qualify-c4-0-F.json').read_text())
label=args.prefix+'-qualify-c4'
candidate=run(label,args.arm,'qualify',ROOT/'exports/strata-ab/qualification-cases.json',strict=True,capacity=4)
result=parity(base,candidate)
(OUT/(label+'-parity.json')).write_text(json.dumps(result,indent=2))
print('C4 PARITY',result,flush=True)
assert result['equal'], 'controlled c4 mismatch'
for capacity in (1,2,3):
    subprocess.run([sys.executable,'-u',str(driver),'qualify','--arms','F',args.arm,
                    '--capacity',str(capacity),'--prefix',f'{args.prefix}-qualify-c{capacity}'],cwd=ROOT,check=True)
subprocess.run([sys.executable,'-u',str(driver),'long','--arms','F',args.arm,
                '--prefix',f'{args.prefix}-long'],cwd=ROOT,check=True)
