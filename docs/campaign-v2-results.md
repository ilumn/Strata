# Concurrency campaign v2 — results

Local-use candidate prepared and launch-tested: measured-policy MTP overlap plus 100 ms prefill yielding, original spec4/rows16. Five fresh alternating pairs passed all performance gates: 6.1% more aggregate decode TPS, 4.4x existing-stream TPS during prefill, no observed gaps over 250 ms, incoming TTFT about 24% longer, and essentially unchanged workflow completion. Controlled token parity, lifecycle and real HTTP streaming checks passed. The numerical limitation below remains disclosed. The daily installation was not replaced; the candidate is stopped after verification.

Daily main f7462a0 is unchanged. Experimental integration branch experiment/concurrency-validation-v2 combines preserved MTP overlap/fixed-cost policy and prefill-yield implementations; logical-slot sorting from the MTP branch is an explicit additional change. Diagnostic reference branch experiment/concurrency-reference-v2 keeps original scheduling and adds the identical opt-in teacher-forcing/logit reader only.

## Validation foundation

Both native builds succeeded. CPU tests:27 Python tests after the additional likelihood test,131072 scheduling cases, and prefill-budget/service checks. The first aggregate Python invocation used the workspace rather than repository cwd and had three import errors; rerunning from the correct repository passed. Numerical comparison unit tests cover equal-distribution shifts, near-tie top1 changes, large distribution errors, nonfinite values, truncated files, mismatched positions and likelihood direction.

Five fresh controlled smoke runs: frozen executable, diagnostic reference, integration default-off, fixed-policy MTP overlap, and combined overlap/yield. Each emitted1024 measured tokens and128 warmup tokens; all four comparisons to frozen matched IDs, lengths and finish reasons.

Independent-reference limitation: the actual GGUF architecture is qwen4exp. Local llama.cpp931351e recognizes it, but its graph implementation explicitly says it is pending complete reimplementation and should not be used as a reference. No independent absolute-model correctness claim is made.

## Numerical screen

Seventeen fresh processes, fast CPU kernels/adaptation enabled, fixed11546 actual resident expert slots. Ten essay/long-prefill arms and seven coding arms. Each uses the same512-token continuation per request, with full row-zero logits sampled every16 positions:128 positions/process. Teacher-forced outputs are checked against the fixture. Timing from these runs is excluded from performance claims.

The method commits one token at a time while speculative rows still execute. Thus it tests numerical effects of batch shapes, scheduling and residency at fixed prefixes, but does not by itself establish multi-token acceptance correctness. Ordinary-generation suites and lifecycle tests remain necessary.

| Configuration | Essay mean KL vs reference1 | Code mean KL vs reference1 |
|---|---:|---:|
| Reference2 |0.001110|0.000353|
| Integration default-off |0.001110|not separately run|
| Fixed draft policy |0.000844|not separately run|
| Fixed policy + MTP overlap |0.000844|0.000417|
| Measured policy + MTP overlap |0.000846|not separately run|
| Rows8/depth2 |0.000917|0.000647|
| Rows12/depth3 |0.000816|0.000497|
| Yield100ms |0.000998|0.000504|
| Fixed policy + MTP overlap + yield100ms |0.001101|0.000494|

All compared candidate means are below the predeclared2x baseline-repeat mean bound. Comparisons against reference2 are also recorded. Default-off and reference2 essay logits match exactly, as do fixed-policy overlap off/on essay logits.

Absolute triggers are retained, not hidden: essay BASE repeat has TV1.091%, slightly above the1% trigger; combined has TV1.150% versus reference1,1.017% versus reference2. Combined maxKL0.01268/0.01365 is below the0.02 trigger. Rows8/depth2 has one maxKL0.03124 versus reference1, but0.01639 versus reference2; its largest outlier retains the same top token. Measured-policy overlap has maxKL0.02576 versus reference2. All coding comparisons pass absolute and relative screens.

The two BASE-repeat essay top1 flips are near ties (34.15% versus33.64%, and33.83% versus33.29%). Other positions show larger confidence changes; do not characterize every numerical difference as a last-bit tie. Candidate mean teacher-NLL changes are also measured: combined is -0.003776/-0.001873 nats on the essay and -0.001630/-0.001805 on code versus the two references. This sampled likelihood diagnostic does not establish benchmark accuracy or general model quality.

These findings justify continuing investigation/performance screening, not deployment by themselves. Absolute outliers require follow-up for any selected finalist. Numerical-summary.json and per-reference full rows preserve the evidence.

## Performance and qualification

Initial normal-kernel/adaptive-cache essay screen,11546 actual resident slots:

| Arm | Aggregate common-decode TPS |
|---|---:|
| Frozen daily |226.54|
| Integration switches off |227.44|
| Fixed draft policy alone |221.56|
| Fixed policy + MTP overlap |232.91|
| Measured policy + MTP overlap |236.76|
| Rows8/depth2 |250.99|
| Rows12/depth3 |242.23|
| Fixed policy + MTP overlap + yield |failed reserve guard; no valid throughput result|

These are single-run screens, not qualified gains. All completed requests reached8192 total output tokens. The combined run exited when a late batch-graph allocation left2514MiB free, below the required2560MiB reserve. Preserve this as a failed configuration, not an OOM-free success. Subsequent tests request10500 expert slots instead of11000 in both arms to allow graph-growth headroom. Earlier11546-slot results are not paired against the reduced-cache runs. Daily settings remain unchanged.

No performance result from teacher forcing is used. These were initial screens; completed qualification follows below. No canonical promotion has occurred.

Normal essay output checks at the larger cache: frozen vs measured-policy MTP matched all8192 output tokens, lengths, finish reasons and warmup. Fixed-policy overlap off/on also matched exactly. This is workload-specific evidence, not general repeatability.

Reduced-cache coding screen (11022 actual slots): frozen236.54 TPS, depth2 245.59, measured-policy MTP247.18, depth2+MTP259.50, fixed-policy MTP+yield261.65. Natural EOS produces different lengths (and different common-decode intervals); these are diagnostic throughput screens, not equivalent fixed-work completion gains.

Reduced-cache30k-token arrival screen, three established decoders plus one incoming prompt:

| Arm | Existing-stream aggregate TPS during prefill | Incoming TTFT(s) | Workflow(s) | Gap burden>250ms(request-seconds) |
|---|---:|---:|---:|---:|
| Frozen |12.06|15.86|35.32|48.40|
| Yield100ms |52.44|20.09|36.12|0|
| Depth2 + measured MTP + yield100ms |40.33|18.45|33.69|0|
| Yield50ms |77.69|24.01|36.57|0|
| Yield200ms |32.66|18.04|35.50|1.02|

Select depth2+measured-policy MTP+yield100ms for deeper qualification: it combines the promising decode setting with zero observed long gaps and modest incoming-TTFT cost. The50/200ms tuning arms isolate yielding alone; no claim those exact numbers describe depth2+MTP at those intervals. Final qualification must repeat paired controls and correctness at the reduced cache.

## Resumed qualification and candidate selection

The user paused the campaign during the initial controlled c4 reference startup. That incomplete report is preserved and excluded. Resumed c4 reference versus depth2+MTP+yield passed all18 controlled cases exactly (raw IDs, lengths, finish reasons and warmup).

The completed reduced-cache numerical follow-up changed the selection. Depth2+MTP+yield exceeded the code relative mean-KL trigger against both references (0.000695/0.000775 versus limit0.000684), and had an essay maxKL0.02675 against reference2. One code top1 change was not a last-bit tie: reference probabilities51.8% versus35.0%. Do not dismiss all differences as harmless floating-point epsilon. The combination remains experimental and is not the proposed local-use default.

Ablations at the same11022-slot cache: depth2 alone passed both coding comparisons; MTP+yield at original spec4/rows16 passed both coding comparisons with meanKL0.000335/0.000347, essentially the same as BASE repeat0.000342. This does not uniquely attribute the earlier excursion to any single component; grouping, scheduling and adaptation interact.

Selected local candidate: measured-policy MTP overlap plus100ms yielding, retaining spec4/rows16. Essay meanKL0.000863/0.000741 is below relative limit0.001711 and the absolute0.001 threshold; maxKL0.01004/0.00998 is below0.02. Average TV1.0404% against reference1 slightly crosses the1% investigation trigger; against reference2 it is0.9017%. The single sampled top1 flip against reference1 had reference probabilities33.8% versus30.8%; all128 sampled top1 decisions matched reference2. Sampled teacher-NLL deltas are+0.001251/+0.003306 nats (essay),+0.000561/-0.000501 (code). These are finite, bounded observations, not proof of general quality equivalence. The TV excursion is retained as a limitation, not hidden by increasing the threshold. Controlled exact suites, long-output validation and lifecycle tests subsequently passed, as recorded below.

The selected combination passed the full18-case controlled suite at each of c1/c2/c3/c4: identical raw tokens, lengths, finish reasons and warmup versus frozen BASE at matching capacity. Cases include seeded sampling and penalties. Those controls disable optimized CPU kernels/adaptation and are correctness evidence only; production timing restores both. All30 current Python concurrency tests pass. Subsequent long-output, performance and lifecycle stages are recorded below.

Long controlled c4 parity also passed:9195 total generated tokens (2022,2343,2384,2446 per request), natural stops and warmup all identical. This exercises membership transitions4→3→2→1. The4096 per-request cap was not reached; do not describe this as16k generated tokens.

## Five fresh alternating performance pairs

Frozen BASE versus measured-policy MTP overlap + yield100ms, both at11022 actual cache slots, normal optimized CPU kernels and adaptation, context98304/request, c4, reserve2560MiB. Greedy essay fixtures; model loading and separate warmup excluded. Twenty fresh model processes: one arrival and one independent decode run per arm per pair. No diagnostic forcing/logit capture. Every pair passed every performance gate. A fresh evaluator additionally checked unique report hashes, matching options/environments apart from declared experiments, normal kernels/adaptation and equal capacity.

| Metric | BASE mean | Combined mean |
|---|---:|---:|
| Aggregate common decode TPS |226.21|239.94|
| Existing-stream TPS during incoming prefill |12.25|53.79|
| Incoming prompt tokens/s |1944.69|1569.10|
| Incoming TTFT(s) |15.53|19.22|
| Full workflow(s) |34.42|34.33|
| Full inter-token gaps>250ms, summed request-seconds |47.36|0|

Pooled decode rates are226.20/239.93 TPS, a6.07% gain. Per-pair decode gains range5.63–6.75%; incoming TTFT ratios1.232–1.244; workflow ratios0.990–1.007. Prefill/decode product ratios3.49–3.66 exceed the observed5.19% repeat spread. All candidate gap burdens were zero. These gap durations sum across requests, not wall-clock seconds. Results do not promise hard real-time latency under arbitrary foreground load.

All five normal-output decode comparisons and all five arrival comparisons have token differences; they are preserved as diagnostics, not represented as exact parity. Controlled suites above remain exact. The numerical investigation limitation remains unchanged.

## Coding and serving checks

Additional coding screens, one pair per sampling mode:

| Sampling | Four-stream common-decode TPS, BASE→candidate | Whole-job output/wall TPS, BASE→candidate | Output counts, BASE→candidate |
|---|---:|---:|---:|
| Greedy |248.51→273.99|251.88→250.11|6698→6174|
| Temperature0.35, top-p0.95, top-k20, fixed per-request seeds |206.84→220.53|205.01→204.74|6746→6120|

Coding common-decode observations improved10.25%/6.62%, but whole-job token rates were essentially unchanged. Outputs and natural stopping points differed. These screens do not establish a general coding-task speedup or semantic-quality equivalence; the repeated fixed-output-cap essay comparison provides the stronger throughput evidence.

Native lifecycle passed all12 behavior checks: three established decoders; incoming partial prefill; queued fifth cancellation before admission; active decoder cancellation; partial-prefill cancellation without output; surviving requests finish; immediate slot reuse while survivors remain active; invalid request rejection and subsequent recovery; actual yield callbacks observed. This test checks behavior, not exact token parity after schedule-dependent cancellation.

Actual OpenAI HTTP/SSE validation passed three repeated-arrival rounds in one model process:12 distinct response IDs,19666 generated output tokens plus32 warmup tokens, valid usage counts, valid finish reasons and final DONE events. Each round starts three streaming essays then submits a7827-token incoming prompt. These are serving/state checks; SSE chunk timestamps are not substituted for native token-TPS measurements. The process exited0.

## Local package and handoff

The package is `Strata-campaign-v2/local-candidate`, with a frozen tested executable (SHA256 `06464a55e3cb41f594b97c51f950cd088b73f49e05cddf91e52c32362bc80b6b`), c4 config, preset-router config and manifest. Other preset entries continue to use existing daily configurations. Root launch files are `Start Strata Candidate.cmd` and `Stop Strata Candidate.cmd`; they use installed PowerShell7 without an execution-policy override. The engine's process environment is cleaned before launch and test switches are applied explicitly by the c4 config.

The actual router exposed the existing model IDs and reported c4/98304/text-only correctly. A real non-streaming request through port8080 loaded the frozen packaged engine and returned `candidate ready.` with4 completion tokens. Both launch files were exercised; shutdown was verified and RAM/VRAM released. Windows CIM briefly retained a terminated-process record; launcher status now checks process liveness to avoid treating that stale record as running.

One background-launch command was rejected by automatic command review with only `blocked by policy`. Verification completed through a foreground tool-managed launch without an execution-policy override; no approval or security-setting change was needed.

See `local-candidate.md` for use and rollback. GPU clocks/voltage were not changed. AMD, multi-GPU, vision under c4, initial-load acceleration and universal fast-mode exact-token identity are not claimed by this candidate.
