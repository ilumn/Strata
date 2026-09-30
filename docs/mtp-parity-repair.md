# Experimental deterministic concurrent draft policy

This branch starts from `3a51c84`, preserving the experimental overlapped MTP
implementation. `STRATA_BATCH_DRAFT` stays **off by default**. The new
`STRATA_DETERMINISTIC_DRAFT_POLICY=1` is also opt-in and affects only the
concurrent server. It retains suffix lookup, learned acceptance rates, window
probes, adaptive expert placement and fast CPU/GPU kernels.

## Reproduced failure and attribution

The parent ran the preserved executable `strata-h3-candidate-15eede15.exe`
(SHA256 `15eede15ad429be60638dd9dbd358c8bd2a3367c6a19a5dad2229dab7462aea1`)
with overlap off/on, normal c4 settings, explicit PCIe fraction 0.55, 2400
output-token caps and `STRATA_CONCURRENT_TRACE=1`. Reports and logs are in
`../exports/strata-next/mtp-old-trace-{off,on}.*`; request comparison is in
`mtp-old-trace-parity.json`. Tracing reproduced exactly the earlier first
committed-token mismatch indices: 1884 / 1787 / 1806 / 1908 for requests
100 / 101 / 102 / 103 respectively.

The first changed verifier input is earlier: round 766, request 102, position
1830. The control chooses MTP rows `279,7806,1220` (count 3); overlap chooses
suffix rows `279,7806,1220,381` (count 4). Common verifier outputs still agree:
`7806,1000,1831`; overlap has the additional speculative output `22000`.
The first extra suffix token is rejected, so this is not immediate emission
of a wrong draft. At round 770 request 100's confidence-limited MTP width
changes from 4 to 1. Comparing raw row zero at round 771 would then compare
different positions (1885 versus 1884), **not** matching mathematical inputs.
Use request-level token comparison to assess emitted parity.

The source explains why overlap changes lookup selection: each slot learns
wall-time cost by window width. Serial observation includes the target and
all earlier slots' commit/draft work. Overlap observation occurs after all
drafts. Both timing magnitude and attribution change when draft work speeds
up, and incidental system timing can change the same policy with overlap
off. Equalizing observation boundaries alone cannot remove this feedback.

Different speculative rows enter target expert routing and usage counts,
even when rejected. This pair crosses an adaptive placement boundary after
round 767. Batch padding is enabled: both physical target windows have four
rows, but the control pads its fourth row with current token `279` whereas
overlap evaluates suffix token `381` there. Equal padded shapes therefore do
not imply equal target inputs. The trace establishes policy divergence before emitted divergence;
it does not contain per-layer arithmetic or residency traces proving every
subsequent propagation step. No claim of harmless numerical divergence is
made.

## Repair being qualified

`DraftPolicy::CostMode::FixedShape` uses the existing relative window-cost
prior for decisions, while updating acceptance estimates and finite probe
counts exactly as before. Timings no longer enter decision state in this
mode. The measured mode and single-request engine retain their defaults.
The concurrent stderr header identifies the selected cost mode and overlap.

This is an explicit policy revision: it need not reproduce historical
wall-time-policy output. Its relevant changed-route comparison enables the
same fixed-shape policy with overlap off and on. Default-policy regression,
stock controls, long-form parity, lifecycle and performance qualification
remain separate gates; passing CPU policy tests alone does not qualify MTP.

CPU tests check 4000 rounds of unequal/spiky/unavailable timings, both proposal
sources, bounded probes and continued acceptance learning. The trace tool
also distinguishes a changed output length from a changed common output
token, rejects duplicate process rounds and requires actual trace records.

## Reproduction commands

Run policy CPU tests with the configured MSVC 14.32 compiler by compiling
`src/spec/draft_policy.cpp` and `src/spec/draft_policy_test.cpp` with `/std:c++20
/EHsc /Iinclude`, then execute the resulting binary.

Run the diagnostic tool with the existing virtual environment:

```powershell
..\Strata\.venv\Scripts\python.exe tools\compare_round_traces.py ..\exports\strata-next\mtp-old-trace-off.stderr.log ..\exports\strata-next\mtp-old-trace-on.stderr.log
..\Strata\.venv\Scripts\python.exe -m unittest discover -s tests\concurrency -p test_round_traces.py -v
```

Native build directory: `build-mtp-cuda130`, CUDA 13.0, MSVC 14.32, Release,
`120-real`, native experts, portable runtime. All model/GPU tests are
serialized and launched by the parent coordinator, never this worker.

Build succeeded at implementation checkpoint `bd4fb7c`. Executable SHA256:
`09d110bffdad3465504bbb907ef16a48d5cc6549ffcff495903782ebb0176d8a`.
The parent has the binary for long revised-policy off/on qualification.
At this handoff, exact normal long parity with the **original measured
policy remains failed**; revised-policy model parity and performance are
pending. Neither experimental flag is promoted.

## First revised-policy long pair (parent validation)

The parent subsequently ran normal adaptive c4 with fast kernels, PCIe
fraction 0.55, 8192-token caps and fixed-shape policy enabled in both arms.
All four essays finish naturally: **9547 committed token IDs and finish
reasons match exactly**. Artifacts are
`../exports/strata-next/mtp-fixed-long-{off,on,parity}.json` with adjacent logs.
Decode throughput is 226.622 versus 240.144 TPS (+5.97%); wall throughput is
215.727 versus 227.507 TPS (+5.46%). These are one preliminary paired trial,
not a promoted performance claim. Repeated pairs, default/stock regression
and lifecycle gates remain outstanding. Original measured-policy output
equivalence is not established or implied by this revised-policy pass.

## Reversed long pair and cross-process repeatability

The parent repeated the same long workload in reverse order (overlap first).
Again all **9547 committed IDs and finish reasons match**. Comparing control
against its previous control also matches all 9547 IDs/reasons, as does
overlap against its previous overlap. Both cross-process comparisons have
identical workloads, resolved arguments and binary hashes. All four processes
resolve to 11172 actual expert-cache slots and report identical active-batch
round counts: c1=14, c2=164, c3=138, c4=822. The c1 drain uses the existing
single-drafter fallback; this does not qualify the separate c1 engine.

| Pair/order | Control decode TPS | Overlap decode TPS | Decode gain | Wall gain |
| --- | ---: | ---: | ---: | ---: |
| 1, off then on | 226.622 | 240.144 | +5.97% | +5.46% |
| 2, on then off | 218.682 | 236.921 | +8.34% | +7.16% |

Control wall TPS in pair 2 is 210.137; overlap is 225.184. Absolute performance
changes between sessions, so the two gains remain paired observations rather
than a claim of one invariant improvement. Both comparisons retain normal
adaptive placement, suffix lookup and fast kernels with fixed-shape proposal
costs in both arms, explicit PCIe fraction 0.55 and unchanged 98304 context /
2560 MiB reserve. Lightweight host profiling is enabled equally; detailed GPU
timers and round tracing are off.

For the reversed pair, 42 control / 41 overlap whole-machine samples taken
approximately every two seconds including startup/warmup show GPU memory
peaks of 28845 / 28847 MiB, available-RAM minima 3939.6 / 3981.7 MiB,
temperature maxima 60 / 60 C and power maxima 324.56 / 334.08 W. These are
sampled observations, not exact peaks. **The first long pair has no resource
arrays**, so these measurements must not be attributed to that earlier pair.
Matching cache capacity is established independently from all four stderr
logs. Raw reversed artifacts are
`../exports/strata-next/mtp-fixed-long-reverse-{off,on,parity}.json` plus
adjacent stderr and `-resources.json` files.

[Machine-readable evidence](mtp-parity-repair-results.json) includes both
pairs and the two cross-run token comparisons. Third-pair seeded code and
parent lifecycle checks remain gates before the final c4 disposition.
This remains an explicit proposal-policy revision, with no claim of exact
historical measured-policy output or arbitrary arrival-pattern equivalence.

## Prepared seeded code confirmation

CPU-only fixture `build-qualification/mtp-seeded-code-2048.json` copies the
existing tuning cases code-merge, code-cache, code-parser and code-graph,
preserving their token IDs (prompt lengths 47/47/47/49). Each requests 2048
output tokens with `temperature=0.35 top_p=0.95 top_k=20 seed=42`, matching the
requested sampling profile. It is in an ignored build directory; its manifest
records the source hash and selection. Fixture SHA256:
`99b0198e24b757808ed013d4023db4399909c2a0b420ab4e80528c03b7818f5b`.

Parent-only command from the LocalLLMs directory:

```powershell
& .\Strata\.venv\Scripts\python.exe .\exports\strata-next\run_pair.py --repo Strata-mtp-parity-fix --exe Strata-mtp-parity-fix/build-mtp-cuda130/strata.exe --label mtp-fixed-seeded-code --flag STRATA_BATCH_DRAFT --env STRATA_DETERMINISTIC_DRAFT_POLICY=1 --set pcie-frac=0.55 --workload 'C:/Users/niran/Documents/Code Projects/LocalLLMs/Strata-mtp-parity-fix/build-qualification/mtp-seeded-code-2048.json'
```

The existing serial runner performs one off/on pair; the workload's max_new
values supply the caps. Preparing the fixture does not run an engine.
