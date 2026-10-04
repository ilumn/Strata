# Concurrent CUDA layer splitting

This extension permits 1–4 independent text or image requests to use the existing CUDA
layer split over 2–8 distinct GPUs. The single-GPU path is retained. GPUs execute
successive layer ranges; each range batches the ready requests before dispatching
its experts. This is model layer parallelism, not replicated servers or tensor
parallelism. Additional cards provide weight/cache capacity; throughput gains
must be measured for the particular workload.

Each request owns a session, verifier, rollback state and portable residual
handoff on every stage. MTP and sampling execute on the final card with private
request state and shared immutable draft weights. The expert arena in system
RAM is shared. Cache adaptation is applied at completed scheduling boundaries
and residency tables are published on every device. Prompt work remains bounded
to one shared workspace per device. Prefill can yield to ready decoders after a
routing barrier has drained; the next layer stage receives only a completed
prompt chunk. Split prompt calls larger than that workspace cannot yield inside
the pipeline.

Build the modified engine first. Generate a separate server configuration:

```sh
python tools/configure_concurrency_candidate.py \
  --config strata-iq2_xs.json --exe engine/strata-multigpu \
  --output strata-c4-multigpu.json --gpus 0,1 \
  --context 131072 --reserve-mib 2560
python serve/server.py --engine strata --config strata-c4-multigpu.json
```

The config uses automatic layer placement, resident INT8 KV, four requests,
sixteen verification rows, MTP width four, prompt chunks of 1024 tokens, and a
100 ms prefill-yield interval. GPU list order selects the layer pipeline order.
The context limit includes input and generated tokens, **per request**. Raising
it increases allocated request state on every device and can reduce expert-cache
capacity. A 128K setting is not a claim of model accuracy at that length or a
promise that any GPU configuration can fit it. Allocation and reserve checks
fail explicitly when capacity is insufficient.

For a fixed split, each stage allocates attention caches and dense layer weights
only for its own layer range. Automatic placement retains full stage allocations
because its boundaries are chosen after cache sizing. To request unquantized
FP16 KV and compact fixed stages, use `--kv fp16 --layer-split 24` on the
configuration tool (the latter is a 24/24 split for this 48-layer model).
For example, `--context 262144 --gpus 0,1 --layer-split 24 --kv fp16`
requests four 262K slots. It still needs live capacity and performance validation.
The resident MTP ring uses the same KV precision, with its separately configured
window; it does not retain 262K draft tokens.

Concurrent images require a CPU `strata-vision` encoder in the source config and
explicit `--images` on the configuration tool. Include `--vision` in engine
arguments. Each request owns its embeddings and image-position table on each
stage. CUDA graphs record the request's table pointer, allowing different image
grids in the same target batch. Text requests reset their positions to the
ordinary one-dimensional progression when a slot is reused. CPU encoding can
operate while GPU generation runs; encoding is serialized by the encoder lock.
The native image command is `CGENI`, with an `image=` key containing the UTF-8
embedding-file path encoded as hexadecimal; text retains `CGEN`.

ROCm, GPU image encoding, streamed KV, control vectors, split-window verification and helper
expert caches remain unsupported in concurrent mode. The monitor retains its
existing hardware display; engine metrics include `gpus`, `concurrency` and
`context`, `kv`, `mtp_kv` and `vision`. Host `nvidia-smi` supplies the per-card memory measurements.

Run the focused Python and native scheduler/prefill-budget checks described in
[concurrency.md](concurrency.md). These checks do not establish GPU correctness.
Live qualification additionally requires health/model endpoints, generation,
four sustained SSE streams with actual four-member target batches, request-local
prompt isolation, cancellation and reuse, queued arrivals, and decoding while
long prompts are being read. Validate a prompt beyond the old context cap before
adopting a larger setting. Image qualification must recognize actual images,
mix different image grids with text, and exercise cancellation and slot reuse.
The image-file test and session-capacity test cover record validation and stage
sizing without GPU inference. Historical single-GPU token-parity and throughput
measurements apply only to the settings recorded in those studies.
