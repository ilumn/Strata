#include "strata/core/session_owner.hpp"
#include <memory>
#include <cstdio>

int main() {
    int count = 0;
    if (cudaGetDeviceCount(&count) != cudaSuccess || count < 2) return 77;
    // Warm both contexts before measuring free VRAM.
    for (int d = 0; d < 2; ++d) { cudaSetDevice(d); cudaFree(nullptr); }
    for (int owner = 0; owner < 2; ++owner) {
        cudaSetDevice(owner);
        size_t allocated = 0, total = 0, after = 0;
        void* arena = nullptr;
        if (cudaMalloc(&arena, 32u << 20) != cudaSuccess) return 1;
        using Owned = std::unique_ptr<strata::core::SessionState, strata::core::DeviceSessionDeleter>;
        Owned session(new strata::core::SessionState, {owner, arena});
        session->qsa_states = new strata::core::QsaState[1]();
        session->qsa_alloc = 1;
        auto& qsa = session->qsa_states[0];
        if (cudaMallocHost((void**) &qsa.host_step, 4096) != cudaSuccess ||
            cudaMallocHost((void**) &qsa.host_pos, 4096) != cudaSuccess ||
            cudaMallocHost(&qsa.kv_host_arena, 4096) != cudaSuccess) return 1;
        void* pinned[] = {qsa.host_step, qsa.host_pos, qsa.kv_host_arena};
        // Measure after pinned registration: its CUDA bookkeeping is not part of the arena.
        if (cudaMemGetInfo(&allocated, &total) != cudaSuccess) return 1;
        cudaSetDevice(1 - owner);
        session.reset();
        int current = -1;
        if (cudaGetDevice(&current) != cudaSuccess || current != 1 - owner) return 2;
        for (void* p : pinned) {
            unsigned flags = 0;
            if (cudaHostGetFlags(&flags, p) == cudaSuccess) return 4;
            cudaGetLastError();
        }
        cudaSetDevice(owner);
        if (cudaDeviceSynchronize() != cudaSuccess || cudaMemGetInfo(&after, &total) != cudaSuccess || after < allocated || after - allocated < (28u << 20)) {
            // Allow 4 MiB for desktop activity while still detecting a leaked 32 MiB arena.
            std::fprintf(stderr, "CUDA%d slot arena was not returned (allocated=%zu, released=%zu)\n",
                         owner, allocated, after);
            return 3;
        }
    }
    return 0;
}
