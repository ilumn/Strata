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
