"""Make a separate c=4 server config from a local Strata installation.

The normal setup-generated config is never modified. Build this branch's engine
first: the upstream downloadable executable does not contain this experiment.
"""
import argparse
import json
from pathlib import Path


def configure(source: dict, engine: Path, context: int, reserve: int, cache: str) -> dict:
    if source.get("vision") or source.get("backend") == "hip" or isinstance(source.get("gpu"), list):
        raise ValueError("This c=4 candidate supports one NVIDIA GPU and text requests only")
    values = {}
    args = iter(source["args"])
    flags = {"--vision", "--no-prefill-borrow"}
    for key in args:
        if key in values or not key.startswith("--"):
            raise ValueError(f"Malformed or duplicate engine argument: {key}")
        values[key] = None if key in flags else next(args)
    incompatible = {"--vision", "--kv-resident", "--control-vector-scaled",
                    "--control-vector-layer-range", "--cvec-mode", "--cvec-dir"}
    present = incompatible & values.keys()
    if present:
        raise ValueError("Incompatible settings in source config: " + ", ".join(sorted(present)))
    required = {"--pack", "--native", "--expert-profile", "--mtp"}
    if not required <= values.keys():
        raise ValueError("Install a supported native model with an expert profile and MTP first")
    if context < 8192 or reserve < 1024:
        raise ValueError("Context must be >=8192 and reserve >=1024 MiB")
    if cache != "auto" and (not cache.isdecimal() or int(cache) <= 0):
        raise ValueError("Expert cache must be 'auto' or a positive slot count")
    values.update({
        "--expert-cache": cache, "--prefill": "1024", "--spec": "4",
        "--max-context": str(context), "--kv": "int8", "--vram-reserve-mib": str(reserve),
        "--concurrency": "4", "--batch-rows": "16", "--batch-padding": "1",
        "--batch-parallel": "1", "--batch-graphs": "8",
        "--concurrent-prefill": "1024", "--pool-workers": "15",
        "--pcie-frac": "0", "--prompt-cache": "0",
    })
    result = dict(source)
    result["exe"] = str(engine)
    result["args"] = [item for key, val in values.items()
                      for item in ([key] if val is None else [key, val])]
    result["model_name"] = source.get("model_name", "strata") + "-c4-candidate"
    result["vision"] = None
    result["env"] = dict(source.get("env", {}),
                         STRATA_BATCH_DRAFT="1",
                         STRATA_DETERMINISTIC_DRAFT_POLICY="0",
                         STRATA_PREFILL_YIELD="1",
                         STRATA_PREFILL_YIELD_MS="100",
                         CUBLAS_WORKSPACE_CONFIG=":4096:8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path,
                        help="setup-generated strata-*.json")
    parser.add_argument("--exe", required=True, type=Path,
                        help="strata.exe built from this candidate branch")
    parser.add_argument("--output", type=Path, default=Path("strata-c4-candidate.json"))
    parser.add_argument("--context", type=int, default=32768)
    parser.add_argument("--reserve-mib", type=int, default=2560)
    parser.add_argument("--expert-cache", default="auto")
    args = parser.parse_args()
    if not args.exe.is_file(): parser.error(f"Candidate engine missing: {args.exe}")
    if not args.config.is_file(): parser.error(f"Installed model config missing: {args.config}")
    if args.output.exists(): parser.error(f"Output already exists: {args.output}")
    source = json.loads(args.config.read_text(encoding="utf-8-sig"))
    result = configure(source, args.exe.resolve(), args.context, args.reserve_mib, args.expert_cache)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}: {result['model_name']}")
    print("The first request will load the model; check the available RAM and VRAM before starting.")


if __name__ == "__main__": main()
