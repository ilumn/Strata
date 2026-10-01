# Candidate c4 expert-cache/reserve comparison — 2026-10-01

Recommendation: retain the packaged fixed-cache, 2560 MiB reserve default. Automatic
sizing at 1434 MiB was stable in these tests and is a viable experimental setting,
but the measured gains do not establish a compelling general trade for its smaller
foreground-memory margin. No serving config, engine code or executable was changed.

## Method

Same frozen candidate executable (SHA256
`06464a55e3cb41f594b97c51f950cd088b73f49e05cddf91e52c32362bc80b6b`),
c4, context 98304/request, vision off, MTP overlap, 100 ms prefill yielding,
spec4/rows16, normal CPU kernels and adaptive caching. Reserve units are MiB:
2560 = 2.5 GiB, 2048 = 2 GiB, 1434 is approximately 1.4 GiB.

The packaged baseline requests 10500 uniform-size cache slots, yielding 11022
actual variable-size slots. Lowering its reserve alone would not enlarge that
fixed cache. Alternative arms therefore use `--expert-cache auto`.

Twenty sequential fresh engine processes, never simultaneous models:

- Initial four-arm screen: one decode and one staggered-arrival run per arm.
- Two more alternating comparisons of fixed2560 vs auto1434: three decode and
  three arrival trials per finalist in total.
- Two reversed-order sampled coding comparisons per finalist, temperature 0.35,
  top-p 0.95, top-k 20, fixed per-request seeds.

Arrival workload: three established decoders, then a 30000-token fourth prompt.
Essay decode caps are 2048 tokens/request; arrival output caps are 1024/request.
Model loading and separate warmup are excluded from throughput. Startup measures
native process launch to READY. NVIDIA memory telemetry is sampled once/second;
reported minimum free memory is sampled, not a guaranteed instantaneous minimum.

The established harness forcibly set reserve to 2560 after overrides. A separate
wrapper replaces that assignment with a default and records startup duration;
every successful report's effective reserve was checked. Original harness and
daily installation remain unchanged. Raw tokens, arguments, logs and telemetry
are retained under workspace `exports/strata-cache-reserve/`.

## Results

| Configuration | Actual slots / cache GiB | Essay aggregate decode TPS | Existing TPS during prefill | Incoming TTFT | Workflow time | Successful starts/workloads |
|---|---:|---:|---:|---:|---:|---:|
| Fixed cache, 2.5 GiB | 11022 / 14.77 | 248.00 | 55.04 | 18.46 s | 32.92 s | 8/8 |
| Auto, 2.5 GiB | 11172 / 14.97 | 244.14 | 53.88 | 18.41 s | 33.44 s | 2/2 |
| Auto, 2.0 GiB | 11544 / 15.47 | 249.75 | 53.59 | 18.27 s | 33.30 s | 2/2 |
| Auto, 1.4 GiB | 11994 / 16.07 | 247.58 | 52.62 | 17.97 s | 32.80 s | 8/8 |

Finalist essay/arrival values are means of three runs; intermediate auto settings
are single-run screens per workload, not equally qualified performance estimates.
Actual slot counts were identical across fresh starts within every arm.

At 1.4 GiB there were 972 more slots (+8.8%), using 1.30 GiB more expert-cache
storage. Essay decode changed -0.17%; incoming prompt throughput improved 2.76%,
TTFT fell 0.49 seconds, existing decode during prefill fell 4.39%, and workflow
duration changed -0.36%. This is a small trade-off, not an outsized overall gain.

Sampled coding common-four-stream TPS averaged 223.57 fixed vs 228.24 auto1434
(+2.09%). Whole-job output/wall rates were 209.00 vs 220.96 (+5.72%), but outputs
and stopping points differed: fixed produced 5933/6269 tokens, auto1434 produced
6949/6949. Do not interpret these as equal-work completion or quality improvements.
These are two-pair workload-specific observations, not a quality benchmark.

## Smoothness and stability

- All 20 processes completed and exited successfully. No cache-shrink messages,
  allocation-retry cache cuts, reserve failures or hangs were observed. In
  particular the 25% reduction mechanism did not activate.
- All eight arrival trials had zero time in inter-token gaps exceeding 250 ms.
- Across all measured workloads, fixed2560 had two approximately 269 ms request
  gaps in one decode run (0.538 summed request-seconds); auto1434 had none, and
  its maximum gap was 171 ms. This isolated event is not sufficient evidence of
  a systematic smoothness improvement. Intermediate arms also had no >250 ms gaps.
- Startup ranges: fixed2560 35.38–36.77 s; auto1434 35.32–36.24 s. No meaningful
  startup-time penalty or inconsistent final cache capacity was observed.
- Minimum sampled free VRAM: fixed2560 3210 MiB; auto2560 3030 MiB; auto2048
  2506 MiB; auto1434 1888 MiB. The requested reserve is a floor/guard, not a target
  utilization figure. Auto sizing also estimates later concurrent allocations.
- Every run used the same pre-existing host-memory fallback: whole-arena
  cudaHostRegister failed, then 44 slices (30 GiB) were pinned successfully;
  large pages were unavailable. This is distinct from a failed GPU expert-cache
  allocation and did not produce cache cuts.

Scope: these workloads cover graph warmup, changing active membership, generation,
and a 30k arriving prompt. They do not establish long-session reliability with all
four 96k windows filled or under heavy foreground GPU-memory pressure. Numerical
quality/semantic benchmarks remain deferred; normal cache-placement-dependent
token differences are expected and were not treated as failures.

The candidate still uses its original fixed cache and 2560 MiB reserve. All test
engines were stopped after measurement. Reproduction scripts are
`tools/cache_reserve_sweep.py`, `tools/cache_bench_wrapper.py` and
`tools/summarize_cache_reserve.py`; `exports/strata-cache-reserve/results.json`
contains aggregate results and per-run evidence.
