# Build and try the c=4 candidate on another Windows PC

This branch is experimental. The tested machine had a single RTX 5090, a Ryzen
9950X3D, 48 GiB RAM, and Swift 1.5 IQ2_XS. The measured setup used four text
requests, a 98304-token context per request, a 2560 MiB VRAM reserve and 11022
resident expert slots. [Results](campaign-v2-results.md) and
[limitations](local-candidate.md) describe the evidence. The independent model
quality benchmark has not been run.

The source and setup helper are in this branch. The tested Windows executable,
model weights, machine-specific config and launch files are **not** in GitHub.
An ordinary `START-HERE.bat` install downloads the upstream release executable;
building the source branch is required to use this candidate.

1. On Windows with one NVIDIA GPU, clone this branch and run `START-HERE.bat` to
   install a compatible text model, pack, profile and MTP layer. Keep the
   generated `strata-*.json` file. This candidate does not support c=4 vision,
   AMD/ROCm, multi-GPU or KV streaming. Check that the model's expert arena fits
   system RAM with headroom for Windows and other applications.
2. Install Visual Studio 2022 C++ build tools, CMake and CUDA 13.0. From a
   Developer PowerShell in the checkout, build this branch's engine (replace
   `120-real` with the CUDA architecture of the target GPU):

   ```powershell
   cmake -S . -B build-candidate -G "Visual Studio 17 2022" -A x64 -DSTRATA_ENABLE_CUDA=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PORTABLE=ON -DSTRATA_BUILD_TESTS=OFF -DCMAKE_CUDA_ARCHITECTURES=120-real
   cmake --build build-candidate --config Release --target strata
   ```

3. Create a separate c=4 config. Substitute your generated model config name:

   ```powershell
   .\.venv\Scripts\python.exe tools\configure_concurrency_candidate.py --config .\strata-your-model.json --exe .\build-candidate\Release\strata.exe
   ```

   This defaults to 32768 context tokens per request, a 2560 MiB VRAM reserve,
   and automatic expert-cache sizing. Start smaller than the tested 98304
   context if the GPU has less VRAM. On a similar RTX 5090 setup, add
   `--context 98304 --expert-cache 10500` to reproduce the tested cache request.
   The helper refuses configurations with vision, KV streaming or multi-GPU;
   it never changes the normal setup config.
4. Start the separate server from the checkout:

   ```powershell
   .\.venv\Scripts\python.exe serve\server.py --engine strata --config .\strata-c4-candidate.json
   ```

   Connect an OpenAI chat-completions client to `http://127.0.0.1:8080/v1` and
   select the model ID printed by the helper. Stop with Ctrl+C. The monitor is
   at `http://127.0.0.1:8080/#monitor` for this direct-server setup.

The performance figures from the RTX 5090 do not predict results on another
GPU. Startup, cache residency and long-context stability should be measured
on that machine before reducing the VRAM reserve.
