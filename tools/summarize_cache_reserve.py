"""Summarize completed cache sweeps, keeping failures and per-run evidence."""
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'exports/strata-cache-reserve'
rows = []
for path in sorted(OUT.glob('*-summary.json')):
    row = json.loads(path.read_text())
    row['file'] = path.name
    gpu = json.loads(path.with_name(path.name.replace('-summary.json', '-gpu.json')).read_text())
    free = []
    for sample in gpu:
        try: free.append(int(sample['gpu'].split(',')[1]))
        except (ValueError, IndexError): pass
    row['min_free_mib'] = min(free) if free else None
    log = path.with_name(path.name.replace('-summary.json', '.stderr.log')).read_text()
    row['cache_cuts'] = sum(log.count(s) for s in ('shrinking the expert cache', 'trying a smaller expert cache'))
    row['reserve_failures'] = log.count('below VRAM reserve') + log.count('below the requested reserve')
    report = json.loads(path.with_name(path.name.replace('-summary.json', '.json')).read_text())
    gaps = [b-a for run in report.get('runs', []) for request in run['requests'].values()
            for a,b in zip(request['times'], request['times'][1:])]
    row['max_token_gap_ms'] = max(gaps)*1000 if gaps else None
    row['all_long_gap_request_seconds'] = sum(g for g in gaps if g > .250)
    row['output_tokens'] = sum(len(request['tokens']) for run in report.get('runs', [])
                               for request in run['requests'].values())
    duration = sum(run['wall_s'] for run in report.get('runs', []))
    row['whole_job_tps'] = row['output_tokens']/duration if duration else None
    rows.append(row)
summary = {}
for arm in sorted({r['arm'] for r in rows}):
    group = [r for r in rows if r['arm'] == arm]
    good = [r for r in group if r['complete'] and r['returncode'] == 0]
    decode = [r['metrics']['TPS'] for r in good if r['phase'] == 'decode']
    overlap = [r['metrics'][0] for r in good if r['phase'] == 'overlap']
    span = lambda xs: {'mean': statistics.mean(xs), 'min': min(xs), 'max': max(xs)} if xs else None
    summary[arm] = {'successful_starts_and_workloads': len(good), 'attempts': len(group),
                    'cache_cuts': sum(r['cache_cuts'] for r in group),
                    'reserve_failures': sum(r['reserve_failures'] for r in group),
                    'actual_slots': sorted({int(s[0]) for r in group for s in r['actual_cache']}),
                    'startup_s': span([r['startup_s'] for r in good]),
                    'min_free_mib': min(r['min_free_mib'] for r in group if r['min_free_mib'] is not None),
                    'max_token_gap_ms': max(r['max_token_gap_ms'] for r in good),
                    'all_long_gap_request_seconds': sum(r['all_long_gap_request_seconds'] for r in good),
                    'code_tps': span([r['metrics']['TPS'] for r in good if r['phase'] == 'code']),
                    'code_whole_job_tps': span([r['whole_job_tps'] for r in good if r['phase'] == 'code']),
                    'decode_tps': span(decode),
                    'overlap': {k: span([r[k] for r in overlap]) for k in
                                ('D', 'P', 'incoming_ttft_s', 'workflow_s', 'long_gap_request_seconds')}}
(OUT / 'results.json').write_text(json.dumps({'summary': summary, 'runs': rows}, indent=2))
print(json.dumps(summary, indent=2))
