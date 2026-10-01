"""Actual HTTP/SSE repeated-arrival smoke; one engine, private loopback port.

Chunk timings are not token-rate measurements. No daily config is changed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.request
from campaign_v2 import ROOT, sha

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from serve.server import StrataEngine, Service, serve
from serve.frontend import ChatTemplate
from strata_tokenizer import Tokenizer


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True); ap.add_argument('--rounds',type=int,default=3)
    args=ap.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    report=json.loads(args.report.read_text()); cfg=json.loads((ROOT/'Strata-concurrency/strata-c4-local.json').read_text())
    assert sha(report['exe'])==report['sha256']
    assert not any(k.startswith('STRATA_DIAGNOSTIC') for k in report['environment'])
    env={k:v for k,v in os.environ.items() if not k.startswith(('STRATA_','CUDA_','CUBLAS_'))}
    env.update(report['environment']); env['PATH']=os.pathsep.join([*cfg['lib_dirs'],env['PATH']])
    env['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    env['CUDA_VISIBLE_DEVICES']='0'
    path=Path(cfg['tokenizer']); vocab=json.loads((path/'vocab.json').read_text(encoding='utf-8'))
    names=['']*len(vocab)
    for token,index in vocab.items(): names[index]=token
    tokenizer=Tokenizer(names,(path/'merges.txt').read_text(encoding='utf-8').split('\n'),json.loads((path/'token_type.json').read_text()))
    engine=None; httpd=None
    result={'complete':False,'source_report':str(args.report.resolve()),'source_sha256':sha(args.report),'rounds':[]}
    try:
        engine=StrataEngine(report['exe'],report['args'],cwd=cfg['cwd'],env=env,log=str(args.output.with_suffix('.stderr.log')))
        template=path/'chat_template.jinja'
        service=Service(engine,tokenizer,ChatTemplate(template if template.exists() else REPO/'serve/chat_template.jinja'),model_name='campaign-test')
        httpd=serve(service,host='127.0.0.1',port=0)
        url=f'http://127.0.0.1:{httpd.server_port}/v1/chat/completions'
        result['port']=httpd.server_port

        def request(prompt,cap,event=None):
            body={'model':'campaign-test','messages':[{'role':'user','content':prompt}],
                  'temperature':0,'top_p':1,'top_k':20,'seed':1234,'reasoning_effort':'off',
                  'max_tokens':cap,'stream':True,'stream_options':{'include_usage':True}}
            start=time.monotonic(); stamps=[]; text=[]; finish=None; usage=None; done=False; response_id=None
            req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=240) as response:
                for raw in response:
                    line=raw.decode().strip()
                    if not line.startswith('data:'): continue
                    data=line[5:].strip()
                    if data=='[DONE]': done=True; break
                    obj=json.loads(data)
                    assert 'error' not in obj,obj
                    if obj.get('id'):
                        assert response_id in (None,obj['id']), 'response identity changed within stream'
                        response_id=obj['id']
                    usage=obj.get('usage') or usage
                    for choice in obj.get('choices',[]):
                        delta=choice.get('delta',{})
                        content=delta.get('content') or delta.get('reasoning_content') or ''
                        if content:
                            stamps.append(time.monotonic()-start); text.append(content)
                            if event and len(stamps)>=64: event.set()
                        finish=choice.get('finish_reason') or finish
            assert done and finish in ('stop','length') and text, 'incomplete SSE response'
            assert response_id and usage and 0 < usage['completion_tokens'] <= cap, 'invalid SSE usage or identity'
            return {'id':response_id,'wall_s':time.monotonic()-start,'chunk_times':stamps,'text':''.join(text),'finish':finish,'usage':usage,'done':done}

        request('Explain gravitational redshift.',32)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index in range(args.rounds):
                events=[threading.Event() for _ in range(3)]
                futures=[pool.submit(request,'Write a lengthy postgraduate essay on general relativity, its history, physical meaning and experimental tests. Avoid equations. Focus especially on '+focus+'.',2048,event)
                         for focus,event in zip(('geometry','astronomy','gravitation'),events)]
                for event in events:
                    assert event.wait(120), 'ongoing streams did not establish'
                assert not any(f.done() for f in futures), 'stream ended before arrival'
                prompt=('The observatory records weather and astronomical measurements in its archive. '*650)+ '\nSummarize this context, then discuss general relativity in detail.'
                futures.append(pool.submit(request,prompt,512))
                completed=[f.result() for f in futures]
                assert len({item['id'] for item in completed})==4, 'SSE response identities collide'
                result['rounds'].append(completed)
                args.output.write_text(json.dumps(result,indent=2))
                print('SSE round complete',index,flush=True)
        result['complete']=True
    except Exception as exc:
        result['error']=repr(exc)
        raise
    finally:
        if httpd: httpd.shutdown(); httpd.server_close()
        if engine: engine.close(); result['engine_exit_code']=engine.proc.returncode
        args.output.write_text(json.dumps(result,indent=2))


if __name__=='__main__': main()
