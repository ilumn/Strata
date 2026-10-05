# Serial / batch numerical qualification

This is an optional diagnostic procedure, not an inference mode. It compares **every FP32 vocabulary entry**
for matched request, token step and position. The overlay forces one target token per window and feeds back a
fixed continuation. It changes no numerical kernel. It must be applied to both reference and candidate sources;
never use these executables for normal serving or performance measurements.

Use two disposable, already-configured source/build trees: the unchanged upstream commit and the candidate.
The overlay targets the v0.1.39 serve loop. Keep the generated backup directories until both sources have been
restored and production executables rebuilt. An interrupted run can be recovered with `--restore`.

```sh
python tools/qualification/instrument.py /path/to/reference --backup /tmp/reference-backup
python tools/qualification/instrument.py /path/to/candidate --backup /tmp/candidate-backup
cmake --build /path/to/reference/build --target strata
cmake --build /path/to/candidate/build --target strata
python tools/qualification/paired.py \
  --reference-exe /path/to/reference/build/strata \
  --candidate-exe /path/to/candidate/build/strata \
  --args /path/to/args.json --requests /path/to/requests.json \
  --output /path/to/new-result-directory --batch 4 --groups 1
python tools/qualification/instrument.py /path/to/reference --backup /tmp/reference-backup --restore
python tools/qualification/instrument.py /path/to/candidate --backup /tmp/candidate-backup --restore
cmake --build /path/to/reference/build --target strata
cmake --build /path/to/candidate/build --target strata
```

`args.json` is a JSON list of ordinary engine arguments, including `--serve`, model/native/PLE paths, MTP,
context/KV and expert-profile/cache settings. Omit batch options: the driver adds them only for the candidate.
For controlled exactness, use `--pcie-frac 0 --adapt-every 1000000 --no-prefill-borrow --prompt-cache 0` and
**the same resident expert identities on each GPU**. Set loader library paths and `CUDA_VISIBLE_DEVICES` in
the shell. The driver sets `STRATA_IQ_MT_MIN=1` for both processes, as upstream's exactness qualification does.
If automatic cache sizing places different experts on CPU versus GPU, first fix cache placement; that changes
arithmetic independently of these PRs. The tool reports no tolerance-based success.

`requests.json` contains raw token IDs. For example:

```json
[
  {"tokens": [198, 40, 1077, 220, 17, 198], "max_new": 32},
  {"tokens": [198, 40, 1077, 220, 18, 198], "max_new": 32},
  {"tokens": [198, 40, 1077, 220, 19, 198], "max_new": 32},
  {"tokens": [198, 40, 1077, 220, 20, 198], "max_new": 32}
]
```

For image requests, add `"image": "/absolute/path/to/encoded.sve"`, include the corresponding image-pad spans
in the tokens, and enable `--vision` in the argument list. Use different grids, mixed text/image requests,
multiple images in one prompt and more requests than slots to exercise reuse. Supply your own encoder output;
this tool neither downloads models nor manufactures substitute embeddings.

Results retain commands, stdout/stderr, generated tokens, complete binary logits and `comparison.json`.
Empty, truncated, duplicate, nonfinite or differently covered traces fail. Byte comparison distinguishes
signed zero as well as ordinary FP32 differences. Run `compare.py reference.bin candidate.bin` to regrade
saved traces without any additional generation.

Keep ordinary greedy/seeded generation, cancellations, malformed requests and performance tests separate.
Teacher forcing proves the tested target numerics, not speculative policy or normal sampling equivalence.
Allocating a large context while testing short prompts does not qualify full-context quality. CUDA/Linux,
other backends and different models each require their own qualification.
