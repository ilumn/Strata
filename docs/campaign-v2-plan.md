# Concurrency campaign v2

Scope: single NVIDIA RTX5090, native Windows, Swift IQ2_XS; c4 primary and c1 regression. Preserve daily installation, clocks/voltage,98304 context/request and2560MiB reserve. Serialize all GPU tests.

Three experiments: MTP overlap (including measured versus fixed-shape draft policy), bounded batch rows/spec-depth tuning, and within-chunk prefill yielding with bounded interval tuning. Integrate only successful candidates. CPU/GPU offload wiring, new kernels and prefix caching are outside this campaign.

## Correctness contract

Exact normal-output identity is diagnostic, no longer a universal veto. Still require exact controlled-suite tokens/lengths/finish reasons, request isolation, cancellation/reuse and valid speculative acceptance. Nonfinite logits, malformed output, memory/state errors and meaningful numerical drift are failures.

Before performance selection, run BASE twice and candidates on identical saved prompt tokens and forced continuations. Record full row-zero logits every16 committed positions. Teacher forcing commits one token per round; therefore it exercises differing speculative window shapes and scheduling but does not alone qualify ordinary multi-token acceptance. Supplement with ordinary-generation controlled suites and lifecycle tests. Recording is disabled for performance runs.

Numerical screening: compare softmax distributions using KL, total variation, top1 agreement, selected-token probability and centered logit RMS. Report per-position outliers and baseline/base variation. Predeclared investigation triggers: mean KL>0.001, any KL>0.02, mean TV>0.01, or candidate mean KL greater than max(2x BASE-repeat mean,0.0001). These are engineering screening thresholds, not proven quality-equivalence bounds; triggering them requires diagnosis, never automatic tolerance inflation. No claim that passing a small fixture proves general model quality.

Original frozen f7462a0 remains a reference. Diagnostic instrumentation necessarily uses a separately identified build with unchanged original scheduling/math; verify its ordinary output against the frozen executable under controlled settings. Candidate integration also contains the preserved logical-slot ordering change; list it explicitly, rather than pretending the default-off combined executable is original BASE.

## Performance and responsiveness

Use equal fixed actual expert capacity, fast CPU kernels and adaptive cache enabled. Independent performance runs have no teacher forcing/logit instrumentation. Report committed aggregate TPS, natural completion and token counts across prose and coding; retain differing-output runs as diagnostic throughput observations with work-length caveats. Confirm finalists in alternating repeated trials, not one lucky run.

Resource adjustment after the first decode screen: request10500 slots (11022 actual), down from11000 (11546 actual). The combined arm tripped the2560MiB guard during late graph growth at the larger cache. All subsequent paired qualification uses the smaller equal cache; do not mix cache sizes into a claimed paired gain. The requested reserve remains2560MiB.

Responsiveness gates: halve total inter-token gap burden above250ms, incoming TTFT<=2x BASE, workflow duration<=1.10x BASE, independent decode-only regression<=3%; positive concurrent decode/prefill tradeoff. Five fresh pairs for final responsiveness qualification, plus repeated arrivals and cancellation/reuse. No paging or abandoned resident engines.

Check available llama.cpp architecture support without installing/downloading a second large model. Lack of a compatible independent engine does not block internal investigation, but must be disclosed as a validation limitation.

Reference check: installed model metadata is general.architecture=qwen4exp. Local llama.cpp931351e (2026-09-30) recognizes it, but src/models/qwen4exp.cpp explicitly marks the graph as pending complete reimplementation and unsuitable as a reference. Do not treat it as a trusted numerical oracle in this campaign. Internal comparisons cannot establish independent absolute model correctness.

Promotion requires correctness and performance evidence together. A failed numerical gate can end qualification with a preserved experimental result; it must not be silently waived merely because exact tokens are no longer mandatory.
