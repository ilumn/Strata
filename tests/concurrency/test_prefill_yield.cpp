#include "strata/program/prefill_yield.hpp"
#include "strata/program/batch_schedule.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <iostream>

using strata::program::PrefillYieldBudget;

int main() {
    PrefillYieldBudget budget(100);
    assert(!budget.due(0, true));
    assert(!budget.due(99.9, true));
    assert(budget.due(100, true));
    assert(!budget.due(1000, false));
    // A 70ms decode round restarts the prompt-work budget at its completion, not its start.
    budget.serviced(170);
    assert(!budget.due(269.9, true));
    assert(budget.due(270, true));
    assert(!budget.take_adaptation());
    budget.defer_adaptation();
    budget.defer_adaptation();
    budget.serviced(300);
    assert(budget.take_adaptation());  // Multiple deadlines coalesce and survive service completion.
    assert(!budget.take_adaptation());

    // Simulate barrier arrivals with three existing decoders and a one-row depth budget.
    // Every eligible decoder progresses; the fourth (the suspended prompt) receives no rows.
    PrefillYieldBudget service(100);
    int generated[4]{};
    int rounds = 0;
    for (int barrier = 1; barrier <= 40; ++barrier) {
        const double now = barrier * 20.0;
        if (!service.due(now, true)) continue;
        const auto rows = strata::program::schedule_rows({1, 1, 1}, 1, true);
        for (int i = 0; i < 3; ++i) generated[(rounds + i) % 3] += rows[i];
        ++rounds;
        if (rounds % 2 == 0) service.defer_adaptation();
        service.serviced(now + 30);  // Decode itself is not charged as prompt work.
    }
    assert(rounds == 6);
    assert(generated[0] == 2 && generated[1] == 2 && generated[2] == 2 && generated[3] == 0);
    assert(service.take_adaptation());
    assert(!service.take_adaptation());
    PrefillYieldBudget next_chunk(100);
    assert(!next_chunk.due(99, true));
    assert(!next_chunk.take_adaptation());
    std::cout << "prefill yield budget and simulated service checks passed\n";
}
