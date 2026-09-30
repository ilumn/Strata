#pragma once

namespace strata::program {

// CPU-only service budget for one suspended prompt chunk. Times are monotonic milliseconds.
// The caller owns the frozen set of eligible decoders and all GPU/arena lifetime rules.
class PrefillYieldBudget {
public:
    explicit PrefillYieldBudget(double interval_ms) : interval_ms_(interval_ms) {}
    bool due(double now_ms, bool ready) const { return ready && now_ms - last_service_ms_ >= interval_ms_; }
    void serviced(double now_ms) { last_service_ms_ = now_ms; }
    void defer_adaptation() { adaptation_pending_ = true; }
    bool take_adaptation() {
        const bool pending = adaptation_pending_;
        adaptation_pending_ = false;
        return pending;
    }
private:
    double interval_ms_;
    double last_service_ms_ = 0;
    bool adaptation_pending_ = false;
};

}  // namespace strata::program
