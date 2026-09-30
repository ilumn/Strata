# Prefill routing-barrier yield prototype

Base: `f7462a061a00acfa4848cd0a9bde0534bbed18fd`. Branch: `experiment/prefill-yield`.
This is an unqualified mechanism experiment. No source changes from the trace or stable-sort branches
are included. The original pointer-based batch ordering is retained. No preset changes.

## Controls and scope

`STRATA_PREFILL_YIELD=1` enables the experiment in concurrent serving only; absent, `0`, and other values
leave it disabled. `STRATA_PREFILL_YIELD_MS` sets the prompt-work service interval in milliseconds
(default 100; finite values in [1, 1000] only). A malformed interval fails startup when enabled.
The existing `--concurrent-prefill 1024` stays 1024; partial final chunks keep their original dimensions.

Only NVIDIA CUDA, one model device, and prompt chunks at most 1024 are supported. Existing concurrency
validation rejects HIP, layer splitting, remote expert caches and streamed KV. The callback path also
rejects split Prefill stages and chunks above 1024. The c1 generate path does not enter ConcurrentServe
and ignores these controls.

The service interval is a soft scheduling budget, not a 250ms latency guarantee: service occurs only
at the next MoE host-routing barrier, and decode execution itself adds latency. The final MTP-prefill
tail remains uninterrupted. There is no new admission, input parsing, cancellation, reset, slot reuse,
or recursive prompt execution inside a callback. CSTOP/QUIT remain processed at the outer loop: a
command arriving just after that check can wait the remaining whole prompt chunk (including all its
yielded decode rounds and final MTP work), the ordinary following decode round/adaptation, and any
admission/reset work ahead of the next check. No finite cancellation deadline is claimed.

## Ownership and ordering

- `ConcurrentServe::run` extracts the original ready-decode block into `decode_ready`. The ordinary
  call passes no filter and no deferred-adaptation budget; its ordering, arithmetic calls, sampling,
  policy observations, adaptation condition and fairness rotation stay the same in source.
- At the start of an enabled prompt chunk, eligibility is frozen to other active slots already ready
  to decode. Finished slots drop out; no replacement is admitted. One round runs when the budget is
  due; fairness rotates after that round, then the service timer restarts after decode completes.
- `Prefill::run` retains its complete stack, session and shared arena. Its existing compute-stream
  synchronization immediately before host grouping is the service point. On actual service, both
  prompt compute and copy streams are checked/drained. At <=1024, the 2048-row whole-chunk issuer is
  disabled. The previous layer's local stager has exited and the current layer has not started grouping
  or staging. Decode does not access the prompt arena, ring events, GEMM or MMQ context.
- Layer fusion boundaries, residual rows, precomputed next-half normalization, routing order, GEMM
  shapes and expert products are unchanged. This does not use `set_stage`, which would change fusion.
- Prefill does not use the shared `ExpertDispatch`/`Drive` scratch. Normal verifier execution assigns
  `dispatch.plan`, waits for its compute/copy work, commits, and completes that slot's draft before the
  callback returns. The next round reassigns the plan. The shared CPU pool is not called by prefill.
  PLE scratch may be shared in the serial configuration, but its operation has finished at this barrier.
- On callback false/exception, the prompt returns an explicit error and ConcurrentServe exits; it does
  not publish partial prompt progress or resume that slot. A scope guard clears both callbacks on all
  exits, preventing dangling captures. Prompt streams have been drained before decode; existing verifier
  and Prefill destructors perform their normal stream cleanup. CUDA failure can still require process exit.

## Cache adaptation is intentionally deferred

During yielded decode, `dispatch.usage` accumulates as usual. When an adaptation deadline is reached,
the chunk budget records one pending adaptation without updating cache bytes, host_res, or hits.d_res.
Multiple deadlines coalesce. Only after `Prefill::run` returns (including copy completion and the on_chunk
MTP callback) does the server call the existing `adapt()` once, using then-current usage and residency.
There are no stored victim slots or blob pointers to replay after they become stale. The following normal
decode round can independently reach its own ordinary adaptation deadline.

This preserves memory safety, not the original adaptation history. Usage decay and swaps happen later
and can change subsequent CPU/GPU expert assignment. DraftPolicy also still uses measured round time.
Consequently same-shape prefill is not proof of token parity. The frozen base already differs between
unchanged process runs; diagnostic investigation and actual-f7462a0 qualification remain mandatory.

## Overhead and reporting

Disabled/default execution installs no callbacks and introduces no new CUDA barriers, clock reads,
snapshot allocations or service work on the decode path. It retains small null/flag checks and the
extracted helper, so zero runtime cost and bitwise token identity are not claimed. The Prefill object
layout changes; its allocation placement could affect the base's pointer-based batch ordering.

Enabled decode-only execution has no prompt callback work. Enabled prompt runs report a final stderr
line with `calls`, `decode_ms`, and `deferred_adaptations`. Existing prompt wall time and prefill timeline
statistics include service time; do not sum them with decode time as independent GPU totals. Use external
TTFT/workflow/gap metrics and the emitted token stream for qualification.

The existing smaller-chunk screen is diagnostic only: 1024 had TTFT 15.36s/workflow 34.50s, 512 had
24.38s/42.47s, and 256 had 41.36s/57.53s. The 256 setting does not meet TTFT<=2x or workflow<=1.1x
on that run, and token parity failed. Raw source: `exports/strata-responsiveness/screen-diagnostic-summary.json`
in the parent workspace. These are not measurements of this prototype.

## Build and verification handoff

No build or GPU/model test was run during implementation, per campaign ownership rules.
`git diff --check` passes. A normalized source comparison against f7462a0 confirmed the extracted decode
body is identical after removing the new eligibility/deferred-adaptation guards and mapping bool failures
back to the original integer returns. That is a source invariant, not execution evidence.

`tests/concurrency/test_prefill_yield.cpp` is a CPU-only budget/deferred-adaptation test with a simulated
three-decoder service schedule. It does not exercise CUDA, actual cancellation, arena aliasing or token
parity. It is registered as `strata-prefill-yield-test`; it remains unbuilt/unrun at handoff.

From a Windows shell, run `build-prefill-yield-local.cmd` in this worktree when the parent authorizes
the serialized build. It selects MSVC 14.32, CUDA 13.0, 120-real, native experts, portable Release,
the same GGML source as the trace build, and the separate `build-prefill-yield-cuda130` directory.
Then run `ctest --test-dir build-prefill-yield-cuda130 -R "strata-(batch-schedule|prefill-yield)-test" --output-on-failure`.

Parent-owned model sequence: disabled candidate vs actual frozen binary; candidate off/on at identical
1024 dimensions and adaptive settings; first differing IDs/reasons and finish behavior; responsiveness,
TTFT<=2x, workflow<=1.1x, decode-only>=0.97, and halving time in >250ms gaps; cancellation/reuse and
invalid-config checks. Inspect the service counters and final MTP tail before changing service interval.
Do not qualify or promote if any required gate fails.
