# MTP overlap parity repair

Base: `3a51c84`, branch `experiment/mtp-parity-fix`. Worktree:
`C:/Users/niran/Documents/Code Projects/LocalLLMs/Strata-mtp-parity-fix`.
The preserved MTP implementation is intentionally the starting point.

## Scope and hypothesis

Preserve suffix lookup, adaptive expert residency, mixed CPU/GPU dispatch and
the existing overlap implementation. Keep overlap disabled by default. Parent
owns all model/GPU execution; this worktree does source work, CPU checks and
native builds only when coordinated with the parent.

Read local-agent-instructions.md and the concurrency optimization plan, report,
machine-readable results, and preserved run_h3_pairs.py. The prior short c4
pairs pass, but the long normal c4 pair first differs around 1800 output tokens.
The existing c2 trace establishes a changed lookup proposal at round 331.

Source finding: serial policy observation includes target work plus preceding
slots' commit/draft work, whereas overlapped observation includes all slots'
work. Even equal observation boundaries would not make wall-time learning
invariant to overlap, tracing, or unrelated load. Speculative windows feed
expert usage/residency and batch routing, so a changed window is not numerically
isolated from later accepted tokens. The MTP batch itself uses private graph,
scratch and stream state, with synchronization before host readback.

Requested a capped 2400-token original-binary c4 traced reproduction from the
parent before claiming attribution of the long-run failure. Added a read-only
trace comparator to distinguish first changed input from first changed output.

Potential repair under evaluation: explicit deterministic cost-shape policy,
retaining online acceptance learning and suffix proposals. This is a policy
change and must be compared with overlap off/on at the same policy, plus stock
controls. It cannot promise identical historical wall-time-policy outputs.
No model tests or unconditional normal-path parity claimed at this point.

## Implemented and CPU-verified

Added opt-in `STRATA_DETERMINISTIC_DRAFT_POLICY=1` for the concurrent engine.
It uses the existing cost-shape prior with online acceptance learning and
finite probes; measured timing policy stays the default. Both overlapping
and serial drafting use the same selected policy. MTP overlap itself stays
off by default; no production feature or preset is disabled/edited.

MSVC 14.32 CPU policy executable passes all 15 checks, including 4000-round
timing perturbations, both proposal sources and probe/acceptance behavior.
Four trace-comparator unit tests pass. Preserved c2 logs independently confirm
round331 as their first input difference. `git diff --check` passes.

Parent reproduced old c4 with 2400-token caps and trace enabled, stored in
`../exports/strata-next/mtp-old-trace-*`. First input difference is round766,
request102 pos1830 (MTP3 versus suffix4). Actual emitted first mismatch indices
1884/1787/1806/1908 match the historical long run. Details and causal limits
are in `docs/mtp-parity-repair.md`.

Native independent serial build is running in `build-mtp-cuda130`, approved
by parent after old reproduction completed and models stopped. CUDA13.0,
MSVC14.32, architecture120-real, portable/native experts, Release. No GPU or
model test was launched by this worker.

Build completed successfully (exit 0). Candidate executable SHA256:
`09d110bffdad3465504bbb907ef16a48d5cc6549ffcff495903782ebb0176d8a`.
Implementation checkpoint: `bd4fb7c`. Parent notified that the binary is
ready for the serialized normal-settings long off/on pair at the new policy.
At handoff, revised-policy model parity/performance is still pending and
exact original measured-policy long parity remains failed/unresolved.

Parent's first revised-policy long pair subsequently passed all 9547 emitted
IDs and finish reasons, normal adaptive fast kernels, PCIe0.55, 8192 caps,
natural EOS. Decode226.622->240.144 (+5.97%); wall215.727->227.507 (+5.46%).
Artifacts `../exports/strata-next/mtp-fixed-long-{off,on,parity}.json`.
One pair only: no promotion; repeats/default/stock/lifecycle checks remain.

## Reversed long confirmation and seeded fixture

Parent reversed long pair passed all 9547 IDs and finish reasons. Independently
compared off vs earlier off and on vs earlier on: both also match all 9547,
with identical arguments/workload/binary. All four resolve 11172 cache slots
and identical batch-round counts 1=14,2=164,3=138,4=822. Pair2 decode gain
8.34%, wall gain7.16%; pair1 gain5.97%/5.46%. Performance varies by session,
so preserve paired rates rather than invent a fixed speedup.

Reverse-pair resource samples: GPU peak off/on28845/28847 MiB, RAM minima
3939.6/3981.7 MiB, temperature60/60 C, power324.56/334.08 W. First pair has
no resource arrays (not silently substituted). Analysis saved in the report
and docs/mtp-parity-repair-results.json. No native code/binary changes.

Generated ignored build-qualification/mtp-seeded-code-2048.json and manifest
from four existing tuning code fixtures, retaining token IDs and setting
temperature0.35/top_p0.95/top_k20/seed42, cap2048. Parent received exact serial
runner command. Source SHA and generated SHA are recorded in the manifest;
generated SHA99b0198e24b757808ed013d4023db4399909c2a0b420ab4e80528c03b7818f5b.
Third workload pair/lifecycle remain pending before scoped c4 disposition.

## Seeded confirmation and lifecycle received

Parent seeded code pair passed exact6385 IDs/finish reasons:785stop,
2048length,2048length,1504stop. Accepted/offered counts match. Decode gain
5.5839%, wall4.4668%, actual11172 cache slots both.35 resource samples each
show peak GPU28932/28931 MiB, RAM minima3729.1/3775.3 MiB, temperature56/55 C,
power254.10/261.73 W. All19 parent lifecycle checks pass; correctbinary,
fixed-shape+overlap1, strict staticcache6297 confirmed in stderr.
Capacity c1/c2/c3 strict stock checks pending before final report commit.
Conclusion remains explicitly revised-policy experimental c4 evidence;
original measured-policy output equivalence remains unclaimed.

## Final scoped qualification

Parent capacity status completes c1/c2/c3 strict stock regression: each18
responses/2409 IDs and finish reasons exact, all exit0, actualcache6297.
With c4 this is72 stock comparisons/9636 tokens, alongside the c4 off/on
fixture pair, three performance pairs/25479 compared IDs and19 lifecycle
checks. Candidate hash unchanged. c1 ignores concurrent flags and is only
a regression check. Raw per-request comparisons independently inspected.

Disposition: qualify only the tested explicit revised fixed-shape-policy
plus overlap experimental opt-in for c4; keep both defaults off and daily
preset unchanged. No original measured-policy fix or unconditional parity
claim. Standalone c1/c2/c3 performance, arbitrary arrival histories, full
98304-token continuations and forced exhaustion remain outside these results.
No code or binary changes during final reporting.
