@echo off
setlocal
cd /d "%~dp0"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" -vcvars_ver=14.32
if errorlevel 1 exit /b %errorlevel%
cmake -S . -B build-prefill-yield-cuda130 -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_COMPILER="%~dp0../toolchains/cuda-13.0/bin/nvcc.exe" -DCUDAToolkit_ROOT="%~dp0../toolchains/cuda-13.0" -DCMAKE_CUDA_ARCHITECTURES=120-real -DSTRATA_ENABLE_CUDA=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PORTABLE=ON -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_CONCURRENCY_TESTS=ON -DSTRATA_PREFILL_MMQ=OFF -DSTRATA_GGML_DIR="%~dp0../Strata-concurrency/build-concurrency/_deps/strata_llamacpp-src"
if errorlevel 1 exit /b %errorlevel%
cmake --build build-prefill-yield-cuda130 --target strata strata-batch-schedule-test strata-prefill-yield-test --parallel 1
exit /b %errorlevel%
