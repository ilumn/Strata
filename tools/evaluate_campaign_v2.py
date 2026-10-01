"""Read-only performance gates. Normal token differences remain diagnostics.

This does not grant numerical/state correctness or authorize promotion.
"""
import argparse
import json
from pathlib import Path
import statistics
from campaign_v2 import OUT, FROZEN, sha
from analyze_prefill_gates import load_report, parity, overlap_metrics, decode_metrics, options


def evaluate(pairs):
    results = []
    seen = set()
    seen_hashes = set()
    configurations = {}
    actual_cache = None
    for pair in pairs:
        reports = {}
        sources = {}
        for role in ('base_overlap','candidate_overlap','base_decode','candidate_decode'):
            report, source = load_report(pair[role], OUT)
            assert source['path'] not in seen, 'reused report'
            assert source['source_sha256'] not in seen_hashes, 'copied report is not a fresh run'
            seen.add(source['path'])
            seen_hashes.add(source['source_sha256'])
            actual_cache = actual_cache or source['actual_cache_slots']
            assert actual_cache and source['actual_cache_slots'] == actual_cache, 'unequal expert capacity'
            assert not any(k.startswith('STRATA_DIAGNOSTIC') for k in report['environment'])
            assert not report['strict'], 'performance uses normal kernels/adaptation'
            assert not any(k in report['environment'] for k in ('STRATA_NO_IQ512','STRATA_NO_IQ256','STRATA_NO_IQ4NL'))
            assert int(options(report).get('--adapt-every','4')) > 0, 'adaptation is disabled'
            if role.startswith('base'):
                assert report['sha256'] == sha(FROZEN)
            config = {k:report[k] for k in ('sha256','args','environment','workload')}
            assert configurations.get(role,config) == config, 'configuration changed between repeats'
            configurations[role] = config
            reports[role],sources[role] = report,source
        for kind in ('overlap','decode'):
            a,b = reports['base_'+kind],reports['candidate_'+kind]
            ao,bo = options(a),options(b)
            changed = {k for k in set(ao)|set(bo) if (k in ao)!=(k in bo) or ao.get(k)!=bo.get(k)}
            assert changed <= {'--spec','--batch-rows'}, 'unmatched runtime options'
            ae,be = a['environment'],b['environment']
            changed_env = {k for k in set(ae)|set(be) if (k in ae)!=(k in be) or ae.get(k)!=be.get(k)}
            assert changed_env <= {'STRATA_BATCH_DRAFT','STRATA_PREFILL_YIELD','STRATA_PREFILL_YIELD_MS','STRATA_DETERMINISTIC_DRAFT_POLICY'}, 'unmatched runtime environment'
        diagnostic = {kind:parity(reports['base_'+kind],reports['candidate_'+kind])
                      for kind in ('overlap','decode')}
        a,b = [overlap_metrics(reports[role])[0] for role in ('base_overlap','candidate_overlap')]
        ad,bd = [decode_metrics(reports[role]) for role in ('base_decode','candidate_decode')]
        ratios = {key:b[key]/a[key] for key in ('D','P','U','incoming_ttft_s','workflow_s')}
        ratios['decode_TPS'] = bd['TPS']/ad['TPS']
        ratios['long_gap_time'] = b['long_gap_request_seconds']/a['long_gap_request_seconds'] if a['long_gap_request_seconds'] else None
        gates = {
            'decode_regression_at_most_3pct':ratios['decode_TPS'] >= .97,
            'incoming_TTFT_at_most_2x':ratios['incoming_ttft_s'] <= 2,
            'workflow_regression_at_most_10pct':ratios['workflow_s'] <= 1.10,
            'gap_burden_reduced_at_least_50pct':ratios['long_gap_time'] is not None and ratios['long_gap_time'] <= .5,
        }
        results.append(dict(sources=sources,base=a,candidate=b,base_decode=ad,candidate_decode=bd,
                            ratios=ratios,gates=gates,normal_token_parity_diagnostic=diagnostic))
    spread = lambda xs:(max(xs)-min(xs))/statistics.median(xs)
    noise = max(.02,spread([p['base']['U'] for p in results]),spread([p['candidate']['U'] for p in results]))
    ratios = [p['ratios']['U'] for p in results]
    gates = {key:all(p['gates'][key] for p in results) for key in results[0]['gates']}
    gates.update(five_fresh_pairs=len(results)>=5,
                 combined_tradeoff_improved_above_noise=all(r>1 for r in ratios) and statistics.median(ratios)>1+noise)
    return dict(performance_gates=gates,performance_pass=all(gates.values()),pairs=results,
                observed_U_noise_fraction=noise,
                limitation='Numerical and state correctness must be qualified separately; normal exact parity is diagnostic.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('manifest',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=evaluate(json.loads(args.manifest.read_text())['pairs'])
    args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result['performance_gates'],indent=2))
