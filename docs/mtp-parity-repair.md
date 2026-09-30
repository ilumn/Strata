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
round 767. The trace establishes policy divergence before emitted divergence;
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
