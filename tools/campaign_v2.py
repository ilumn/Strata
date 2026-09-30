"""Serial v2 campaign phases; separate numerical diagnostics and performance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from numerical_compare import compare

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'exports/strata-campaign-v2'
REF=ROOT/'Strata-reference-v2/build-prefill-yield-cuda130/strata.exe'
CAND=ROOT/'Strata-campaign-v2/build-prefill-yield-cuda130/strata.exe'
FROZEN=ROOT/'exports/strata-ab/strata-baseline-a290571.exe'
sys.path.insert(0,str(ROOT/'Strata-prefill-budget/tools'))
from analyze_prefill_gates import validate,parity,decode_metrics,overlap_metrics

ARMS={
 'R':(REF,{},{}), 'default':(CAND,{},{}),
 'fixed':(CAND,{'STRATA_DETERMINISTIC_DRAFT_POLICY':'1'},{}),
 'mtp':(CAND,{'STRATA_DETERMINISTIC_DRAFT_POLICY':'1','STRATA_BATCH_DRAFT':'1'},{}),
 'mtp_measured':(CAND,{'STRATA_BATCH_DRAFT':'1'},{}),
 'depth2':(CAND,{}, {'spec':'2','batch-rows':'8'}),
 'depth3':(CAND,{}, {'spec':'3','batch-rows':'12'}),
 'yield':(CAND,{'STRATA_PREFILL_YIELD':'1'},{}),
 'combined':(CAND,{'STRATA_DETERMINISTIC_DRAFT_POLICY':'1','STRATA_BATCH_DRAFT':'1','STRATA_PREFILL_YIELD':'1'},{}),
 'F':(FROZEN,{},{}),
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(label,arm,phase,fixture,force=None,strict=False):
    exe,overrides,settings=ARMS[arm]
    output=OUT/(label+'.json')
    if output.exists(): raise FileExistsError(output)
    env={k:v for k,v in os.environ.items() if not k.startswith(('STRATA_','CUDA_','CUBLAS_'))}
    env.update(CUDA_VISIBLE_DEVICES='0',CUBLAS_WORKSPACE_CONFIG=':4096:8',STRATA_BATCH_DRAFT='0',
               STRATA_DETERMINISTIC_DRAFT_POLICY='0',STRATA_PREFILL_YIELD='0',STRATA_PREFILL_YIELD_MS='100')
    env.update(overrides)
    if force:
        env.update(STRATA_DIAGNOSTIC_FORCE=str(force),STRATA_DIAGNOSTIC_LOGITS=str(OUT/(label+'.logits')))
    command=[sys.executable,'-u',str(ROOT/'Strata-prefill-budget/tools/bench_concurrency.py'),
             '--config',str(ROOT/'Strata-concurrency/strata-c4-local.json'),'--exe',str(exe),
             '--output',str(output),'--workload',str(fixture),'--repeat','1']
    if strict: command+=['--strict']
    common={'prefill':'1024','concurrent-prefill':'1024','pool-workers':'15','expert-cache':'11000',
            'pcie-frac':'0','prompt-cache':'0'}
    common.update(settings)
    for key,value in common.items(): command+=['--set',key+'='+value]
    if phase in ('numeric','overlap'): command+=['--stagger-after','64']
    manifest={'command':command,'exe_sha256':sha(exe),'fixture_sha256':sha(fixture),'environment_overrides':{k:v for k,v in env.items() if k.startswith(('STRATA_','CUDA_','CUBLAS_'))}}
    (OUT/(label+'-launch.json')).write_text(json.dumps(manifest,indent=2))
    print('START',label,flush=True)
    subprocess.run(command,cwd=ROOT,env=env,check=True)
    report=json.loads(output.read_text()); validate(report)
    assert report['sha256']==manifest['exe_sha256']
    print('COMPLETE',label,flush=True)
    return report

def fixture(name,source,cap):
    path=OUT/name
    cases=json.loads((ROOT/source).read_text())['workload']
    for i,case in enumerate(cases):
        case['max_new']=cap; case['sampling']=f' temperature=0 top_p=1 top_k=20 seed={1234+i}'
    content=json.dumps(cases,indent=2)
    if path.exists(): assert path.read_text()==content
    else: path.write_text(content)
    return path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('phase',choices=['smoke','numeric','decode','overlap'])
    ap.add_argument('--arms',nargs='+',required=True,choices=ARMS); ap.add_argument('--prefix',required=True)
    args=ap.parse_args(); OUT.mkdir(exist_ok=True)
    overlap=args.phase in ('numeric','overlap')
    cap=512 if args.phase=='numeric' else 256 if args.phase=='smoke' else 1024 if overlap else 2048
    source='exports/strata-responsiveness/'+('base-repeat-0-chunk1024.json' if overlap else 'decode-base-0-chunk1024.json')
    work=fixture(args.phase+'-fixture.json',source,cap)
    force=None
    if args.phase=='numeric':
        saved=json.loads((ROOT/source).read_text())['runs'][0]['requests']
        force=OUT/'force.txt'
        content='\n'.join(f'{rid} {cap} '+ ' '.join(map(str,item['tokens'][:cap])) for rid,item in saved.items())+'\n'
        if force.exists(): assert force.read_text()==content
        else: force.write_text(content)
    reports={}
    for i,arm in enumerate(args.arms):
        label=f'{args.prefix}-{i}-{arm}'
        reports[label]=run(label,arm,args.phase,work,force,args.phase=='smoke')
        if args.phase=='numeric' and len(reports)>1:
            first=next(iter(reports)); result=compare(OUT/(first+'.logits'),OUT/(label+'.logits'))
            (OUT/(label+'-numerical.json')).write_text(json.dumps(result,indent=2))
            print('NUMERICAL',label,json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
        elif args.phase=='smoke' and len(reports)>1:
            result=parity(next(iter(reports.values())),reports[label])
            (OUT/(label+'-parity.json')).write_text(json.dumps(result,indent=2))
            print('PARITY',result,flush=True)
            if not result['equal']: raise RuntimeError('controlled smoke failed')
        elif args.phase in ('decode','overlap'):
            result=decode_metrics(reports[label]) if args.phase=='decode' else overlap_metrics(reports[label])
            (OUT/(label+'-metrics.json')).write_text(json.dumps(result,indent=2))
            print('METRICS',label,result,flush=True)

if __name__=='__main__': main()
