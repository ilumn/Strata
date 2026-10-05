"""Strict FP32 vocabulary comparison for traces from the temporary qualification overlay."""
import argparse, array, json, math, struct
from pathlib import Path

def read(path):
    rows = {}
    with Path(path).open('rb') as f:
        while header := f.read(32):
            if len(header) != 32: raise ValueError('truncated trace header')
            rid, step, pos, count = struct.unpack('<4Q', header)
            if count < 1 or count > 1048576: raise ValueError('invalid vocabulary size')
            data = f.read(count * 4)
            if len(data) != count * 4: raise ValueError('truncated logits')
            values = array.array('f'); values.frombytes(data)
            if not all(map(math.isfinite, values)): raise ValueError('nonfinite logits')
            key = rid, step, pos
            if key in rows: raise ValueError('duplicate trace record')
            rows[key] = data
    if not rows: raise ValueError('empty trace')
    return rows

def compare(reference, candidate):
    a, b = read(reference), read(candidate)
    if a.keys() != b.keys(): raise ValueError('request/step/position coverage differs')
    count = 0; different = 0; max_abs = 0.0
    for key in a:
        if len(a[key]) != len(b[key]): raise ValueError('vocabulary sizes differ')
        count += len(a[key]) // 4
        if a[key] == b[key]: continue
        av = array.array('f'); av.frombytes(a[key])
        bv = array.array('f'); bv.frombytes(b[key])
        ai = array.array('I'); ai.frombytes(a[key])
        bi = array.array('I'); bi.frombytes(b[key])
        different += sum(x != y for x, y in zip(ai, bi))
        max_abs = max(max_abs, max(abs(x-y) for x,y in zip(av,bv)))
    return dict(rows=len(a), values=count, different_values=different, max_abs=max_abs,
                bitwise_exact=different == 0)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate');p.add_argument('--output')
    args=p.parse_args();result=compare(args.reference,args.candidate)
    print(json.dumps(result,indent=2))
    if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(0 if result['bitwise_exact'] else 1)
