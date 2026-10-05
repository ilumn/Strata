#pragma once

#include "strata/core/on_device.hpp"
#include "strata/core/session.hpp"

namespace strata::core {

/// A carved session borrows its arena. Keep ownership with the allocating stage so trimming
/// batch slots after another stage runs out of memory actually returns the earlier stage's VRAM.
struct DeviceSessionDeleter {
    int device = -1;
    void* arena = nullptr;
    void operator()(SessionState* session) const {
        if (session == nullptr) return;
        const OnDevice on_device(device);
        session_release(*session);
        for (int64_t i = 0; session->qsa_states && i < session->qsa_alloc; ++i)
            qsa_state_release_host(session->qsa_states[session->qsa_ord0 + i]);
        delete[] session->qsa_states;
        if (arena != nullptr) cudaFree(arena);
        delete session;
    }
};

}  // namespace strata::core
