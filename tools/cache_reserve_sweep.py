"""Fresh-process candidate cache/reserve comparisons; no daily config mutations."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'exports/strata-cache-reserve'
sys.path.insert(0, str(ROOT / 'Strata-prefill-budget/tools'))
from analyze_prefill_gates import validate, decode_metrics, overlap_metrics

ARMS = {'fixed2560': ('10500', 2560), 'auto2560': ('auto', 2560),
        'auto2048': ('auto', 2048), 'auto1434': ('auto', 1434),
        'fixed1434': ('11250', 1434)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arms', nargs='+', choices=ARMS, required=True)
    ap.add_argument('--repeat', type=int, default=1)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--phases', nargs='+', choices=['decode','overlap','code'], default=['decode','overlap'])
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    for repeat in range(args.repeat):
        for phase in args.phases:
            for arm in args.arms[::1 if repeat % 2 == 0 else -1]:
                label = f'{args.prefix}-{repeat}-{phase}-{arm}'
                output = OUT / (label + '.json')
                if output.exists(): raise FileExistsError(output)
                cache, reserve = ARMS[arm]
                command = [sys.executable, '-u', str(Path(__file__).with_name('cache_bench_wrapper.py')),
                           '--config', str(ROOT / 'Strata-campaign-v2/local-candidate/c4.json'),
                           '--output', str(output), '--repeat', '1',
                           '--workload', str(ROOT / ('exports/strata-campaign-v2/' +
                                ('local-candidate-sampled-code' if phase == 'code' else phase) + '-fixture.json')),
                           '--set', f'expert-cache={cache}', '--set', f'vram-reserve-mib={reserve}']
                if phase == 'overlap': command += ['--stagger-after', '64']
                env = {k:v for k,v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'CUBLAS_'))}
                samples = []
                stop = threading.Event()
                def monitor():
                    while not stop.is_set():
                        sample = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.free,utilization.gpu',
                                                 '--format=csv,noheader,nounits'], capture_output=True, text=True)
                        samples.append({'time': time.time(), 'gpu': sample.stdout.strip()})
                        stop.wait(1)
                thread = threading.Thread(target=monitor, daemon=True)
                thread.start()
                print('START', label, flush=True)
                try:
                    child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, text=True)
                    try:
                        stdout, stderr = child.communicate(timeout=600)
                    except subprocess.TimeoutExpired:
                        # Terminate this benchmark tree, including its native engine, before any next arm.
                        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
                        stdout, stderr = child.communicate(timeout=30)
                        stderr += '\nBenchmark exceeded 600 seconds; terminated its process tree.'
                    result = subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
                finally:
                    stop.set(); thread.join()
                    (OUT / (label + '-gpu.json')).write_text(json.dumps(samples))
                (OUT / (label + '-driver.log')).write_text(result.stdout + '\n' + result.stderr)
                report = json.loads(output.read_text())
                log = output.with_suffix('.stderr.log').read_text()
                actual = re.findall(r'expert cache (\d+) slots, ([\d.]+) GiB', log)
                alerts = [s for s in log.splitlines() if any(w in s.lower() for w in
                          ('shrinking', 'smaller expert cache', 'insufficient', 'out of memory', 'reserve violated'))]
                summary = {'arm': arm, 'phase': phase, 'requested_cache': cache, 'reserve_mib': reserve,
                           'returncode': result.returncode, 'complete': report.get('complete'),
                           'startup_s': report.get('startup_s'), 'actual_cache': actual, 'alerts': alerts}
                if result.returncode == 0:
                    validate(report)
                    assert report['args'][report['args'].index('--vram-reserve-mib')+1] == str(reserve)
                    summary['metrics'] = overlap_metrics(report) if phase == 'overlap' else decode_metrics(report)
                (OUT / (label + '-summary.json')).write_text(json.dumps(summary, indent=2))
                print('RESULT', json.dumps(summary), flush=True)

if __name__ == '__main__': main()
