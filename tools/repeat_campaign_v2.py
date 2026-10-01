"""Serial alternating fresh-process responsiveness qualification."""
import argparse
import json
from campaign_v2 import OUT, ARMS, run
from evaluate_campaign_v2 import evaluate


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--arm',required=True,choices=ARMS)
    parser.add_argument('--prefix',required=True); parser.add_argument('--pairs',type=int,default=5)
    args=parser.parse_args()
    manifest=OUT/(args.prefix+'-manifest.json')
    if manifest.exists(): raise FileExistsError(manifest)
    pairs=[]
    for i in range(args.pairs):
        pair={}
        for phase in ('overlap','decode'):
            for arm in (['F',args.arm] if i%2==0 else [args.arm,'F']):
                label=f'{args.prefix}-{i}-{phase}-{arm}'
                run(label,arm,phase,OUT/(phase+'-fixture.json'))
                pair[('base_' if arm=='F' else 'candidate_')+phase]=label+'.json'
        pairs.append(pair)
        manifest.write_text(json.dumps({'pairs':pairs},indent=2))
        result=evaluate(pairs)
        (OUT/(args.prefix+'-gates.json')).write_text(json.dumps(result,indent=2))
        print('PAIR',i,json.dumps(result['pairs'][-1]['ratios']),flush=True)
        print('GATES',json.dumps(result['performance_gates']),flush=True)


if __name__=='__main__': main()
