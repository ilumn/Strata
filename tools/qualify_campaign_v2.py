"""Serial numerical and controlled-generation qualification of one finalist."""
import argparse
import subprocess
import sys
from pathlib import Path
from campaign_v2 import ROOT, ARMS


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--arm',required=True,choices=ARMS); ap.add_argument('--prefix',required=True)
    args=ap.parse_args(); driver=Path(__file__).with_name('campaign_v2.py')
    for dataset in ('essay','code'):
        subprocess.run([sys.executable,'-u',str(driver),'numeric','--arms','R','R',args.arm,
                        '--dataset',dataset,'--prefix',f'{args.prefix}-numeric-{dataset}'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('summarize_numerical_v2.py')),
                    '--groups',f'{args.prefix}-numeric-essay:force.txt',f'{args.prefix}-numeric-code:force-code.txt',
                    '--output',f'{args.prefix}-numerical-summary.json'],cwd=ROOT,check=True)
    for capacity in (4,1,2,3):
        subprocess.run([sys.executable,'-u',str(driver),'qualify','--arms','F',args.arm,
                        '--capacity',str(capacity),'--prefix',f'{args.prefix}-qualify-c{capacity}'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'-u',str(driver),'long','--arms','F',args.arm,
                    '--prefix',f'{args.prefix}-long'],cwd=ROOT,check=True)


if __name__=='__main__': main()
