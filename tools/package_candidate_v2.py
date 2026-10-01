"""Package a qualified local c4 candidate without replacing the daily installation."""
import argparse
import json
from pathlib import Path
import shutil
from campaign_v2 import ROOT,OUT,CAND,sha

ap=argparse.ArgumentParser(); ap.add_argument('--performance-prefix',required=True)
ap.add_argument('--qualification-prefix',required=True); ap.add_argument('--lifecycle',required=True); ap.add_argument('--sse',required=True)
args=ap.parse_args()
read=lambda name:json.loads((OUT/name).read_text())
gates=read(args.performance_prefix+'-gates.json')
assert gates['performance_pass'], 'performance gates not passed'
qualification=[args.qualification_prefix+'-qualify-c4-parity.json']
qualification += [f'{args.qualification_prefix}-qualify-c{c}-1-combined_measured-parity.json' for c in (1,2,3)]
qualification += [args.qualification_prefix+'-long-1-combined_measured-parity.json']
assert all(read(name)['equal'] for name in qualification), 'controlled parity not passed'
assert read(args.lifecycle)['behavior_passed'], 'lifecycle not passed'
sse=read(args.sse); assert sse['complete'] and sse['engine_exit_code']==0, 'SSE not passed'
manifest=read(args.performance_prefix+'-manifest.json')
report=read(manifest['pairs'][0]['candidate_decode'])
assert report['sha256']==sha(CAND), 'candidate binary changed'
destination=CAND.parents[1]/'local-candidate'
if destination.exists(): raise FileExistsError(destination)
destination.mkdir(); (destination/'bin').mkdir()
engine=destination/'bin/strata.exe'; shutil.copy2(CAND,engine)
cfg=json.loads((ROOT/'Strata-concurrency/strata-c4-local.json').read_text())
cfg.update(exe=str(engine),args=report['args'],log=str(destination/'c4.log'),
           env={k:v for k,v in report['environment'].items() if k!='STRATA_CONCURRENT_PROFILE'})
cfg['env']['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
assert cfg['env']['STRATA_BATCH_DRAFT']=='1' and cfg['env']['STRATA_PREFILL_YIELD']=='1'
config=destination/'c4.json'; config.write_text(json.dumps(cfg,indent=2))
router=json.loads((ROOT/'Strata-concurrency/strata-presets-local.json').read_text())
router['models']['swift-1.5-iq2_xs-c4']=str(config)
router['log_dir']=str(destination/'preset-logs')
(destination/'router.json').write_text(json.dumps(router,indent=2))
source_shared=ROOT/'Strata-concurrency/strata-c4-local.shared-settings.json'
if source_shared.exists(): shutil.copy2(source_shared,destination/'c4.shared-settings.json')
package={'exe_sha256':sha(engine),'source_exe':str(CAND),'performance_report':str(OUT/(args.performance_prefix+'-gates.json')),
         'qualification_reports':qualification,'lifecycle':args.lifecycle,'sse':args.sse,
         'numerical_limitation':'Essay TV 1.0404% vs first reference crossed 1% investigation trigger; other reference 0.9017%. See campaign-v2-results.md.',
         'daily_installation_replaced':False}
(destination/'manifest.json').write_text(json.dumps(package,indent=2))
for action in ('Start','Stop'):
    path=ROOT/f'{action} Strata Candidate.cmd'
    if path.exists(): raise FileExistsError(path)
    powershell=shutil.which('pwsh.exe')
    assert powershell, 'PowerShell 7 is required for the tested launcher'
    path.write_text('@echo off\n"'+powershell+'" -NoProfile -File "%~dp0Strata-campaign-v2\\tools\\local_candidate.ps1" -Action '+action+'\nif errorlevel 1 pause\n')
print(destination)
