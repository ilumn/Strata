// src/spec/draft_policy_test.cpp - DraftPolicy: when does a lookup window beat the MTP's?
//
// Simulated rounds with the costs measured on the RTX 5070 (window-cost: ~10 ms more per token) check that
//   1. with no lookup proposal the MTP window is kept;
//   2. lookup drafts that are mostly rejected stop being taken (their bucket's rate falls);
//   3. lookup drafts that are always accepted are taken, and the window grows with them;
//   4. match-length buckets learn separately (short matches failing does not stop long ones);
//   5. the policy never proposes a window beyond its cap.
#include "strata/spec/draft_policy.hpp"

#include <cstdio>

using strata::spec::DraftPolicy;

namespace {
int g_fail = 0;
void check(bool ok, const char* what) {
    std::printf("  %-66s %s\n", what, ok ? "ok" : "FAIL");
    if (!ok) ++g_fail;
}
double cost(int t) { return 19.0 + 10.5 * (t - 1); }   // ms per round, measured shape
}  // namespace

int main() {
    std::printf("draft_policy_test\n");
    {
        DraftPolicy p(6);
        for (int i = 0; i < 50; ++i) p.observe(false, 4, 2, 0, cost(4));   // MTP windows of 4: 3 tokens each
        const DraftPolicy::Pick k = p.choose(4, 0, 0);
        check(!k.lookup && k.t == 4, "no proposal: the MTP window");
    }
    {
        DraftPolicy p(6);
        for (int i = 0; i < 50; ++i) p.observe(false, 4, 2, 0, cost(4));
        for (int t = 2; t <= 6; ++t) p.observe(false, t, 0, 0, cost(t));
        for (int i = 0; i < 40; ++i) p.observe(true, 6, 0, 4, cost(6));      // short matches, all rejected
        check(p.lookup_rate(4) < 0.15, "rejected short-match drafts: their rate falls below 0.15");
        check(!p.choose(4, 5, 4).lookup, "rejected short-match drafts: no longer taken");
        for (int i = 0; i < 40; ++i) p.observe(true, 6, 5, 30, cost(6));     // long matches, all accepted
        check(p.lookup_rate(30) > 0.9, "accepted long-match drafts: their rate rises above 0.9");
        const DraftPolicy::Pick k = p.choose(4, 5, 30);
        check(k.lookup && k.t == 6, "accepted long matches: the full lookup window is taken");
        check(!p.choose(4, 5, 4).lookup, "buckets are separate: short matches still not taken");
        check(p.choose(4, 20, 30).t <= 6, "never beyond the window cap");
    }
    {
        DraftPolicy p(8);
        for (int i = 0; i < 50; ++i) p.observe(false, 3, 2, 0, cost(3));      // a very good MTP: 3 of 3 tokens
        for (int t = 2; t <= 8; ++t) p.observe(false, t, t - 1, 0, cost(t));
        for (int i = 0; i < 40; ++i) p.observe(true, 4, 2, 8, cost(4));       // lookup at q ~ 0.67
        check(!p.choose(3, 7, 8).lookup, "a mediocre lookup does not replace a strong MTP window");
    }
    {
        DraftPolicy p(6);
        for (int i = 0; i < 50; ++i) p.observe(false, 4, 3, 0, cost(4));      // a near-perfect MTP, only size 4 seen
        const DraftPolicy::Pick k = p.choose(4, 5, 40);
        check(k.lookup && k.t == 6, "an unmeasured size is probed for a confident lookup");
        for (int i = 0; i < 3; ++i) p.observe(true, 6, 5, 40, 3.0 * cost(6));   // it turns out very expensive
        check(!p.choose(4, 5, 40).lookup, "after the probes, the measured cost decides");
    }
    {
        DraftPolicy slow(8, 0.03, DraftPolicy::CostMode::FixedShape);
        DraftPolicy fast(8, 0.03, DraftPolicy::CostMode::FixedShape);
        bool same = true, used_lookup = false, used_mtp = false;
        // Identical observed tokens with timing spikes, order-dependent serial
        // costs and invalid/unavailable timing. Future choices must stay equal.
        for (int i = 0; i < 4000; ++i) {
            const int t = 2 + i % 7, accepted = (i / 7) % t;
            const bool lookup = i % 3 != 0;
            const int match = 4 + i % 40;
            slow.observe(lookup, t, accepted, match, i % 9 ? 500.0 * t : -1.0);
            fast.observe(lookup, t, accepted, match, i % 11 ? 0.01 * (9 - t) : 0.0);
            for (int n = 2; n <= 8; ++n) {
                const auto a = slow.choose(n, 7, match), b = fast.choose(n, 7, match);
                same = same && a.lookup == b.lookup && a.t == b.t;
                used_lookup = used_lookup || a.lookup;
                used_mtp = used_mtp || !a.lookup;
            }
        }
        check(same, "fixed costs: timing cannot change learned policy decisions");
        check(used_lookup && used_mtp, "fixed costs retain both lookup and MTP choices");
    }
    {
        DraftPolicy p(8, 0.03, DraftPolicy::CostMode::FixedShape);
        for (int i = 0; i < 40; ++i) p.observe(false, 4, 3, 0, 0);
        check(p.choose(4, 7, 40).lookup, "fixed costs: unseen confident long window is probed");
        for (int i = 0; i < 3; ++i) p.observe(true, 8, 0, 40, 0);
        check(!p.choose(4, 7, 40).lookup, "fixed costs: finite probes and rejection learning retained");
        for (int i = 0; i < 50; ++i) p.observe(true, 8, 7, 40, 0);
        const auto pick = p.choose(2, 7, 40);
        check(pick.lookup && pick.t > 2, "fixed costs: accepted long lookup remains enabled");
    }
    std::printf(g_fail ? "FAIL\n" : "PASS\n");
    return g_fail ? 1 : 0;
}
