# Local concurrency candidate

The package passed the controlled suites, repeated performance gates,
cancellation/reuse checks and HTTP streaming checks. The daily installation is
not replaced. The saved local branch is `candidate/concurrency-smoothness-v2`.

From `C:\Users\niran\Documents\Code Projects\LocalLLMs`:

- `Start Strata Candidate.cmd` starts the separate preset router.
- `Stop Strata Candidate.cmd` stops that router and its model processes.
- Existing `Start Strata.cmd` / `Stop Strata.cmd` remain the daily-build launchers.

Use one launcher at a time. The candidate refuses to start while another Strata
engine or either required listening port is occupied. The API remains
`http://127.0.0.1:8080/v1`; select the existing `swift-1.5-iq2_xs-c4` model in DSH.
Other presets still point to their existing daily configurations. The model loads
on the first request. The monitor is on the loaded backend port reported by
`http://127.0.0.1:8080/router/status`, followed by `/#monitor`.

The c4 candidate combines two independently promising mechanisms:

- MTP drafts from independent requests overlap on their CUDA streams.
- Prefill yields at safe routing barriers, targeting 100 ms of prompt work between
  opportunities to advance already-running decoders.

It keeps the original `--spec 4 --batch-rows 16`, measured draft-cost policy,
optimized CPU kernels and adaptive expert caching. The proposed depth2/rows8
combination remains experimental because its numerical screening was less clean.

Configuration: vision off, context 98304 per request, KV int8, 2560 MiB reserve,
prefill chunks 1024, 15 pool workers. A fixed cache request 10500 yields 11022 actual
resident slots on this pack. This matches qualification and leaves more graph-growth
room than the larger cache configuration that hit the reserve guard. No GPU clock,
voltage, power-limit or system settings are changed.

This scheduling policy protects ongoing streams while another request prefills;
the incoming request can take longer to start. It does not remove model-load or
preset-switch delays. Performance evidence uses fresh paired runs with equal cache
capacity and excludes model loading. See `campaign-v2-results.md` for the results.

Correctness is scoped: controlled exact-token suites and long generation
passed, but normal fast execution is not universally token-repeatable even in
BASE. One essay numerical comparison crossed the 1% average-TV investigation trigger
(1.0404%, versus 0.9017% against the second reference); the finding is preserved.
The small sampled-logit tests do not establish general model quality. A compatible,
trusted independent llama.cpp reference was unavailable for this qwen4exp model.

The package contains a frozen tested executable, c4/router configurations and a
manifest. The launcher verifies the executable SHA256 before starting. Source and
validation scripts remain in this worktree; raw reports remain under
`exports/strata-campaign-v2` in the workspace.
