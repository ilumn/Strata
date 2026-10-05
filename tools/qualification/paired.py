"""Paired serial/batch full-vocabulary test. Both executables need the temporary overlay."""
import argparse,json,os,subprocess,threading,queue,time
from pathlib import Path
from compare import compare
def run(name,exe,args,requests,out,env,batch=0,groups=1):
 rs=requests
 cmd=[str(exe),*args]
 if batch:cmd+=['--batch',str(batch),'--batch-groups',str(groups)]
 env=dict(env);env['STRATA_UPSTREAM_TRACE']=str(out/(name+'.bin'))
 (out/(name+'.command.json')).write_text(json.dumps({'args':cmd,'requests':rs,'canonical_experts':env.get('STRATA_IQ_MT_MIN')},indent=2))
 log=(out/(name+'.stderr')).open('w');raw=(out/(name+'.stdout')).open('w')
 p=subprocess.Popen(cmd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1)
 q=queue.Queue()
 def pump():
  for l in p.stdout:raw.write(l);raw.flush();q.put(l.strip())
  q.put(None)
 t=threading.Thread(target=pump,daemon=True);t.start()
 results={i:[] for i in range(1,len(rs)+1)};active={};pending=list(enumerate(rs,1));done=set();admit=None;deadline=time.monotonic()+450
 def send(rid,r,slot=None):
  nonlocal admit
  n=r.get('max_new',16);path=r.get('image');keys=r.get('keys','');tokens=','.join(map(str,r['tokens']))
  line=('BGENI' if path else 'BGEN')+f' {slot} {n}' if batch else ('GENI' if path else 'GEN')+f' {n}'
  line+=keys+(' '+str(path) if path else '')+' '+tokens
  p.stdin.write(line+'\n');p.stdin.flush();admit=(rid,slot)
  if slot is not None:active[slot]=rid
 def schedule():
  if admit is not None or not pending:return
  if not batch:
   rid,r=pending.pop(0);send(rid,r);return
  free=next((s for s in range(batch) if s not in active),None)
  if free is not None:rid,r=pending.pop(0);send(rid,r,free)
 try:
  while True:
   l=q.get(timeout=max(.1,deadline-time.monotonic()))
   if l is None:raise RuntimeError('exited before ready '+str(p.poll()))
   if l.startswith('READY'):break
  print(name,'READY',flush=True);deadline=time.monotonic()+1200;schedule()
  while len(done)<len(rs):
   l=q.get(timeout=max(.1,deadline-time.monotonic()))
   if l is None:raise RuntimeError('engine exited '+str(p.poll()))
   f=l.split();kind=f[0] if f else ''
   if kind=='ERR':raise RuntimeError(l)
   if kind=='T':results[admit[0]].append(int(f[1]))
   if kind=='BT':results[active[int(f[1])]].append(int(f[2]))
   if kind=='BDONE':rid=active.pop(int(f[1]));done.add(rid);print(name,'DONE',rid,flush=True);schedule()
   if kind=='DONE' and not batch:rid=admit[0];done.add(rid);admit=None;print(name,'DONE',rid,flush=True);schedule()
   if kind=='BADM':
    rid,slot=admit
    if f[2]=='0':done.add(rid);active.pop(slot,None)
    admit=None;schedule()
  p.stdin.write('QUIT\n');p.stdin.flush();p.wait(timeout=60)
  if p.returncode:raise RuntimeError('shutdown '+str(p.returncode))
  (out/(name+'.tokens.json')).write_text(json.dumps(results,indent=2));return results
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=20)
  t.join(2);log.close();raw.close()

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--reference-exe',type=Path,required=True)
 parser.add_argument('--candidate-exe',type=Path,required=True)
 parser.add_argument('--args',type=Path,required=True,help='JSON list of engine arguments, including --serve')
 parser.add_argument('--requests',type=Path,required=True,help='JSON list of tokens, optional image path and max_new')
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--batch',type=int,default=4)
 parser.add_argument('--groups',type=int,default=1)
 options=parser.parse_args()
 out=options.output.resolve();out.mkdir(parents=True,exist_ok=False)
 args=json.loads(options.args.read_text());requests=json.loads(options.requests.read_text())
 if not requests or not all(isinstance(r.get('tokens'),list) and r['tokens'] for r in requests):parser.error('nonempty token lists required')
 if not 2<=options.batch<=8 or options.groups<1 or options.batch%options.groups:parser.error('batch 2..8, groups must divide batch')
 env=os.environ.copy();env['STRATA_IQ_MT_MIN']='1'
 run('reference',options.reference_exe.resolve(),args,requests,out,env)
 run('candidate',options.candidate_exe.resolve(),args,requests,out,env,options.batch,options.groups)
 result=compare(out/'reference.bin',out/'candidate.bin')
 (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 raise SystemExit(0 if result['bitwise_exact'] else 1)
