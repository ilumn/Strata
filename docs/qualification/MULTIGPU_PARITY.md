# Concurrent multi-GPU qualification

Qualified against official [Niko1221/Strata](https://github.com/Niko1221/Strata) v0.1.39, commit
`6f32ec070f23ced9f50e704d854d775da52591ab`, on 2026-10-05 UTC. Both branches start independently from that commit. Upstream already supplies
batch/multi-GPU and vision support; this proposal corrects and qualifies those implementations.

A fully resident stage on official v0.1.39 finishes its batch graph without ringing CPU doorbells. The
blocking and pipeline controllers nevertheless wait for them; a two-card run fails with `layer 24 never rang
(graph finished)`. The correction skips that per-layer wait for resident stages, releases the PLE upload
fence when applicable, and retains graph completion/error checks. Mixed CPU/GPU stages retain their handshake.

Slot arena ownership now includes device context, pinned QSA staging/backing and host descriptors. Trimming
slots returns their memory and restores a live rope-angle table. Verifier, MTP and prefill teardown runs on
the allocating device; prefill member owners are included. Logit diagnostics reject rows beyond the last window.

## Evidence

| Case | Paired steps | FP32 vocabulary values | Result |
| --- | ---: | ---: | --- |
| Four slots, one batch group; partial + fully resident split stages | 64 | 15,892,480 | bitwise exact |
| Four slots, two pipeline groups; partial + fully resident stages | 64 | 15,892,480 | bitwise exact |
| Four slots, two groups; both stages fully resident, trimmed weights | 64 | 15,892,480 | bitwise exact |
| Four slots, FP16 KV, allocated context 262,144 | 64 | 15,892,480 | bitwise exact |
| Portable published harness, four short requests of 32 steps, two groups | 128 | 31,784,960 | bitwise exact |

Clean production executables also matched all eight greedy/seeded text requests, 261 emitted tokens. The
device-session ownership regression passes on both cards and verifies VRAM return, pinned-memory release and
restoration of the caller's device. Two GPUs were available; four-GPU hardware was not qualified.

## Numerical controls and practical limits

Hardware: two RTX 5090 32 GiB cards, Ryzen 7900X, Linux, GCC 13, CUDA 13.0.88, SM120. Model:
`SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`, IQ3_XXS, vocabulary 248,320. Reference and candidate
use the same retained native GGUF, pack, PLE, MTP files and expert identities. Image fixtures are actual CPU
vision-encoder outputs from red-square 128x128 and blue-circle 256x128 PNGs, with 16 and 32 embedding rows.

Teacher forcing compares every FP32 vocabulary value at each request/step/position, not just generated tokens
or selected logits. The checker rejects nonfinite/truncated/differently covered evidence and distinguishes
signed zero. All passing comparisons have maximum absolute difference zero. Diagnostic hooks are confined to
an optional temporary overlay, restored before production tests and excluded from the production sources.

Exactness uses upstream's documented `STRATA_IQ_MT_MIN=1`, no PCIe CPU/GPU reassignment, a fixed expert tier,
no prompt borrowing and prompt cache disabled. Fixed profiles hold placement equal where slot memory could
change automatic cache sizing. Default CPU batch rounding, adaptive expert placement, and upstream's absence
of batch penalties remain upstream limitations; these results do not promise serial/batch equality outside
these controls. Sampling tests use no penalties and retain position-based seeded draws.

Text prompts cover 12, 63, 265 and 515 tokens; image prompts include different grids, mixed text, multiple
images and reuse. The 262K cases allocate that capacity with FP16 KV and use short inputs. They do not establish
full-262K prompt accuracy, quality or performance. This is numerical qualification, not an intelligence or UX
benchmark. Other models, quantizations, operating systems and GPU backends need separate qualification.

The focused tests above pass. The entire upstream test suite was not run; no full-suite success is claimed.
See [the reproducible procedure](../../tools/qualification/README.md) for the exact temporary overlay, paired
controller and strict saved-trace comparator. Ordinary production generation is checked separately.

## Combined integration check

The two independent branches merge cleanly. The merged implementation also matches the unchanged official
serial reference bit-for-bit for six mixed requests through four slots on two GPUs, including a fully
resident second stage: 96 paired steps, 23,838,720 FP32 vocabulary values, maximum absolute difference zero.
This check uses the same exactness controls and short-input limits stated above.

The arena-release test measures free VRAM after pinned registration and requires recovery of at least
28 MiB from a 32 MiB arena, allowing 4 MiB for desktop activity. It separately verifies release of all
pinned blocks and restoration of the calling device. Five consecutive final runs pass.
