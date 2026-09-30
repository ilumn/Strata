"""Locate the first changed verifier input/output in concurrent trace logs.

Diagnostic only: differing speculative outputs need not be emitted. Pair this
with summarize_concurrency.py's request-level IDs/finish-reason comparison.
"""
import argparse
import json
import re
from pathlib import Path


PATTERN = re.compile(r"^round-(input|output|order) (\d+)(.*)$")


def read_trace(path):
    records = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = PATTERN.match(line)
        if not match:
            continue
        kind, number, tail = match.groups()
        fields = dict(re.findall(r"(\w+)=([^ ]*)", tail))
        request = int(fields.pop("id", -1))
        key = (int(number), kind, request)
        if key in records:
            raise ValueError(f"duplicate trace record {key}; use one process per log")
        records[key] = fields if kind != "order" else tail.strip()
    if not records:
        raise ValueError(f"no round trace records: {path}")
    return records


def compare(left, right):
    result = {}
    for kind in ("order", "input", "output"):
        keys = sorted(k for k in left.keys() | right.keys() if k[1] == kind)
        different = next((k for k in keys if left.get(k) != right.get(k)), None)
        result[kind] = None if different is None else {
            "round": different[0], "request_id": different[2],
            "left": left.get(different), "right": right.get(different),
        }
    result["common_output_token"] = None
    for key in sorted(k for k in left.keys() & right.keys() if k[1] == "output"):
        a = left[key]["tokens"].split(",")
        b = right[key]["tokens"].split(",")
        row = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
        if row is not None:
            input_key = (key[0], "input", key[2])
            result["common_output_token"] = {
                "round": key[0], "request_id": key[2], "row": row,
                "left": a[row], "right": b[row],
                "same_current_input": (left[input_key] == right[input_key])
                    if input_key in left and input_key in right else None,
            }
            break
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(read_trace(args.left), read_trace(args.right)), indent=2))


if __name__ == "__main__":
    main()
